"""
Unit tests for the FinanceRepository layer.
Verifies CRUD operations for profiles, plans, evaluations, and 30-day feedback filtering.
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta

from app.domain.models import (
    UserProfile,
    RiskAppetite,
    PlanAction,
    ActionCategory,
    ActionStatus,
    FinancialPlanPayload,
    HHHEvaluationResult,
    ActionFeedback,
    PlanStatus,
)
from app.infrastructure.repository import InMemoryFinanceRepository


@pytest.fixture
def repo():
    return InMemoryFinanceRepository()


@pytest.fixture
def sample_profile():
    return UserProfile(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        age=28,
        annual_income=75000.0,
        monthly_expenses=4000.0,
        savings=20000.0,
        investments=15000.0,
        debt=10000.0,
        risk_appetite=RiskAppetite.AGGRESSIVE,
        investment_horizon_years=32,
        retirement_age_target=60,
        primary_goal="Wealth building",
        monthly_investment_capacity=1000.0,
    )


@pytest.fixture
def sample_plan():
    actions = [
        PlanAction(
            id="act_1",
            category=ActionCategory.EMERGENCY_FUND,
            title="Emergency Fund",
            recommendation="Save 3 months",
            rationale="Buffer",
            assumptions="4.5% APY",
            effort="low",
            status=ActionStatus.PENDING,
        ),
        PlanAction(
            id="act_2",
            category=ActionCategory.DEBT_MANAGEMENT,
            title="Loan Payoff",
            recommendation="Pay $300/mo extra",
            rationale="Save interest",
            assumptions="4.5% rate",
            effort="medium",
            status=ActionStatus.PENDING,
        ),
        PlanAction(
            id="act_3",
            category=ActionCategory.INVESTMENT,
            title="Index Fund",
            recommendation="Invest $700/mo",
            rationale="Growth",
            assumptions="7.5% return",
            effort="medium",
            status=ActionStatus.PENDING,
        ),
    ]
    return FinancialPlanPayload(
        health_summary="Strong foundation for growth.",
        actions=actions,
    )


class TestFinanceRepository:
    @pytest.mark.asyncio
    async def test_profile_crud(self, repo, sample_profile):
        # Save profile
        saved = await repo.save_profile(sample_profile)
        assert saved.user_id == sample_profile.user_id

        # Retrieve profile
        fetched = await repo.get_profile(sample_profile.user_id)
        assert fetched is not None
        assert fetched.annual_income == 75000.0

        # Query non-existent profile returns None
        missing = await repo.get_profile(uuid4())
        assert missing is None

    @pytest.mark.asyncio
    async def test_plan_saving_and_status_updates(self, repo, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)

        # Save plan
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)
        assert isinstance(plan_id, UUID)

        # Retrieve active plan
        active = await repo.get_active_plan(sample_profile.user_id)
        assert active is not None
        assert active["id"] == plan_id
        assert active["status"] == PlanStatus.ACTIVE
        assert len(active["actions"]) == 3

        # Update status to archived
        await repo.update_plan_status(plan_id, PlanStatus.ARCHIVED)
        archived = await repo.get_active_plan(sample_profile.user_id)
        assert archived is None  # No active plan exists anymore

    @pytest.mark.asyncio
    async def test_action_status_mutation(self, repo, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)

        # Mutate action act_1 to WORKED
        await repo.update_action_status(plan_id, "act_1", ActionStatus.WORKED)

        active = await repo.get_active_plan(sample_profile.user_id)
        act_1 = next(a for a in active["actions"] if a["id"] == "act_1")
        assert act_1["status"] == ActionStatus.WORKED

    @pytest.mark.asyncio
    async def test_evaluations_logging(self, repo, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)

        eval_result = HHHEvaluationResult(
            helpful_score=4,
            honest_score=4,
            harmless_score=4,
            passed=True,
            critical_issue=False,
            critique=None,
        )
        eval_id = await repo.save_evaluation(plan_id, eval_result, iteration=0)
        assert isinstance(eval_id, UUID)

        evals = await repo.get_evaluations_for_plan(plan_id)
        assert len(evals) == 1
        assert evals[0]["helpful_score"] == 4
        assert evals[0]["passed"] is True

    @pytest.mark.asyncio
    async def test_30_day_feedback_boundary_filtering(self, repo, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)
        now = datetime.now(timezone.utc)

        # 1. Feedback from 10 days ago (Should be included)
        fb_recent = ActionFeedback(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_1",
            outcome="worked",
            notes="Setup HYSA without issues",
            created_at=now - timedelta(days=10),
        )
        await repo.save_feedback(fb_recent)

        # 2. Feedback from 29 days ago (Should be included)
        fb_border = ActionFeedback(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_2",
            outcome="did_not_work",
            notes="Minimum payment too tight",
            created_at=now - timedelta(days=29),
        )
        await repo.save_feedback(fb_border)

        # 3. Feedback from 35 days ago (Should be EXCLUDED)
        fb_old = ActionFeedback(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_3",
            outcome="worked",
            notes="Old action from last month",
            created_at=now - timedelta(days=35),
        )
        await repo.save_feedback(fb_old)

        # Query recent feedback with default 30 days
        recent_feedback = await repo.get_recent_feedback(sample_profile.user_id, days=30)

        # Only the 10-day and 29-day items must be returned
        assert len(recent_feedback) == 2
        returned_action_ids = [f.action_id for f in recent_feedback]
        assert "act_1" in returned_action_ids
        assert "act_2" in returned_action_ids
        assert "act_3" not in returned_action_ids
