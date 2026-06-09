from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.response import build_response
from app.features.options.repository import get_cached_chain, cache_chain
from app.features.options.service import fetch_options_chain
from app.redis import get_redis

router = APIRouter(prefix="/options", tags=["options"])


@router.get("/{symbol}")
async def get_chain(
    symbol: str,
    expiry: str | None = Query(default=None),
    redis=Depends(get_redis),
):
    sym = symbol.upper().strip()
    if not sym.isalpha() or len(sym) > 10:
        raise HTTPException(status_code=422, detail="Invalid ticker symbol")

    cache_key = expiry or "nearest"
    cached = await get_cached_chain(sym, cache_key, redis)
    if cached:
        return build_response(cached)

    chain = await fetch_options_chain(sym, expiry)
    if not chain:
        raise HTTPException(status_code=404, detail=f"No options data found for {sym}")

    await cache_chain(sym, chain.get("expiry", cache_key), chain, redis)
    return build_response(chain)
