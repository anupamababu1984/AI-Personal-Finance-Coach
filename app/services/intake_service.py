from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel
from app.domain.models import UserProfile, ActionFeedback
from app.infrastructure.repository import FinanceRepository


class IntakeContext(BaseModel):
    """Encapsulates the complete intake payload required by the Planning Agent."""
    profile: UserProfile
    recent_feedback: List[ActionFeedback]
    feedback_summary: Optional[str] = None


class IntakeService:
    """Orchestrates intake retrieval and feedback prompt preparation."""

    def __init__(self, repo: FinanceRepository):
        self.repo = repo

    async def get_intake_context(self, user_id: UUID) -> IntakeContext:
        """
        Retrieves user profile and 30-day feedback, assembling them into an IntakeContext.
        Raises ValueError if the profile does not exist.
        """
        profile = await self.repo.get_profile(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")

        feedback = await self.repo.get_recent_feedback(user_id, days=30)
        summary = self.format_feedback_summary(feedback)

        return IntakeContext(
            profile=profile,
            recent_feedback=feedback,
            feedback_summary=summary,
        )

    def format_feedback_summary(self, feedback: List[ActionFeedback]) -> Optional[str]:
        """Formats feedback items into clean markdown for injection into AI prompts."""
        if not feedback:
            return None

        lines = ["### Recent User Feedback (Last 30 Days):"]
        for f in feedback:
            status = "SUCCESS/WORKED" if f.outcome == "worked" else "REJECTED/DID NOT WORK"
            notes_part = f" - Notes: {f.notes}" if f.notes else ""
            lines.append(f"- Action [{f.action_id}]: {status}{notes_part}")

        return "\n".join(lines)
