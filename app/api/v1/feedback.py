from fastapi import APIRouter, Depends
from app.services.feedback_service import FeedbackService, FeedbackSubmission
from app.core.deps import get_feedback_service

router = APIRouter(tags=["Feedback"])


@router.post("/feedback")
async def submit_action_feedback(
    submission: FeedbackSubmission,
    service: FeedbackService = Depends(get_feedback_service),
):
    """Submit user feedback on a plan action item."""
    feedback_id = await service.submit_feedback(submission)
    return {"status": "recorded", "feedback_id": feedback_id}
