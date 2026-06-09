import json
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.yfinance_client import fetch_market_indices
from app.integrations.news_client import fetch_market_news
from app.features.themes.service import get_theme_intelligence as _get_theme_intelligence
from app.features.insiders.service import get_insider_highlights as _get_insider_highlights

INDICES_KEY = "public:market-indices"
NEWS_KEY    = "public:news-feed"
INDICES_TTL = 60     # seconds
NEWS_TTL    = 300    # seconds


async def get_market_summary(redis: Redis) -> list[dict]:
    cached = await redis.get(INDICES_KEY)
    if cached:
        return json.loads(cached)
    data = await fetch_market_indices()
    if data:
        await redis.setex(INDICES_KEY, INDICES_TTL, json.dumps(data))
    return data


async def get_news_feed(redis: Redis, limit: int = 24) -> list[dict]:
    cached = await redis.get(NEWS_KEY)
    if cached:
        return json.loads(cached)[:limit]
    data = await fetch_market_news(limit)
    if data:
        await redis.setex(NEWS_KEY, NEWS_TTL, json.dumps(data))
    return data


async def get_theme_intelligence(redis: Redis, db: AsyncSession) -> list[dict]:
    return await _get_theme_intelligence(redis, db)


async def get_insider_highlights(redis: Redis, db: AsyncSession, limit: int = 5) -> list[dict]:
    return await _get_insider_highlights(redis, db, limit)
