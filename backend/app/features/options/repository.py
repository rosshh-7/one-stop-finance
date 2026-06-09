import json
from redis.asyncio import Redis

TTL = 60  # 1 minute — options data moves fast


def _key(symbol: str, expiry: str) -> str:
    return f"options_chain:{symbol.upper()}:{expiry}"


async def get_cached_chain(symbol: str, expiry: str, redis: Redis) -> dict | None:
    raw = await redis.get(_key(symbol, expiry))
    return json.loads(raw) if raw else None


async def cache_chain(symbol: str, expiry: str, chain: dict, redis: Redis) -> None:
    await redis.setex(_key(symbol, expiry), TTL, json.dumps(chain))
