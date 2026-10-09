from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, conint
from datetime import datetime
from uuid import UUID


class RiskAppetite(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class ActionCategory(str, Enum):
    EMERGENCY_FUND = "emergency_fund"
    DEBT_MANAGEMENT = "debt_management"
    INVESTMENT = "investment"
    BUDGETING = "budgeting"


class ActionStatus(str, Enum):
    PENDING = "pending"
    WORKED = "worked"
    DID_NOT_WORK = "did_not_work"


class PlanStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    FALLBACK = "fallback"


class UserProfile(BaseModel):
    user_id: UUID
    age: conint(ge=18, le=120)
    annual_income: float = Field(..., ge=0)
    monthly_expenses: float = Field(..., ge=0)
    savings: float = Field(default=0.0, ge=0)
    investments: float = Field(default=0.0, ge=0)
    debt: float = Field(default=0.0, ge=0)
    debt_details: Optional[str] = None
    risk_appetite: RiskAppetite
    investment_horizon_years: conint(ge=0)
    retirement_age_target: conint(ge=18)
    primary_goal: str
    monthly_investment_capacity: float = Field(..., ge=0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PlanAction(BaseModel):
    id: str = Field(..., description="Unique action identifier, e.g. act_1")
    category: ActionCategory
    title: str = Field(..., max_length=120)
    recommendation: str
    rationale: str
    assumptions: str
    effort: Literal["low", "medium", "high"]
    status: ActionStatus = ActionStatus.PENDING


class FinancialPlanPayload(BaseModel):
    health_summary: str
    actions: List[PlanAction] = Field(..., min_length=3, max_length=5)


class HHHEvaluationResult(BaseModel):
    helpful_score: conint(ge=0, le=4)
    honest_score: conint(ge=0, le=4)
    harmless_score: conint(ge=0, le=4)
    passed: bool
    critical_issue: bool = False
    critique: Optional[str] = None


class ActionFeedback(BaseModel):
    id: Optional[UUID] = None
    user_id: UUID
    plan_id: UUID
    action_id: str
    outcome: Literal["worked", "did_not_work"]
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
