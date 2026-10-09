"""
Unit tests for domain models, benchmarks, and standard test personas.
Verifies Pydantic v2 validation constraints, benchmark constants, and persona fixtures.
"""
import pytest
from uuid import UUID
from pydantic import ValidationError

from app.domain.models import (
    RiskAppetite,
    ActionCategory,
    ActionStatus,
    PlanStatus,
    UserProfile,
    PlanAction,
    FinancialPlanPayload,
    HHHEvaluationResult,
    ActionFeedback,
)
from app.domain.benchmarks import CURATED_MARKET_BENCHMARKS
from app.domain.personas import (
    PERSONA_1,
    PERSONA_2,
    PERSONA_3,
    TEST_PERSONAS,
)


class TestDomainModels:
    def test_valid_user_profile_creation(self):
        profile = UserProfile(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            age=30,
            annual_income=80000.0,
            monthly_expenses=3500.0,
            savings=15000.0,
            investments=25000.0,
            debt=5000.0,
            risk_appetite=RiskAppetite.MODERATE,
            investment_horizon_years=20,
            retirement_age_target=65,
            primary_goal="Retirement growth",
            monthly_investment_capacity=1200.0,
        )
        assert profile.age == 30
        assert profile.risk_appetite == RiskAppetite.MODERATE
        assert profile.annual_income == 80000.0

    def test_user_profile_age_constraints(self):
        # Age below 18 must fail
        with pytest.raises(ValidationError):
            UserProfile(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                age=17,
                annual_income=50000.0,
                monthly_expenses=2000.0,
                risk_appetite=RiskAppetite.AGGRESSIVE,
                investment_horizon_years=30,
                retirement_age_target=60,
                primary_goal="Wealth building",
                monthly_investment_capacity=500.0,
            )

        # Age above 120 must fail
        with pytest.raises(ValidationError):
            UserProfile(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                age=125,
                annual_income=50000.0,
                monthly_expenses=2000.0,
                risk_appetite=RiskAppetite.AGGRESSIVE,
                investment_horizon_years=10,
                retirement_age_target=130,
                primary_goal="Wealth building",
                monthly_investment_capacity=500.0,
            )

    def test_user_profile_negative_financials_fail(self):
        # Negative income must fail
        with pytest.raises(ValidationError):
            UserProfile(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                age=30,
                annual_income=-5000.0,
                monthly_expenses=2000.0,
                risk_appetite=RiskAppetite.CONSERVATIVE,
                investment_horizon_years=10,
                retirement_age_target=65,
                primary_goal="Preservation",
                monthly_investment_capacity=500.0,
            )

    def test_plan_action_count_constraint(self):
        def make_action(act_id: str):
            return PlanAction(
                id=act_id,
                category=ActionCategory.EMERGENCY_FUND,
                title="Emergency Reserve",
                recommendation="Save 3 months expenses",
                rationale="Liquidity safety",
                assumptions="HYSA APY 4.5%",
                effort="low",
                status=ActionStatus.PENDING,
            )

        # Less than 3 actions must fail
        with pytest.raises(ValidationError):
            FinancialPlanPayload(
                health_summary="Solid foundation",
                actions=[make_action("act_1"), make_action("act_2")],
            )

        # Valid 3 to 5 actions must pass
        valid_plan = FinancialPlanPayload(
            health_summary="Solid foundation",
            actions=[make_action("act_1"), make_action("act_2"), make_action("act_3")],
        )
        assert len(valid_plan.actions) == 3

        # More than 5 actions must fail
        with pytest.raises(ValidationError):
            FinancialPlanPayload(
                health_summary="Too many actions",
                actions=[make_action(f"act_{i}") for i in range(1, 7)],
            )

    def test_hhh_evaluation_result_bounds(self):
        valid_eval = HHHEvaluationResult(
            helpful_score=4,
            honest_score=3,
            harmless_score=4,
            passed=True,
            critical_issue=False,
            critique=None,
        )
        assert valid_eval.passed is True

        # Score > 4 must fail
        with pytest.raises(ValidationError):
            HHHEvaluationResult(
                helpful_score=5,
                honest_score=3,
                harmless_score=4,
                passed=False,
            )


class TestCuratedBenchmarks:
    def test_curated_benchmarks_constants(self):
        assert CURATED_MARKET_BENCHMARKS.hysa_apy == 0.045
        assert CURATED_MARKET_BENCHMARKS.historical_equity_return == 0.075
        assert CURATED_MARKET_BENCHMARKS.standard_emergency_fund.min_months == 3
        assert CURATED_MARKET_BENCHMARKS.standard_emergency_fund.max_months == 6
        assert CURATED_MARKET_BENCHMARKS.safe_withdrawal_rate == 0.04
        assert CURATED_MARKET_BENCHMARKS.last_updated == "2026-10-01"


class TestPersonas:
    def test_persona_count(self):
        assert len(TEST_PERSONAS) == 3

    def test_persona_1_younger_wealth_builder(self):
        assert PERSONA_1.age == 28
        assert PERSONA_1.annual_income == 75000.0
        assert PERSONA_1.monthly_expenses == 4000.0
        assert PERSONA_1.savings == 20000.0
        assert PERSONA_1.investments == 15000.0
        assert PERSONA_1.debt == 10000.0
        assert PERSONA_1.risk_appetite == RiskAppetite.AGGRESSIVE
        assert PERSONA_1.investment_horizon_years == 32
        assert PERSONA_1.retirement_age_target == 60
        assert PERSONA_1.monthly_investment_capacity == 1000.0

    def test_persona_2_mid_career(self):
        assert PERSONA_2.age == 45
        assert PERSONA_2.annual_income == 150000.0
        assert PERSONA_2.monthly_expenses == 7000.0
        assert PERSONA_2.savings == 100000.0
        assert PERSONA_2.investments == 350000.0
        assert PERSONA_2.debt == 250000.0
        assert PERSONA_2.risk_appetite == RiskAppetite.MODERATE
        assert PERSONA_2.investment_horizon_years == 17
        assert PERSONA_2.retirement_age_target == 62
        assert PERSONA_2.monthly_investment_capacity == 3000.0

    def test_persona_3_near_retirement(self):
        assert PERSONA_3.age == 62
        assert PERSONA_3.annual_income == 110000.0
        assert PERSONA_3.monthly_expenses == 5500.0
        assert PERSONA_3.savings == 300000.0
        assert PERSONA_3.investments == 1000000.0
        assert PERSONA_3.debt == 50000.0
        assert PERSONA_3.risk_appetite == RiskAppetite.CONSERVATIVE
        assert PERSONA_3.investment_horizon_years == 5
        assert PERSONA_3.retirement_age_target == 65
        assert PERSONA_3.monthly_investment_capacity == 1500.0
