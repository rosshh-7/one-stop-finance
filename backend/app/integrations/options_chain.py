import asyncio
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf


def _fetch_options_snapshot_sync(symbol: str) -> dict | None:
    ticker = yf.Ticker(symbol)

    expiries = ticker.options
    if not expiries:
        return None

    # Pick nearest expiry that's at least 5 days out
    today = datetime.utcnow().date()
    target = next(
        (e for e in expiries if (datetime.strptime(e, "%Y-%m-%d").date() - today).days >= 5),
        expiries[0],
    )

    chain = ticker.option_chain(target)
    calls: pd.DataFrame = chain.calls.dropna(subset=["strike", "openInterest"])
    puts: pd.DataFrame = chain.puts.dropna(subset=["strike", "openInterest"])

    if calls.empty or puts.empty:
        return None

    total_call_oi = int(calls["openInterest"].sum())
    total_put_oi = int(puts["openInterest"].sum())
    pcr = round(total_put_oi / max(total_call_oi, 1), 4)

    avg_call_iv = round(float(calls["impliedVolatility"].mean()) * 100, 2)
    avg_put_iv = round(float(puts["impliedVolatility"].mean()) * 100, 2)

    max_pain = _compute_max_pain(calls, puts)
    net_gex = _compute_net_gex(calls, puts)

    return {
        "expiry": target,
        "put_call_ratio": pcr,
        "max_pain": round(max_pain, 2),
        "total_call_oi": total_call_oi,
        "total_put_oi": total_put_oi,
        "avg_call_iv": avg_call_iv,
        "avg_put_iv": avg_put_iv,
        "net_gex": round(net_gex, 2),
    }


def _compute_max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> float:
    all_strikes = sorted(set(calls["strike"]).union(puts["strike"]))
    min_pain = float("inf")
    max_pain_strike = all_strikes[0]

    for s in all_strikes:
        call_pain = float(
            ((calls["strike"] - s).clip(lower=0) * calls["openInterest"]).sum()
        )
        put_pain = float(
            ((s - puts["strike"]).clip(lower=0) * puts["openInterest"]).sum()
        )
        total = call_pain + put_pain
        if total < min_pain:
            min_pain = total
            max_pain_strike = s

    return float(max_pain_strike)


def _compute_net_gex(calls: pd.DataFrame, puts: pd.DataFrame) -> float:
    """Simplified GEX: call OI - put OI weighted by delta proxy (ATM = 0.5)."""
    call_gex = float((calls["openInterest"] * 100 * 0.5).sum())
    put_gex = float((puts["openInterest"] * 100 * 0.5).sum())
    return call_gex - put_gex


def _fetch_ohlcv_sync(symbol: str, period: str = "3mo") -> pd.DataFrame | None:
    df = yf.download(symbol, period=period, interval="1d", progress=False, auto_adjust=True)
    if df.empty:
        return None
    return df


async def fetch_options_snapshot(symbol: str) -> dict | None:
    return await asyncio.to_thread(_fetch_options_snapshot_sync, symbol)


async def fetch_ohlcv(symbol: str, period: str = "3mo") -> pd.DataFrame | None:
    return await asyncio.to_thread(_fetch_ohlcv_sync, symbol, period)
