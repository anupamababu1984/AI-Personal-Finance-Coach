from typing import Dict, Any, Optional
from app.core.config import settings
from app.infrastructure.repository import FinanceRepository, InMemoryFinanceRepository
from app.domain.benchmarks import CURATED_MARKET_BENCHMARKS
from app.domain.personas import TEST_PERSONAS
from app.infrastructure.llm_client import LLMClient, MockLLMClient, AnthropicLLMClient
from app.services.intake_service import IntakeService
from app.agents.planning_agent import PlanningAgent
from app.agents.hhh_evaluator_agent import HHHEvaluatorAgent
from app.services.workflow_engine import WorkflowEngine
from app.services.feedback_service import FeedbackService

# Global in-memory singleton for development and testing
_global_repository = InMemoryFinanceRepository()

# Pre-seed standard test personas so demo works out of the box
for persona in TEST_PERSONAS:
    _global_repository.profiles[persona.user_id] = persona


class SmartDemoLLMClient:
    """
    Demo LLM client that generates realistic, persona-tailored plans
    and passing HHH scorecards when no live Anthropic API key is provided.
    """

    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        # If this is an evaluation call, return passing scorecard
        if "evaluation critic" in system_prompt or "PROPOSED PLAN ACTIONS" in user_prompt:
            return {
                "helpful_score": 4,
                "honest_score": 4,
                "harmless_score": 4,
                "passed": True,
                "critical_issue": False,
                "critique": None,
            }

        # Persona-tailored demo plans
        if "Age: 28" in user_prompt:
            return {
                "health_summary": "Aggressive wealth-building strategy focused on equity compounding and high-interest debt elimination.",
                "actions": [
                    {
                        "id": "act_1",
                        "category": "emergency_fund",
                        "title": "Establish 3-Month High-Yield Emergency Reserve",
                        "recommendation": "Allocate $500/mo into a 4.5% APY High-Yield Savings Account until reaching $12,000.",
                        "rationale": "Protects cash flow before committing heavily to aggressive long-term investing.",
                        "assumptions": "Assumes standard cash savings earn 4.5% APY in current HYSA.",
                        "effort": "low",
                        "status": "pending",
                    },
                    {
                        "id": "act_2",
                        "category": "debt_management",
                        "title": "Accelerate Student Loan Payoff",
                        "recommendation": "Direct $300/mo extra toward $10,000 student loan balance.",
                        "rationale": "Guarantees a 4.5% return by eliminating loan interest drag.",
                        "assumptions": "Assumes fixed 4.5% interest rate.",
                        "effort": "medium",
                        "status": "pending",
                    },
                    {
                        "id": "act_3",
                        "category": "investment",
                        "title": "Broad-Market Equity Index Compounding",
                        "recommendation": "Invest remaining $200/mo into diversified low-cost total stock market index funds.",
                        "rationale": "Takes advantage of 32-year investment horizon to compound wealth.",
                        "assumptions": "Assumes 7.5% long-term historical equity market average.",
                        "effort": "low",
                        "status": "pending",
                    },
                ],
            }
        elif "Age: 45" in user_prompt:
            return {
                "health_summary": "Balanced mid-career strategy optimizing mortgage, college funding, and retirement catch-up.",
                "actions": [
                    {
                        "id": "act_1",
                        "category": "investment",
                        "title": "Dual Retirement & College Fund Allocation",
                        "recommendation": "Split $2,000/mo: $1,200 to retirement accounts and $800 to 529 college education plan.",
                        "rationale": "Balances upcoming college expenses with retirement catch-up.",
                        "assumptions": "Assumes 7.5% long-term market return.",
                        "effort": "medium",
                        "status": "pending",
                    },
                    {
                        "id": "act_2",
                        "category": "debt_management",
                        "title": "Mortgage Rate Optimization",
                        "recommendation": "Maintain standard 3.5% mortgage payments; invest excess cash flow.",
                        "rationale": "Mortgage interest rate is below expected investment returns.",
                        "assumptions": "Fixed 3.5% mortgage rate.",
                        "effort": "low",
                        "status": "pending",
                    },
                    {
                        "id": "act_3",
                        "category": "emergency_fund",
                        "title": "Expand Family Emergency Reserve",
                        "recommendation": "Maintain $42,000 (6 months of living expenses) in liquid HYSA.",
                        "rationale": "Buffers dependent family members against unexpected events.",
                        "assumptions": "4.5% HYSA yield.",
                        "effort": "medium",
                        "status": "pending",
                    },
                ],
            }
        else:
            return {
                "health_summary": "Capital preservation and fixed income yield optimization for near-retirement stability.",
                "actions": [
                    {
                        "id": "act_1",
                        "category": "investment",
                        "title": "Rebalance toward Capital Preservation & Yield",
                        "recommendation": "Rebalance $1,000,000 portfolio to 60% high-quality fixed income and 40% dividend equities.",
                        "rationale": "Eliminates sequence-of-returns risk 3 years before planned retirement.",
                        "assumptions": "4.0% safe withdrawal rule benchmark.",
                        "effort": "medium",
                        "status": "pending",
                    },
                    {
                        "id": "act_2",
                        "category": "emergency_fund",
                        "title": "Build 12-Month Retirement Cash Cushion",
                        "recommendation": "Hold $66,000 in liquid high-yield cash equivalents.",
                        "rationale": "Prevents selling equities during market pullbacks in early retirement.",
                        "assumptions": "4.5% HYSA APY.",
                        "effort": "low",
                        "status": "pending",
                    },
                    {
                        "id": "act_3",
                        "category": "debt_management",
                        "title": "Eliminate Remaining Mortgage Before Retirement",
                        "recommendation": "Allocate $1,500/mo capacity to pay off $50,000 mortgage before retiring.",
                        "rationale": "Removes fixed housing overhead during retirement.",
                        "assumptions": "Mortgage balance $50,000.",
                        "effort": "high",
                        "status": "pending",
                    },
                ],
            }


def get_llm_client() -> LLMClient:
    """Returns live Anthropic client if API key is configured, else SmartDemoLLMClient."""
    if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.strip() and not settings.ANTHROPIC_API_KEY.startswith("your_"):
        return AnthropicLLMClient(api_key=settings.ANTHROPIC_API_KEY, model=settings.ANTHROPIC_MODEL)
    return SmartDemoLLMClient()


def get_repository() -> FinanceRepository:
    """Returns the database repository instance."""
    return _global_repository


def get_intake_service() -> IntakeService:
    repo = get_repository()
    return IntakeService(repo=repo)


def get_planning_agent() -> PlanningAgent:
    llm = get_llm_client()
    return PlanningAgent(llm_client=llm, benchmarks=CURATED_MARKET_BENCHMARKS)


def get_hhh_evaluator_agent() -> HHHEvaluatorAgent:
    llm = get_llm_client()
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
