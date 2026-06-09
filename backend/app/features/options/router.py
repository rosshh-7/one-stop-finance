from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.response import build_response
from app.redis import get_redis
from app.features.options.service import fetch_options_chain, scan_universe
from app.features.options.repository import (
    get_cached_chain, set_cached_chain,
    get_cached_scanner, set_cached_scanner,
)

router = APIRouter(prefix="/options", tags=["options"])


@router.get("/scanner")
async def get_scanner(redis=Depends(get_redis)):
    """Top 10 bullish and top 10 bearish stocks by options chain signals."""
    cached = await get_cached_scanner(redis)
    if cached:
        return build_response(cached)

    result = await scan_universe()
    data = result.model_dump()
    await set_cached_scanner(data, redis)
    return build_response(data)


@router.get("/{symbol}")
async def get_options_chain(
    symbol: str,
    expiry: str | None = Query(default=None),
    redis=Depends(get_redis),
):
    sym = symbol.upper().strip()
    if not sym.isalpha() or len(sym) > 10:
        raise HTTPException(status_code=422, detail="Invalid ticker symbol")

    cache_expiry = expiry or "nearest"
    cached = await get_cached_chain(sym, cache_expiry, redis)
    if cached:
        return build_response(cached)

    chain = await fetch_options_chain(sym, expiry)
    if chain is None:
        raise HTTPException(status_code=404, detail=f"No options data found for {sym}")

    data = chain.model_dump()
    await set_cached_chain(sym, data["expiry"], data, redis)
    return build_response(data)
