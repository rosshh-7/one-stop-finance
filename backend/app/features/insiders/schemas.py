from datetime import datetime
from pydantic import BaseModel


class InsiderHighlight(BaseModel):
    symbol: str
    issuer_name: str | None
    insider_name: str
    insider_title: str | None
    transaction_type: str
    total_value: float | None
    signal_score: int | None
    transaction_date: datetime | None
    sec_filing_url: str | None

    model_config = {"from_attributes": True}
