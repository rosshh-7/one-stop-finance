from fastapi import APIRouter, Depends, HTTPException

from app.core.response import build_response
from app.features.onchain_prediction.repository import get_cached_prediction, cache_prediction
from app.features.onchain_prediction.service import compute_prediction
from app.redis import get_redis

router = APIRouter(prefix="/onchain-prediction", tags=["onchain-prediction"])


@router.get("/{symbol}")
async def get_prediction(
    symbol: str,
    redis=Depends(get_redis),
):
    sym = symbol.upper().strip()
    if not sym.isalpha() or len(sym) > 10:
        raise HTTPException(status_code=422, detail="Invalid ticker symbol")

    cached = await get_cached_prediction(sym, redis)
    if cached:
        return build_response(cached)

    prediction = await compute_prediction(sym)
    await cache_prediction(sym, prediction, redis)
    return build_response(prediction)


@router.post("/{symbol}/refresh")
async def refresh_prediction(
    symbol: str,
    redis=Depends(get_redis),
):
    sym = symbol.upper().strip()
    if not sym.isalpha() or len(sym) > 10:
        raise HTTPException(status_code=422, detail="Invalid ticker symbol")

    prediction = await compute_prediction(sym)
    await cache_prediction(sym, prediction, redis)
    return build_response(prediction)
