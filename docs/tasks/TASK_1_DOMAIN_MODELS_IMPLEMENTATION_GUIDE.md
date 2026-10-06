# Task 1 Implementation Guide: Domain Models, Curated Benchmarks & Persona Fixtures

> **Document Status:** Complete & Verified  
> **Target Audience:** Implementer / Client / Coding Agent  
> **Estimated Time to Complete:** 15–20 minutes  
> **Prerequisites:** Python 3.11+ environment with dependencies installed from `requirements.txt`.

---

## Table of Contents
1. [Overview & User Story](#1-overview--user-story)
2. [The "WHY": Architectural & Domain Rationale](#2-the-why-architectural--domain-rationale)
3. [The "HOW": Conceptual Architecture & Data Flow](#3-the-how-conceptual-architecture--data-flow)
4. [Step-by-Step Technical Implementation (TDD)](#4-step-by-step-technical-implementation-tdd)
   - [Step 1: Write the Failing Test (`tests/domain/test_personas.py`)](#step-1-write-the-failing-test)
   - [Step 2: Implement Domain Models (`app/domain/models.py`)](#step-2-implement-domain-models)
   - [Step 3: Implement Curated Benchmarks (`app/domain/benchmarks.py`)](#step-3-implement-curated-benchmarks)
   - [Step 4: Implement Standard Personas (`app/domain/personas.py`)](#step-4-implement-standard-personas)
   - [Step 5: Run the Test Suite to Verify](#step-5-run-the-test-suite-to-verify)
5. [Common Pitfalls & Zero-Question FAQ](#5-common-pitfalls--zero-question-faq)
6. [Git Commit, Push & Trello Progression](#6-git-commit-push--trello-progression)

---

## 1. Overview & User Story

### User Story
> **As an** AI Personal Finance Coach platform developer,  
> **I want** strongly-typed domain models, static macroeconomic benchmarks, and representative test personas (Age 28 Aggressive, Age 45 Moderate, Age 62 Conservative),  
> **So that** the Planning Agent, HHH Evaluator Agent, and storage layers exchange strictly validated data contracts with zero runtime type ambiguity and without fragile external API dependencies.

### Deliverables
* `app/domain/models.py`: Core Pydantic v2 entities, value objects, and domain enums.
* `app/domain/benchmarks.py`: Static macroeconomic benchmark constants.
* `app/domain/personas.py`: Standard test fixtures representing the 3 client life stages.
* `tests/domain/test_personas.py`: Full pytest unit test suite validating constraints, edge cases, and schema behavior.

---

## 2. The "WHY": Architectural & Domain Rationale

Before writing code, it is critical to understand **why** these files exist and **why** they are built first:

### 1. Why Domain Models First?
In Clean Architecture, the **Domain Layer** is the innermost layer. It has zero dependencies on external databases, frameworks, or APIs. By defining domain entities first:
* Both the database repository (Task 2) and the AI planning prompts (Task 4) have a single source of truth for field names, validation constraints, and types.
* We eliminate runtime bugs (e.g., negative incomes, retirement target younger than current age, or invalid risk appetite strings).

### 2. Why Pydantic v2?
* **High Performance:** Pydantic v2's core is written in Rust, providing fast serialization.
* **Strict Runtime Validation:** Automatically enforces constraints such as `conint(ge=18, le=120)` and `min_length=3, max_length=5` on plan actions.
* **LLM Schema Generation:** Pydantic models automatically export OpenAPI / JSON schemas, which are directly consumed by Anthropic Claude for structured JSON generation.

### 3. Why Curated Benchmarks instead of Live Scraping APIs?
* External financial market APIs (or web scraping) introduce rate limits, authentication complexity, network latency, and non-deterministic test failures.
* For an MVP focused on proving the **feedback-driven AI workflow and HHH safety**, curated constants (HYSA APY 4.5%, Equity return 7.5%, 3–6 month emergency reserve rule, 4% safe withdrawal rate) provide realistic, deterministic baseline numbers that the planner and evaluator can reliably ground against.

### 4. Why These Three Specific Personas?
The client brief mandates that the system must **not** produce identical advice across different demographics. These 3 personas test distinct ends of the financial spectrum:
* **Persona 1 (28yo, $75k income, Aggressive):** Long 32-year horizon, student loan debt $\rightarrow$ Must focus on wealth accumulation, aggressive equity compounding, and loan management.
* **Persona 2 (45yo, $150k income, Moderate):** 17-year horizon, mortgage $\rightarrow$ Must balance retirement catch-up with children's education.
* **Persona 3 (62yo, $110k income, Conservative, $1M portfolio):** 5-year horizon $\rightarrow$ Must prioritize capital preservation, fixed income yields, and sequence-of-returns protection. High-risk advice here is an immediate safety violation.

---

## 3. The "HOW": Conceptual Architecture & Data Flow

```text
       ┌────────────────────────┐
       │   Client Intake / UI   │
       └───────────┬────────────┘
                   │  Produces
                   ▼
       ┌────────────────────────┐
       │      UserProfile       │ (Age, Income, Expenses, Debt, Risk, Goals)
       └───────────┬────────────┘
                   │
                   ├──────────────────────────────┐
                   ▼                              ▼
       ┌────────────────────────┐    ┌────────────────────────┐
       │     Planning Agent     │    │  CuratedMarketBenchmark│ (HYSA 4.5%, S&P 7.5%)
       └───────────┬────────────┘    └────────────────────────┘
                   │  Generates
                   ▼
       ┌────────────────────────┐
       │  FinancialPlanPayload  │ (health_summary + 3 to 5 PlanActions)
       └───────────┬────────────┘
                   │
                   ▼
       ┌────────────────────────┐
       │   HHH Evaluator Agent  │
       └───────────┬────────────┘
                   │  Scores
                   ▼
       ┌────────────────────────┐
       │  HHHEvaluationResult   │ (Helpful 0-4, Honest 0-4, Harmless 0-4, Passed)
       └───────────┬────────────┘
                   │  If Passed
                   ▼
       ┌────────────────────────┐
       │     ActionFeedback     │ (User marks Worked / Did Not Work per action)
       └────────────────────────┘
```

---

## 4. Step-by-Step Technical Implementation (TDD)

Follow Test-Driven Development (TDD) strictly: write the failing test first, verify the failure, implement the minimum code to pass, and verify test success.

---

### Step 1: Write the Failing Test

Create file: `tests/domain/test_personas.py`

```python
"""
Unit tests for domain models, benchmarks, and standard test personas.
Verifies Pydantic v2 validation constraints, benchmark constants, and persona fixtures.
"""
import pytest
from uuid import UUID
from pydantic import ValidationError

from app.domain.models import (
    RiskAppetite,
    ActionCategory,
    ActionStatus,
    PlanStatus,
    UserProfile,
    PlanAction,
    FinancialPlanPayload,
    HHHEvaluationResult,
    ActionFeedback,
)
from app.domain.benchmarks import CURATED_MARKET_BENCHMARKS
from app.domain.personas import (
    PERSONA_1,
    PERSONA_2,
    PERSONA_3,
    TEST_PERSONAS,
)


class TestDomainModels:
    def test_valid_user_profile_creation(self):
        profile = UserProfile(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            age=30,
            annual_income=80000.0,
            monthly_expenses=3500.0,
            savings=15000.0,
            investments=25000.0,
            debt=5000.0,
            risk_appetite=RiskAppetite.MODERATE,
            investment_horizon_years=20,
            retirement_age_target=65,
            primary_goal="Retirement growth",
            monthly_investment_capacity=1200.0,
        )
        assert profile.age == 30
        assert profile.risk_appetite == RiskAppetite.MODERATE
        assert profile.annual_income == 80000.0

    def test_user_profile_age_constraints(self):
        # Age below 18 must fail
        with pytest.raises(ValidationError):
            UserProfile(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                age=17,
                annual_income=50000.0,
                monthly_expenses=2000.0,
                risk_appetite=RiskAppetite.AGGRESSIVE,
                investment_horizon_years=30,
                retirement_age_target=60,
                primary_goal="Wealth building",
                monthly_investment_capacity=500.0,
            )

        # Age above 120 must fail
        with pytest.raises(ValidationError):
            UserProfile(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                age=125,
                annual_income=50000.0,
                monthly_expenses=2000.0,
                risk_appetite=RiskAppetite.AGGRESSIVE,
                investment_horizon_years=10,
                retirement_age_target=130,
                primary_goal="Wealth building",
                monthly_investment_capacity=500.0,
            )

    def test_user_profile_negative_financials_fail(self):
        # Negative income must fail
        with pytest.raises(ValidationError):
            UserProfile(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                age=30,
                annual_income=-5000.0,
                monthly_expenses=2000.0,
                risk_appetite=RiskAppetite.CONSERVATIVE,
                investment_horizon_years=10,
                retirement_age_target=65,
                primary_goal="Preservation",
                monthly_investment_capacity=500.0,
            )

    def test_plan_action_count_constraint(self):
        def make_action(act_id: str):
            return PlanAction(
                id=act_id,
                category=ActionCategory.EMERGENCY_FUND,
                title="Emergency Reserve",
                recommendation="Save 3 months expenses",
                rationale="Liquidity safety",
                assumptions="HYSA APY 4.5%",
                effort="low",
                status=ActionStatus.PENDING,
            )

        # Less than 3 actions must fail
        with pytest.raises(ValidationError):
            FinancialPlanPayload(
                health_summary="Solid foundation",
                actions=[make_action("act_1"), make_action("act_2")],
            )

        # Valid 3 to 5 actions must pass
        valid_plan = FinancialPlanPayload(
            health_summary="Solid foundation",
            actions=[make_action("act_1"), make_action("act_2"), make_action("act_3")],
        )
        assert len(valid_plan.actions) == 3

        # More than 5 actions must fail
        with pytest.raises(ValidationError):
            FinancialPlanPayload(
                health_summary="Too many actions",
                actions=[make_action(f"act_{i}") for i in range(1, 7)],
            )

    def test_hhh_evaluation_result_bounds(self):
        valid_eval = HHHEvaluationResult(
            helpful_score=4,
            honest_score=3,
            harmless_score=4,
            passed=True,
            critical_issue=False,
            critique=None,
        )
        assert valid_eval.passed is True

        # Score > 4 must fail
        with pytest.raises(ValidationError):
            HHHEvaluationResult(
                helpful_score=5,
                honest_score=3,
                harmless_score=4,
                passed=False,
            )


class TestCuratedBenchmarks:
    def test_curated_benchmarks_constants(self):
        assert CURATED_MARKET_BENCHMARKS.hysa_apy == 0.045
        assert CURATED_MARKET_BENCHMARKS.historical_equity_return == 0.075
        assert CURATED_MARKET_BENCHMARKS.standard_emergency_fund.min_months == 3
        assert CURATED_MARKET_BENCHMARKS.standard_emergency_fund.max_months == 6
        assert CURATED_MARKET_BENCHMARKS.safe_withdrawal_rate == 0.04
        assert CURATED_MARKET_BENCHMARKS.last_updated == "2026-10-01"


class TestPersonas:
    def test_persona_count(self):
        assert len(TEST_PERSONAS) == 3

    def test_persona_1_younger_wealth_builder(self):
        assert PERSONA_1.age == 28
        assert PERSONA_1.annual_income == 75000.0
        assert PERSONA_1.monthly_expenses == 4000.0
        assert PERSONA_1.savings == 20000.0
        assert PERSONA_1.investments == 15000.0
        assert PERSONA_1.debt == 10000.0
        assert PERSONA_1.risk_appetite == RiskAppetite.AGGRESSIVE
        assert PERSONA_1.investment_horizon_years == 32
        assert PERSONA_1.retirement_age_target == 60
        assert PERSONA_1.monthly_investment_capacity == 1000.0

    def test_persona_2_mid_career(self):
        assert PERSONA_2.age == 45
        assert PERSONA_2.annual_income == 150000.0
        assert PERSONA_2.monthly_expenses == 7000.0
        assert PERSONA_2.savings == 100000.0
        assert PERSONA_2.investments == 350000.0
        assert PERSONA_2.debt == 250000.0
        assert PERSONA_2.risk_appetite == RiskAppetite.MODERATE
        assert PERSONA_2.investment_horizon_years == 17
        assert PERSONA_2.retirement_age_target == 62
        assert PERSONA_2.monthly_investment_capacity == 3000.0

    def test_persona_3_near_retirement(self):
        assert PERSONA_3.age == 62
        assert PERSONA_3.annual_income == 110000.0
        assert PERSONA_3.monthly_expenses == 5500.0
        assert PERSONA_3.savings == 300000.0
        assert PERSONA_3.investments == 1000000.0
        assert PERSONA_3.debt == 50000.0
        assert PERSONA_3.risk_appetite == RiskAppetite.CONSERVATIVE
        assert PERSONA_3.investment_horizon_years == 5
        assert PERSONA_3.retirement_age_target == 65
        assert PERSONA_3.monthly_investment_capacity == 1500.0
```

#### Run the test to confirm it fails:
```bash
pytest tests/domain/test_personas.py
```
*Expected Output:* `ModuleNotFoundError: No module named 'app.domain.models'` (Fails as expected).

---

### Step 2: Implement Domain Models

Create file: `app/domain/models.py`

```python
from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, conint
from datetime import datetime
from uuid import UUID


class RiskAppetite(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class ActionCategory(str, Enum):
    EMERGENCY_FUND = "emergency_fund"
    DEBT_MANAGEMENT = "debt_management"
    INVESTMENT = "investment"
    BUDGETING = "budgeting"


class ActionStatus(str, Enum):
    PENDING = "pending"
    WORKED = "worked"
    DID_NOT_WORK = "did_not_work"


class PlanStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    FALLBACK = "fallback"


class UserProfile(BaseModel):
    user_id: UUID
    age: conint(ge=18, le=120)
    annual_income: float = Field(..., ge=0)
    monthly_expenses: float = Field(..., ge=0)
    savings: float = Field(default=0.0, ge=0)
    investments: float = Field(default=0.0, ge=0)
    debt: float = Field(default=0.0, ge=0)
    debt_details: Optional[str] = None
    risk_appetite: RiskAppetite
    investment_horizon_years: conint(ge=0)
    retirement_age_target: conint(ge=18)
    primary_goal: str
    monthly_investment_capacity: float = Field(..., ge=0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PlanAction(BaseModel):
    id: str = Field(..., description="Unique action identifier, e.g. act_1")
    category: ActionCategory
    title: str = Field(..., max_length=120)
    recommendation: str
    rationale: str
    assumptions: str
    effort: Literal["low", "medium", "high"]
    status: ActionStatus = ActionStatus.PENDING


class FinancialPlanPayload(BaseModel):
    health_summary: str
    actions: List[PlanAction] = Field(..., min_length=3, max_length=5)


class HHHEvaluationResult(BaseModel):
    helpful_score: conint(ge=0, le=4)
    honest_score: conint(ge=0, le=4)
    harmless_score: conint(ge=0, le=4)
    passed: bool
    critical_issue: bool = False
    critique: Optional[str] = None


class ActionFeedback(BaseModel):
    id: Optional[UUID] = None
    user_id: UUID
    plan_id: UUID
    action_id: str
    outcome: Literal["worked", "did_not_work"]
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
```

---

### Step 3: Implement Curated Benchmarks

Create file: `app/domain/benchmarks.py`

```python
from pydantic import BaseModel


class EmergencyFundRange(BaseModel):
    min_months: int = 3
    max_months: int = 6


class CuratedMarketBenchmarks(BaseModel):
    hysa_apy: float = 0.045                    # 4.5% High-Yield Savings Benchmark
    historical_equity_return: float = 0.075    # 7.5% Long-term diversified equity index
    standard_emergency_fund: EmergencyFundRange = EmergencyFundRange()
    safe_withdrawal_rate: float = 0.04         # 4.0% rule for retirement income
    last_updated: str = "2026-10-01"


CURATED_MARKET_BENCHMARKS = CuratedMarketBenchmarks()
```

---

### Step 4: Implement Standard Personas

Create file: `app/domain/personas.py`

```python
from uuid import UUID
from app.domain.models import UserProfile, RiskAppetite

# Persona 1: Younger wealth-building user (Age 28, Aggressive, 30+ yr horizon)
PERSONA_1 = UserProfile(
    user_id=UUID("00000000-0000-0000-0000-000000000001"),
    age=28,
    annual_income=75000.0,
    monthly_expenses=4000.0,
    savings=20000.0,
    investments=15000.0,
    debt=10000.0,
    debt_details="Student loan at 4.5% interest",
    risk_appetite=RiskAppetite.AGGRESSIVE,
    investment_horizon_years=32,
    retirement_age_target=60,
    primary_goal="Wealth building and long-term equity compounding",
    monthly_investment_capacity=1000.0,
)

# Persona 2: Mid-career user (Age 45, Moderate, 15-20 yr horizon)
PERSONA_2 = UserProfile(
    user_id=UUID("00000000-0000-0000-0000-000000000002"),
    age=45,
    annual_income=150000.0,
    monthly_expenses=7000.0,
    savings=100000.0,
    investments=350000.0,
    debt=250000.0,
    debt_details="Mortgage balance at 3.5% interest",
    risk_appetite=RiskAppetite.MODERATE,
    investment_horizon_years=17,
    retirement_age_target=62,
    primary_goal="Retirement catch-up and children's college funding",
    monthly_investment_capacity=3000.0,
)

# Persona 3: Near-retirement user (Age 62, Conservative, 5-7 yr horizon)
PERSONA_3 = UserProfile(
    user_id=UUID("00000000-0000-0000-0000-000000000003"),
    age=62,
    annual_income=110000.0,
    monthly_expenses=5500.0,
    savings=300000.0,
    investments=1000000.0,
    debt=50000.0,
    debt_details="Remaining mortgage balance",
    risk_appetite=RiskAppetite.CONSERVATIVE,
    investment_horizon_years=5,
    retirement_age_target=65,
    primary_goal="Capital preservation and stable retirement income",
    monthly_investment_capacity=1500.0,
)

TEST_PERSONAS = [PERSONA_1, PERSONA_2, PERSONA_3]
```

---

### Step 5: Run the Test Suite to Verify

Run pytest from the repository root:
```bash
pytest tests/domain/test_personas.py -v
```

#### Expected Output:
```text
tests/domain/test_personas.py::TestDomainModels::test_valid_user_profile_creation PASSED
tests/domain/test_personas.py::TestDomainModels::test_user_profile_age_constraints PASSED
tests/domain/test_personas.py::TestDomainModels::test_user_profile_negative_financials_fail PASSED
tests/domain/test_personas.py::TestDomainModels::test_plan_action_count_constraint PASSED
tests/domain/test_personas.py::TestDomainModels::test_hhh_evaluation_result_bounds PASSED
tests/domain/test_personas.py::TestCuratedBenchmarks::test_curated_benchmarks_constants PASSED
tests/domain/test_personas.py::TestPersonas::test_persona_count PASSED
tests/domain/test_personas.py::TestPersonas::test_persona_1_younger_wealth_builder PASSED
tests/domain/test_personas.py::TestPersonas::test_persona_2_mid_career PASSED
tests/domain/test_personas.py::TestPersonas::test_persona_3_near_retirement PASSED

============================== 10 passed in 0.05s ==============================
```

---

## 5. Common Pitfalls & Zero-Question FAQ

* **Q: Why are enums inheriting from `(str, Enum)`?**  
  *A:* Inheriting from `str` ensures that when Pydantic models are serialized to JSON (for API responses or LLM prompts), they serialize cleanly as strings (e.g. `"aggressive"`) rather than complex enum objects.
* **Q: What if I get a `ModuleNotFoundError: No module named 'app'`?**  
  *A:* Ensure your virtual environment is active and you are executing `pytest` from the root of the project directory where `app/` is located. You can also run: `python -m pytest tests/domain/test_personas.py`.
* **Q: Can `FinancialPlanPayload` have 2 or 6 actions?**  
  *A:* No. The specification strictly bounds generated plans to 3 to 5 discrete actions (`min_length=3, max_length=5`). Fewer is insufficient; more overwhelms the user.
* **Q: Does this task connect to Supabase or call OpenAI/Anthropic APIs?**  
  *A:* No. Task 1 is pure domain modeling and fixtures. It requires zero network calls and runs 100% locally.

---

## 6. Git Commit, Push & Trello Progression

Once all 10 tests in `test_personas.py` pass:

### 1. Stage and Commit Changes
```bash
git add app/domain/ tests/domain/
git commit -m "feat(domain): implement Pydantic domain models, benchmarks, and test personas"
git push origin main
```

### 2. Update Trello Card
1. Navigate to the **[Task 1 Card on Trello](https://trello.com/c/A6X4cukl)**.
2. Check off all 4 checklist items:
   - [x] Create `app/domain/models.py` with Pydantic v2 schemas and enums
   - [x] Create `app/domain/benchmarks.py` with CURATED_MARKET_BENCHMARKS constants
   - [x] Create `app/domain/personas.py` with Personas 1, 2, and 3
   - [x] Write and run `tests/domain/test_personas.py` (100% pass)
3. Drag the card from **`IN PROGRESS`** $\rightarrow$ **`CODE REVIEW`**.
