# Task 6 Implementation Guide: Safe Educational Fallback & Workflow Engine

> **Document Status:** Complete & Verified  
> **Target Audience:** Implementer / Client / Coding Agent  
> **Estimated Time to Complete:** 15–20 minutes  
> **Prerequisites:** Tasks 1 through 5 completed (Domain models, benchmarks, repository, intake service, planning agent, and HHH evaluator agent available).

---

## Table of Contents
1. [Overview & User Story](#1-overview--user-story)
2. [The "WHY": The Kitchen Loop & Safety Net](#2-the-why-the-kitchen-loop--safety-net)
3. [The "HOW": The Retry State Machine Architecture](#3-the-how-the-retry-state-machine-architecture)
4. [Step-by-Step Technical Implementation (TDD)](#4-step-by-step-technical-implementation-tdd)
   - [Step 1: Write the Failing Test (`tests/services/test_workflow_engine.py`)](#step-1-write-the-failing-test)
   - [Step 2: Implement the Safe Fallback (`app/services/safe_fallback.py`)](#step-2-implement-the-safe-fallback)
   - [Step 3: Implement the Workflow Engine (`app/services/workflow_engine.py`)](#step-3-implement-the-workflow-engine)
   - [Step 4: Run the Test Suite to Verify](#step-4-run-the-test-suite-to-verify)
5. [Common Pitfalls & Zero-Question FAQ](#5-common-pitfalls--zero-question-faq)
6. [Git Commit, Push & Trello Progression](#6-git-commit-push--trello-progression)

---

## 1. Overview & User Story

### User Story
> **As an** orchestration coordinator,  
> **I want** a Workflow Engine that coordinates the Plan $\rightarrow$ HHH Evaluation loop with up to 2 automated revision retries (incorporating critique),  
> **So that** borderline plans are automatically improved, and unresolvable or dangerous plans are safely replaced with a standardized conservative educational fallback.

### Deliverables
* `app/services/safe_fallback.py`:
  * `get_safe_fallback_plan(profile)`: Generates a non-prescriptive, foundational educational plan with 3 standard financial hygiene actions.
* `app/services/workflow_engine.py`:
  * `WorkflowResult`: Pydantic model wrapping the persisted plan, status (`active` vs `fallback`), actions, and evaluation history.
  * `WorkflowEngine`: State machine coordinating intake, candidate generation, HHH evaluation, critique injection, retries, and persistence.
* `tests/services/test_workflow_engine.py`: Pytest suite verifying immediate pass, revision pass, exhausted retries, and immediate critical failure bypass.

---

## 2. The "WHY": The Kitchen Loop & Safety Net

In Tasks 3, 4, and 5:
* Task 3 gave us the **Prep Cook (`IntakeService`)**.
* Task 4 gave us the **Head Chef (`PlanningAgent`)**.
* Task 5 gave us the **Food Critic (`HHHEvaluatorAgent`)**.

Now, how do they work together?

Without an **Orchestration Workflow Engine**, they don't!
* The Chef would cook a meal, but wouldn't know where to send it.
* If the Critic rejected a dish, the kitchen would crash or serve bad food anyway.

### The Workflow Engine is the Restaurant General Manager:
1. **Coordinates the Hand-off:** Gathers ingredients from the Prep Cook and hands them to the Chef.
2. **Takes the dish to the Critic:** Runs HHH Evaluation.
3. **Manages Revisions (Max 2 Retries):**
   * If the Critic says: *"Score 2/4 on Helpful: You didn't allocate specific dollar amounts,"* the Manager takes that exact critique back to the Chef: *"Chef, fix the dollar amounts."*
   * The Chef cooks Revision 1 $\rightarrow$ The Critic inspects again.
4. **The Safety Net (Safe Educational Fallback):**
   * What if the Chef fails 3 times in a row? Or recommends something recklessly dangerous (like speculative options for a retiree)?
   * The General Manager **stops the chef immediately**. We do NOT serve bad food.
   * Instead, we hand the customer a **Standard Educational Guide** (Cash flow audit, 3-month emergency fund, high-interest debt inventory) with an honest disclaimer: *"We could not safely tailor specific recommendations with your current inputs."*

---

## 3. The "HOW": The Retry State Machine Architecture

```text
                  [User requests plan generation]
                               │
                               ▼
                   Fetch IntakeContext (Profile + 30d Feedback)
                               │
                               ▼
                  ┌──► [Attempt Iteration i (0, 1, 2)]
                  │            │
                  │            ▼
                  │    Planner Generates Candidate Plan
                  │            │
                  │            ▼
                  │    HHH Evaluator Grades Plan
                  │            │
                  │    ┌───────┴───────┐
                  │    │               │
                  │  PASS             FAIL
                  │    │               │
                  │    ▼               ├─────────────────────────┐
                  │  Save Plan         │                         │
                  │  (status='active') │ If critical_issue=True  │ If normal failure &
                  │    │               │ OR iterations >= 2      │ iterations < 2
                  │    ▼               │                         │
                  │  Record Evals      ▼                         ▼
                  │    │           Load Safe Fallback        Pass Critique to
                  │    ▼           (status='fallback')       Next Attempt (i+1)
                  │  Return            │                         │
                  │  Active Plan       ▼                         └─────────┘
                  │                Save Fallback Plan
                  │                & Record Evals
                  │                    │
                  │                    ▼
                  │                Return Fallback Plan
                  ▼                    ▼
               [Customer Receives Safe, Vetted Plan]
```

---

## 4. Step-by-Step Technical Implementation (TDD)

---

### Step 1: Write the Failing Test

Create file: `tests/services/test_workflow_engine.py`

```python
"""
Unit tests for the WorkflowEngine state machine and safe fallback.
Tests immediate pass, revision retry success, exhausted retries to fallback, and immediate critical issue bypass.
"""
import pytest
from uuid import UUID

from app.domain.models import (
    UserProfile,
    RiskAppetite,
    PlanStatus,
    ActionCategory,
    ActionStatus,
    FinancialPlanPayload,
    PlanAction,
)
from app.domain.benchmarks import CURATED_MARKET_BENCHMARKS
from app.infrastructure.repository import InMemoryFinanceRepository
from app.infrastructure.llm_client import MockLLMClient
from app.services.intake_service import IntakeService
from app.agents.planning_agent import PlanningAgent
from app.agents.hhh_evaluator_agent import HHHEvaluatorAgent
from app.services.workflow_engine import WorkflowEngine, WorkflowResult


@pytest.fixture
def repo():
    return InMemoryFinanceRepository()


@pytest.fixture
def sample_profile():
    return UserProfile(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        age=28,
        annual_income=75000.0,
        monthly_expenses=4000.0,
        savings=20000.0,
        investments=15000.0,
        debt=10000.0,
        risk_appetite=RiskAppetite.AGGRESSIVE,
        investment_horizon_years=32,
        retirement_age_target=60,
        primary_goal="Wealth building",
        monthly_investment_capacity=1000.0,
    )


@pytest.fixture
def candidate_plan_dict():
    return {
        "health_summary": "Aggressive wealth compounding plan.",
        "actions": [
            {
                "id": "act_1",
                "category": "emergency_fund",
                "title": "HYSA Buffer",
                "recommendation": "Save $500/mo into 4.5% HYSA.",
                "rationale": "Liquidity buffer",
                "assumptions": "4.5% APY",
                "effort": "low",
                "status": "pending",
            },
            {
                "id": "act_2",
                "category": "debt_management",
                "title": "Student Debt Acceleration",
                "recommendation": "Pay $300/mo extra on loan.",
                "rationale": "Clear debt",
                "assumptions": "4.5% rate",
                "effort": "medium",
                "status": "pending",
            },
            {
                "id": "act_3",
                "category": "investment",
                "title": "Equity Indexing",
                "recommendation": "Invest $200/mo in market index.",
                "rationale": "7.5% long term return",
                "assumptions": "7.5% return",
                "effort": "medium",
                "status": "pending",
            },
        ],
    }


class SequentialMockLLMClient:
    """Mock LLM client returning a sequence of responses across multiple calls."""

    def __init__(self, responses: list):
        self.responses = list(responses)
        self.call_count = 0

    async def generate_json(self, system_prompt: str, user_prompt: str):
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return self.responses[-1]


class TestWorkflowEngine:
    @pytest.mark.asyncio
    async def test_workflow_immediate_pass(self, repo, sample_profile, candidate_plan_dict):
        await repo.save_profile(sample_profile)
        intake_svc = IntakeService(repo)

        # Call 1: Planner returns candidate plan
        # Call 2: Evaluator returns passing scorecard (all 4s)
        pass_eval = {
            "helpful_score": 4,
            "honest_score": 4,
            "harmless_score": 4,
            "passed": True,
            "critical_issue": False,
            "critique": None,
        }
        mock_llm = SequentialMockLLMClient([candidate_plan_dict, pass_eval])
        planner = PlanningAgent(mock_llm, CURATED_MARKET_BENCHMARKS)
        evaluator = HHHEvaluatorAgent(mock_llm)

        engine = WorkflowEngine(intake_svc, planner, evaluator, repo)
        result = await engine.run(sample_profile.user_id)

        assert isinstance(result, WorkflowResult)
        assert result.status == PlanStatus.ACTIVE
        assert len(result.actions) == 3
        assert len(result.evaluations) == 1
        assert result.evaluations[0]["passed"] is True

    @pytest.mark.asyncio
    async def test_workflow_retry_pass(self, repo, sample_profile, candidate_plan_dict):
        await repo.save_profile(sample_profile)
        intake_svc = IntakeService(repo)

        # Call 1: Plan Attempt 0
        # Call 2: Eval 0 fails (Helpful=2)
        # Call 3: Plan Attempt 1 (revised with critique)
        # Call 4: Eval 1 passes
        fail_eval = {
            "helpful_score": 2,
            "honest_score": 4,
            "harmless_score": 4,
            "passed": False,
            "critical_issue": False,
            "critique": "Lacks specific dollar amounts.",
        }
        pass_eval = {
            "helpful_score": 4,
            "honest_score": 4,
            "harmless_score": 4,
            "passed": True,
            "critical_issue": False,
            "critique": None,
        }
        mock_llm = SequentialMockLLMClient([candidate_plan_dict, fail_eval, candidate_plan_dict, pass_eval])
        planner = PlanningAgent(mock_llm, CURATED_MARKET_BENCHMARKS)
        evaluator = HHHEvaluatorAgent(mock_llm)

        engine = WorkflowEngine(intake_svc, planner, evaluator, repo)
        result = await engine.run(sample_profile.user_id)

        assert result.status == PlanStatus.ACTIVE
        assert len(result.evaluations) == 2
        assert result.evaluations[0]["passed"] is False
        assert result.evaluations[1]["passed"] is True

    @pytest.mark.asyncio
    async def test_workflow_exhausted_retries_triggers_fallback(self, repo, sample_profile, candidate_plan_dict):
        await repo.save_profile(sample_profile)
        intake_svc = IntakeService(repo)

        # 3 failed attempts (attempts 0, 1, 2 all fail evaluation)
        fail_eval = {
            "helpful_score": 2,
            "honest_score": 4,
            "harmless_score": 4,
            "passed": False,
            "critical_issue": False,
            "critique": "Still too generic.",
        }
        responses = [
            candidate_plan_dict, fail_eval,  # Attempt 0
            candidate_plan_dict, fail_eval,  # Attempt 1
            candidate_plan_dict, fail_eval,  # Attempt 2
        ]
        mock_llm = SequentialMockLLMClient(responses)
        planner = PlanningAgent(mock_llm, CURATED_MARKET_BENCHMARKS)
        evaluator = HHHEvaluatorAgent(mock_llm)

        engine = WorkflowEngine(intake_svc, planner, evaluator, repo)
        result = await engine.run(sample_profile.user_id)

        assert result.status == PlanStatus.FALLBACK
        assert "unable to tailor specific" in result.health_summary.lower()
        assert len(result.actions) == 3
        assert result.actions[0].id == "act_fallback_1"
        assert len(result.evaluations) == 3

    @pytest.mark.asyncio
    async def test_workflow_critical_harmless_triggers_immediate_fallback(self, repo, sample_profile, candidate_plan_dict):
        await repo.save_profile(sample_profile)
        intake_svc = IntakeService(repo)

        # Critical harmless failure on attempt 0
        critical_eval = {
            "helpful_score": 4,
            "honest_score": 4,
            "harmless_score": 1,
            "passed": False,
            "critical_issue": True,
            "critique": "Reckless trade detected.",
        }
        mock_llm = SequentialMockLLMClient([candidate_plan_dict, critical_eval])
        planner = PlanningAgent(mock_llm, CURATED_MARKET_BENCHMARKS)
        evaluator = HHHEvaluatorAgent(mock_llm)

        engine = WorkflowEngine(intake_svc, planner, evaluator, repo)
        result = await engine.run(sample_profile.user_id)

        # Must immediately trigger fallback without retrying
        assert result.status == PlanStatus.FALLBACK
        assert len(result.evaluations) == 1
        assert result.evaluations[0]["critical_issue"] is True
```

#### Run the test to confirm it fails:
```bash
pytest tests/services/test_workflow_engine.py
```
*Expected Output:* `ModuleNotFoundError: No module named 'app.services.safe_fallback'` (Fails as expected).

---

### Step 2: Implement the Safe Fallback

Create file: `app/services/safe_fallback.py`

```python
from app.domain.models import (
    FinancialPlanPayload,
    PlanAction,
    ActionCategory,
    ActionStatus,
    UserProfile,
)


def get_safe_fallback_plan(profile: UserProfile) -> FinancialPlanPayload:
    """
    Returns a standardized conservative educational baseline plan when
    AI plan attempts fail HHH criteria or encounter critical safety violations.
    """
    return FinancialPlanPayload(
        health_summary=(
            "We were unable to tailor specific investment or allocation recommendations safely "
            "based on the current inputs. Here is a conservative, educational baseline guide to establish financial health."
        ),
        actions=[
            PlanAction(
                id="act_fallback_1",
                category=ActionCategory.BUDGETING,
                title="Cash Flow Audit & Discretionary Expense Tracking",
                recommendation="Audit all monthly expenditures for 30 days to establish clear net disposable cash flow before committing capital.",
                rationale="Ensures living expenses are fully quantified and avoids cash flow deficits.",
                assumptions="Assumes manual or bank statement review of past 30-90 days.",
                effort="low",
                status=ActionStatus.PENDING,
            ),
            PlanAction(
                id="act_fallback_2",
                category=ActionCategory.EMERGENCY_FUND,
                title="Establish 3-Month Baseline Emergency Reserve",
                recommendation="Accumulate 3 months of essential living expenses in a liquid high-yield savings account before investing.",
                rationale="Protects against unexpected life disruptions without incurring debt.",
                assumptions="Assumes funds are kept strictly in FDIC-insured liquid accounts.",
                effort="medium",
                status=ActionStatus.PENDING,
            ),
            PlanAction(
                id="act_fallback_3",
                category=ActionCategory.DEBT_MANAGEMENT,
                title="High-Interest Debt Inventory & Prioritization",
                recommendation="List all existing liabilities by interest rate and target debts above 7% APY before taking market risk.",
                rationale="Guarantees a return equal to the avoided interest drag.",
                assumptions="Assumes minimum monthly payments are maintained on all debt lines.",
                effort="medium",
                status=ActionStatus.PENDING,
            ),
        ],
    )
```

---

### Step 3: Implement the Workflow Engine

Create file: `app/services/workflow_engine.py`

```python
from uuid import UUID
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.domain.models import (
    PlanStatus,
    PlanAction,
    FinancialPlanPayload,
    HHHEvaluationResult,
)
from app.infrastructure.repository import FinanceRepository
from app.services.intake_service import IntakeService
from app.agents.planning_agent import PlanningAgent
from app.agents.hhh_evaluator_agent import HHHEvaluatorAgent
from app.services.safe_fallback import get_safe_fallback_plan


class WorkflowResult(BaseModel):
    """Result payload returned by the Workflow Engine."""
    plan_id: UUID
    status: PlanStatus
    health_summary: str
    actions: List[PlanAction]
    evaluations: List[Dict[str, Any]]


class WorkflowEngine:
    """
    Coordinates the Plan -> HHH Evaluation revision loop.
    Enforces max 2 revision retries (3 total attempts) with critique injection,
    and falls back to safe educational guidance on failure or critical safety issues.
    """

    MAX_RETRIES: int = 2  # Total attempts = 1 initial + 2 retries = 3 attempts

    def __init__(
        self,
        intake_service: IntakeService,
        planning_agent: PlanningAgent,
        evaluator_agent: HHHEvaluatorAgent,
        repository: FinanceRepository,
    ):
        self.intake_service = intake_service
        self.planning_agent = planning_agent
        self.evaluator_agent = evaluator_agent
        self.repository = repository

    async def run(self, user_id: UUID) -> WorkflowResult:
        context = await self.intake_service.get_intake_context(user_id)
        profile = context.profile
        recent_feedback = context.recent_feedback

        evaluation_records: List[HHHEvaluationResult] = []
        prior_critique: Optional[str] = None
        active_plan_payload: Optional[FinancialPlanPayload] = None
        plan_status: PlanStatus = PlanStatus.FALLBACK

        for attempt in range(self.MAX_RETRIES + 1):
            # 1. Generate candidate plan
            candidate = await self.planning_agent.generate_plan(
                profile=profile,
                recent_feedback=recent_feedback,
                prior_critique=prior_critique,
            )

            # 2. Evaluate candidate plan against HHH rubric
            eval_result = await self.evaluator_agent.evaluate(
                plan=candidate,
                profile=profile,
                recent_feedback=recent_feedback,
            )
            evaluation_records.append(eval_result)

            # 3. Handle immediate pass
            if eval_result.passed:
                active_plan_payload = candidate
                plan_status = PlanStatus.ACTIVE
                break

            # 4. Handle immediate critical harmlessness issue
            if eval_result.critical_issue:
                # Halt immediately, bypass remaining retries
                break

            # 5. Prepare critique for next retry iteration
            prior_critique = eval_result.critique

        # If retries exhausted or critical safety failure, apply Safe Fallback
        if plan_status != PlanStatus.ACTIVE or active_plan_payload is None:
            active_plan_payload = get_safe_fallback_plan(profile)
            plan_status = PlanStatus.FALLBACK

        # Save plan to repository
        plan_id = await self.repository.save_plan(
            plan=active_plan_payload,
            user_id=user_id,
            status=plan_status,
        )

        # Save evaluation audit logs
        persisted_evaluations = []
        for idx, eval_rec in enumerate(evaluation_records):
            await self.repository.save_evaluation(
                plan_id=plan_id,
                eval_result=eval_rec,
                iteration=idx,
            )
            persisted_evaluations.append({
                "iteration": idx,
                "helpful_score": eval_rec.helpful_score,
                "honest_score": eval_rec.honest_score,
                "harmless_score": eval_rec.harmless_score,
                "passed": eval_rec.passed,
                "critical_issue": eval_rec.critical_issue,
                "critique": eval_rec.critique,
            })

        return WorkflowResult(
            plan_id=plan_id,
            status=plan_status,
            health_summary=active_plan_payload.health_summary,
            actions=active_plan_payload.actions,
            evaluations=persisted_evaluations,
        )
```

---

### Step 4: Run the Test Suite to Verify

Run pytest:
```bash
pytest tests/services/test_workflow_engine.py -v
```

#### Expected Output:
```text
tests/services/test_workflow_engine.py::TestWorkflowEngine::test_workflow_immediate_pass PASSED [ 25%]
tests/services/test_workflow_engine.py::TestWorkflowEngine::test_workflow_retry_pass PASSED [ 50%]
tests/services/test_workflow_engine.py::TestWorkflowEngine::test_workflow_exhausted_retries_triggers_fallback PASSED [ 75%]
tests/services/test_workflow_engine.py::TestWorkflowEngine::test_workflow_critical_harmless_triggers_immediate_fallback PASSED [100%]

============================== 4 passed in 0.04s ==============================
```

Run full suite:
```bash
pytest
```
*Expected: 31 passed across all domain, repository, service, and agent modules!*

---

## 5. Common Pitfalls & Zero-Question FAQ

* **Q: Exactly how many total attempts can happen?**  
  *A:* Exactly 3 attempts maximum (`attempt 0` = initial plan, `attempt 1` = first retry, `attempt 2` = second retry). If attempt 2 fails, the safe fallback is returned.
* **Q: What if the first attempt has `critical_issue = True`?**  
  *A:* The engine immediately breaks the loop (`attempt 0` only) and returns the Safe Fallback plan. It never attempts a revision on an inherently reckless recommendation.
* **Q: Are evaluation audit records preserved even for failed attempts?**  
  *A:* Yes! Every evaluation attempt (whether it passed or failed) is stored in the database and linked to the final `plan_id` so reviewers can inspect the AI's full reasoning trail.

---

## 6. Git Commit, Push & Trello Progression

Once all tests pass:

### 1. Stage, Commit and Push
```bash
git add app/services/safe_fallback.py app/services/workflow_engine.py tests/services/test_workflow_engine.py
git commit -m "feat(services): implement safe fallback and workflow engine revision state machine"
git push origin main
```

### 2. Update Trello Card
1. Navigate to **[Task 6 Card on Trello](https://trello.com/c/2QHkNGNA)**.
2. Check off all checklist items.
3. Move the card from **`IN PROGRESS`** $\rightarrow$ **`CODE REVIEW`**.
