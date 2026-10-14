# Task 3 Implementation Guide: Intake Service & 30-Day Feedback Retrieval

> **Document Status:** Complete & Verified  
> **Target Audience:** Implementer / Client / Coding Agent  
> **Estimated Time to Complete:** 15 minutes  
> **Prerequisites:** Task 1 (Domain Models) & Task 2 (Repository Layer) completed.

---

## Table of Contents
1. [Overview & User Story](#1-overview--user-story)
2. [The "WHY": The Prep Cook Analogy](#2-the-why-the-prep-cook-analogy)
3. [The "HOW": Aggregation & Markdown Formatting](#3-the-how-aggregation--markdown-formatting)
4. [Step-by-Step Technical Implementation (TDD)](#4-step-by-step-technical-implementation-tdd)
   - [Step 1: Write the Failing Test (`tests/services/test_intake_service.py`)](#step-1-write-the-failing-test)
   - [Step 2: Implement the Service (`app/services/intake_service.py`)](#step-2-implement-the-service)
   - [Step 3: Run the Test Suite to Verify](#step-3-run-the-test-suite-to-verify)
5. [Common Pitfalls & Zero-Question FAQ](#5-common-pitfalls--zero-question-faq)
6. [Git Commit, Push & Trello Progression](#6-git-commit-push--trello-progression)

---

## 1. Overview & User Story

### User Story
> **As a** financial planning service,  
> **I want** an Intake Service that retrieves the user's demographic profile and their past 30 days of action feedback, formatting it into a concise context payload,  
> **So that** the Planning Agent receives all necessary inputs and recent preferences in a single structured call without directly accessing the database.

### Deliverables
* `app/services/intake_service.py`:
  * `IntakeContext`: Pydantic model packaging `profile`, `recent_feedback`, and formatted `feedback_summary`.
  * `IntakeService`: Service class orchestrating repository calls and prompt formatting.
* `tests/services/test_intake_service.py`: Unit test suite testing complete context assembly, empty feedback handling, and missing profile exceptions.

---

## 2. The "WHY": The Prep Cook Analogy

In a restaurant kitchen, the **Head Chef (our Planning AI Agent)** shouldn't have to walk back to the pantry, find potatoes, wash them, and chop them.
If the Chef has to do all the prep work, orders take forever, mistakes happen, and the food burns.

Instead, the restaurant has a **Prep Cook (our `IntakeService`)**:
1. The Prep Cook walks over to the Filing Cabinet/Librarian (our `FinanceRepository`).
2. Gathers the ingredients:
   - The user's financial profile (income, debts, savings, goals).
   - The user's feedback from the last 30 days (what worked, what they disliked).
3. Formats and organizes everything neatly on a tray (`IntakeContext`).
4. Hands the tray directly to the Head Chef.

This keeps our AI code clean, testable, and focused strictly on financial strategy.

---

## 3. The "HOW": Aggregation & Markdown Formatting

### Data Assembly Flow
```text
                  ┌───────────────────────────────┐
                  │      IntakeService            │
                  └──────────────┬────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │ Calls repository:             │
                 │ 1. repo.get_profile(user_id)  │
                 │ 2. repo.get_recent_feedback() │
                 └───────────────┬───────────────┘
                                 │
                                 ▼
                 ┌───────────────────────────────┐
                 │    Format Feedback Summary    │
                 │  - Formats human-readable     │
                 │    markdown lines             │
                 └───────────────┬───────────────┘
                                 │
                                 ▼
                 ┌───────────────────────────────┐
                 │         IntakeContext         │
                 │  • profile: UserProfile       │
                 │  • recent_feedback: List[...] │
                 │  • feedback_summary: str      │
                 └───────────────────────────────┘
```

### The Formatted Feedback Summary Format
If feedback exists, it formats into readable markdown lines that can be directly dropped into the LLM prompt:
```text
### Recent User Feedback (Last 30 Days):
- Action [act_1]: SUCCESS/WORKED - Notes: Setup HYSA without issues
- Action [act_2]: REJECTED/DID NOT WORK - Notes: Minimum deposit was too high
```
If no feedback exists, `feedback_summary` is set cleanly to `None`. The AI will know not to assume prior preferences.

---

## 4. Step-by-Step Technical Implementation (TDD)

---

### Step 1: Write the Failing Test

Create file: `tests/services/test_intake_service.py`

```python
"""
Unit tests for IntakeService.
Verifies profile retrieval, feedback aggregation, and prompt summary formatting.
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta

from app.domain.models import (
    UserProfile,
    RiskAppetite,
    ActionFeedback,
)
from app.infrastructure.repository import InMemoryFinanceRepository
from app.services.intake_service import IntakeService, IntakeContext


@pytest.fixture
def repo():
    return InMemoryFinanceRepository()


@pytest.fixture
def intake_service(repo):
    return IntakeService(repo)


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


class TestIntakeService:
    @pytest.mark.asyncio
    async def test_get_intake_context_with_feedback(self, intake_service, repo, sample_profile):
        await repo.save_profile(sample_profile)
        now = datetime.now(timezone.utc)
        plan_id = uuid4()

        # Add 2 feedback items
        fb1 = ActionFeedback(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_1",
            outcome="worked",
            notes="Set up automated transfer",
            created_at=now - timedelta(days=5),
        )
        fb2 = ActionFeedback(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_2",
            outcome="did_not_work",
            notes="Minimum deposit too high",
            created_at=now - timedelta(days=12),
        )
        await repo.save_feedback(fb1)
        await repo.save_feedback(fb2)

        context = await intake_service.get_intake_context(sample_profile.user_id)

        assert isinstance(context, IntakeContext)
        assert context.profile.user_id == sample_profile.user_id
        assert len(context.recent_feedback) == 2
        assert context.feedback_summary is not None
        assert "### Recent User Feedback (Last 30 Days):" in context.feedback_summary
        assert "Action [act_1]: SUCCESS/WORKED" in context.feedback_summary
        assert "Action [act_2]: REJECTED/DID NOT WORK" in context.feedback_summary

    @pytest.mark.asyncio
    async def test_get_intake_context_zero_feedback(self, intake_service, repo, sample_profile):
        await repo.save_profile(sample_profile)

        context = await intake_service.get_intake_context(sample_profile.user_id)

        assert context.profile.user_id == sample_profile.user_id
        assert len(context.recent_feedback) == 0
        assert context.feedback_summary is None

    @pytest.mark.asyncio
    async def test_nonexistent_user_raises_value_error(self, intake_service):
        missing_id = uuid4()
        with pytest.raises(ValueError, match=f"Profile not found for user {missing_id}"):
            await intake_service.get_intake_context(missing_id)
```

#### Run the test to confirm it fails:
```bash
pytest tests/services/test_intake_service.py
```
*Expected Output:* `ModuleNotFoundError: No module named 'app.services.intake_service'` (Fails as expected).

---

### Step 2: Implement the Service

Create file: `app/services/intake_service.py`

```python
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel
from app.domain.models import UserProfile, ActionFeedback
from app.infrastructure.repository import FinanceRepository


class IntakeContext(BaseModel):
    """Encapsulates the complete intake payload required by the Planning Agent."""
    profile: UserProfile
    recent_feedback: List[ActionFeedback]
    feedback_summary: Optional[str] = None


class IntakeService:
    """Orchestrates intake retrieval and feedback prompt preparation."""

    def __init__(self, repo: FinanceRepository):
        self.repo = repo

    async def get_intake_context(self, user_id: UUID) -> IntakeContext:
        """
        Retrieves user profile and 30-day feedback, assembling them into an IntakeContext.
        Raises ValueError if the profile does not exist.
        """
        profile = await self.repo.get_profile(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")

        feedback = await self.repo.get_recent_feedback(user_id, days=30)
        summary = self.format_feedback_summary(feedback)

        return IntakeContext(
            profile=profile,
            recent_feedback=feedback,
            feedback_summary=summary,
        )

    def format_feedback_summary(self, feedback: List[ActionFeedback]) -> Optional[str]:
        """Formats feedback items into clean markdown for injection into AI prompts."""
        if not feedback:
            return None

        lines = ["### Recent User Feedback (Last 30 Days):"]
        for f in feedback:
            status = "SUCCESS/WORKED" if f.outcome == "worked" else "REJECTED/DID NOT WORK"
            notes_part = f" - Notes: {f.notes}" if f.notes else ""
            lines.append(f"- Action [{f.action_id}]: {status}{notes_part}")

        return "\n".join(lines)
```

---

### Step 3: Run the Test Suite to Verify

Run pytest:
```bash
pytest tests/services/test_intake_service.py -v
```

#### Expected Output:
```text
tests/services/test_intake_service.py::TestIntakeService::test_get_intake_context_with_feedback PASSED [ 33%]
tests/services/test_intake_service.py::TestIntakeService::test_get_intake_context_zero_feedback PASSED [ 66%]
tests/services/test_intake_service.py::TestIntakeService::test_nonexistent_user_raises_value_error PASSED [100%]

============================== 3 passed in 0.02s ==============================
```

Run full suite:
```bash
pytest
```
*Expected: 18 passed across all domain, repository, and service tests!*

---

## 5. Common Pitfalls & Zero-Question FAQ

* **Q: Why does `IntakeService` take `repo: FinanceRepository` in `__init__`?**  
  *A:* Dependency Injection. This allows us to pass `InMemoryFinanceRepository` in unit tests, or `SupabaseFinanceRepository` in production, without changing the service code.
* **Q: What happens if a user is brand new and has no feedback?**  
  *A:* `recent_feedback` is an empty list `[]`, and `feedback_summary` is `None`. The Planning Agent in Task 4 will see that no feedback exists and will create the first plan without inventing preferences.

---

## 6. Git Commit, Push & Trello Progression

Once all tests pass:

### 1. Stage, Commit and Push
```bash
git add app/services/ tests/services/
git commit -m "feat(services): implement intake service with prompt summary formatting"
git push origin main
```

### 2. Update Trello Card
1. Navigate to **[Task 3 Card on Trello](https://trello.com/c/Kw34ahs2)**.
2. Check off all checklist items.
3. Move the card from **`IN PROGRESS`** $\rightarrow$ **`CODE REVIEW`**.
