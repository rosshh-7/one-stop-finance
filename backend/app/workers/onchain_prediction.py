"""
Pre-computes on-chain price predictions for a watchlist of popular tickers
every 15 minutes during market hours. Results are cached in Redis so API
responses are instant.
"""

import asyncio
import json

from app.celery_app import celery as celery_app
from app.features.onchain_prediction.repository import cache_prediction
from app.features.onchain_prediction.service import compute_prediction
from app.redis import get_redis

WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN",
    "GOOGL", "META", "AMD", "SPY", "QQQ",
]


@celery_app.task(name="workers.onchain_prediction.precompute")
def precompute_predictions():
    asyncio.run(_precompute_all())


async def _precompute_all():
    redis = await get_redis()
    for symbol in WATCHLIST:
        try:
            prediction = await compute_prediction(symbol)
            await cache_prediction(symbol, prediction, redis)
        except Exception:
            pass
