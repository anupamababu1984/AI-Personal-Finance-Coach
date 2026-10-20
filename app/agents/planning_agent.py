from typing import List, Optional
from app.domain.models import (
    UserProfile,
    ActionFeedback,
    FinancialPlanPayload,
)
from app.domain.benchmarks import CuratedMarketBenchmarks
from app.infrastructure.llm_client import LLMClient


class PlanningAgent:
    """Generates structured financial plans tailored to demographics and feedback."""

    def __init__(self, llm_client: LLMClient, benchmarks: CuratedMarketBenchmarks):
        self.llm_client = llm_client
        self.benchmarks = benchmarks

    async def generate_plan(
        self,
        profile: UserProfile,
        recent_feedback: List[ActionFeedback],
        prior_critique: Optional[str] = None,
    ) -> FinancialPlanPayload:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(profile, recent_feedback, prior_critique)

        response_dict = await self.llm_client.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return FinancialPlanPayload.model_validate(response_dict)

    def _build_system_prompt(self) -> str:
        b = self.benchmarks
        return f"""You are an expert, objective AI Personal Finance Coach.
Your objective is to generate a personalized, realistic, and strictly grounded personal financial plan formatted as an actionable checklist.

CURATED MARKET BENCHMARKS (Do not deviate from these baseline assumptions):
- High-Yield Savings Account (HYSA) APY: {b.hysa_apy * 100:.1f}%
- Historical Diversified Equity Index Return: {b.historical_equity_return * 100:.1f}% annual average
- Standard Emergency Fund Target: {b.standard_emergency_fund.min_months} to {b.standard_emergency_fund.max_months} months of living expenses
- Safe Retirement Withdrawal Rate: {b.safe_withdrawal_rate * 100:.1f}% rule

RULES:
1. Generate between 3 and 5 prioritized actions.
2. Each action MUST have: id (act_1, act_2, ...), category (emergency_fund, debt_management, investment, budgeting), title, recommendation, rationale, assumptions, effort (low, medium, high), status (pending).
3. Ground all recommendations strictly in the user's provided income, expenses, debt, risk appetite, and goals.
4. If monthly expenses exceed income, prioritize cash flow triage and debt prevention over investing.
5. If recent user feedback indicates an action worked or DID NOT WORK, adapt your recommendations accordingly. DO NOT re-recommend mechanisms the user previously rejected.
6. Output MUST strictly be valid JSON conforming to:
{{
  "health_summary": "...",
  "actions": [
    {{
      "id": "act_1",
      "category": "emergency_fund",
      "title": "...",
      "recommendation": "...",
      "rationale": "...",
      "assumptions": "...",
      "effort": "low",
      "status": "pending"
    }}
  ]
}}"""

    def _build_user_prompt(
        self,
        profile: UserProfile,
        recent_feedback: List[ActionFeedback],
        prior_critique: Optional[str] = None,
    ) -> str:
        feedback_lines = []
        if recent_feedback:
            feedback_lines.append("RECENT USER FEEDBACK (Last 30 Days):")
            for f in recent_feedback:
                outcome_str = "WORKED" if f.outcome == "worked" else "did_not_work"
                notes_part = f" - Notes: {f.notes}" if f.notes else ""
                feedback_lines.append(f"- Action [{f.action_id}]: {outcome_str}{notes_part}")
        else:
            feedback_lines.append("RECENT USER FEEDBACK: None. This is a fresh planning run.")

        feedback_section = "\n".join(feedback_lines)

        critique_section = ""
        if prior_critique:
            critique_section = f"""CRITICAL REVISION INSTRUCTIONS FROM PREVIOUS HHH EVALUATION:
Your previous plan attempt failed evaluation with the following critique:
"{prior_critique}"
You must explicitly correct these issues in this revision."""

        return f"""USER PROFILE:
- Age: {profile.age}
- Annual Income: ${profile.annual_income:,.2f}
- Monthly Expenses: ${profile.monthly_expenses:,.2f}
- Savings: ${profile.savings:,.2f}
- Investments: ${profile.investments:,.2f}
- Debt: ${profile.debt:,.2f} ({profile.debt_details or 'None'})
- Risk Appetite: {profile.risk_appetite.value}
- Investment Horizon: {profile.investment_horizon_years} years
- Retirement Target Age: {profile.retirement_age_target}
- Primary Goal: {profile.primary_goal}
- Monthly Investment Capacity: ${profile.monthly_investment_capacity:,.2f}

{feedback_section}

{critique_section}

Generate the candidate financial plan JSON now."""
