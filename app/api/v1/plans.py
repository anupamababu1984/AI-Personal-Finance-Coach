from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from app.services.workflow_engine import WorkflowEngine
from app.infrastructure.repository import FinanceRepository
from app.core.deps import get_workflow_engine, get_repository

router = APIRouter(tags=["Plans"])


class GeneratePlanRequest(BaseModel):
    user_id: UUID


@router.post("/plans/generate")
async def generate_plan(
    request: GeneratePlanRequest,
    engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Trigger the Plan -> HHH Evaluation -> Revision loop for a user."""
    result = await engine.run(user_id=request.user_id)
    return result


@router.get("/plans/{user_id}/active")
async def get_active_plan(
    user_id: UUID,
    repo: FinanceRepository = Depends(get_repository),
):
    """Retrieve the current active or fallback plan for a user."""
    active_plan = await repo.get_active_plan(user_id=user_id)
    if not active_plan:
        raise HTTPException(status_code=404, detail="No active plan found for user")
    return active_plan
