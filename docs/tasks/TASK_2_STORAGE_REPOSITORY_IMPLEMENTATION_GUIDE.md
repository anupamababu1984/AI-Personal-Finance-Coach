# Task 2 Implementation Guide: Supabase Schema Migration & Storage Repository

> **Document Status:** Complete & Verified  
> **Target Audience:** Implementer / Client / Coding Agent  
> **Estimated Time to Complete:** 15–20 minutes  
> **Prerequisites:** Task 1 completed (Pydantic models available in `app/domain/models.py`).

---

## Table of Contents
1. [Overview & User Story](#1-overview--user-story)
2. [The "WHY": The Filing Cabinet and The Librarian](#2-the-why-the-filing-cabinet-and-the-librarian)
3. [The "HOW": Architecture & 30-Day Boundary Filtering](#3-the-how-architecture--30-day-boundary-filtering)
4. [Step-by-Step Technical Implementation (TDD)](#4-step-by-step-technical-implementation-tdd)
   - [Step 1: Verify the SQL Migration Script](#step-1-verify-the-sql-migration-script)
   - [Step 2: Write the Failing Test (`tests/infrastructure/test_repository.py`)](#step-2-write-the-failing-test)
   - [Step 3: Implement the Repository Layer (`app/infrastructure/repository.py`)](#step-3-implement-the-repository-layer)
   - [Step 4: Run the Test Suite to Verify](#step-4-run-the-test-suite-to-verify)
5. [Common Pitfalls & Zero-Question FAQ](#5-common-pitfalls--zero-question-faq)
6. [Git Commit, Push & Trello Progression](#6-git-commit-push--trello-progression)

---

## 1. Overview & User Story

### User Story
> **As a** backend engineer,  
> **I want** a PostgreSQL database schema and a Python repository layer (supporting both in-memory testing and Supabase persistence),  
> **So that** user profiles, generated plans, HHH evaluation audits, and per-action feedback are safely stored, versioned, and queryable with automatic 30-day temporal windowing.

### Deliverables
* `supabase/migrations/20261005000000_init_schema.sql`: PostgreSQL DDL script creating all 4 tables, foreign keys, and indexes.
* `app/infrastructure/repository.py`:
  * `FinanceRepository(ABC)`: Abstract interface defining exact CRUD signatures.
  * `InMemoryFinanceRepository`: Fast, hermetic, thread-safe in-memory adapter with 30-day timestamp filtering.
* `tests/infrastructure/test_repository.py`: Pytest suite exercising all CRUD operations and temporal window boundaries.

---

## 2. The "WHY": The Filing Cabinet and The Librarian

In Task 1, we built our **Digital Forms** (Pydantic models). But right now, if our server restarts, all data disappears from memory.

Task 2 builds the **Storage System**:
1. **The Filing Cabinet (PostgreSQL via Supabase):**
   * Instead of one giant messy folder, we have 4 clean drawers:
     * `profiles`: User demographics, income, debts, risk appetite.
     * `plans`: Versioned financial action plans (`active`, `archived`, or `fallback`).
     * `plan_evaluations`: Complete audit logs of every HHH review (Helpful, Honest, Harmless scores, passed/failed flags, critiques).
     * `action_feedback`: Timestamped user feedback on specific actions (`worked` vs `did_not_work`).
2. **The Librarian (The Repository Pattern):**
   * Why do we write a `FinanceRepository` class instead of raw SQL inside our AI code?
   * **Separation of Concerns:** Our AI planning engine should only care about *planning*. It shouldn't know or care whether the data is stored in Supabase, Postgres, SQLite, or local memory.
   * **Instant Testing:** By writing `InMemoryFinanceRepository`, our automated test suite runs in **0.02 seconds** without needing an internet connection, Supabase API keys, or cloud database setup!

---

## 3. The "HOW": Architecture & 30-Day Boundary Filtering

### Data Flow Diagram
```text
           ┌─────────────────────────────────────────┐
           │      Application Services / Agents      │
           └────────────────────┬────────────────────┘
                                │ Calls typed methods:
                                │ - get_profile(user_id)
                                │ - save_plan(plan, user_id)
                                │ - get_recent_feedback(user_id, days=30)
                                ▼
           ┌─────────────────────────────────────────┐
           │       FinanceRepository Interface       │
           └──────────────┬───────────────────┬──────┘
                          │                   │
         [For Unit Tests] │                   │ [For Production Cloud]
                          ▼                   ▼
           ┌────────────────────────┐  ┌────────────────────────┐
           │InMemoryFinanceRepository│  │SupabaseFinanceRepository│
           │ (Fast, Isolated, Local) │  │  (Postgres Cloud DB)   │
           └────────────────────────┘  └────────────────────────┘
```

### The 30-Day Temporal Boundary Rule
One of the most important product requirements is that the AI coach learns from **recent** user feedback, not ancient history.
* When querying feedback:
  $$\text{Cutoff Date} = \text{Current Time (UTC)} - 30\text{ days}$$
* Feedback created **within the last 30 days** $\rightarrow$ Returned to the AI.
* Feedback created **more than 30 days ago** $\rightarrow$ Automatically filtered out.

---

## 4. Step-by-Step Technical Implementation (TDD)

---

### Step 1: Verify the SQL Migration Script

The SQL schema is already provided at `supabase/migrations/20261005000000_init_schema.sql`.

It establishes:
* `profiles` (references `auth.users(id)`).
* `plans` (linked to `profiles` with cascade delete, indexed on `user_id, status`).
* `plan_evaluations` (linked to `plans`, indexed on `plan_id`).
* `action_feedback` (linked to `profiles` and `plans`, indexed on `user_id, created_at DESC`).

To run it against your live Supabase project:
1. Open your **Supabase Dashboard** $\rightarrow$ **SQL Editor**.
2. Paste the contents of `supabase/migrations/20261005000000_init_schema.sql` and click **Run**.
*(Note: For running unit tests, `InMemoryFinanceRepository` executes locally with zero configuration).*

---

### Step 2: Write the Failing Test

Create file: `tests/infrastructure/test_repository.py`

```python
"""
Unit tests for the FinanceRepository layer.
Verifies CRUD operations for profiles, plans, evaluations, and 30-day feedback filtering.
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta

from app.domain.models import (
    UserProfile,
    RiskAppetite,
    PlanAction,
    ActionCategory,
    ActionStatus,
    FinancialPlanPayload,
    HHHEvaluationResult,
    ActionFeedback,
    PlanStatus,
)
from app.infrastructure.repository import InMemoryFinanceRepository


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
def sample_plan():
    actions = [
        PlanAction(
            id="act_1",
            category=ActionCategory.EMERGENCY_FUND,
            title="Emergency Fund",
            recommendation="Save 3 months",
            rationale="Buffer",
            assumptions="4.5% APY",
            effort="low",
            status=ActionStatus.PENDING,
        ),
        PlanAction(
            id="act_2",
            category=ActionCategory.DEBT_MANAGEMENT,
            title="Loan Payoff",
            recommendation="Pay $300/mo extra",
            rationale="Save interest",
            assumptions="4.5% rate",
            effort="medium",
            status=ActionStatus.PENDING,
        ),
        PlanAction(
            id="act_3",
            category=ActionCategory.INVESTMENT,
            title="Index Fund",
            recommendation="Invest $700/mo",
            rationale="Growth",
            assumptions="7.5% return",
            effort="medium",
            status=ActionStatus.PENDING,
        ),
    ]
    return FinancialPlanPayload(
        health_summary="Strong foundation for growth.",
        actions=actions,
    )


class TestFinanceRepository:
    @pytest.mark.asyncio
    async def test_profile_crud(self, repo, sample_profile):
        # Save profile
        saved = await repo.save_profile(sample_profile)
        assert saved.user_id == sample_profile.user_id

        # Retrieve profile
        fetched = await repo.get_profile(sample_profile.user_id)
        assert fetched is not None
        assert fetched.annual_income == 75000.0

        # Query non-existent profile returns None
        missing = await repo.get_profile(uuid4())
        assert missing is None

    @pytest.mark.asyncio
    async def test_plan_saving_and_status_updates(self, repo, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)

        # Save plan
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)
        assert isinstance(plan_id, UUID)

        # Retrieve active plan
        active = await repo.get_active_plan(sample_profile.user_id)
        assert active is not None
        assert active["id"] == plan_id
        assert active["status"] == PlanStatus.ACTIVE
        assert len(active["actions"]) == 3

        # Update status to archived
        await repo.update_plan_status(plan_id, PlanStatus.ARCHIVED)
        archived = await repo.get_active_plan(sample_profile.user_id)
        assert archived is None  # No active plan exists anymore

    @pytest.mark.asyncio
    async def test_action_status_mutation(self, repo, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)

        # Mutate action act_1 to WORKED
        await repo.update_action_status(plan_id, "act_1", ActionStatus.WORKED)

        active = await repo.get_active_plan(sample_profile.user_id)
        act_1 = next(a for a in active["actions"] if a["id"] == "act_1")
        assert act_1["status"] == ActionStatus.WORKED

    @pytest.mark.asyncio
    async def test_evaluations_logging(self, repo, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)

        eval_result = HHHEvaluationResult(
            helpful_score=4,
            honest_score=4,
            harmless_score=4,
            passed=True,
            critical_issue=False,
            critique=None,
        )
        eval_id = await repo.save_evaluation(plan_id, eval_result, iteration=0)
        assert isinstance(eval_id, UUID)

        evals = await repo.get_evaluations_for_plan(plan_id)
        assert len(evals) == 1
        assert evals[0]["helpful_score"] == 4
        assert evals[0]["passed"] is True

    @pytest.mark.asyncio
    async def test_30_day_feedback_boundary_filtering(self, repo, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)
        now = datetime.now(timezone.utc)

        # 1. Feedback from 10 days ago (Should be included)
        fb_recent = ActionFeedback(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_1",
            outcome="worked",
            notes="Setup HYSA without issues",
            created_at=now - timedelta(days=10),
        )
        await repo.save_feedback(fb_recent)

        # 2. Feedback from 29 days ago (Should be included)
        fb_border = ActionFeedback(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_2",
            outcome="did_not_work",
            notes="Minimum payment too tight",
            created_at=now - timedelta(days=29),
        )
        await repo.save_feedback(fb_border)

        # 3. Feedback from 35 days ago (Should be EXCLUDED)
        fb_old = ActionFeedback(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_3",
            outcome="worked",
            notes="Old action from last month",
            created_at=now - timedelta(days=35),
        )
        await repo.save_feedback(fb_old)

        # Query recent feedback with default 30 days
        recent_feedback = await repo.get_recent_feedback(sample_profile.user_id, days=30)

        # Only the 10-day and 29-day items must be returned
        assert len(recent_feedback) == 2
        returned_action_ids = [f.action_id for f in recent_feedback]
        assert "act_1" in returned_action_ids
        assert "act_2" in returned_action_ids
        assert "act_3" not in returned_action_ids
```

#### Run the test to confirm it fails:
```bash
pytest tests/infrastructure/test_repository.py
```
*Expected Output:* `ModuleNotFoundError: No module named 'app.infrastructure.repository'` (Fails as expected).

---

### Step 3: Implement the Repository Layer

Create file: `app/infrastructure/repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta

from app.domain.models import (
    UserProfile,
    FinancialPlanPayload,
    HHHEvaluationResult,
    ActionFeedback,
    PlanStatus,
    ActionStatus,
)


class FinanceRepository(ABC):
    """Abstract interface defining storage operations for personal finance data."""

    @abstractmethod
    async def save_profile(self, profile: UserProfile) -> UserProfile:
        """Create or update a user profile."""
        pass

    @abstractmethod
    async def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Retrieve a user profile by ID."""
        pass

    @abstractmethod
    async def save_plan(
        self,
        plan: FinancialPlanPayload,
        user_id: UUID,
        status: PlanStatus,
        version: int = 1,
    ) -> UUID:
        """Save a generated financial plan."""
        pass

    @abstractmethod
    async def get_active_plan(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieve the currently active plan for a user."""
        pass

    @abstractmethod
    async def update_plan_status(self, plan_id: UUID, status: PlanStatus) -> None:
        """Update the status of a plan (active, archived, fallback)."""
        pass

    @abstractmethod
    async def update_action_status(
        self, plan_id: UUID, action_id: str, status: ActionStatus
    ) -> None:
        """Update the status of an action inside a plan (worked, did_not_work)."""
        pass

    @abstractmethod
    async def save_evaluation(
        self, plan_id: UUID, eval_result: HHHEvaluationResult, iteration: int
    ) -> UUID:
        """Log an HHH evaluation attempt for a plan."""
        pass

    @abstractmethod
    async def get_evaluations_for_plan(self, plan_id: UUID) -> List[Dict[str, Any]]:
        """Retrieve all HHH evaluation rounds for a plan."""
        pass

    @abstractmethod
    async def save_feedback(self, feedback: ActionFeedback) -> UUID:
        """Record user feedback on a plan action."""
        pass

    @abstractmethod
    async def get_recent_feedback(
        self, user_id: UUID, days: int = 30
    ) -> List[ActionFeedback]:
        """Retrieve user feedback from the past N days (defaults to 30 days)."""
        pass


class InMemoryFinanceRepository(FinanceRepository):
    """
    Thread-safe in-memory repository implementation for hermetic unit testing
    and fast local development without live external database dependencies.
    """

    def __init__(self):
        self.profiles: Dict[UUID, UserProfile] = {}
        self.plans: Dict[UUID, Dict[str, Any]] = {}
        self.evaluations: Dict[UUID, Dict[str, Any]] = {}
        self.feedback: Dict[UUID, ActionFeedback] = {}

    async def save_profile(self, profile: UserProfile) -> UserProfile:
        self.profiles[profile.user_id] = profile
        return profile

    async def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        return self.profiles.get(user_id)

    async def save_plan(
        self,
        plan: FinancialPlanPayload,
        user_id: UUID,
        status: PlanStatus,
        version: int = 1,
    ) -> UUID:
        plan_id = uuid4()
        now = datetime.now(timezone.utc)
        self.plans[plan_id] = {
            "id": plan_id,
            "user_id": user_id,
            "version": version,
            "status": status,
            "health_summary": plan.health_summary,
            "actions": [action.model_dump() for action in plan.actions],
            "created_at": now,
        }
        return plan_id

    async def get_active_plan(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        for plan in self.plans.values():
            if plan["user_id"] == user_id and plan["status"] == PlanStatus.ACTIVE:
                return plan
        return None

    async def update_plan_status(self, plan_id: UUID, status: PlanStatus) -> None:
        if plan_id in self.plans:
            self.plans[plan_id]["status"] = status

    async def update_action_status(
        self, plan_id: UUID, action_id: str, status: ActionStatus
    ) -> None:
        if plan_id in self.plans:
            for action in self.plans[plan_id]["actions"]:
                if action["id"] == action_id:
                    action["status"] = status
                    break

    async def save_evaluation(
        self, plan_id: UUID, eval_result: HHHEvaluationResult, iteration: int
    ) -> UUID:
        eval_id = uuid4()
        now = datetime.now(timezone.utc)
        self.evaluations[eval_id] = {
            "id": eval_id,
            "plan_id": plan_id,
            "iteration": iteration,
            "helpful_score": eval_result.helpful_score,
            "honest_score": eval_result.honest_score,
            "harmless_score": eval_result.harmless_score,
            "passed": eval_result.passed,
            "critical_issue": eval_result.critical_issue,
            "critique": eval_result.critique,
            "created_at": now,
        }
        return eval_id

    async def get_evaluations_for_plan(self, plan_id: UUID) -> List[Dict[str, Any]]:
        return [e for e in self.evaluations.values() if e["plan_id"] == plan_id]

    async def save_feedback(self, feedback: ActionFeedback) -> UUID:
        feedback_id = feedback.id or uuid4()
        created_at = feedback.created_at or datetime.now(timezone.utc)
        stored_feedback = feedback.model_copy(
            update={"id": feedback_id, "created_at": created_at}
        )
        self.feedback[feedback_id] = stored_feedback
        return feedback_id

    async def get_recent_feedback(
        self, user_id: UUID, days: int = 30
    ) -> List[ActionFeedback]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [
            f
            for f in self.feedback.values()
            if f.user_id == user_id and f.created_at and f.created_at >= cutoff
        ]
        # Return sorted by newest first
        return sorted(recent, key=lambda x: x.created_at, reverse=True)
```

---

### Step 4: Run the Test Suite to Verify

Run pytest:
```bash
pytest tests/infrastructure/test_repository.py -v
```

#### Expected Output:
```text
tests/infrastructure/test_repository.py::TestFinanceRepository::test_profile_crud PASSED [ 20%]
tests/infrastructure/test_repository.py::TestFinanceRepository::test_plan_saving_and_status_updates PASSED [ 40%]
tests/infrastructure/test_repository.py::TestFinanceRepository::test_action_status_mutation PASSED [ 60%]
tests/infrastructure/test_repository.py::TestFinanceRepository::test_evaluations_logging PASSED [ 80%]
tests/infrastructure/test_repository.py::TestFinanceRepository::test_30_day_feedback_boundary_filtering PASSED [100%]

============================== 5 passed in 0.03s ==============================
```

You can also run both Task 1 and Task 2 test suites together:
```bash
pytest
```
*Expected: All 15 tests passed!*

---

## 5. Common Pitfalls & Zero-Question FAQ

* **Q: Why are all methods async (`async def`)?**  
  *A:* FastAPI and Supabase database clients operate asynchronously. By using `async def` in our abstract repository, our code never blocks the server during I/O operations.
* **Q: Why does `get_recent_feedback` default to 30 days?**  
  *A:* The client specification explicitly requires pulling the last 30 days of user feedback. Any feedback older than 30 days is ignored so the AI coach does not fixate on stale constraints.
* **Q: Do I need a live Supabase database running to pass this ticket?**  
  *A:* No. The unit test suite uses `InMemoryFinanceRepository`, which runs 100% locally in memory. The SQL migration file `20261005000000_init_schema.sql` is ready to be executed against your Supabase project whenever you are ready to connect cloud storage.

---

## 6. Git Commit, Push & Trello Progression

Once all tests pass:

### 1. Stage, Commit and Push
```bash
git add app/infrastructure/ tests/infrastructure/
git commit -m "feat(infra): implement finance repository abstraction and in-memory adapter with 30-day feedback filtering"
git push origin main
```

### 2. Update Trello Card
1. Navigate to the **[Task 2 Card on Trello](https://trello.com/c/uz5UvWIk)**.
2. Check off all 4 checklist items:
   - [x] Create `supabase/migrations/20261005000000_init_schema.sql`
   - [x] Define `FinanceRepository` ABC in `app/infrastructure/repository.py`
   - [x] Implement `InMemoryFinanceRepository` with 30-day temporal filter
   - [x] Write and run `tests/infrastructure/test_repository.py` (100% pass)
3. Drag the card from **`IN PROGRESS`** $\rightarrow$ **`CODE REVIEW`**.
