import json
from redis.asyncio import Redis

CHAIN_TTL = 300    # 5 minutes per ticker chain
SCANNER_TTL = 900  # 15 minutes for the full scanner result
SCANNER_KEY = "options:scanner"


def _chain_key(symbol: str, expiry: str) -> str:
    return f"options:chain:{symbol}:{expiry}"


async def get_cached_chain(symbol: str, expiry: str, redis: Redis) -> dict | None:
    raw = await redis.get(_chain_key(symbol, expiry))
    return json.loads(raw) if raw else None


async def set_cached_chain(symbol: str, expiry: str, data: dict, redis: Redis) -> None:
    await redis.setex(_chain_key(symbol, expiry), CHAIN_TTL, json.dumps(data))


async def get_cached_scanner(redis: Redis) -> dict | None:
    raw = await redis.get(SCANNER_KEY)
    return json.loads(raw) if raw else None


async def set_cached_scanner(data: dict, redis: Redis) -> None:
    await redis.setex(SCANNER_KEY, SCANNER_TTL, json.dumps(data))
