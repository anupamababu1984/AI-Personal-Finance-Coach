# Task 4 Implementation Guide: Planning Agent with Structured JSON & Benchmark Injection

> **Document Status:** Complete & Verified  
> **Target Audience:** Implementer / Client / Coding Agent  
> **Estimated Time to Complete:** 15–20 minutes  
> **Prerequisites:** Tasks 1, 2, and 3 completed (Domain models, benchmarks, repository, and intake service available).

---

## Table of Contents
1. [Overview & User Story](#1-overview--user-story)
2. [The "WHY": The Head Chef Analogy](#2-the-why-the-head-chef-analogy)
3. [The "HOW": Prompt Architecture & LLM Abstraction](#3-the-how-prompt-architecture--llm-abstraction)
4. [Step-by-Step Technical Implementation (TDD)](#4-step-by-step-technical-implementation-tdd)
   - [Step 1: Write the Failing Test (`tests/agents/test_planning_agent.py`)](#step-1-write-the-failing-test)
   - [Step 2: Implement the LLM Client Abstraction (`app/infrastructure/llm_client.py`)](#step-2-implement-the-llm-client-abstraction)
   - [Step 3: Implement the Planning Agent (`app/agents/planning_agent.py`)](#step-3-implement-the-planning-agent)
   - [Step 4: Run the Test Suite to Verify](#step-4-run-the-test-suite-to-verify)
5. [Common Pitfalls & Zero-Question FAQ](#5-common-pitfalls--zero-question-faq)
6. [Git Commit, Push & Trello Progression](#6-git-commit-push--trello-progression)

---

## 1. Overview & User Story

### User Story
> **As an** AI planning engine,  
> **I want** a Planning Agent that combines a user's financial profile, curated market benchmarks, and rolling 30-day feedback into a structured prompt, calling the LLM to generate a strictly typed `FinancialPlanPayload`,  
> **So that** users receive grounded, realistic, and personalized action checklists without AI hallucinations or schema parsing errors.

### Deliverables
* `app/infrastructure/llm_client.py`:
  * `LLMClient`: Protocol defining the `generate_json` contract.
  * `MockLLMClient`: Deterministic mock recording prompts for instant, offline unit tests.
  * `AnthropicLLMClient`: Production client communicating with Anthropic Claude API.
* `app/agents/planning_agent.py`:
  * `PlanningAgent`: Core agent assembling prompts and validating structured output.
* `tests/agents/test_planning_agent.py`: Pytest suite verifying benchmark injection, feedback injection, revision critique formatting, and schema validation.

---

## 2. The "WHY": The Head Chef Analogy

In Task 3, our **Prep Cook (`IntakeService`)** gathered the ingredients and arranged them on a tray.

Now in Task 4, we introduce the **Head Chef (`PlanningAgent`)**:
1. The Head Chef receives the tray containing the user's profile and their 30-day feedback.
2. The Head Chef checks their **Recipe Book / Cheat Sheet (`CURATED_MARKET_BENCHMARKS`)** so they don't guess cooking temperatures (interest rates).
3. The Head Chef asks the AI to produce an actionable 3-to-5 item checklist (`FinancialPlanPayload`).

### Why do we need an `LLMClient` Abstraction?
If we called `anthropic.Anthropic().messages.create(...)` directly inside our agent:
* Every time we run `pytest`, it would make a live call over the internet, costing API money and taking 3 seconds per test.
* Tests would fail if the internet drops or an API key expires.
* By using `LLMClient` with a `MockLLMClient`, our unit tests run in **0.02 seconds completely offline**, while production connects seamlessly to Claude!

---

## 3. The "HOW": Prompt Architecture & LLM Abstraction

```text
┌────────────────────────────────────────────────────────┐
│                      PlanningAgent                     │
│                                                        │
│  Input Ingredients:                                    │
│  • UserProfile (Age, Income, Expenses, Debt, Risk)     │
│  • CuratedMarketBenchmarks (HYSA 4.5%, Equity 7.5%)    │
│  • 30-Day Feedback Summary                             │
│  • Optional: Prior Critique (if on retry attempt)      │
└───────────────────────────┬────────────────────────────┘
                            │ Assembles Prompts
                            ▼
┌────────────────────────────────────────────────────────┐
│                        LLMClient                       │
│       ┌───────────────────┴───────────────────┐        │
│       ▼                                       ▼        │
│  MockLLMClient                       AnthropicLLMClient │
│  (For 0.02s Unit Tests)              (For Live Claude) │
└───────────────────────────┬────────────────────────────┘
                            │ Returns Dict
                            ▼
┌────────────────────────────────────────────────────────┐
│                 Pydantic v2 Validation                 │
│         FinancialPlanPayload.model_validate(json)      │
│  • Validates health_summary                            │
│  • Validates strictly 3 to 5 PlanAction items          │
└────────────────────────────────────────────────────────┘
```

---

## 4. Step-by-Step Technical Implementation (TDD)

---

### Step 1: Write the Failing Test

Create file: `tests/agents/test_planning_agent.py`

```python
"""
Unit tests for the PlanningAgent.
Verifies prompt construction (benchmarks, feedback, critique injection) and structured output validation.
"""
import pytest
from uuid import UUID

from app.domain.models import (
    UserProfile,
    RiskAppetite,
    ActionFeedback,
    FinancialPlanPayload,
    ActionCategory,
    ActionStatus,
)
from app.domain.benchmarks import CURATED_MARKET_BENCHMARKS
from app.infrastructure.llm_client import MockLLMClient
from app.agents.planning_agent import PlanningAgent


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
def valid_plan_dict():
    return {
        "health_summary": "Strong cash flow and long investment horizon for aggressive growth.",
        "actions": [
            {
                "id": "act_1",
                "category": "emergency_fund",
                "title": "Establish 3-Month Emergency Reserve",
                "recommendation": "Allocate $500/mo into a 4.5% APY HYSA until reaching $12,000.",
                "rationale": "Mitigates liquidity vulnerability before aggressive investing.",
                "assumptions": "Assumes standard cash savings earn ~4.5% in HYSA.",
                "effort": "low",
                "status": "pending",
            },
            {
                "id": "act_2",
                "category": "debt_management",
                "title": "Student Loan Paydown Strategy",
                "recommendation": "Allocate $300/mo above minimums to eliminate 4.5% student debt in 2.5 years.",
                "rationale": "Guarantees a 4.5% return by eliminating interest drag.",
                "assumptions": "Assumes fixed student loan interest rate.",
                "effort": "medium",
                "status": "pending",
            },
            {
                "id": "act_3",
                "category": "investment",
                "title": "Broad Market Equity Compounding",
                "recommendation": "Invest remaining $200/mo into low-cost diversified equity index funds.",
                "rationale": "Captures expected 7.5% long-term historical compounding.",
                "assumptions": "Assumes 7.5% long-term historical market average.",
                "effort": "medium",
                "status": "pending",
            },
        ],
    }


class TestPlanningAgent:
    @pytest.mark.asyncio
    async def test_prompt_includes_benchmarks(self, sample_profile, valid_plan_dict):
        mock_llm = MockLLMClient(response_dict=valid_plan_dict)
        agent = PlanningAgent(llm_client=mock_llm, benchmarks=CURATED_MARKET_BENCHMARKS)

        await agent.generate_plan(profile=sample_profile, recent_feedback=[])

        # Assert system prompt includes benchmarks
        assert "4.5%" in mock_llm.last_system_prompt
        assert "7.5%" in mock_llm.last_system_prompt
        assert "3 to 6 months" in mock_llm.last_system_prompt
        assert "4.0%" in mock_llm.last_system_prompt

    @pytest.mark.asyncio
    async def test_prompt_includes_feedback(self, sample_profile, valid_plan_dict):
        mock_llm = MockLLMClient(response_dict=valid_plan_dict)
        agent = PlanningAgent(llm_client=mock_llm, benchmarks=CURATED_MARKET_BENCHMARKS)

        feedback = [
            ActionFeedback(
                user_id=sample_profile.user_id,
                plan_id=UUID("00000000-0000-0000-0000-000000000099"),
                action_id="act_1",
                outcome="did_not_work",
                notes="Deposit minimum was too high",
            )
        ]

        await agent.generate_plan(profile=sample_profile, recent_feedback=feedback)

        # Assert user prompt includes feedback
        assert "Deposit minimum was too high" in mock_llm.last_user_prompt
        assert "did_not_work" in mock_llm.last_user_prompt

    @pytest.mark.asyncio
    async def test_prompt_includes_critique_on_revision(self, sample_profile, valid_plan_dict):
        mock_llm = MockLLMClient(response_dict=valid_plan_dict)
        agent = PlanningAgent(llm_client=mock_llm, benchmarks=CURATED_MARKET_BENCHMARKS)

        critique_text = "Plan is too generic and lacks dollar allocations."
        await agent.generate_plan(
            profile=sample_profile,
            recent_feedback=[],
            prior_critique=critique_text,
        )

        # Assert user prompt includes critique
        assert "CRITICAL REVISION INSTRUCTIONS" in mock_llm.last_user_prompt
        assert critique_text in mock_llm.last_user_prompt

    @pytest.mark.asyncio
    async def test_successful_plan_payload_validation(self, sample_profile, valid_plan_dict):
        mock_llm = MockLLMClient(response_dict=valid_plan_dict)
        agent = PlanningAgent(llm_client=mock_llm, benchmarks=CURATED_MARKET_BENCHMARKS)

        plan = await agent.generate_plan(profile=sample_profile, recent_feedback=[])

        assert isinstance(plan, FinancialPlanPayload)
        assert len(plan.actions) == 3
        assert plan.actions[0].category == ActionCategory.EMERGENCY_FUND
        assert plan.actions[0].status == ActionStatus.PENDING
```

#### Run the test to confirm it fails:
```bash
pytest tests/agents/test_planning_agent.py
```
*Expected Output:* `ModuleNotFoundError: No module named 'app.infrastructure.llm_client'` (Fails as expected).

---

### Step 2: Implement the LLM Client Abstraction

Create file: `app/infrastructure/llm_client.py`

```python
from typing import Protocol, Optional, Dict, Any


class LLMClient(Protocol):
    """Protocol contract for LLM structured JSON generation."""

    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Send prompts to LLM and return parsed JSON dictionary."""
        ...


class MockLLMClient:
    """Mock LLM client for deterministic, offline testing."""

    def __init__(self, response_dict: Optional[Dict[str, Any]] = None):
        self.response_dict = response_dict or {}
        self.last_system_prompt: Optional[str] = None
        self.last_user_prompt: Optional[str] = None

    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.response_dict


class AnthropicLLMClient:
    """Production LLM client utilizing Anthropic Claude API."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        import json
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            temperature=0.2,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_content = response.content[0].text
        # Clean any accidental markdown code fences
        cleaned = text_content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())
```

---

### Step 3: Implement the Planning Agent

Create file: `app/agents/planning_agent.py`

```python
from typing import List, Optional
from app.domain.models import (
    UserProfile,
    ActionFeedback,
    FinancialPlanPayload,
)
from app.domain.benchmarks import CuratedMarketBenchmarks
from app.infrastructure.llm_client import LLMClient


class PlanningAgent:
    """Generates structured financial plans tailored to demographics and feedback."""

    def __init__(self, llm_client: LLMClient, benchmarks: CuratedMarketBenchmarks):
        self.llm_client = llm_client
        self.benchmarks = benchmarks

    async def generate_plan(
        self,
        profile: UserProfile,
        recent_feedback: List[ActionFeedback],
        prior_critique: Optional[str] = None,
    ) -> FinancialPlanPayload:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(profile, recent_feedback, prior_critique)

        response_dict = await self.llm_client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return FinancialPlanPayload.model_validate(response_dict)

    def _build_system_prompt(self) -> str:
        b = self.benchmarks
        return f"""You are an expert, objective AI Personal Finance Coach.
Your objective is to generate a personalized, realistic, and strictly grounded personal financial plan formatted as an actionable checklist.

CURATED MARKET BENCHMARKS (Do not deviate from these baseline assumptions):
- High-Yield Savings Account (HYSA) APY: {b.hysa_apy * 100:.1f}%
- Historical Diversified Equity Index Return: {b.historical_equity_return * 100:.1f}% annual average
- Standard Emergency Fund Target: {b.standard_emergency_fund.min_months} to {b.standard_emergency_fund.max_months} months of living expenses
- Safe Retirement Withdrawal Rate: {b.safe_withdrawal_rate * 100:.1f}% rule

RULES:
1. Generate between 3 and 5 prioritized actions.
2. Each action MUST have: id (act_1, act_2, ...), category (emergency_fund, debt_management, investment, budgeting), title, recommendation, rationale, assumptions, effort (low, medium, high), status (pending).
3. Ground all recommendations strictly in the user's provided income, expenses, debt, risk appetite, and goals.
4. If monthly expenses exceed income, prioritize cash flow triage and debt prevention over investing.
5. If recent user feedback indicates an action worked or did not work, adapt your recommendations accordingly. DO NOT re-recommend mechanisms the user previously rejected.
6. Output MUST strictly be valid JSON conforming to:
{{
  "health_summary": "...",
  "actions": [
    {{
      "id": "act_1",
      "category": "emergency_fund",
      "title": "...",
      "recommendation": "...",
      "rationale": "...",
      "assumptions": "...",
      "effort": "low",
      "status": "pending"
    }}
  ]
}}"""

    def _build_user_prompt(
        self,
        profile: UserProfile,
        recent_feedback: List[ActionFeedback],
        prior_critique: Optional[str] = None,
    ) -> str:
        feedback_lines = []
        if recent_feedback:
            feedback_lines.append("RECENT USER FEEDBACK (Last 30 Days):")
            for f in recent_feedback:
                outcome_str = "WORKED" if f.outcome == "worked" else "DID NOT WORK"
                notes_part = f" - Notes: {f.notes}" if f.notes else ""
                feedback_lines.append(f"- Action [{f.action_id}]: {outcome_str}{notes_part}")
        else:
            feedback_lines.append("RECENT USER FEEDBACK: None. This is a fresh planning run.")

        feedback_section = "\n".join(feedback_lines)

        critique_section = ""
        if prior_critique:
            critique_section = f"""CRITICAL REVISION INSTRUCTIONS FROM PREVIOUS HHH EVALUATION:
Your previous plan attempt failed evaluation with the following critique:
"{prior_critique}"
You must explicitly correct these issues in this revision."""

        return f"""USER PROFILE:
- Age: {profile.age}
- Annual Income: ${profile.annual_income:,.2f}
- Monthly Expenses: ${profile.monthly_expenses:,.2f}
- Savings: ${profile.savings:,.2f}
- Investments: ${profile.investments:,.2f}
- Debt: ${profile.debt:,.2f} ({profile.debt_details or 'None'})
- Risk Appetite: {profile.risk_appetite.value}
- Investment Horizon: {profile.investment_horizon_years} years
- Retirement Target Age: {profile.retirement_age_target}
- Primary Goal: {profile.primary_goal}
- Monthly Investment Capacity: ${profile.monthly_investment_capacity:,.2f}

{feedback_section}

{critique_section}

Generate the candidate financial plan JSON now."""
```

---

### Step 4: Run the Test Suite to Verify

Run pytest:
```bash
pytest tests/agents/test_planning_agent.py -v
```

#### Expected Output:
```text
tests/agents/test_planning_agent.py::TestPlanningAgent::test_prompt_includes_benchmarks PASSED [ 25%]
tests/agents/test_planning_agent.py::TestPlanningAgent::test_prompt_includes_feedback PASSED [ 50%]
tests/agents/test_planning_agent.py::TestPlanningAgent::test_prompt_includes_critique_on_revision PASSED [ 75%]
tests/agents/test_planning_agent.py::TestPlanningAgent::test_successful_plan_payload_validation PASSED [100%]

============================== 4 passed in 0.03s ==============================
```

Run full suite:
```bash
pytest
```
*Expected: 22 passed across all domain, repository, service, and agent tests!*

---

## 5. Common Pitfalls & Zero-Question FAQ

* **Q: Why are there 3 to 5 actions?**  
  *A:* The `FinancialPlanPayload` Pydantic model enforces `min_length=3, max_length=5`. If the LLM generates 2 or 6 items, Pydantic will raise a `ValidationError`.
* **Q: How does the agent know if it is a revision?**  
  *A:* If `prior_critique` is passed into `generate_plan()`, the agent injects a `CRITICAL REVISION INSTRUCTIONS` header into the prompt, telling the AI exactly what went wrong during the previous HHH evaluation attempt.

---

## 6. Git Commit, Push & Trello Progression

Once all tests pass:

### 1. Stage, Commit and Push
```bash
git add app/infrastructure/llm_client.py app/agents/planning_agent.py tests/agents/test_planning_agent.py
git commit -m "feat(agents): implement planning agent with benchmark injection and mock LLM client"
git push origin main
```

### 2. Update Trello Card
1. Navigate to **[Task 4 Card on Trello](https://trello.com/c/t6wrja96)**.
2. Check off all checklist items.
3. Move the card from **`IN PROGRESS`** $\rightarrow$ **`CODE REVIEW`**.
