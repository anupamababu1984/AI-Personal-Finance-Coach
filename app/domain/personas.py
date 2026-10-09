from uuid import UUID
from app.domain.models import UserProfile, RiskAppetite

# Persona 1: Younger wealth-building user (Age 28, Aggressive, 30+ yr horizon)
PERSONA_1 = UserProfile(
    user_id=UUID("00000000-0000-0000-0000-000000000001"),
    age=28,
    annual_income=75000.0,
    monthly_expenses=4000.0,
    savings=20000.0,
    investments=15000.0,
    debt=10000.0,
    debt_details="Student loan at 4.5% interest",
    risk_appetite=RiskAppetite.AGGRESSIVE,
    investment_horizon_years=32,
    retirement_age_target=60,
    primary_goal="Wealth building and long-term equity compounding",
    monthly_investment_capacity=1000.0,
)

# Persona 2: Mid-career user (Age 45, Moderate, 15-20 yr horizon)
PERSONA_2 = UserProfile(
    user_id=UUID("00000000-0000-0000-0000-000000000002"),
    age=45,
    annual_income=150000.0,
    monthly_expenses=7000.0,
    savings=100000.0,
    investments=350000.0,
    debt=250000.0,
    debt_details="Mortgage balance at 3.5% interest",
    risk_appetite=RiskAppetite.MODERATE,
    investment_horizon_years=17,
    retirement_age_target=62,
    primary_goal="Retirement catch-up and children's college funding",
    monthly_investment_capacity=3000.0,
)

# Persona 3: Near-retirement user (Age 62, Conservative, 5-7 yr horizon)
PERSONA_3 = UserProfile(
    user_id=UUID("00000000-0000-0000-0000-000000000003"),
    age=62,
    annual_income=110000.0,
    monthly_expenses=5500.0,
    savings=300000.0,
    investments=1000000.0,
    debt=50000.0,
    debt_details="Remaining mortgage balance",
    risk_appetite=RiskAppetite.CONSERVATIVE,
    investment_horizon_years=5,
    retirement_age_target=65,
    primary_goal="Capital preservation and stable retirement income",
    monthly_investment_capacity=1500.0,
)

TEST_PERSONAS = [PERSONA_1, PERSONA_2, PERSONA_3]
