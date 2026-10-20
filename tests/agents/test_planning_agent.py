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
