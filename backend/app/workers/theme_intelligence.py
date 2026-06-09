"""
Celery task: score all active themes every 15 minutes.

Reads insider_filings already collected by the insider_data worker and computes
a conviction score (0–100) for each theme based on unique company count and
signal bonuses. Stores results in theme_scores table and invalidates the Redis
cache so the next public API request re-fetches fresh data.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.celery_app import celery
from app.database import async_session_factory
from app.models.insider import InsiderFiling, TransactionType
from app.models.theme import Theme, ThemeTicker, ThemeScore, ConvergenceLevel
from app.redis import get_redis

logger = logging.getLogger(__name__)

THEME_SCORES_KEY = "public:theme-intelligence"

# ── Scoring constants ─────────────────────────────────────────────────────────
_BASE_SCORE = {6: 50, 5: 42, 4: 34, 3: 25, 2: 14, 1: 5, 0: 0}

_BONUS_CSUITE          = 10
_BONUS_LARGE_TRADE     = 8   # single trade ≥ $1M
_BONUS_BIG_AGGREGATE   = 5   # total > $5M
_BONUS_CLUSTER         = 5   # 3+ insiders at the same company
_DIVERSITY_BONUS       = 10  # 3+ different signal types firing


def _compute_score(
    insider_rows: list,
    theme_symbols: set[str],
) -> tuple[float, dict, int]:
    """Return (score, signal_breakdown, unique_companies_buying)."""
    buys = [
        r for r in insider_rows
        if r.symbol in theme_symbols and r.transaction_type == TransactionType.BUY
    ]

    companies: set[str] = {r.symbol for r in buys}
    unique_cos = len(companies)
    base = _BASE_SCORE.get(min(unique_cos, 6), 0)

    bonuses: dict[str, int] = {}

    # C-suite bonus
    csuite_cos = {r.symbol for r in buys if r.signal_score and r.signal_score >= 60}
    if csuite_cos:
        bonuses["csuite"] = _BONUS_CSUITE

    # Large single trade
    if any(r.total_value and r.total_value >= 1_000_000 for r in buys):
        bonuses["large_trade"] = _BONUS_LARGE_TRADE

    # Big aggregate
    total_value = sum(r.total_value or 0 for r in buys)
    if total_value >= 5_000_000:
        bonuses["big_aggregate"] = _BONUS_BIG_AGGREGATE

    # Cluster (3+ insiders at same company)
    from collections import Counter
    per_company = Counter(r.symbol for r in buys)
    if any(v >= 3 for v in per_company.values()):
        bonuses["cluster"] = _BONUS_CLUSTER

    # Diversity bonus
    if len(bonuses) >= 3:
        bonuses["diversity"] = _DIVERSITY_BONUS

    score = min(base + sum(bonuses.values()), 100)

    level_val = (
        ConvergenceLevel.ALERT if score >= 70
        else ConvergenceLevel.WATCH if score >= 45
        else ConvergenceLevel.QUIET
    )

    breakdown = {
        "base_score": base,
        "unique_companies_buying": unique_cos,
        "total_value_accumulated": total_value,
        "csuite_count": len(csuite_cos),
        "bonuses": bonuses,
        "level": level_val.value,
    }

    return score, breakdown, unique_cos


async def _run_scoring():
    cutoff = datetime.now(timezone.utc) - timedelta(days=14)

    async with async_session_factory() as session:
        # Load all recent insider buys (last 14 days)
        recent_buys = (await session.execute(
            select(InsiderFiling).where(
                InsiderFiling.transaction_type == TransactionType.BUY,
                InsiderFiling.filing_date >= cutoff,
            )
        )).scalars().all()

        # Load all active themes with their ticker symbols
        themes = (await session.execute(
            select(Theme).where(Theme.is_active == True)
        )).scalars().all()

        # Preload all theme tickers in one query
        all_tickers = (await session.execute(
            select(ThemeTicker).where(ThemeTicker.is_active == True)
        )).scalars().all()

        tickers_by_theme: dict[str, set[str]] = {}
        for tt in all_tickers:
            tickers_by_theme.setdefault(tt.theme_id, set()).add(tt.symbol)

        now = datetime.now(timezone.utc)
        scored = 0

        for theme in themes:
            symbols = tickers_by_theme.get(theme.id, set())
            score, breakdown, unique_cos = _compute_score(recent_buys, symbols)

            level = (
                ConvergenceLevel.ALERT if score >= 70
                else ConvergenceLevel.WATCH if score >= 45
                else ConvergenceLevel.QUIET
            )

            # Upsert into theme_scores
            existing = (await session.execute(
                select(ThemeScore).where(ThemeScore.theme_id == theme.id)
            )).scalar_one_or_none()

            if existing:
                existing.score = score
                existing.level = level
                existing.unique_companies_buying = unique_cos
                existing.total_value_accumulated = breakdown["total_value_accumulated"]
                existing.csuite_count = breakdown["csuite_count"]
                existing.signal_breakdown = breakdown
                existing.scored_at = now
            else:
                session.add(ThemeScore(
                    theme_id=theme.id,
                    score=score,
                    level=level,
                    unique_companies_buying=unique_cos,
                    total_value_accumulated=breakdown["total_value_accumulated"],
                    csuite_count=breakdown["csuite_count"],
                    signal_breakdown=breakdown,
                    scored_at=now,
                ))
            scored += 1

        await session.commit()

    # Invalidate the public Redis cache so next request re-fetches from DB
    redis = await get_redis()
    await redis.delete(THEME_SCORES_KEY)

    logger.info("Scored %d themes", scored)
    return scored


@celery.task(name="app.workers.theme_intelligence.score_all_themes")
def score_all_themes():
    scored = asyncio.get_event_loop().run_until_complete(_run_scoring())
    return {"themes_scored": scored}
