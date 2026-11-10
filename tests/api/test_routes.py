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
