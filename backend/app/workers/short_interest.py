"""
FINRA short interest collector.

Downloads FINRA's bi-monthly short interest flat files from their public FTP.
High short interest on a theme ticker combined with insider buying generates
a +8 scoring bonus ("short squeeze setup").
Runs every 14 days via Celery Beat.

FINRA releases files on the 1st and 15th of each month:
  https://www.finra.org/investors/learn-to-invest/advanced-investing/short-selling/finra-short-sale-volume-data
"""
import asyncio
import csv
import io
import logging
from datetime import datetime, timezone

import httpx

from app.celery_app import celery
from app.database import celery_session
from app.models.base import new_uuid
from app.models.theme import ShortInterest
from app.theme_config import THEME_CONFIG

logger = logging.getLogger(__name__)

_FINRA_URL = "https://cdn.finra.org/equity/regsho/monthly/CNMSshvol{yyyymm}.txt"
_CONSOLIDATION_URL = "https://cdn.finra.org/equity/regsho/monthly/CNMSshvol{yyyymm}.txt"


def _fetch_finra_sync(yyyymm: str) -> list[dict]:
    """Download FINRA short interest flat file for the given month."""
    url = _FINRA_URL.format(yyyymm=yyyymm)
    try:
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text), delimiter="|")
        rows = []
        for row in reader:
            symbol = (row.get("Symbol") or "").strip().upper()
            short_vol = row.get("ShortVolume") or row.get("ShortExemptVolume")
            total_vol = row.get("TotalVolume")
            date_str = row.get("Date") or ""
            if not symbol:
                continue
            rows.append({
                "ticker": symbol,
                "short_interest": int(short_vol) if short_vol and short_vol.isdigit() else None,
                "total_volume": int(total_vol) if total_vol and total_vol.isdigit() else None,
                "date": date_str,
            })
        return rows
    except Exception as exc:
        logger.debug("FINRA short interest download failed for %s: %s", yyyymm, exc)
        return []


def _short_ratio(short_interest: int | None, total_volume: int | None) -> float | None:
    if short_interest and total_volume and total_volume > 0:
        return round(short_interest / total_volume, 4)
    return None


async def _run_short_interest_sync() -> int:
    now = datetime.now(timezone.utc)
    yyyymm = now.strftime("%Y%m")

    theme_symbols = {t["symbol"] for theme in THEME_CONFIG for t in theme["tickers"]}
    rows = await asyncio.to_thread(_fetch_finra_sync, yyyymm)

    # Filter to theme tickers only
    theme_rows = [r for r in rows if r["ticker"] in theme_symbols]

    inserted = 0
    async with celery_session() as session:
        from sqlalchemy import select
        for row in theme_rows:
            date_str = row["date"]
            try:
                settlement_dt = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                settlement_dt = now

            exists = (await session.execute(
                select(ShortInterest.id)
                .where(ShortInterest.ticker == row["ticker"])
                .where(ShortInterest.settlement_date == settlement_dt)
            )).scalar_one_or_none()
            if exists:
                continue

            ratio = _short_ratio(row["short_interest"], row["total_volume"])
            session.add(ShortInterest(
                id=new_uuid(),
                ticker=row["ticker"],
                short_interest=row["short_interest"],
                short_ratio=ratio,
                settlement_date=settlement_dt,
                created_at=now,
            ))
            inserted += 1

        await session.commit()
    return inserted


@celery.task(name="app.workers.short_interest.fetch_short_interest")
def fetch_short_interest():
    logger.info("fetch_short_interest: starting")
    count = asyncio.run(_run_short_interest_sync())
    logger.info("fetch_short_interest: inserted %d rows", count)
