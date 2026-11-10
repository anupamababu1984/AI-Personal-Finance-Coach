from uuid import UUID
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.domain.models import (
    PlanStatus,
    PlanAction,
    FinancialPlanPayload,
    HHHEvaluationResult,
)
from app.infrastructure.repository import FinanceRepository
from app.services.intake_service import IntakeService
from app.agents.planning_agent import PlanningAgent
from app.agents.hhh_evaluator_agent import HHHEvaluatorAgent
from app.services.safe_fallback import get_safe_fallback_plan


class WorkflowResult(BaseModel):
    """Result payload returned by the Workflow Engine."""
    plan_id: UUID
    status: PlanStatus
    health_summary: str
    actions: List[PlanAction]
    evaluations: List[Dict[str, Any]]


class WorkflowEngine:
    """
    Coordinates the Plan -> HHH Evaluation revision loop.
    Enforces max 2 revision retries (3 total attempts) with critique injection,
    and falls back to safe educational guidance on failure or critical safety issues.
    """

    MAX_RETRIES: int = 2  # Total attempts = 1 initial + 2 retries = 3 attempts

    def __init__(
        self,
        intake_service: IntakeService,
        planning_agent: PlanningAgent,
        evaluator_agent: HHHEvaluatorAgent,
        repository: FinanceRepository,
    ):
        self.intake_service = intake_service
        self.planning_agent = planning_agent
        self.evaluator_agent = evaluator_agent
        self.repository = repository

    async def run(self, user_id: UUID) -> WorkflowResult:
        context = await self.intake_service.get_intake_context(user_id)
        profile = context.profile
        recent_feedback = context.recent_feedback

        evaluation_records: List[HHHEvaluationResult] = []
        prior_critique: Optional[str] = None
        active_plan_payload: Optional[FinancialPlanPayload] = None
        plan_status: PlanStatus = PlanStatus.FALLBACK

        for attempt in range(self.MAX_RETRIES + 1):
            # 1. Generate candidate plan
            candidate = await self.planning_agent.generate_plan(
                profile=profile,
                recent_feedback=recent_feedback,
                prior_critique=prior_critique,
            )

            # 2. Evaluate candidate plan against HHH rubric
            eval_result = await self.evaluator_agent.evaluate(
                plan=candidate,
                profile=profile,
                recent_feedback=recent_feedback,
            )
            evaluation_records.append(eval_result)

            # 3. Handle immediate pass
            if eval_result.passed:
                active_plan_payload = candidate
                plan_status = PlanStatus.ACTIVE
                break

            # 4. Handle immediate critical harmlessness issue
            if eval_result.critical_issue:
                # Halt immediately, bypass remaining retries
                break

            # 5. Prepare critique for next retry iteration
            prior_critique = eval_result.critique

        # If retries exhausted or critical safety failure, apply Safe Fallback
        if plan_status != PlanStatus.ACTIVE or active_plan_payload is None:
            active_plan_payload = get_safe_fallback_plan(profile)
            plan_status = PlanStatus.FALLBACK

        # Save plan to repository
        plan_id = await self.repository.save_plan(
            plan=active_plan_payload,
            user_id=user_id,
            status=plan_status,
        )

        # Save evaluation audit logs
        persisted_evaluations = []
        for idx, eval_rec in enumerate(evaluation_records):
            await self.repository.save_evaluation(
                plan_id=plan_id,
                eval_result=eval_rec,
                iteration=idx,
            )
            persisted_evaluations.append({
                "iteration": idx,
                "helpful_score": eval_rec.helpful_score,
                "honest_score": eval_rec.honest_score,
                "harmless_score": eval_rec.harmless_score,
                "passed": eval_rec.passed,
                "critical_issue": eval_rec.critical_issue,
                "critique": eval_rec.critique,
            })

        return WorkflowResult(
            plan_id=plan_id,
            status=plan_status,
            health_summary=active_plan_payload.health_summary,
            actions=active_plan_payload.actions,
            evaluations=persisted_evaluations,
        )
