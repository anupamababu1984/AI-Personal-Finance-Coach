from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta

from app.domain.models import (
    UserProfile,
    FinancialPlanPayload,
    HHHEvaluationResult,
    ActionFeedback,
    PlanStatus,
    ActionStatus,
)


class FinanceRepository(ABC):
    """Abstract interface defining storage operations for personal finance data."""

    @abstractmethod
    async def save_profile(self, profile: UserProfile) -> UserProfile:
        """Create or update a user profile."""
        pass

    @abstractmethod
    async def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Retrieve a user profile by ID."""
        pass

    @abstractmethod
    async def save_plan(
        self,
        plan: FinancialPlanPayload,
        user_id: UUID,
        status: PlanStatus,
        version: int = 1,
    ) -> UUID:
        """Save a generated financial plan."""
        pass

    @abstractmethod
    async def get_active_plan(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieve the currently active plan for a user."""
        pass

    @abstractmethod
    async def update_plan_status(self, plan_id: UUID, status: PlanStatus) -> None:
        """Update the status of a plan (active, archived, fallback)."""
        pass

    @abstractmethod
    async def update_action_status(
        self, plan_id: UUID, action_id: str, status: ActionStatus
    ) -> None:
        """Update the status of an action inside a plan (worked, did_not_work)."""
        pass

    @abstractmethod
    async def save_evaluation(
        self, plan_id: UUID, eval_result: HHHEvaluationResult, iteration: int
    ) -> UUID:
        """Log an HHH evaluation attempt for a plan."""
        pass

    @abstractmethod
    async def get_evaluations_for_plan(self, plan_id: UUID) -> List[Dict[str, Any]]:
        """Retrieve all HHH evaluation rounds for a plan."""
        pass

    @abstractmethod
    async def save_feedback(self, feedback: ActionFeedback) -> UUID:
        """Record user feedback on a plan action."""
        pass

    @abstractmethod
    async def get_recent_feedback(
        self, user_id: UUID, days: int = 30
    ) -> List[ActionFeedback]:
        """Retrieve user feedback from the past N days (defaults to 30 days)."""
        pass


class InMemoryFinanceRepository(FinanceRepository):
    """
    Thread-safe in-memory repository implementation for hermetic unit testing
    and fast local development without live external database dependencies.
    """

    def __init__(self):
        self.profiles: Dict[UUID, UserProfile] = {}
        self.plans: Dict[UUID, Dict[str, Any]] = {}
        self.evaluations: Dict[UUID, Dict[str, Any]] = {}
        self.feedback: Dict[UUID, ActionFeedback] = {}

    async def save_profile(self, profile: UserProfile) -> UserProfile:
        self.profiles[profile.user_id] = profile
        return profile

    async def get_profile(self, user_id: UUID) -> Optional[UserProfile]:
        return self.profiles.get(user_id)

    async def save_plan(
        self,
        plan: FinancialPlanPayload,
        user_id: UUID,
        status: PlanStatus,
        version: int = 1,
    ) -> UUID:
        plan_id = uuid4()
        now = datetime.now(timezone.utc)
        self.plans[plan_id] = {
            "id": plan_id,
            "user_id": user_id,
            "version": version,
            "status": status,
            "health_summary": plan.health_summary,
            "actions": [action.model_dump() for action in plan.actions],
            "created_at": now,
        }
        return plan_id

    async def get_active_plan(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        for plan in self.plans.values():
            if plan["user_id"] == user_id and plan["status"] == PlanStatus.ACTIVE:
                return plan
        return None

    async def update_plan_status(self, plan_id: UUID, status: PlanStatus) -> None:
        if plan_id in self.plans:
            self.plans[plan_id]["status"] = status

    async def update_action_status(
        self, plan_id: UUID, action_id: str, status: ActionStatus
    ) -> None:
        if plan_id in self.plans:
            for action in self.plans[plan_id]["actions"]:
                if action["id"] == action_id:
                    action["status"] = status
                    break

    async def save_evaluation(
        self, plan_id: UUID, eval_result: HHHEvaluationResult, iteration: int
    ) -> UUID:
        eval_id = uuid4()
        now = datetime.now(timezone.utc)
        self.evaluations[eval_id] = {
            "id": eval_id,
            "plan_id": plan_id,
            "iteration": iteration,
            "helpful_score": eval_result.helpful_score,
            "honest_score": eval_result.honest_score,
            "harmless_score": eval_result.harmless_score,
            "passed": eval_result.passed,
            "critical_issue": eval_result.critical_issue,
            "critique": eval_result.critique,
            "created_at": now,
        }
        return eval_id

    async def get_evaluations_for_plan(self, plan_id: UUID) -> List[Dict[str, Any]]:
        return [e for e in self.evaluations.values() if e["plan_id"] == plan_id]

    async def save_feedback(self, feedback: ActionFeedback) -> UUID:
        feedback_id = feedback.id or uuid4()
        created_at = feedback.created_at or datetime.now(timezone.utc)
        stored_feedback = feedback.model_copy(
            update={"id": feedback_id, "created_at": created_at}
        )
        self.feedback[feedback_id] = stored_feedback
        return feedback_id

    async def get_recent_feedback(
        self, user_id: UUID, days: int = 30
    ) -> List[ActionFeedback]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = [
            f
            for f in self.feedback.values()
            if f.user_id == user_id and f.created_at and f.created_at >= cutoff
        ]
        # Return sorted by newest first
        return sorted(recent, key=lambda x: x.created_at, reverse=True)
