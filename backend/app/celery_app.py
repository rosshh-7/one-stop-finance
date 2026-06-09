from celery import Celery
from app.config import settings

celery = Celery(
    "osf",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.market_indices",
        "app.workers.insider_data",
        "app.workers.options_data",
        "app.workers.sentiment",
        "app.workers.theme_intelligence",
        "app.workers.trend_signals",
        "app.workers.realtime_push",
        "app.workers.onchain_prediction",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/New_York",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

celery.conf.beat_schedule = {
    # Market indices — every 30s during market hours
    "fetch-market-indices": {
        "task": "app.workers.market_indices.fetch",
        "schedule": 30.0,
    },
    # Insider filings — every 15 min
    "poll-sec-edgar": {
        "task": "app.workers.insider_data.poll_sec_edgar",
        "schedule": 900.0,
    },
    # Unusual options — every 60s
    "cache-unusual-options": {
        "task": "app.workers.options_data.cache_unusual",
        "schedule": 60.0,
    },
    # News sentiment — every 3 min
    "fetch-and-score-sentiment": {
        "task": "app.workers.sentiment.fetch_and_score",
        "schedule": 180.0,
    },
    # Theme intelligence scoring — every 15 min
    "score-all-themes": {
        "task": "app.workers.theme_intelligence.score_all_themes",
        "schedule": 900.0,
    },
    # Trend reversal signals — every 15 min
    "scan-trend-signals": {
        "task": "app.workers.trend_signals.scan",
        "schedule": 900.0,
    },
    # Real-time quote push — every 15s
    "push-realtime-quotes": {
        "task": "app.workers.realtime_push.push_quotes",
        "schedule": 15.0,
    },
    # On-chain prediction pre-compute — every 15 min
    "precompute-onchain-predictions": {
        "task": "workers.onchain_prediction.precompute",
        "schedule": 900.0,
    },
}
