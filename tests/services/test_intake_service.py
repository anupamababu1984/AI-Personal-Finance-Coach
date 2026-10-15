"""
Unit tests for IntakeService.
Verifies profile retrieval, feedback aggregation, and prompt summary formatting.
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta

from app.domain.models import (
    UserProfile,
    RiskAppetite,
    ActionFeedback,
)
from app.infrastructure.repository import InMemoryFinanceRepository
from app.services.intake_service import IntakeService, IntakeContext


@pytest.fixture
def repo():
    return InMemoryFinanceRepository()


@pytest.fixture
def intake_service(repo):
    return IntakeService(repo)


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


class TestIntakeService:
    @pytest.mark.asyncio
    async def test_get_intake_context_with_feedback(self, intake_service, repo, sample_profile):
        await repo.save_profile(sample_profile)
        now = datetime.now(timezone.utc)
        plan_id = uuid4()

        # Add 2 feedback items
        fb1 = ActionFeedback(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_1",
            outcome="worked",
            notes="Set up automated transfer",
            created_at=now - timedelta(days=5),
        )
        fb2 = ActionFeedback(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_2",
            outcome="did_not_work",
            notes="Minimum deposit too high",
            created_at=now - timedelta(days=12),
        )
        await repo.save_feedback(fb1)
        await repo.save_feedback(fb2)

        context = await intake_service.get_intake_context(sample_profile.user_id)

        assert isinstance(context, IntakeContext)
        assert context.profile.user_id == sample_profile.user_id
        assert len(context.recent_feedback) == 2
        assert context.feedback_summary is not None
        assert "### Recent User Feedback (Last 30 Days):" in context.feedback_summary
        assert "Action [act_1]: SUCCESS/WORKED" in context.feedback_summary
        assert "Action [act_2]: REJECTED/DID NOT WORK" in context.feedback_summary

    @pytest.mark.asyncio
    async def test_get_intake_context_zero_feedback(self, intake_service, repo, sample_profile):
        await repo.save_profile(sample_profile)

        context = await intake_service.get_intake_context(sample_profile.user_id)

        assert context.profile.user_id == sample_profile.user_id
        assert len(context.recent_feedback) == 0
        assert context.feedback_summary is None

    @pytest.mark.asyncio
    async def test_nonexistent_user_raises_value_error(self, intake_service):
        missing_id = uuid4()
        with pytest.raises(ValueError, match=f"Profile not found for user {missing_id}"):
            await intake_service.get_intake_context(missing_id)
