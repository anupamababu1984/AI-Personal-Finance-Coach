# Task 7 Implementation Guide: Action Feedback Service & Adaptive Loop Integration

> **Document Status:** Complete & Verified  
> **Target Audience:** Implementer / Client / Coding Agent  
> **Estimated Time to Complete:** 15 minutes  
> **Prerequisites:** Tasks 1 through 6 completed (Domain models, benchmarks, repository, intake service, planning agent, evaluator agent, and workflow engine available).

---

## Table of Contents
1. [Overview & User Story](#1-overview--user-story)
2. [The "WHY": Closing the Learning Loop](#2-the-why-closing-the-learning-loop)
3. [The "HOW": State Mutation & Adaptive Flow](#3-the-how-state-mutation--adaptive-flow)
4. [Step-by-Step Technical Implementation (TDD)](#4-step-by-step-technical-implementation-tdd)
   - [Step 1: Write the Failing Test (`tests/services/test_feedback_service.py`)](#step-1-write-the-failing-test)
   - [Step 2: Implement the Feedback Service (`app/services/feedback_service.py`)](#step-2-implement-the-feedback-service)
   - [Step 3: Run the Test Suite to Verify](#step-3-run-the-test-suite-to-verify)
5. [Common Pitfalls & Zero-Question FAQ](#5-common-pitfalls--zero-question-faq)
6. [Git Commit, Push & Trello Progression](#6-git-commit-push--trello-progression)

---

## 1. Overview & User Story

### User Story
> **As a** user,  
> **I want** to submit feedback on individual plan actions (marking them as `worked` or `did_not_work` with optional qualitative notes),  
> **So that** my active plan reflects my progress and my coach automatically adapts my future plans based on my actual real-world experience over the last 30 days.

### Deliverables
* `app/services/feedback_service.py`:
  * `FeedbackSubmission`: Pydantic model validating incoming user feedback payloads.
  * `FeedbackService`: Service coordinating feedback logging and mutating active plan action statuses in the repository.
* `tests/services/test_feedback_service.py`: Pytest suite verifying feedback persistence, plan action status mutation (`pending` $\rightarrow$ `worked` / `did_not_work`), and closed-loop integration with `IntakeService`.

---

## 2. The "WHY": Closing the Learning Loop

Most "AI apps" are one-way streets:
* The user asks for something.
* The AI gives an answer.
* The conversation ends.

If the user tries the advice and it fails (e.g. *"I tried opening that high-yield savings account, but the $5,000 minimum deposit was too high for my immediate cash flow"*), an ordinary app will repeat the exact same advice next week!

### Task 7 closes the loop:
1. **Interactive Feedback:** Users don't just read advice; they click **"Worked"** or **"Didn't Work"** on each checklist item and add notes.
2. **Immediate Progress Tracking:** The active plan updates in real-time (the action item changes from `pending` to `worked` or `did_not_work`).
3. **Adaptive Learning:** The feedback is timestamped and stored in `action_feedback`. When the user asks for a new plan in 2 weeks, our **Prep Cook (`IntakeService`)** grabs that feedback, hands it to our **Head Chef (`PlanningAgent`)**, and the AI coach explicitly avoids repeating rejected recommendations!

---

## 3. The "HOW": State Mutation & Adaptive Flow

```text
1. User clicks "Didn't Work" on Action [act_1]
   "Minimum deposit was too high"
               │
               ▼
   FeedbackService.submit_feedback()
               │
       ┌───────┴────────────────────────┐
       │                                │
       ▼                                ▼
[Step 1: Save Event]             [Step 2: Mutate Plan]
repo.save_feedback()             repo.update_action_status()
Stores in `action_feedback`      Updates active plan JSON:
table with current timestamp     action[act_1].status = 'did_not_work'
       │
       ▼
[Step 3: Closed-Loop Next Run]
Next time WorkflowEngine runs:
IntakeService retrieves feedback from last 30 days:
"- Action [act_1]: REJECTED/DID NOT WORK - Notes: Minimum deposit was too high"
       │
       ▼
PlanningAgent receives constraint:
"Previous feedback: User rejected high-minimum accounts.
 Recommend low-minimum or zero-minimum cash accounts instead."
```

---

## 4. Step-by-Step Technical Implementation (TDD)

---

### Step 1: Write the Failing Test

Create file: `tests/services/test_feedback_service.py`

```python
"""
Unit and integration tests for the FeedbackService.
Verifies feedback persistence, active plan action mutation, and 30-day adaptive integration.
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
from app.infrastructure.repository import InMemoryFinanceRepository
from app.services.intake_service import IntakeService
from app.services.feedback_service import FeedbackService, FeedbackSubmission


@pytest.fixture
def repo():
    return InMemoryFinanceRepository()


@pytest.fixture
def feedback_service(repo):
    return FeedbackService(repo)


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
def sample_plan():
    return FinancialPlanPayload(
        health_summary="Strong foundation for growth.",
        actions=[
            PlanAction(
                id="act_1",
                category=ActionCategory.EMERGENCY_FUND,
                title="Establish 3-Month Emergency Reserve",
                recommendation="Allocate $500/mo into a 4.5% APY HYSA until reaching $12,000.",
                rationale="Mitigates liquidity vulnerability before aggressive investing.",
                assumptions="Assumes standard cash savings earn ~4.5% in HYSA.",
                effort="low",
                status=ActionStatus.PENDING,
            ),
            PlanAction(
                id="act_2",
                category=ActionCategory.DEBT_MANAGEMENT,
                title="Student Loan Paydown Strategy",
                recommendation="Allocate $300/mo extra to clear debt.",
                rationale="Eliminate interest drag.",
                assumptions="4.5% loan rate",
                effort="medium",
                status=ActionStatus.PENDING,
            ),
            PlanAction(
                id="act_3",
                category=ActionCategory.INVESTMENT,
                title="Broad Market Equity Compounding",
                recommendation="Invest $200/mo into low-cost index funds.",
                rationale="7.5% long-term returns.",
                assumptions="7.5% historical return",
                effort="medium",
                status=ActionStatus.PENDING,
            ),
        ],
    )


class TestFeedbackService:
    @pytest.mark.asyncio
    async def test_submit_feedback_persists_record(self, repo, feedback_service, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)

        submission = FeedbackSubmission(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_1",
            outcome="worked",
            notes="Opened account and set up automated transfer",
        )

        feedback_id = await feedback_service.submit_feedback(submission)
        assert isinstance(feedback_id, UUID)

        # Verify feedback stored in repository
        recent = await repo.get_recent_feedback(sample_profile.user_id, days=30)
        assert len(recent) == 1
        assert recent[0].action_id == "act_1"
        assert recent[0].outcome == "worked"
        assert recent[0].notes == "Opened account and set up automated transfer"

    @pytest.mark.asyncio
    async def test_submit_feedback_updates_active_plan_action_status(self, repo, feedback_service, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)

        # Initially act_1 is pending
        active_before = await repo.get_active_plan(sample_profile.user_id)
        assert active_before["actions"][0]["status"] == ActionStatus.PENDING

        # Submit 'did_not_work' feedback on act_1
        submission = FeedbackSubmission(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_1",
            outcome="did_not_work",
            notes="Deposit minimum was too high",
        )
        await feedback_service.submit_feedback(submission)

        # Active plan action status must now be DID_NOT_WORK
        active_after = await repo.get_active_plan(sample_profile.user_id)
        assert active_after["actions"][0]["status"] == ActionStatus.DID_NOT_WORK
        # Other actions remain untouched
        assert active_after["actions"][1]["status"] == ActionStatus.PENDING

    @pytest.mark.asyncio
    async def test_closed_feedback_loop_integration(self, repo, feedback_service, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)

        # Submit feedback
        submission = FeedbackSubmission(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_1",
            outcome="did_not_work",
            notes="Minimum deposit was too high for my freelancing cash flow",
        )
        await feedback_service.submit_feedback(submission)

        # Call IntakeService to verify feedback is immediately captured
        intake_service = IntakeService(repo)
        intake_context = await intake_service.get_intake_context(sample_profile.user_id)

        assert len(intake_context.recent_feedback) == 1
        assert "REJECTED/DID NOT WORK" in intake_context.feedback_summary
        assert "Minimum deposit was too high" in intake_context.feedback_summary
```

#### Run the test to confirm it fails:
```bash
pytest tests/services/test_feedback_service.py
```
*Expected Output:* `ModuleNotFoundError: No module named 'app.services.feedback_service'` (Fails as expected).

---

### Step 2: Implement the Feedback Service

Create file: `app/services/feedback_service.py`

```python
from uuid import UUID, uuid4
from typing import Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.domain.models import ActionFeedback, ActionStatus
from app.infrastructure.repository import FinanceRepository


class FeedbackSubmission(BaseModel):
    """Payload sent by the client when providing feedback on a plan action."""
    user_id: UUID
    plan_id: UUID
    action_id: str = Field(..., min_length=1)
    outcome: Literal["worked", "did_not_work"]
    notes: Optional[str] = None


class FeedbackService:
    """Handles logging user feedback and mutating active plan action statuses."""

    def __init__(self, repo: FinanceRepository):
        self.repo = repo

    async def submit_feedback(self, submission: FeedbackSubmission) -> UUID:
        """
        1. Persists the feedback event to the repository.
        2. Updates the target action status in the active plan (WORKED or DID_NOT_WORK).
        3. Returns the unique feedback ID.
        """
        feedback_entity = ActionFeedback(
            id=uuid4(),
            user_id=submission.user_id,
            plan_id=submission.plan_id,
            action_id=submission.action_id,
            outcome=submission.outcome,
            notes=submission.notes,
            created_at=datetime.now(timezone.utc),
        )
        feedback_id = await self.repo.save_feedback(feedback_entity)

        # Mutate the targeted action status in the active plan
        new_status = (
            ActionStatus.WORKED
            if submission.outcome == "worked"
            else ActionStatus.DID_NOT_WORK
        )
        await self.repo.update_action_status(
            plan_id=submission.plan_id,
            action_id=submission.action_id,
            status=new_status,
        )

        return feedback_id
```

---

### Step 3: Run the Test Suite to Verify

Run pytest:
```bash
pytest tests/services/test_feedback_service.py -v
```

#### Expected Output:
```text
tests/services/test_feedback_service.py::TestFeedbackService::test_submit_feedback_persists_record PASSED [ 33%]
tests/services/test_feedback_service.py::TestFeedbackService::test_submit_feedback_updates_active_plan_action_status PASSED [ 66%]
tests/services/test_feedback_service.py::TestFeedbackService::test_closed_feedback_loop_integration PASSED [100%]

============================== 3 passed in 0.02s ==============================
```

Run full project test suite:
```bash
pytest
```
*Expected: 34 passed across the entire project!*

---

## 5. Common Pitfalls & Zero-Question FAQ

* **Q: Does submitting feedback automatically trigger plan re-generation?**  
  *A:* No. Feedback recording is a lightweight, instant operation. It records the feedback and mutates the current action's status. The *next* time the user clicks "Generate Plan" or "Update Plan", the Workflow Engine pulls the newly recorded feedback.
* **Q: What if the user submits feedback on multiple actions?**  
  *A:* Each action item submits its own `FeedbackSubmission`. All submissions from the past 30 days are aggregated together by `IntakeService`.

---

## 6. Git Commit, Push & Trello Progression

Once all tests pass:

### 1. Stage, Commit and Push
```bash
git add app/services/feedback_service.py tests/services/test_feedback_service.py
git commit -m "feat(services): implement feedback service and active plan status mutation"
git push origin main
```

### 2. Update Trello Card
1. Navigate to **[Task 7 Card on Trello](https://trello.com/c/xrQ8GFzM)**.
2. Check off all checklist items.
3. Move the card from **`IN PROGRESS`** $\rightarrow$ **`CODE REVIEW`**.
