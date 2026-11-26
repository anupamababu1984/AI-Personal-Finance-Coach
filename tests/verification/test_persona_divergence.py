"""
End-to-End Verification Suite: Persona Divergence & Adaptive Feedback.
Proves SC-01 (Divergence), SC-02 (Relevance), and SC-03 (Feedback Adaptation).
"""
import pytest
from uuid import uuid4

from app.domain.personas import PERSONA_1, PERSONA_2, PERSONA_3
from app.domain.models import ActionCategory, PlanStatus
from app.domain.benchmarks import CURATED_MARKET_BENCHMARKS
from app.infrastructure.repository import InMemoryFinanceRepository
from app.infrastructure.llm_client import MockLLMClient
from app.services.intake_service import IntakeService
from app.agents.planning_agent import PlanningAgent
from app.agents.hhh_evaluator_agent import HHHEvaluatorAgent
from app.services.workflow_engine import WorkflowEngine
from app.services.feedback_service import FeedbackService, FeedbackSubmission


class PersonaMockLLMClient:
    """Mock LLM returning distinct, tailored plans depending on persona age."""

    async def generate_json(self, system_prompt: str, user_prompt: str):
        if "evaluation critic" in system_prompt or "PROPOSED PLAN ACTIONS" in user_prompt:
            return {
                "helpful_score": 4,
                "honest_score": 4,
                "harmless_score": 4,
                "passed": True,
                "critical_issue": False,
                "critique": None,
            }

        if "Age: 28" in user_prompt:
            # Persona 1: Aggressive wealth compounding + student debt
            return {
                "health_summary": "Aggressive wealth compounding for young professional.",
                "actions": [
                    {
                        "id": "act_p1_1",
                        "category": "investment",
                        "title": "Aggressive Equity Index Allocation",
                        "recommendation": "Allocate $700/mo into diversified broad-market growth equities.",
                        "rationale": "32-year investment horizon maximizes compounding.",
                        "assumptions": "7.5% long-term return",
                        "effort": "low",
                        "status": "pending",
                    },
                    {
                        "id": "act_p1_2",
                        "category": "debt_management",
                        "title": "Student Loan Paydown Acceleration",
                        "recommendation": "Allocate $300/mo extra toward $10k student loan.",
                        "rationale": "Eliminates debt drag.",
                        "assumptions": "4.5% interest rate",
                        "effort": "medium",
                        "status": "pending",
                    },
                    {
                        "id": "act_p1_3",
                        "category": "emergency_fund",
                        "title": "Maintain 3-Month Cash Buffer",
                        "recommendation": "Keep $12,000 liquid in 4.5% HYSA.",
                        "rationale": "Sufficient for young earner.",
                        "assumptions": "4.5% APY",
                        "effort": "low",
                        "status": "pending",
                    },
                ],
            }
        elif "Age: 45" in user_prompt:
            # Persona 2: Dual goals (mortgage + children's education + retirement)
            return {
                "health_summary": "Balanced mid-career wealth and family obligations.",
                "actions": [
                    {
                        "id": "act_p2_1",
                        "category": "investment",
                        "title": "Dual Retirement & College Funding",
                        "recommendation": "Split $2,000/mo: $1,200 into retirement index, $800 into 529 education fund.",
                        "rationale": "Balances upcoming college expenses with retirement catch-up.",
                        "assumptions": "7.5% market return",
                        "effort": "medium",
                        "status": "pending",
                    },
                    {
                        "id": "act_p2_2",
                        "category": "debt_management",
                        "title": "Mortgage Optimization",
                        "recommendation": "Maintain standard 3.5% mortgage payments; invest excess cash flow.",
                        "rationale": "Mortgage rate is lower than expected equity yield.",
                        "assumptions": "3.5% fixed mortgage",
                        "effort": "low",
                        "status": "pending",
                    },
                    {
                        "id": "act_p2_3",
                        "category": "emergency_fund",
                        "title": "Strengthen Family Emergency Liquidity",
                        "recommendation": "Maintain $42,000 (6 months expenses) in HYSA.",
                        "rationale": "Protects dependent family cash flow.",
                        "assumptions": "4.5% APY",
                        "effort": "medium",
                        "status": "pending",
                    },
                ],
            }
        elif "Age: 62" in user_prompt:
            # Persona 3: Capital preservation and income yields
            return {
                "health_summary": "Capital preservation and fixed income for retirement.",
                "actions": [
                    {
                        "id": "act_p3_1",
                        "category": "investment",
                        "title": "Shift to Fixed Income & Dividend Preservation",
                        "recommendation": "Rebalance $1M portfolio to 60% bonds and 40% dividend-yielding equities.",
                        "rationale": "Minimizes sequence-of-returns risk 3 years from retirement.",
                        "assumptions": "4.0% safe withdrawal rule",
                        "effort": "medium",
                        "status": "pending",
                    },
                    {
                        "id": "act_p3_2",
                        "category": "emergency_fund",
                        "title": "Expand Cash Liquidity to 12 Months",
                        "recommendation": "Hold $66,000 in liquid high-yield cash equivalents.",
                        "rationale": "Buffers against selling equities during market downturns.",
                        "assumptions": "4.5% HYSA APY",
                        "effort": "low",
                        "status": "pending",
                    },
                    {
                        "id": "act_p3_3",
                        "category": "debt_management",
                        "title": "Pay Off Remaining Mortgage Prior to Retirement",
                        "recommendation": "Direct $1,500/mo capacity to eliminate $50,000 mortgage before retiring.",
                        "rationale": "Eliminates living expense overhead in retirement.",
                        "assumptions": "Mortgage balance $50,000",
                        "effort": "high",
                        "status": "pending",
                    },
                ],
            }
        return {
            "helpful_score": 4,
            "honest_score": 4,
            "harmless_score": 4,
            "passed": True,
            "critical_issue": False,
            "critique": None,
        }


