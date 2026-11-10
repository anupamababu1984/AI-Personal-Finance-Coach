from typing import List
from fastapi import APIRouter, Depends
from app.domain.models import UserProfile
from app.domain.personas import TEST_PERSONAS
from app.infrastructure.repository import FinanceRepository
from app.core.deps import get_repository

router = APIRouter(tags=["Intake & Personas"])


@router.get("/personas", response_model=List[UserProfile])
async def get_personas():
    """Retrieve the three standard demo test personas (Age 28, 45, 62)."""
    return TEST_PERSONAS


@router.post("/intake")
async def create_or_update_intake(
    profile: UserProfile,
    repo: FinanceRepository = Depends(get_repository),
):
    """Save or update user financial intake profile."""
    saved_profile = await repo.save_profile(profile)
    return {"status": "success", "profile": saved_profile}
