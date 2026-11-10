from app.domain.models import (
    FinancialPlanPayload,
    PlanAction,
    ActionCategory,
    ActionStatus,
    UserProfile,
)


def get_safe_fallback_plan(profile: UserProfile) -> FinancialPlanPayload:
    """
    Returns a standardized conservative educational baseline plan when
    AI plan attempts fail HHH criteria or encounter critical safety violations.
    """
    return FinancialPlanPayload(
        health_summary=(
            "We were unable to tailor specific investment or allocation recommendations safely "
            "based on the current inputs. Here is a conservative, educational baseline guide to establish financial health."
        ),
        actions=[
            PlanAction(
                id="act_fallback_1",
                category=ActionCategory.BUDGETING,
                title="Cash Flow Audit & Discretionary Expense Tracking",
                recommendation="Audit all monthly expenditures for 30 days to establish clear net disposable cash flow before committing capital.",
                rationale="Ensures living expenses are fully quantified and avoids cash flow deficits.",
                assumptions="Assumes manual or bank statement review of past 30-90 days.",
                effort="low",
                status=ActionStatus.PENDING,
            ),
            PlanAction(
                id="act_fallback_2",
                category=ActionCategory.EMERGENCY_FUND,
                title="Establish 3-Month Baseline Emergency Reserve",
                recommendation="Accumulate 3 months of essential living expenses in a liquid high-yield savings account before investing.",
                rationale="Protects against unexpected life disruptions without incurring debt.",
                assumptions="Assumes funds are kept strictly in FDIC-insured liquid accounts.",
                effort="medium",
                status=ActionStatus.PENDING,
            ),
            PlanAction(
                id="act_fallback_3",
                category=ActionCategory.DEBT_MANAGEMENT,
                title="High-Interest Debt Inventory & Prioritization",
                recommendation="List all existing liabilities by interest rate and target debts above 7% APY before taking market risk.",
                rationale="Guarantees a return equal to the avoided interest drag.",
                assumptions="Assumes minimum monthly payments are maintained on all debt lines.",
                effort="medium",
                status=ActionStatus.PENDING,
            ),
        ],
    )
