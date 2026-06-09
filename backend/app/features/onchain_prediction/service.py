from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

from app.integrations.options_chain import fetch_options_snapshot, fetch_ohlcv
from app.ml.features.chain_features import build_features
from app.ml.predictors.price_predictor import score


async def compute_prediction(symbol: str) -> dict:
    sym = symbol.upper()

    options_data, ohlcv = await _fetch_all(sym)

    current_price = _current_price(ohlcv)
    support, resistance = _support_resistance(ohlcv)

    features = build_features(options_data, ohlcv)
    result = score(features)

    return {
        "symbol": sym,
        "current_price": current_price,
        "direction": result["direction"],
        "confidence": result["confidence"],
        "bull_score": result["bull_score"],
        "bear_score": result["bear_score"],
        "support": support,
        "resistance": resistance,
        "max_pain": options_data.get("max_pain") if options_data else None,
        "options": options_data,
        "signals": result["signals"],
        "horizon": "1W",
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }


async def _fetch_all(symbol: str):
    import asyncio
    return await asyncio.gather(
        fetch_options_snapshot(symbol),
        fetch_ohlcv(symbol),
    )


def _current_price(ohlcv: pd.DataFrame | None) -> float:
    if ohlcv is None or ohlcv.empty:
        return 0.0
    try:
        col = ohlcv["Close"]
        if isinstance(ohlcv.columns, pd.MultiIndex):
            col = col.squeeze()
        return round(float(col.dropna().iloc[-1]), 2)
    except Exception:
        return 0.0


def _support_resistance(ohlcv: pd.DataFrame | None) -> tuple[float | None, float | None]:
    if ohlcv is None or len(ohlcv) < 20:
        return None, None
    try:
        col = ohlcv["Close"]
        if isinstance(ohlcv.columns, pd.MultiIndex):
            col = col.squeeze()
        recent = col.dropna().tail(20)
        return round(float(recent.min()), 2), round(float(recent.max()), 2)
    except Exception:
        return None, None
