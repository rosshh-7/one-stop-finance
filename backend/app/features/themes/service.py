from datetime import datetime, timezone
from redis.asyncio import Redis

from app.features.themes.schemas import SyncSourceKey, SyncSourceStatus, SyncStatusResponse

# Metadata for each rate-limited source
SYNC_SOURCES: dict[str, dict] = {
    "fmp": {
        "label": "FMP Ticker Classification",
        "description": "Company profiles used by Haiku to classify tickers into themes",
        "stale_after_hours": 168,  # 7 days — 250 calls/day limit
    },
    "trends": {
        "label": "Google Trends",
        "description": "Theme keyword search velocity via pytrends",
        "stale_after_hours": 168,  # 7 days — Google soft-blocks heavy use
    },
    "polygon": {
        "label": "Options Flow",
        "description": "EOD options volume anomaly detection per theme ticker",
        "stale_after_hours": 24,   # 1 day — daily EOD pull
    },
    "etf": {
        "label": "ETF Holdings",
        "description": "Theme ETF constituent lists for ticker coverage expansion",
        "stale_after_hours": 168,  # 7 days — holdings change slowly
    },
    "etf_signals": {
        "label": "Theme-ETF Flow + Options",
        "description": "Daily volume vs 30d baseline + put/call ratio + OTM call OI per theme ETF",
        "stale_after_hours": 24,   # 1 day — daily yfinance snapshot
    },
}

REDIS_PREFIX = "theme:sync"


async def get_sync_status(redis: Redis) -> SyncStatusResponse:
    sources: list[SyncSourceStatus] = []

    for source_key, meta in SYNC_SOURCES.items():
        status = await redis.get(f"{REDIS_PREFIX}:{source_key}:status") or "idle"
        last_run = await redis.get(f"{REDIS_PREFIX}:{source_key}:last_run")
        error = await redis.get(f"{REDIS_PREFIX}:{source_key}:error")

        is_stale = True
        if last_run:
            last_dt = datetime.fromisoformat(last_run)
            age_hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
            is_stale = age_hours > meta["stale_after_hours"]

        sources.append(SyncSourceStatus(
            source=source_key,
            label=meta["label"],
            description=meta["description"],
            status=status,
            last_synced_at=last_run,
            is_stale=is_stale,
            stale_after_hours=meta["stale_after_hours"],
            error=error,
        ))

    return SyncStatusResponse(sources=sources)


async def trigger_sync(
    redis: Redis,
    source: SyncSourceKey | str,
) -> tuple[list[str], list[str]]:
    """
    Dispatch Celery sync tasks for the requested source(s).
    Returns (triggered, skipped) — skipped if a sync is already running.
    """
    from app.workers.theme_intelligence import (
        sync_fmp, sync_trends, sync_polygon, sync_etf, sync_etf_signals,
    )

    task_map = {
        "fmp":         sync_fmp,
        "trends":      sync_trends,
        "polygon":     sync_polygon,
        "etf":         sync_etf,
        "etf_signals": sync_etf_signals,
    }

    targets = list(task_map.keys()) if source == "all" else [source]
    triggered, skipped = [], []

    for key in targets:
        current_status = await redis.get(f"{REDIS_PREFIX}:{key}:status")
        if current_status == "running":
            skipped.append(key)
            continue

        await redis.set(f"{REDIS_PREFIX}:{key}:status", "running")
        await redis.delete(f"{REDIS_PREFIX}:{key}:error")
        task_map[key].delay()
        triggered.append(key)

    return triggered, skipped


# ---------------------------------------------------------------------------
# Full pipeline status + trigger
# ---------------------------------------------------------------------------

PIPELINE_KEY = "theme:pipeline"

_STEP_LABELS = {
    "edgar":       "Fetching insider filings",
    "congress":    "Fetching congressional trades",
    "contracts":   "Fetching government contracts",
    "fmp":         "Classifying new tickers (Haiku)",
    "trends":      "Syncing Google Trends",
    "etf":         "Syncing ETF holdings",
    "polygon":     "Detecting options anomalies",
    "etf_signals": "Theme-ETF flow + options snapshot",
    "scoring":     "Scoring all themes",
}


async def get_pipeline_status(redis: Redis) -> dict:
    data = await redis.hgetall(PIPELINE_KEY)
    status       = data.get("status", "idle")
    current_step = data.get("current_step", "")
    return {
        "status":        status,
        "current_step":  current_step,
        "step_label":    _STEP_LABELS.get(current_step, current_step),
        "last_run":      data.get("last_run"),
        "started_at":    data.get("started_at"),
        "error":         data.get("error") or None,
    }


async def trigger_pipeline(redis: Redis) -> dict:
    current = await redis.hget(PIPELINE_KEY, "status")
    if current == "running":
        return {"triggered": False, "reason": "Pipeline already running"}

    from app.workers.theme_intelligence import run_pipeline
    await redis.hset(PIPELINE_KEY, "status", "running")
    await redis.hset(PIPELINE_KEY, "current_step", "Starting...")
    run_pipeline.delay()
    return {"triggered": True, "reason": "Pipeline started"}