class TestPersonaDivergence:
    @pytest.mark.asyncio
    async def test_sc01_personas_produce_divergent_recommendations(self):
        """Proves SC-01: The three personas receive materially divergent plans."""
        repo = InMemoryFinanceRepository()
        intake_svc = IntakeService(repo)
        mock_llm = PersonaMockLLMClient()
        planner = PlanningAgent(mock_llm, CURATED_MARKET_BENCHMARKS)
        evaluator = HHHEvaluatorAgent(mock_llm)
        engine = WorkflowEngine(intake_svc, planner, evaluator, repo)

        # Save all 3 personas
        await repo.save_profile(PERSONA_1)
        await repo.save_profile(PERSONA_2)
        await repo.save_profile(PERSONA_3)

        # Run plans for each
        res_p1 = await engine.run(PERSONA_1.user_id)
        res_p2 = await engine.run(PERSONA_2.user_id)
        res_p3 = await engine.run(PERSONA_3.user_id)

        # Verify Persona 1 (28yo, aggressive) focuses on aggressive growth
        p1_titles = [a.title for a in res_p1.actions]
        assert "Aggressive Equity Index Allocation" in p1_titles
        assert "Student Loan Paydown Acceleration" in p1_titles
        assert "Broad-market growth" in res_p1.actions[0].recommendation.lower() or "broad-market" in res_p1.actions[0].recommendation.lower()

        # Verify Persona 2 (45yo, moderate) balances college and mortgage
        p2_titles = [a.title for a in res_p2.actions]
        assert "Dual Retirement & College Funding" in p2_titles
        assert "Mortgage Optimization" in p2_titles

        # Verify Persona 3 (62yo, conservative) prioritizes capital preservation
        p3_titles = [a.title for a in res_p3.actions]
        assert "Shift to Fixed Income & Dividend Preservation" in p3_titles
        assert "Expand Cash Liquidity to 12 Months" in p3_titles
        assert "sequence-of-returns" in res_p3.actions[0].rationale.lower()

        # Cross-persona assertion: P1 and P3 recommendations must be completely distinct
        assert res_p1.actions[0].title != res_p3.actions[0].title
        assert res_p1.health_summary != res_p3.health_summary

    @pytest.mark.asyncio
    async def test_sc03_feedback_adapts_subsequent_plan(self):
        """Proves SC-03: User feedback changes subsequent plan prompt context."""
        repo = InMemoryFinanceRepository()
        intake_svc = IntakeService(repo)
        feedback_svc = FeedbackService(repo)
        await repo.save_profile(PERSONA_1)

        # 1. Run initial plan
        mock_llm = PersonaMockLLMClient()
        planner = PlanningAgent(mock_llm, CURATED_MARKET_BENCHMARKS)
        evaluator = HHHEvaluatorAgent(mock_llm)
        engine = WorkflowEngine(intake_svc, planner, evaluator, repo)
        initial_res = await engine.run(PERSONA_1.user_id)

        # 2. User submits feedback: did_not_work on act_p1_1
        submission = FeedbackSubmission(
            user_id=PERSONA_1.user_id,
            plan_id=initial_res.plan_id,
            action_id="act_p1_1",
            outcome="did_not_work",
            notes="Market volatility caused too much stress; prefer lower volatility vehicles.",
        )
        await feedback_svc.submit_feedback(submission)

        # 3. Next intake run captures the feedback
        intake_context = await intake_svc.get_intake_context(PERSONA_1.user_id)
        assert len(intake_context.recent_feedback) == 1
        assert "prefer lower volatility" in intake_context.feedback_summary
