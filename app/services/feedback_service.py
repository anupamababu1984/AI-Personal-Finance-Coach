from uuid import UUID, uuid4
from typing import Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.domain.models import ActionFeedback, ActionStatus
from app.infrastructure.repository import FinanceRepository


class FeedbackSubmission(BaseModel):
    """Payload sent by the client when providing feedback on a plan action."""
    user_id: UUID
    plan_id: UUID
    action_id: str = Field(..., min_length=1)
    outcome: Literal["worked", "did_not_work"]
    notes: Optional[str] = None


class FeedbackService:
    """Handles logging user feedback and mutating active plan action statuses."""

    def __init__(self, repo: FinanceRepository):
        self.repo = repo

    async def submit_feedback(self, submission: FeedbackSubmission) -> UUID:
        """
        1. Persists the feedback event to the repository.
        2. Updates the target action status in the active plan (WORKED or DID_NOT_WORK).
        3. Returns the unique feedback ID.
        """
        feedback_entity = ActionFeedback(
            id=uuid4(),
            user_id=submission.user_id,
            plan_id=submission.plan_id,
            action_id=submission.action_id,
            outcome=submission.outcome,
            notes=submission.notes,
            created_at=datetime.now(timezone.utc),
        )
        feedback_id = await self.repo.save_feedback(feedback_entity)

        # Mutate the targeted action status in the active plan
        new_status = (
            ActionStatus.WORKED
            if submission.outcome == "worked"
            else ActionStatus.DID_NOT_WORK
        )
        await self.repo.update_action_status(
            plan_id=submission.plan_id,
            action_id=submission.action_id,
            status=new_status,
        )

        return feedback_id
