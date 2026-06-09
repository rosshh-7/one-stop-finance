from datetime import datetime
from pydantic import BaseModel


class ThemeSummary(BaseModel):
    name: str
    slug: str
    benchmark_etf: str | None
    score: float
    level: str
    unique_companies_buying: int
    total_value_accumulated: float
    primary_signal: str
    scored_at: datetime | None

    model_config = {"from_attributes": True}
