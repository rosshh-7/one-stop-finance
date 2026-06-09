import asyncio
import math

import pandas as pd
import yfinance as yf

from app.integrations.options_chain import _compute_max_pain


def _fetch_chain_sync(symbol: str, expiry: str | None) -> dict:
    ticker = yf.Ticker(symbol)
    expiries = ticker.options
    if not expiries:
        return {}

    selected = expiry if expiry in expiries else expiries[0]
    chain = ticker.option_chain(selected)

    price_info = ticker.fast_info
    underlying = round(float(price_info.last_price or 0), 2)

    calls_df = chain.calls.fillna(0)
    puts_df = chain.puts.fillna(0)

    calls = _parse_contracts(calls_df, underlying, "call")
    puts = _parse_contracts(puts_df, underlying, "put")

    total_call_oi = int(calls_df["openInterest"].sum())
    total_put_oi = int(puts_df["openInterest"].sum())
    pcr = round(total_put_oi / max(total_call_oi, 1), 3)

    max_pain = _compute_max_pain(
        calls_df.dropna(subset=["strike", "openInterest"]),
        puts_df.dropna(subset=["strike", "openInterest"]),
    )

    return {
        "symbol": symbol.upper(),
        "expiry": selected,
        "expiries": list(expiries[:12]),
        "underlying_price": underlying,
        "put_call_ratio": pcr,
        "max_pain": round(max_pain, 2),
        "calls": calls,
        "puts": puts,
    }


def _parse_contracts(df: pd.DataFrame, underlying: float, kind: str) -> list[dict]:
    rows = []
    for _, row in df.iterrows():
        strike = float(row.get("strike", 0))
        iv = float(row.get("impliedVolatility", 0))

        # Approximate delta: rough Black-Scholes sign
        delta = _approx_delta(strike, underlying, iv, kind)

        rows.append({
            "strike": round(strike, 2),
            "bid": round(float(row.get("bid", 0)), 2),
            "ask": round(float(row.get("ask", 0)), 2),
            "last": round(float(row.get("lastPrice", 0)), 2),
            "volume": int(row.get("volume", 0)),
            "open_interest": int(row.get("openInterest", 0)),
            "implied_volatility": round(iv * 100, 2),
            "delta": delta,
            "gamma": None,
            "theta": None,
            "in_the_money": bool(row.get("inTheMoney", False)),
        })
    return rows


def _approx_delta(strike: float, spot: float, iv: float, kind: str) -> float | None:
    if iv <= 0 or spot <= 0 or strike <= 0:
        return None
    try:
        moneyness = math.log(spot / strike) / max(iv, 0.01)
        raw = 0.5 + moneyness * 0.3
        raw = max(0.01, min(0.99, raw))
        return round(raw if kind == "call" else raw - 1, 3)
    except Exception:
        return None


async def fetch_options_chain(symbol: str, expiry: str | None = None) -> dict:
    return await asyncio.to_thread(_fetch_chain_sync, symbol, expiry)
