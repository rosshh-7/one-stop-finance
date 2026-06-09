import json
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.insiders.repository import get_top_insider_buys

INSIDER_HIGHLIGHTS_KEY = "public:insider-highlights"
INSIDER_HIGHLIGHTS_TTL = 4 * 60 * 60  # 4 hours


async def get_insider_highlights(redis: Redis, db: AsyncSession, limit: int = 5) -> list[dict]:
    cached = await redis.get(INSIDER_HIGHLIGHTS_KEY)
    if cached:
        return json.loads(cached)[:limit]

    data = await get_top_insider_buys(db, limit=limit)
    if data:
        await redis.setex(INSIDER_HIGHLIGHTS_KEY, INSIDER_HIGHLIGHTS_TTL, json.dumps(data))
    return data
