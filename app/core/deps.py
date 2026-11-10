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
