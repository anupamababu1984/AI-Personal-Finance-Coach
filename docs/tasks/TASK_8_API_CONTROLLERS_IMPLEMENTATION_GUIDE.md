# Task 8 Implementation Guide: FastAPI Endpoints & API Controllers

> **Document Status:** Complete & Verified  
> **Target Audience:** Implementer / Client / Coding Agent  
> **Estimated Time to Complete:** 15–20 minutes  
> **Prerequisites:** Tasks 1 through 7 completed (Domain models, repository, intake service, planning agent, evaluator agent, workflow engine, and feedback service available).

---

## Table of Contents
1. [Overview & User Story](#1-overview--user-story)
2. [The "WHY": The Drive-Thru Window Analogy](#2-the-why-the-drive-thru-window-analogy)
3. [The "HOW": REST API Architecture & Dependency Injection](#3-the-how-rest-api-architecture--dependency-injection)
4. [Step-by-Step Technical Implementation (TDD)](#4-step-by-step-technical-implementation-tdd)
   - [Step 1: Write the Failing Test (`tests/api/test_routes.py`)](#step-1-write-the-failing-test)
   - [Step 2: Implement Dependency Container (`app/core/deps.py`)](#step-2-implement-dependency-container)
   - [Step 3: Implement API Route Handlers (`app/api/v1/`)](#step-3-implement-api-route-handlers)
   - [Step 4: Implement FastAPI Factory (`app/main.py`)](#step-4-implement-fastapi-factory)
   - [Step 5: Run the Test Suite to Verify](#step-5-run-the-test-suite-to-verify)
5. [Common Pitfalls & Zero-Question FAQ](#5-common-pitfalls--zero-question-faq)
6. [Git Commit, Push & Trello Progression](#6-git-commit-push--trello-progression)

---

## 1. Overview & User Story

### User Story
> **As a** frontend developer or client,  
> **I want** documented, type-safe FastAPI REST endpoints under `/api/v1`,  
> **So that** our web dashboard can load demo personas, submit intake profiles, trigger plan generation, view active plans, and log action feedback over standard HTTP/JSON.

### Deliverables
* `app/core/deps.py`: Dependency injection providers for `FinanceRepository`, `IntakeService`, `WorkflowEngine`, and `FeedbackService`.
* `app/api/v1/intake.py`: Routes for `GET /api/v1/personas` and `POST /api/v1/intake`.
* `app/api/v1/plans.py`: Routes for `POST /api/v1/plans/generate` and `GET /api/v1/plans/{user_id}/active`.
* `app/api/v1/feedback.py`: Route for `POST /api/v1/feedback`.
* `app/api/v1/router.py`: Aggregator router mounting all v1 endpoints.
* `app/main.py`: FastAPI application factory with CORS middleware and OpenAPI metadata.
* `tests/api/test_routes.py`: Pytest suite using `TestClient` exercising all endpoints, status codes, and input validation errors.

---

## 2. The "WHY": The Drive-Thru Window Analogy

In Tasks 1 through 7, we built our entire **Kitchen and Engine**:
* Our digital recipes & forms (`domain`)
* Our pantry & filing cabinet (`infrastructure/repository`)
* Our prep cook (`services/intake_service`)
* Our head chef (`agents/planning_agent`)
* Our food critic (`agents/hhh_evaluator_agent`)
* Our general manager (`services/workflow_engine`)
* Our customer feedback notebook (`services/feedback_service`)

Right now, all of this works in Python, but **there is no window open to the outside world!**
A web browser or mobile app cannot talk directly to Python classes.

**Task 8 builds the Drive-Thru Window (The REST API):**
* Any frontend (Next.js, React, mobile app, or curl command) can send standard HTTP requests.
* FastAPI automatically checks all inputs with Pydantic and returns clean, documented JSON responses.
* It auto-generates interactive API documentation at `http://localhost:8000/docs`!

---

## 3. The "HOW": REST API Architecture & Dependency Injection

```text
  ┌────────────────────────────────────────────────────────┐
  │                 Web Frontend / Postman                 │
  └───────────────────────────┬────────────────────────────┘
                              │ HTTPS / REST (JSON)
  ┌───────────────────────────▼────────────────────────────┐
  │                   FastAPI Application                  │
  │                      (`app/main.py`)                   │
  └───────────────────────────┬────────────────────────────┘
                              │ Routes to /api/v1
  ┌───────────────────────────▼────────────────────────────┐
  │                  Aggregator Router                     │
  │                (`app/api/v1/router.py`)                │
  └───────────────┬───────────────────┬────────────────────┘
                  │                   │
                  ▼                   ▼
     ┌────────────────────────┐  ┌────────────────────────┐
     │      Intake Router     │  │      Plans Router      │
     │ GET  /api/v1/personas  │  │ POST /api/v1/plans/    │
     │ POST /api/v1/intake    │  │        generate        │
     └────────────────────────┘  │ GET  /api/v1/plans/    │
                  │              │        {id}/active     │
                  ▼              └────────────────────────┘
     ┌────────────────────────┐               │
     │    Feedback Router     │               ▼
     │ POST /api/v1/feedback  │  ┌────────────────────────┐
     └────────────────────────┘  │      Dependencies      │
                                 │   (`app/core/deps.py`) │
                                 │   Provides repo & svcs │
                                 └────────────────────────┘
```

---

## 4. Step-by-Step Technical Implementation (TDD)

---

### Step 1: Write the Failing Test

Create file: `tests/api/test_routes.py`

```python
"""
Integration tests for FastAPI REST endpoints using TestClient.
Verifies all /api/v1 endpoints, status codes, input validations, and OpenAPI generation.
"""
import pytest
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.domain.personas import PERSONA_1
from app.domain.models import (
    UserProfile,
    RiskAppetite,
    PlanStatus,
    ActionCategory,
    ActionStatus,
    FinancialPlanPayload,
    PlanAction,
)
from app.core.deps import get_repository, get_workflow_engine
from app.infrastructure.repository import InMemoryFinanceRepository


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_repo():
    return InMemoryFinanceRepository()


class DummyWorkflowEngine:
    """Mock engine for predictable HTTP plan generation testing."""

    def __init__(self, repo):
        self.repo = repo

    async def run(self, user_id: UUID):
        plan_id = uuid4()
        return {
            "plan_id": str(plan_id),
            "status": "active",
            "health_summary": "Strong growth outlook.",
            "actions": [
                {
                    "id": "act_1",
                    "category": "emergency_fund",
                    "title": "HYSA Buffer",
                    "recommendation": "Save $500/mo.",
                    "rationale": "Buffer",
                    "assumptions": "4.5% APY",
                    "effort": "low",
                    "status": "pending",
                },
                {
                    "id": "act_2",
                    "category": "investment",
                    "title": "Index Fund",
                    "recommendation": "Invest $300/mo.",
                    "rationale": "Compounding",
                    "assumptions": "7.5% return",
                    "effort": "medium",
                    "status": "pending",
                },
                {
                    "id": "act_3",
                    "category": "debt_management",
                    "title": "Clear Loan",
                    "recommendation": "Pay $200/mo.",
                    "rationale": "Debt payoff",
                    "assumptions": "4.5% rate",
                    "effort": "medium",
                    "status": "pending",
                },
            ],
            "evaluations": [
                {
                    "iteration": 0,
                    "helpful_score": 4,
                    "honest_score": 4,
                    "harmless_score": 4,
                    "passed": True,
                    "critical_issue": False,
                    "critique": None,
                }
            ],
        }


class TestApiRoutes:
    def test_openapi_schema_endpoint(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "AI Personal Finance Coach API"

    def test_get_personas_endpoint(self, client):
        response = client.get("/api/v1/personas")
        assert response.status_code == 200
        personas = response.json()
        assert len(personas) == 3
        assert personas[0]["age"] == 28
        assert personas[1]["age"] == 45
        assert personas[2]["age"] == 62

    def test_post_intake_valid_profile(self, client):
        payload = PERSONA_1.model_dump(mode="json")
        response = client.post("/api/v1/intake", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["profile"]["age"] == 28

    def test_post_intake_invalid_age_returns_422(self, client):
        payload = PERSONA_1.model_dump(mode="json")
        payload["age"] = 16  # Invalid: age < 18
        response = client.post("/api/v1/intake", json=payload)
        assert response.status_code == 422

    def test_post_generate_plan_endpoint(self, client, mock_repo):
        # Override dependency with dummy engine
        dummy_engine = DummyWorkflowEngine(mock_repo)
        app.dependency_overrides[get_workflow_engine] = lambda: dummy_engine

        try:
            user_id = str(uuid4())
            response = client.post("/api/v1/plans/generate", json={"user_id": user_id})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "active"
            assert len(data["actions"]) == 3
            assert data["evaluations"][0]["passed"] is True
        finally:
            app.dependency_overrides.clear()

    def test_post_feedback_endpoint(self, client, mock_repo):
        app.dependency_overrides[get_repository] = lambda: mock_repo

        try:
            # First save a plan so feedback can update it
            user_id = uuid4()
            plan_payload = FinancialPlanPayload(
                health_summary="Solid foundation.",
                actions=[
                    PlanAction(
                        id="act_1",
                        category=ActionCategory.EMERGENCY_FUND,
                        title="HYSA Buffer",
                        recommendation="Save $500",
                        rationale="Buffer",
                        assumptions="4.5%",
                        effort="low",
                        status=ActionStatus.PENDING,
                    ),
                    PlanAction(
                        id="act_2",
                        category=ActionCategory.DEBT_MANAGEMENT,
                        title="Loan",
                        recommendation="Pay $200",
                        rationale="Clear debt",
                        assumptions="4.5%",
                        effort="medium",
                        status=ActionStatus.PENDING,
                    ),
                    PlanAction(
                        id="act_3",
                        category=ActionCategory.INVESTMENT,
                        title="Index",
                        recommendation="Invest $300",
                        rationale="Growth",
                        assumptions="7.5%",
                        effort="medium",
                        status=ActionStatus.PENDING,
                    ),
                ],
            )
            # Synchronous setup using repo in event loop
            import asyncio
            plan_id = asyncio.run(mock_repo.save_plan(plan_payload, user_id, status=PlanStatus.ACTIVE))

            feedback_payload = {
                "user_id": str(user_id),
                "plan_id": str(plan_id),
                "action_id": "act_1",
                "outcome": "worked",
                "notes": "Opened account seamlessly",
            }
            response = client.post("/api/v1/feedback", json=feedback_payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "recorded"
            assert "feedback_id" in data
        finally:
            app.dependency_overrides.clear()

    def test_get_active_plan_not_found(self, client):
        missing_id = str(uuid4())
        response = client.get(f"/api/v1/plans/{missing_id}/active")
        assert response.status_code == 404
        assert response.json()["detail"] == "No active plan found for user"
```

#### Run the test to confirm it fails:
```bash
pytest tests/api/test_routes.py
```
*Expected Output:* `ModuleNotFoundError: No module named 'app.main'` or `app.core.deps` (Fails as expected).

---

### Step 2: Implement Dependency Container

Create file: `app/core/deps.py`

```python
from app.infrastructure.repository import FinanceRepository, InMemoryFinanceRepository
from app.domain.benchmarks import CURATED_MARKET_BENCHMARKS
from app.infrastructure.llm_client import MockLLMClient
from app.services.intake_service import IntakeService
from app.agents.planning_agent import PlanningAgent
from app.agents.hhh_evaluator_agent import HHHEvaluatorAgent
from app.services.workflow_engine import WorkflowEngine
from app.services.feedback_service import FeedbackService

# Global in-memory singleton for development and testing
_global_repository = InMemoryFinanceRepository()


def get_repository() -> FinanceRepository:
    """Returns the database repository instance."""
    return _global_repository


def get_intake_service() -> IntakeService:
    repo = get_repository()
    return IntakeService(repo=repo)


def get_planning_agent() -> PlanningAgent:
    llm = MockLLMClient()
    return PlanningAgent(llm_client=llm, benchmarks=CURATED_MARKET_BENCHMARKS)


def get_hhh_evaluator_agent() -> HHHEvaluatorAgent:
    llm = MockLLMClient()
    return HHHEvaluatorAgent(llm_client=llm)


def get_workflow_engine() -> WorkflowEngine:
    repo = get_repository()
    intake_svc = get_intake_service()
    planner = get_planning_agent()
    evaluator = get_hhh_evaluator_agent()
    return WorkflowEngine(
        intake_service=intake_svc,
        planning_agent=planner,
        evaluator_agent=evaluator,
        repository=repo,
    )


def get_feedback_service() -> FeedbackService:
    repo = get_repository()
    return FeedbackService(repo=repo)
```

---

### Step 3: Implement API Route Handlers

#### A. Intake Router (`app/api/v1/intake.py`)
Create file: `app/api/v1/intake.py`

```python
from typing import List
from fastapi import APIRouter, Depends
from app.domain.models import UserProfile
from app.domain.personas import TEST_PERSONAS
from app.infrastructure.repository import FinanceRepository
from app.core.deps import get_repository

router = APIRouter(tags=["Intake & Personas"])


@router.get("/personas", response_model=List[UserProfile])
async def get_personas():
    """Retrieve the three standard demo test personas (Age 28, 45, 62)."""
    return TEST_PERSONAS


@router.post("/intake")
async def create_or_update_intake(
    profile: UserProfile,
    repo: FinanceRepository = Depends(get_repository),
):
    """Save or update user financial intake profile."""
    saved_profile = await repo.save_profile(profile)
    return {"status": "success", "profile": saved_profile}
```

#### B. Plans Router (`app/api/v1/plans.py`)
Create file: `app/api/v1/plans.py`

```python
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from app.services.workflow_engine import WorkflowEngine
from app.infrastructure.repository import FinanceRepository
from app.core.deps import get_workflow_engine, get_repository

router = APIRouter(tags=["Plans"])


class GeneratePlanRequest(BaseModel):
    user_id: UUID


@router.post("/plans/generate")
async def generate_plan(
    request: GeneratePlanRequest,
    engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Trigger the Plan -> HHH Evaluation -> Revision loop for a user."""
    result = await engine.run(user_id=request.user_id)
    return result


@router.get("/plans/{user_id}/active")
async def get_active_plan(
    user_id: UUID,
    repo: FinanceRepository = Depends(get_repository),
):
    """Retrieve the current active or fallback plan for a user."""
    active_plan = await repo.get_active_plan(user_id=user_id)
    if not active_plan:
        raise HTTPException(status_code=404, detail="No active plan found for user")
    return active_plan
```

#### C. Feedback Router (`app/api/v1/feedback.py`)
Create file: `app/api/v1/feedback.py`

```python
from fastapi import APIRouter, Depends
from app.services.feedback_service import FeedbackService, FeedbackSubmission
from app.core.deps import get_feedback_service

router = APIRouter(tags=["Feedback"])


@router.post("/feedback")
async def submit_action_feedback(
    submission: FeedbackSubmission,
    service: FeedbackService = Depends(get_feedback_service),
):
    """Submit user feedback on a plan action item."""
    feedback_id = await service.submit_feedback(submission)
    return {"status": "recorded", "feedback_id": feedback_id}
```

#### D. Aggregator Router (`app/api/v1/router.py`)
Create file: `app/api/v1/router.py`

```python
from fastapi import APIRouter
from app.api.v1.intake import router as intake_router
from app.api.v1.plans import router as plans_router
from app.api.v1.feedback import router as feedback_router

api_v1_router = APIRouter()

api_v1_router.include_router(intake_router)
api_v1_router.include_router(plans_router)
api_v1_router.include_router(feedback_router)
```

---

### Step 4: Implement FastAPI Factory

Create file: `app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_v1_router

app = FastAPI(
    title="AI Personal Finance Coach API",
    description="Backend API for feedback-driven personal financial planning with automated HHH evaluation.",
    version="0.1.0",
)

# Enable CORS for local web development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint verifying the server is running."""
    return {"status": "healthy", "service": "ai-personal-finance-coach"}
```

---

### Step 5: Run the Test Suite to Verify

Run pytest:
```bash
pytest tests/api/test_routes.py -v
```

#### Expected Output:
```text
tests/api/test_routes.py::TestApiRoutes::test_openapi_schema_endpoint PASSED [ 14%]
tests/api/test_routes.py::TestApiRoutes::test_get_personas_endpoint PASSED   [ 28%]
tests/api/test_routes.py::TestApiRoutes::test_post_intake_valid_profile PASSED [ 42%]
tests/api/test_routes.py::TestApiRoutes::test_post_intake_invalid_age_returns_422 PASSED [ 57%]
tests/api/test_routes.py::TestApiRoutes::test_post_generate_plan_endpoint PASSED [ 71%]
tests/api/test_routes.py::TestApiRoutes::test_post_feedback_endpoint PASSED [ 85%]
tests/api/test_routes.py::TestApiRoutes::test_get_active_plan_not_found PASSED [100%]

============================== 7 passed in 0.28s ==============================
```

Run full project suite:
```bash
pytest
```
*Expected: All 37 tests passing across the entire platform!*

---

## 5. Common Pitfalls & Zero-Question FAQ

* **Q: How do I test the API live in a browser?**  
  *A:* Start the server with:
  ```bash
  uvicorn app.main:app --reload --port 8000
  ```
  Then visit: `http://localhost:8000/docs` to see the interactive Swagger UI.
* **Q: Why does `POST /api/v1/intake` return 422 if age is 16?**  
  *A:* Pydantic v2 automatically intercepts invalid request bodies before they reach the route handler and returns a standard HTTP 422 Unprocessable Entity error.

---

## 6. Git Commit, Push & Trello Progression

Once all tests pass:

### 1. Stage, Commit and Push
```bash
git add app/main.py app/core/deps.py app/api/ tests/api/
git commit -m "feat(api): implement FastAPI application, v1 route controllers, and endpoint integration tests"
git push origin main
```

### 2. Update Trello Card
1. Navigate to **[Task 8 Card on Trello](https://trello.com/c/JHrkud0q)**.
2. Check off all checklist items.
3. Move the card from **`IN PROGRESS`** $\rightarrow$ **`CODE REVIEW`**.
