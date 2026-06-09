from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import build_response
from app.database import get_db
from app.redis import get_redis
from app.features.public.service import (
    get_market_summary,
    get_news_feed,
    get_theme_intelligence,
    get_insider_highlights,
)

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/market-summary")
async def market_summary(redis: Redis = Depends(get_redis)):
    data = await get_market_summary(redis)
    return build_response({"indices": data})


@router.get("/news-feed")
async def news_feed(limit: int = 24, redis: Redis = Depends(get_redis)):
    data = await get_news_feed(redis, limit)
    return build_response({"articles": data})


@router.get("/theme-intelligence")
async def theme_intelligence(
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
):
    data = await get_theme_intelligence(redis, db)
    return build_response({"themes": data})


@router.get("/insider-highlights")
async def insider_highlights(
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
):
    data = await get_insider_highlights(redis, db)
    return build_response({"highlights": data})
