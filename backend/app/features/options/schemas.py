from pydantic import BaseModel


class OptionContract(BaseModel):
    strike: float
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float
    in_the_money: bool


class OptionsChainResponse(BaseModel):
    symbol: str
    expiry: str
    expiries: list[str]
    underlying_price: float
    max_pain: float
    put_call_ratio: float
    total_contracts: int
    calls: list[OptionContract]
    puts: list[OptionContract]


class StockScore(BaseModel):
    symbol: str
    score: float          # -100 to +100; positive = bullish
    signal: str           # "Strong Bullish" | "Bullish" | "Bearish" | "Strong Bearish"
    put_call_ratio: float
    max_pain: float
    underlying_price: float
    max_pain_pct: float   # (max_pain - spot) / spot * 100
    call_volume: int
    put_volume: int


class ScannerResponse(BaseModel):
    bullish: list[StockScore]
    bearish: list[StockScore]
    scanned_at: str
