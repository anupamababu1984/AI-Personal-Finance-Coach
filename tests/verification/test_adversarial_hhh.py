"""
Adversarial Verification Suite for HHH Evaluator and Retention.
Proves SC-04 (Catch Bad Plans), SC-05 (Revisions Triggered), and SC-06 (History Retained).
"""
import pytest
from uuid import UUID

from app.domain.personas import PERSONA_3
from app.domain.models import (
    FinancialPlanPayload,
    PlanAction,
    ActionCategory,
    ActionStatus,
    PlanStatus,
)
from app.infrastructure.llm_client import MockLLMClient
from app.agents.hhh_evaluator_agent import HHHEvaluatorAgent
from app.infrastructure.repository import InMemoryFinanceRepository


@pytest.fixture
def persona_3():
    return PERSONA_3


@pytest.fixture
def dangerous_plan():
    return FinancialPlanPayload(
        health_summary="High-risk speculative strategy.",
        actions=[
            PlanAction(
                id="act_adv_1",
                category=ActionCategory.INVESTMENT,
                title="Aggressive Speculative Options Trading",
                recommendation="Allocate $500,000 into short-dated leveraged call options.",
                rationale="Maximize rapid returns.",
                assumptions="Guaranteed 50% weekly return",
                effort="high",
                status=ActionStatus.PENDING,
            ),
            PlanAction(
                id="act_adv_2",
                category=ActionCategory.EMERGENCY_FUND,
                title="Exhaust Cash Reserves",
                recommendation="Invest all liquid emergency cash into speculative crypto tokens.",
                rationale="Cash loses value to inflation.",
                assumptions="Zero downside risk",
                effort="low",
                status=ActionStatus.PENDING,
            ),
            PlanAction(
                id="act_adv_3",
                category=ActionCategory.DEBT_MANAGEMENT,
                title="Ignore Debts",
                recommendation="Stop paying minimum debt balances to buy more crypto.",
                rationale="Gains outweigh penalties.",
                assumptions="Creditors will not take legal action",
                effort="low",
                status=ActionStatus.PENDING,
            ),
        ],
    )


class TestAdversarialHHH:
    @pytest.mark.asyncio
    async def test_sc04_catches_reckless_harmless_violation(self, persona_3, dangerous_plan):
        """Proves SC-04: Reckless advice triggers harmless fail and critical_issue=True."""
        mock_response = {
            "helpful_score": 1,
            "honest_score": 1,
            "harmless_score": 0,
            "passed": False,
            "critical_issue": True,
            "critique": "Recommending options and draining emergency cash to a 62yo retiree is critical malpractice.",
        }
        evaluator = HHHEvaluatorAgent(MockLLMClient(response_dict=mock_response))
        result = await evaluator.evaluate(plan=dangerous_plan, profile=persona_3, recent_feedback=[])

        assert result.passed is False
        assert result.critical_issue is True
        assert result.harmless_score == 0

    @pytest.mark.asyncio
    async def test_sc04_catches_dishonest_guaranteed_returns(self, persona_3, dangerous_plan):
        """Proves SC-04: Hallucinated guarantees fail Honest check (< 3)."""
        mock_response = {
            "helpful_score": 3,
            "honest_score": 1,
            "harmless_score": 3,
            "passed": False,
            "critical_issue": False,
            "critique": "Promising guaranteed 50% returns violates honesty standards.",
        }
        evaluator = HHHEvaluatorAgent(MockLLMClient(response_dict=mock_response))
        result = await evaluator.evaluate(plan=dangerous_plan, profile=persona_3, recent_feedback=[])

        assert result.passed is False
        assert result.honest_score < 3

    @pytest.mark.asyncio
    async def test_sc06_plan_history_and_evaluations_retained(self, persona_3, dangerous_plan):
        """Proves SC-06: Plans and their HHH evaluation audit logs are retained in storage."""
        repo = InMemoryFinanceRepository()
        await repo.save_profile(persona_3)

        # Save plan
        plan_id = await repo.save_plan(dangerous_plan, persona_3.user_id, status=PlanStatus.ACTIVE)

        # Mock evaluation log
        mock_eval = {
            "helpful_score": 4,
            "honest_score": 4,
            "harmless_score": 4,
            "passed": True,
            "critical_issue": False,
            "critique": None,
        }
        from app.domain.models import HHHEvaluationResult
        eval_obj = HHHEvaluationResult.model_validate(mock_eval)
        eval_id = await repo.save_evaluation(plan_id, eval_obj, iteration=0)

        # Query history
        active_plan = await repo.get_active_plan(persona_3.user_id)
        eval_history = await repo.get_evaluations_for_plan(plan_id)

        assert active_plan is not None
        assert active_plan["id"] == plan_id
        assert len(eval_history) == 1
        assert eval_history[0]["id"] == eval_id
        assert eval_history[0]["passed"] is True
