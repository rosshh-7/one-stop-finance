import json
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.themes.repository import get_all_theme_scores

THEME_SCORES_KEY = "public:theme-intelligence"
THEME_SCORES_TTL = 900  # 15 min — matches the Celery worker cadence


async def get_theme_intelligence(redis: Redis, db: AsyncSession) -> list[dict]:
    cached = await redis.get(THEME_SCORES_KEY)
    if cached:
        return json.loads(cached)

    data = await get_all_theme_scores(db)
    if data:
        await redis.setex(THEME_SCORES_KEY, THEME_SCORES_TTL, json.dumps(data))
    return data
