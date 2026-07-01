"""
Per-theme news sentiment worker.

Aggregates headlines from Yahoo Finance RSS feeds (free, no key), assigns
each headline to one or more themes via name + ETF symbol + top-ticker
keyword matching, then computes a per-theme sentiment score.

Results are written to Redis (`theme:sentiment:{slug}` → JSON) and read by
`_run_scoring()` during the next scoring cycle. The `sentiment_signal`
flag on `ThemeScore` is True when the rolling sentiment is positive.

No DB writes — this is short-lived signal cached for the next scoring run.
"""
import asyncio
import json
import logging
import re
from datetime import datetime, timezone

import redis as redis_sync

from app.celery_app import celery
from app.config import settings
from app.integrations.news_client import _fetch_news_sync
from app.integrations.sentiment_analyzer import score_headlines
from app.theme_config import THEME_CONFIG

logger = logging.getLogger(__name__)

REDIS_PREFIX = "theme:sentiment"
TTL_SEC = 3 * 3600  # 3 hours — beat runs every 3 min, so cache always fresh


def _redis():
    return redis_sync.from_url(settings.redis_url, decode_responses=True)


def _build_keyword_map() -> dict[str, set[str]]:
    """
    For each theme slug build a lowercase keyword set used to match headlines.
    Includes theme name tokens, benchmark ETF, and top ticker symbols.
    """
    out: dict[str, set[str]] = {}
    for cfg in THEME_CONFIG:
        slug = cfg["slug"]
        kws: set[str] = set()
        # Theme name tokens (>= 4 chars) — drops "&", "and", "the"
        for tok in re.findall(r"[a-zA-Z]+", cfg["name"].lower()):
            if len(tok) >= 4:
                kws.add(tok)
        # ETF symbol
        if cfg.get("benchmark_etf"):
            kws.add(cfg["benchmark_etf"].lower())
        # Top tickers (longer-than-1-char to avoid 'F', 'V', 'C' false hits)
        for t in cfg.get("tickers", [])[:12]:
            sym = t["symbol"]
            if len(sym) >= 3:
                kws.add(sym.lower())
        out[slug] = kws
    return out


def _bucket_headlines(items: list[dict], keyword_map: dict[str, set[str]]) -> dict[str, list[str]]:
    """Assign each headline to every theme whose keyword set it hits."""
    buckets: dict[str, list[str]] = {slug: [] for slug in keyword_map}
    for it in items:
        text = f"{it.get('title') or ''} {it.get('summary') or ''}".lower()
        text_tokens = set(re.findall(r"[a-zA-Z]+", text))
        for slug, kws in keyword_map.items():
            if text_tokens & kws:
                buckets[slug].append(it.get("title") or "")
    return buckets


def _run() -> int:
    items = _fetch_news_sync(limit=60)
    if not items:
        logger.info("sentiment: no news items returned")
        return 0

    keyword_map = _build_keyword_map()
    buckets = _bucket_headlines(items, keyword_map)

    r = _redis()
    now = datetime.now(timezone.utc).isoformat()
    written = 0
    for slug, headlines in buckets.items():
        result = score_headlines(headlines)
        payload = {**result, "updated_at": now}
        r.setex(f"{REDIS_PREFIX}:{slug}", TTL_SEC, json.dumps(payload))
        written += 1
        if headlines:
            logger.info(
                "sentiment: %-22s score=%+.2f from %d headlines",
                slug, result["score"], result["headlines_count"],
            )
    return written


@celery.task(name="app.workers.sentiment.fetch_and_score")
def fetch_and_score():
    logger.info("sentiment: starting")
    try:
        n = _run()
        logger.info("sentiment: wrote %d theme sentiment entries to Redis", n)
    except Exception as exc:
        logger.error("sentiment: failed — %s", exc)
        raise
