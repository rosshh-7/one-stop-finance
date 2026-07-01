"""
SEC EDGAR Form D VC raise collector.

Scans recent Form D filings (venture capital raises) for AI/tech keyword matches.
Form D signals indicate early-stage funding flowing into a theme, feeding the
ai_ecosystem_count and ai_ecosystem_usd scoring inputs.
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
from app.models.theme import FormDSignal
from app.theme_config import THEME_CONFIG
from app.theme_keywords import THEME_INDUSTRY_KEYWORDS

logger = logging.getLogger(__name__)

_EFTS_URL = "https://efts.sec.gov/LATEST/search-index?q={query}&dateRange=custom&startdt={start}&enddt={end}&forms=D"
_SLEEP = 0.15

_AI_KEYWORDS = ["artificial intelligence", "machine learning", "generative ai", "llm", "foundation model"]

_AMOUNT_RE = re.compile(r'totalOfferingAmount["\s:>]+(\d[\d,.]+)', re.IGNORECASE)


def _is_ai_related(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _AI_KEYWORDS)


def _extract_amount(text: str) -> float | None:
    m = _AMOUNT_RE.search(text)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return None


def _theme_slugs_for_text(text: str) -> list[str]:
    lower = text.lower()
    slugs = []
    for slug, keywords in THEME_INDUSTRY_KEYWORDS.items():
        if any(kw.lower() in lower for kw in keywords[:5]):
            slugs.append(slug)
    return slugs[:3]


def _fetch_formd_sync(query_term: str, days: int, user_agent: str) -> list[dict]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    url = _EFTS_URL.format(
        query=query_term.replace(" ", "+"),
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
    )
    try:
        resp = httpx.get(url, headers={"User-Agent": user_agent}, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
        results = []
        for hit in hits[:20]:
            src = hit.get("_source", {})
            accession = src.get("accession_no", "")
            filed = src.get("file_date", "")
            entity = src.get("entity_name", "")
            description = src.get("description", "") or ""
            if accession and filed:
                results.append({
                    "accession_number": accession,
                    "company_name": entity,
                    "filed_date": filed,
                    "description": description,
                })
        return results
    except Exception as exc:
        logger.debug("EDGAR Form D search failed for '%s': %s", query_term, exc)
        return []


async def _run_formd_sync(days: int = 7) -> int:
    user_agent = settings.edgar_user_agent
    now = datetime.now(timezone.utc)
    inserted = 0

    async with celery_session() as session:
        from sqlalchemy import select
        for keyword in _AI_KEYWORDS:
            filings = await asyncio.to_thread(_fetch_formd_sync, keyword, days, user_agent)
            time.sleep(_SLEEP)
            for f in filings:
                exists = (await session.execute(
                    select(FormDSignal.id)
                    .where(FormDSignal.accession_number == f["accession_number"])
                )).scalar_one_or_none()
                if exists:
                    continue

                try:
                    filed_dt = datetime.strptime(f["filed_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

                desc = f["description"]
                session.add(FormDSignal(
                    id=new_uuid(),
                    accession_number=f["accession_number"],
                    company_name=f["company_name"],
                    filed_date=filed_dt,
                    amount_raised=_extract_amount(desc),
                    is_ai_related=_is_ai_related(desc),
                    theme_slugs=_theme_slugs_for_text(f["company_name"] + " " + desc),
                    created_at=now,
                ))
                inserted += 1

        await session.commit()
    return inserted


@celery.task(name="app.workers.sec_formd.fetch_formd_signals")
def fetch_formd_signals():
    logger.info("fetch_formd_signals: starting")
    count = asyncio.run(_run_formd_sync())
    logger.info("fetch_formd_signals: inserted %d rows", count)
