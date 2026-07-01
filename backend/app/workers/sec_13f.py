"""
SEC EDGAR 13F institutional holdings collector.

Queries the EDGAR full-text search for recent 13F-HR filings on theme tickers.
Tracks new positions (is_new_position=True) for the current quarter.
A theme with 2+ new institutional positions earns a +5 scoring bonus.
Runs quarterly via Celery Beat.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

from app.celery_app import celery
from app.config import settings
from app.database import celery_session
from app.models.base import new_uuid
from app.models.theme import InstitutionalHolding
from app.theme_config import THEME_CONFIG

logger = logging.getLogger(__name__)

_EFTS_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={start}&enddt={end}&forms=13F-HR"
_SLEEP = 0.15


def _current_quarter() -> str:
    now = datetime.now(timezone.utc)
    q = (now.month - 1) // 3 + 1
    return f"{now.year}Q{q}"


def _fetch_13f_sync(ticker: str, days: int, user_agent: str) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    url = _EFTS_URL.format(
        ticker=ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
    )
    try:
        resp = httpx.get(url, headers={"User-Agent": user_agent}, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        results = []
        for hit in hits[:5]:
            src = hit.get("_source", {})
            cik = str(src.get("file_num", "") or "").zfill(10)
            filed = src.get("file_date", "")
            entity = src.get("entity_name", "")
            if cik and filed:
                results.append({"institution": entity, "institution_cik": cik, "filed_date": filed})
        return results
    except Exception as exc:
        logger.debug("EDGAR 13F search failed for %s: %s", ticker, exc)
        return []


async def _run_13f_sync(days: int = 100) -> int:
    user_agent = settings.edgar_user_agent
    all_symbols = list({t["symbol"] for theme in THEME_CONFIG for t in theme["tickers"]})
    quarter = _current_quarter()
    now = datetime.now(timezone.utc)
    inserted = 0

    async with celery_session() as session:
        from sqlalchemy import select
        for symbol in all_symbols:
            filings = await asyncio.to_thread(_fetch_13f_sync, symbol, days, user_agent)
            time.sleep(_SLEEP)
            for f in filings:
                exists = (await session.execute(
                    select(InstitutionalHolding.id)
                    .where(InstitutionalHolding.ticker == symbol)
                    .where(InstitutionalHolding.institution_cik == f["institution_cik"])
                    .where(InstitutionalHolding.quarter == quarter)
                )).scalar_one_or_none()
                if exists:
                    continue

                session.add(InstitutionalHolding(
                    id=new_uuid(),
                    ticker=symbol,
                    institution=f["institution"],
                    institution_cik=f["institution_cik"],
                    is_new_position=True,
                    quarter=quarter,
                    created_at=now,
                ))
                inserted += 1

        await session.commit()
    return inserted


@celery.task(name="app.workers.sec_13f.fetch_institutional_holdings")
def fetch_institutional_holdings():
    logger.info("fetch_institutional_holdings: starting")
    count = asyncio.run(_run_13f_sync())
    logger.info("fetch_institutional_holdings: inserted %d rows", count)
