"""
SEC EDGAR 8-K M&A and AI deal signal collector.

Scans 8-K filings from the last 7 days for theme company tickers.
Flags filings mentioning acquisition, merger, partnership, or AI-related keywords.
These feed the ai_ecosystem_count + ai_ecosystem_usd scoring inputs.
Runs weekly via Celery Beat.
"""
import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import httpx

from app.celery_app import celery
from app.config import settings
from app.database import celery_session
from app.models.base import new_uuid
from app.models.theme import EightKSignal
from app.theme_config import THEME_CONFIG
from app.theme_keywords import THEME_INDUSTRY_KEYWORDS

logger = logging.getLogger(__name__)

_EFTS_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={start}&enddt={end}&forms=8-K"
_FILING_INDEX = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_dashes}/{acc_nodash}-index.json"
_SLEEP = 0.15

_AI_KEYWORDS = {"artificial intelligence", "machine learning", "large language model", "llm", "generative ai", "ai deal", "ai partnership"}
_MA_KEYWORDS = {"acquisition", "merger", "purchase agreement", "definitive agreement", "signed agreement"}
_DEAL_AMOUNT_RE = re.compile(r'\$\s*([\d,]+(?:\.\d+)?)\s*(billion|million)', re.IGNORECASE)


def _classify_8k(text: str) -> tuple[str | None, float | None]:
    """Return (signal_type, deal_amount) from 8-K text snippet."""
    lower = text.lower()
    is_ai = any(kw in lower for kw in _AI_KEYWORDS)
    is_ma = any(kw in lower for kw in _MA_KEYWORDS)

    if not (is_ai or is_ma):
        return None, None

    signal_type = "ai_deal" if is_ai else "ma"
    deal_amount = None
    m = _DEAL_AMOUNT_RE.search(text)
    if m:
        num = float(m.group(1).replace(",", ""))
        mult = 1_000_000_000 if m.group(2).lower() == "billion" else 1_000_000
        deal_amount = num * mult

    return signal_type, deal_amount


def _fetch_8ks_sync(ticker: str, days: int, user_agent: str) -> list[dict]:
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
        for hit in hits[:8]:
            src = hit.get("_source", {})
            accession = src.get("accession_no", "")
            filed = src.get("file_date", "")
            entity = src.get("entity_name", "")
            description = src.get("description", "") or src.get("period_of_report", "")
            if not (accession and filed):
                continue
            signal_type, deal_amount = _classify_8k(description)
            if signal_type:
                results.append({
                    "accession_number": accession,
                    "company_name": entity,
                    "filed_date": filed,
                    "signal_type": signal_type,
                    "deal_amount": deal_amount,
                    "description": description[:500],
                })
        return results
    except Exception as exc:
        logger.debug("EDGAR 8-K search failed for %s: %s", ticker, exc)
        return []


def _themes_for_ticker(ticker: str) -> list[str]:
    slugs = []
    for theme in THEME_CONFIG:
        if any(t["symbol"] == ticker for t in theme["tickers"]):
            slugs.append(theme["slug"])
    return slugs


async def _run_8k_sync(days: int = 7) -> int:
    user_agent = settings.edgar_user_agent
    all_symbols = list({t["symbol"] for theme in THEME_CONFIG for t in theme["tickers"]})
    now = datetime.now(timezone.utc)
    inserted = 0

    async with celery_session() as session:
        from sqlalchemy import select
        for symbol in all_symbols:
            filings = await asyncio.to_thread(_fetch_8ks_sync, symbol, days, user_agent)
            time.sleep(_SLEEP)
            for f in filings:
                exists = (await session.execute(
                    select(EightKSignal.id)
                    .where(EightKSignal.accession_number == f["accession_number"])
                )).scalar_one_or_none()
                if exists:
                    continue

                try:
                    filed_dt = datetime.strptime(f["filed_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

                session.add(EightKSignal(
                    id=new_uuid(),
                    accession_number=f["accession_number"],
                    ticker=symbol,
                    company_name=f["company_name"],
                    filed_date=filed_dt,
                    signal_type=f["signal_type"],
                    deal_amount=f["deal_amount"],
                    description=f["description"],
                    theme_slugs=_themes_for_ticker(symbol),
                    created_at=now,
                ))
                inserted += 1

        await session.commit()
    return inserted


@celery.task(name="app.workers.sec_8k.fetch_8k_signals")
def fetch_8k_signals():
    logger.info("fetch_8k_signals: starting")
    count = asyncio.run(_run_8k_sync())
    logger.info("fetch_8k_signals: inserted %d rows", count)
