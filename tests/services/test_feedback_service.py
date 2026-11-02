"""
Unit and integration tests for the FeedbackService.
Verifies feedback persistence, active plan action mutation, and 30-day adaptive integration.
"""
import pytest
from uuid import UUID

from app.domain.models import (
    UserProfile,
    RiskAppetite,
    PlanStatus,
    ActionCategory,
    ActionStatus,
    FinancialPlanPayload,
    PlanAction,
)
from app.infrastructure.repository import InMemoryFinanceRepository
from app.services.intake_service import IntakeService
from app.services.feedback_service import FeedbackService, FeedbackSubmission


@pytest.fixture
def repo():
    return InMemoryFinanceRepository()


@pytest.fixture
def feedback_service(repo):
    return FeedbackService(repo)


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
    return FinancialPlanPayload(
        health_summary="Strong foundation for growth.",
        actions=[
            PlanAction(
                id="act_1",
                category=ActionCategory.EMERGENCY_FUND,
                title="Establish 3-Month Emergency Reserve",
                recommendation="Allocate $500/mo into a 4.5% APY HYSA until reaching $12,000.",
                rationale="Mitigates liquidity vulnerability before aggressive investing.",
                assumptions="Assumes standard cash savings earn ~4.5% in HYSA.",
                effort="low",
                status=ActionStatus.PENDING,
            ),
            PlanAction(
                id="act_2",
                category=ActionCategory.DEBT_MANAGEMENT,
                title="Student Loan Paydown Strategy",
                recommendation="Allocate $300/mo extra to clear debt.",
                rationale="Eliminate interest drag.",
                assumptions="4.5% loan rate",
                effort="medium",
                status=ActionStatus.PENDING,
            ),
            PlanAction(
                id="act_3",
                category=ActionCategory.INVESTMENT,
                title="Broad Market Equity Compounding",
                recommendation="Invest $200/mo into low-cost index funds.",
                rationale="7.5% long-term returns.",
                assumptions="7.5% historical return",
                effort="medium",
                status=ActionStatus.PENDING,
            ),
        ],
    )


class TestFeedbackService:
    @pytest.mark.asyncio
    async def test_submit_feedback_persists_record(self, repo, feedback_service, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)

        submission = FeedbackSubmission(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_1",
            outcome="worked",
            notes="Opened account and set up automated transfer",
        )

        feedback_id = await feedback_service.submit_feedback(submission)
        assert isinstance(feedback_id, UUID)

        # Verify feedback stored in repository
        recent = await repo.get_recent_feedback(sample_profile.user_id, days=30)
        assert len(recent) == 1
        assert recent[0].action_id == "act_1"
        assert recent[0].outcome == "worked"
        assert recent[0].notes == "Opened account and set up automated transfer"

    @pytest.mark.asyncio
    async def test_submit_feedback_updates_active_plan_action_status(self, repo, feedback_service, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)

        # Initially act_1 is pending
        active_before = await repo.get_active_plan(sample_profile.user_id)
        assert active_before["actions"][0]["status"] == ActionStatus.PENDING

        # Submit 'did_not_work' feedback on act_1
        submission = FeedbackSubmission(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_1",
            outcome="did_not_work",
            notes="Deposit minimum was too high",
        )
        await feedback_service.submit_feedback(submission)

        # Active plan action status must now be DID_NOT_WORK
        active_after = await repo.get_active_plan(sample_profile.user_id)
        assert active_after["actions"][0]["status"] == ActionStatus.DID_NOT_WORK
        # Other actions remain untouched
        assert active_after["actions"][1]["status"] == ActionStatus.PENDING

    @pytest.mark.asyncio
    async def test_closed_feedback_loop_integration(self, repo, feedback_service, sample_profile, sample_plan):
        await repo.save_profile(sample_profile)
        plan_id = await repo.save_plan(sample_plan, sample_profile.user_id, status=PlanStatus.ACTIVE)

        # Submit feedback
        submission = FeedbackSubmission(
            user_id=sample_profile.user_id,
            plan_id=plan_id,
            action_id="act_1",
            outcome="did_not_work",
            notes="Minimum deposit was too high for my freelancing cash flow",
        )
        await feedback_service.submit_feedback(submission)

        # Call IntakeService to verify feedback is immediately captured
        intake_service = IntakeService(repo)
        intake_context = await intake_service.get_intake_context(sample_profile.user_id)

        assert len(intake_context.recent_feedback) == 1
        assert "REJECTED/DID NOT WORK" in intake_context.feedback_summary
        assert "Minimum deposit was too high" in intake_context.feedback_summary
