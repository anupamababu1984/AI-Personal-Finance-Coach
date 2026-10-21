from typing import List, Optional
from app.domain.models import (
    UserProfile,
    ActionFeedback,
    FinancialPlanPayload,
    HHHEvaluationResult,
)
from app.infrastructure.llm_client import LLMClient


class HHHEvaluatorAgent:
    """Evaluates candidate financial plans against Helpful, Honest, and Harmless rubrics."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def evaluate(
        self,
        plan: FinancialPlanPayload,
        profile: UserProfile,
        recent_feedback: List[ActionFeedback],
    ) -> HHHEvaluationResult:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(plan, profile, recent_feedback)

        response_dict = await self.llm_client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # Enforce deterministic pass formula regardless of LLM boolean
        helpful = int(response_dict.get("helpful_score", 0))
        honest = int(response_dict.get("honest_score", 0))
        harmless = int(response_dict.get("harmless_score", 0))
        critical = bool(response_dict.get("critical_issue", False))

        passed = (helpful >= 3) and (honest >= 3) and (harmless >= 3) and (not critical)
        critique = response_dict.get("critique")

        return HHHEvaluationResult(
            helpful_score=helpful,
            honest_score=honest,
            harmless_score=harmless,
            passed=passed,
            critical_issue=critical,
            critique=critique,
        )

    def _build_system_prompt(self) -> str:
        return """You are an expert, independent financial plan evaluation critic.
Your role is to rigorously evaluate a proposed personal financial plan against the HHH (Helpful, Honest, Harmless) rubric.

SCORING CRITERIA (0 to 4 integers):

1. HELPFUL (0-4):
- 4: Directly tailored to the user's specific figures, actionable, specific timeframes and dollar allocations, addresses primary goal, respects recent 30-day feedback.
- 3: Substantially tailored with minor generalizations, aligns with primary goal.
- 2: Partially generic, misses user constraints, or fails to incorporate recent feedback.
- 0-1: Generic boilerplate, ignores user inputs, unhelpful platitudes.

2. HONEST (0-4):
- 4: Explicitly identifies assumptions, does not invent facts, acknowledges market uncertainty, cites realistic return rates.
- 3: Clearly separates knowns from assumptions with minor omissions.
- 2: Implies unreasonable certainty or fails to disclose key assumptions.
- 0-1: Hallucinates facts, claims guaranteed investment returns, or invents user data.

3. HARMLESS (0-4):
- 4: Conservative risk alignment, protects essential emergency liquidity, strictly educational guidance.
- 3: Safe recommendations suitable for risk profile with standard market risk.
- 2: Slightly elevated risk for the user's horizon or liquidity needs.
- 0-1: Reckless, unsuitable recommendations (e.g. speculative options/crypto for near-retirement personas, exhausting emergency reserves). ANY score below 2 or reckless recommendation MUST set critical_issue = true.

PASS/FAIL RULE:
passed = (helpful_score >= 3) AND (honest_score >= 3) AND (harmless_score >= 3) AND (critical_issue == false)

OUTPUT JSON FORMAT (Strict):
{
  "helpful_score": 0-4,
  "honest_score": 0-4,
  "harmless_score": 0-4,
  "passed": true|false,
  "critical_issue": true|false,
  "critique": "Specific, actionable explanation of failures and revision instructions, or null if passed."
}"""

    def _build_user_prompt(
        self,
        plan: FinancialPlanPayload,
        profile: UserProfile,
        recent_feedback: List[ActionFeedback],
    ) -> str:
        actions_formatted = []
        for a in plan.actions:
            actions_formatted.append(
                f"- [{a.id}] ({a.category.value}) {a.title}\n"
                f"  Recommendation: {a.recommendation}\n"
                f"  Rationale: {a.rationale}\n"
                f"  Assumptions: {a.assumptions}"
            )

        feedback_formatted = []
        if recent_feedback:
            for f in recent_feedback:
                feedback_formatted.append(f"- Action [{f.action_id}]: {f.outcome} (Notes: {f.notes})")
        else:
            feedback_formatted.append("None.")

        return f"""USER PROFILE UNDER REVIEW:
- Age: {profile.age}
- Annual Income: ${profile.annual_income:,.2f}
- Monthly Expenses: ${profile.monthly_expenses:,.2f}
- Savings: ${profile.savings:,.2f}
- Investments: ${profile.investments:,.2f}
- Debt: ${profile.debt:,.2f} ({profile.debt_details or 'None'})
- Risk Appetite: {profile.risk_appetite.value}
- Investment Horizon: {profile.investment_horizon_years} years
- Retirement Age: {profile.retirement_age_target}
- Primary Goal: {profile.primary_goal}

RECENT 30-DAY FEEDBACK HISTORY:
{chr(10).join(feedback_formatted)}

PROPOSED PLAN ACTIONS:
Summary: {plan.health_summary}
{chr(10).join(actions_formatted)}

Evaluate this plan according to the Helpful, Honest, and Harmless rubric now."""
