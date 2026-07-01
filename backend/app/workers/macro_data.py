"""
FRED macro data collector.

Pulls key economic series from the St. Louis Fed FRED API.
Macro alignment (sector trending correctly) adds a +4 scoring bonus.
Requires FRED_API_KEY in .env (free, instant signup at fred.stlouisfed.org).
Runs daily via Celery Beat.

Series tracked and their theme relevance:
  INDPRO   Industrial Production Index         → defense, clean energy, grid
  UMCSENT  Consumer Sentiment                  → fintech, ev
  DCOILWTICO  Crude Oil Spot Price             → clean energy, ev (inverse)
  FEDFUNDS Federal Funds Rate                  → fintech (rate environment)
  CPILFESL Core CPI                            → fintech, macro backdrop
  GPUS     Gov't spending                      → defense, gov contracts themes
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.celery_app import celery
from app.config import settings
from app.database import celery_session
from app.models.base import new_uuid
from app.models.theme import MacroSignal

logger = logging.getLogger(__name__)

_FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

# series_id → (name, relevant theme slugs)
_SERIES: dict[str, tuple[str, list[str]]] = {
    "INDPRO":     ("Industrial Production", ["defense-aerospace", "grid-power-infrastructure", "clean-energy"]),
    "UMCSENT":    ("Consumer Sentiment",    ["fintech-payments", "ev-battery-tech"]),
    "DCOILWTICO": ("Crude Oil Spot",        ["clean-energy", "ev-battery-tech"]),
    "FEDFUNDS":   ("Federal Funds Rate",    ["fintech-payments"]),
    "CPILFESL":   ("Core CPI",             ["fintech-payments"]),
    "MANEMP":     ("Manufacturing Jobs",   ["defense-aerospace", "humanoid-robotics"]),
}


def _fetch_series_sync(series_id: str, api_key: str) -> dict | None:
    """Fetch latest observation and previous observation for a FRED series."""
    try:
        resp = httpx.get(
            _FRED_URL,
            params={
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "limit": 2,
                "sort_order": "desc",
            },
            timeout=15,
        )
        resp.raise_for_status()
        observations = resp.json().get("observations", [])
        if len(observations) < 1:
            return None
        latest = observations[0]
        prev = observations[1] if len(observations) > 1 else None

        def _parse_val(obs) -> float | None:
            try:
                return float(obs["value"])
            except (TypeError, ValueError):
                return None

        val = _parse_val(latest)
        prev_val = _parse_val(prev) if prev else None
        pct_change = None
        if val is not None and prev_val and prev_val != 0:
            pct_change = round((val - prev_val) / abs(prev_val) * 100, 4)

        return {
            "date": latest.get("date"),
            "value": val,
            "prev_value": prev_val,
            "pct_change": pct_change,
        }
    except Exception as exc:
        logger.debug("FRED series %s fetch failed: %s", series_id, exc)
        return None


async def _run_macro_sync() -> int:
    api_key = settings.fred_api_key
    if not api_key:
        logger.info("fetch_macro_data: FRED_API_KEY not set — skipping")
        return 0

    now = datetime.now(timezone.utc)
    inserted = 0

    async with celery_session() as session:
        from sqlalchemy import select
        for series_id, (series_name, theme_slugs) in _SERIES.items():
            data = await asyncio.to_thread(_fetch_series_sync, series_id, api_key)
            if not data or data["value"] is None:
                continue

            obs_dt = None
            if data["date"]:
                try:
                    obs_dt = datetime.strptime(data["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    obs_dt = now

            exists = (await session.execute(
                select(MacroSignal.id)
                .where(MacroSignal.series_id == series_id)
                .where(MacroSignal.observation_date == obs_dt)
            )).scalar_one_or_none()
            if exists:
                continue

            session.add(MacroSignal(
                id=new_uuid(),
                series_id=series_id,
                series_name=series_name,
                observation_date=obs_dt or now,
                value=data["value"],
                prev_value=data["prev_value"],
                pct_change=data["pct_change"],
                theme_relevance=theme_slugs,
                created_at=now,
            ))
            inserted += 1

        await session.commit()
    return inserted


@celery.task(name="app.workers.macro_data.fetch_macro_data")
def fetch_macro_data():
    logger.info("fetch_macro_data: starting")
    count = asyncio.run(_run_macro_sync())
    logger.info("fetch_macro_data: inserted/updated %d rows", count)
