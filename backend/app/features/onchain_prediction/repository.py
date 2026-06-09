import json

from redis.asyncio import Redis

PREDICTION_TTL = 300  # 5 minutes


def _key(symbol: str) -> str:
    return f"onchain_prediction:{symbol.upper()}"


async def get_cached_prediction(symbol: str, redis: Redis) -> dict | None:
    raw = await redis.get(_key(symbol))
    if raw:
        return json.loads(raw)
    return None


async def cache_prediction(symbol: str, prediction: dict, redis: Redis) -> None:
    await redis.setex(_key(symbol), PREDICTION_TTL, json.dumps(prediction))
