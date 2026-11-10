from fastapi import APIRouter
from app.api.v1.intake import router as intake_router
from app.api.v1.plans import router as plans_router
from app.api.v1.feedback import router as feedback_router

api_v1_router = APIRouter()

api_v1_router.include_router(intake_router)
api_v1_router.include_router(plans_router)
api_v1_router.include_router(feedback_router)
