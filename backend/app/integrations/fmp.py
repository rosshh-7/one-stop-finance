"""
Financial Modeling Prep integration — fetches company profiles used to
classify unknown tickers into themes via Claude Haiku.

Free tier: 250 requests/day. Sleeps 0.3s between calls.
"""
import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://financialmodelingprep.com/api/v3"
_SLEEP = 0.3


async def fetch_company_profile(symbol: str, api_key: str) -> dict | None:
    """
    Returns a normalised company profile or None.
    Shape: {symbol, company_name, sector, industry, description, market_cap, market_cap_tier}
    """
    if not api_key:
        return None

    url = f"{_BASE}/profile/{symbol}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params={"apikey": api_key})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.debug("FMP profile fetch failed for %s: %s", symbol, exc)
        return None

    if not data or not isinstance(data, list):
        return None
    entry = data[0]
    market_cap = entry.get("mktCap") or 0
    return {
        "symbol":          (entry.get("symbol") or symbol).upper(),
        "company_name":    entry.get("companyName") or symbol,
        "sector":          entry.get("sector") or "",
        "industry":        entry.get("industry") or "",
        "description":     (entry.get("description") or "")[:1200],
        "market_cap":      float(market_cap),
        "market_cap_tier": _market_cap_tier(market_cap),
    }


async def fetch_profiles_batch(symbols: list[str], api_key: str) -> list[dict]:
    """Rate-limited batch fetch."""
    out: list[dict] = []
    for sym in symbols:
        prof = await fetch_company_profile(sym, api_key)
        if prof:
            out.append(prof)
        await asyncio.sleep(_SLEEP)
    return out


def _market_cap_tier(market_cap: float | int) -> str:
    if market_cap >= 10_000_000_000:
        return "large"
    if market_cap >= 2_000_000_000:
        return "mid"
    if market_cap >= 300_000_000:
        return "small"
    return "micro"
