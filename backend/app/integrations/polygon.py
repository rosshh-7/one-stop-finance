"""
Polygon.io integration for EOD options volume anomaly detection.
Uses the free tier (15-min delayed data, unlimited REST calls).
Rate limit on free tier: ~5 req/min — we sleep 12s between calls.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.polygon.io"
_SLEEP = 12.0   # 5 req/min on free tier = 1 req per 12s


async def fetch_ticker_volume(
    ticker: str,
    api_key: str,
    lookback_days: int = 31,
) -> dict | None:
    """
    Fetch daily aggregate (close volume) for a ticker over the past N days.
    Returns {symbol, avg_30d_volume, today_volume, anomaly_ratio} or None.
    """
    if not api_key:
        return None

    now = datetime.now(timezone.utc)
    from_date = (now - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    to_date   = now.strftime("%Y-%m-%d")

    url = f"{_BASE}/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params={"apiKey": api_key, "adjusted": "true"})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.debug("Polygon fetch failed for %s: %s", ticker, exc)
        return None

    results = data.get("results") or []
    if len(results) < 5:
        return None

    # Last result = most recent trading day
    recent = results[-1]
    today_vol = recent.get("v", 0) or 0

    # 30-day average excluding the last day
    avg_30d = sum(r.get("v", 0) for r in results[:-1]) / max(len(results) - 1, 1)

    if avg_30d == 0:
        return None

    return {
        "symbol":         ticker,
        "total_volume":   int(today_vol),
        "avg_30d_volume": int(avg_30d),
        "anomaly_ratio":  round(today_vol / avg_30d, 2),
        "signal_date":    datetime.now(timezone.utc),
    }


async def fetch_all_theme_volumes(
    symbols: list[str],
    api_key: str,
) -> list[dict]:
    """Fetch volume anomalies for all theme tickers, rate-limited."""
    results = []
    for sym in symbols:
        result = await fetch_ticker_volume(sym, api_key)
        if result:
            results.append(result)
        await asyncio.sleep(_SLEEP)
    return results
