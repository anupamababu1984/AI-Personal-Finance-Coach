from pydantic import BaseModel


class EmergencyFundRange(BaseModel):
    min_months: int = 3
    max_months: int = 6


class CuratedMarketBenchmarks(BaseModel):
    hysa_apy: float = 0.045                    # 4.5% High-Yield Savings Benchmark
    historical_equity_return: float = 0.075    # 7.5% Long-term diversified equity index
    standard_emergency_fund: EmergencyFundRange = EmergencyFundRange()
    safe_withdrawal_rate: float = 0.04         # 4.0% rule for retirement income
    last_updated: str = "2026-10-01"


CURATED_MARKET_BENCHMARKS = CuratedMarketBenchmarks()
