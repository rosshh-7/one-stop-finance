from typing import Literal
from pydantic import BaseModel


class PredictionSignal(BaseModel):
    name: str
    raw_value: float
    display_value: str
    direction: Literal["bullish", "bearish", "neutral"]
    weight: float


class OptionsSnapshot(BaseModel):
    expiry: str
    put_call_ratio: float
    max_pain: float
    total_call_oi: int
    total_put_oi: int
    avg_call_iv: float
    avg_put_iv: float
    net_gex: float


class PricePrediction(BaseModel):
    symbol: str
    current_price: float
    direction: Literal["bullish", "bearish", "neutral"]
    confidence: float  # 0–100
    bull_score: float  # weighted sum of bullish signals
    bear_score: float  # weighted sum of bearish signals
    support: float | None
    resistance: float | None
    max_pain: float | None
    options: OptionsSnapshot | None
    signals: list[PredictionSignal]
    horizon: str  # "1W"
    cached_at: str
