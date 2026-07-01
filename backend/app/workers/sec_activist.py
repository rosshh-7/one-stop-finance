"""
SEC EDGAR 13D/G activist stake collector.

Scans EDGAR full-text search for 13D and 13G filings on theme tickers.
New activist stakes (is_new=True) feed a +12 bonus in the scoring engine.
Runs daily via Celery Beat.
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
from app.models.theme import ActivistStake
from app.theme_config import THEME_CONFIG

logger = logging.getLogger(__name__)

_EFTS_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={start}&enddt={end}&forms={form}"
_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
_SLEEP = 0.15


def _fetch_filings_sync(ticker: str, form: str, days: int, user_agent: str) -> list[dict]:
    """Use EDGAR full-text search to find 13D/G filings mentioning a ticker."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    url = _EFTS_URL.format(
        ticker=ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        form=form,
    )
    try:
        resp = httpx.get(url, headers={"User-Agent": user_agent}, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        results = []
        for hit in hits[:10]:  # cap per ticker
            src = hit.get("_source", {})
            accession = src.get("accession_no", "")
            filed = src.get("file_date", "")
            entity = src.get("entity_name", "")
            cik = str(src.get("file_num", "") or "").zfill(10)
            if accession and filed:
                results.append({
                    "accession_number": accession,
                    "filer_name": entity,
                    "filer_cik": cik,
                    "filed_date": filed,
                })
        return results
    except Exception as exc:
        logger.debug("EDGAR EFTS 13D/G search failed for %s/%s: %s", ticker, form, exc)
        return []


async def _run_activist_sync(days: int = 7) -> int:
    user_agent = settings.edgar_user_agent
    all_symbols = list({t["symbol"] for theme in THEME_CONFIG for t in theme["tickers"]})
    now = datetime.now(timezone.utc)
    inserted = 0

    async with celery_session() as session:
        from sqlalchemy import select
        for symbol in all_symbols:
            for form in ("13D", "13G"):
                filings = await asyncio.to_thread(
                    _fetch_filings_sync, symbol, form, days, user_agent
                )
                time.sleep(_SLEEP)
                for f in filings:
                    try:
                        filed_dt = datetime.strptime(f["filed_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue

                    exists = (await session.execute(
                        select(ActivistStake.id)
                        .where(ActivistStake.ticker == symbol)
                        .where(ActivistStake.filer_cik == f["filer_cik"])
                        .where(ActivistStake.filed_date == filed_dt)
                    )).scalar_one_or_none()
                    if exists:
                        continue

                    session.add(ActivistStake(
                        id=new_uuid(),
                        ticker=symbol,
                        filer_name=f["filer_name"],
                        filer_cik=f["filer_cik"],
                        filing_type=form,
                        filed_date=filed_dt,
                        is_new=True,
                        created_at=now,
                    ))
                    inserted += 1

        await session.commit()
    return inserted


@celery.task(name="app.workers.sec_activist.fetch_activist_stakes")
def fetch_activist_stakes():
    logger.info("fetch_activist_stakes: starting")
    count = asyncio.run(_run_activist_sync())
    logger.info("fetch_activist_stakes: inserted %d rows", count)
