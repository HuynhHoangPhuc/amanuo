"""Analytics response models for usage, cost, and provider comparison."""

from pydantic import BaseModel


class DailyUsageStat(BaseModel):
    date: str
    job_count: int
    success_count: int
    failed_count: int
    review_count: int
    avg_confidence: float | None


class DailyCostStat(BaseModel):
    date: str
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    provider_breakdown: dict[str, float]  # {"gemini": 0.05, "mistral": 0.02}


class ProviderStat(BaseModel):
    provider: str  # "gemini", "mistral", "local"
    job_count: int
    success_rate: float  # percentage 0-100
    avg_confidence: float | None
    avg_latency_ms: float | None
    total_cost_usd: float


class AnalyticsOverview(BaseModel):
    total_jobs: int
    total_cost_usd: float
    avg_confidence: float | None
    active_schemas: int
    period: str  # "7d", "30d", "90d"
