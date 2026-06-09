from pydantic import BaseModel


class OptionContract(BaseModel):
    strike: float
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float | None
    gamma: float | None
    theta: float | None
    in_the_money: bool


class OptionsChain(BaseModel):
    symbol: str
    expiry: str
    expiries: list[str]
    underlying_price: float
    put_call_ratio: float
    max_pain: float
    calls: list[OptionContract]
    puts: list[OptionContract]
