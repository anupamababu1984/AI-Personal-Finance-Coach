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
