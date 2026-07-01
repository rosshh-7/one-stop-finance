"""
USPTO PatentsView patent signal collector.

Queries PatentsView for recently granted patents by theme companies.
Patent velocity (new grants per quarter) feeds a scoring bonus.
Runs quarterly via Celery Beat.

API docs: https://patentsview.org/apis/purpose
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.celery_app import celery
from app.database import celery_session
from app.models.base import new_uuid
from app.models.theme import PatentSignal
from app.theme_config import THEME_CONFIG

logger = logging.getLogger(__name__)

_PATENTS_API = "https://search.patentsview.org/api/v1/patent/"


def _ticker_to_company(ticker: str) -> str | None:
    for theme in THEME_CONFIG:
        for t in theme["tickers"]:
            if t["symbol"] == ticker:
                return t.get("company_name")
    return None


def _themes_for_ticker(ticker: str) -> list[str]:
    return [
        theme["slug"] for theme in THEME_CONFIG
        if any(t["symbol"] == ticker for t in theme["tickers"])
    ]


def _fetch_patents_sync(company_name: str, days: int) -> list[dict]:
    """Query PatentsView for recent grants by company name."""
    if not company_name:
        return []
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    try:
        resp = httpx.post(
            _PATENTS_API,
            json={
                "q": {"_and": [
                    {"_text_phrase": {"assignee.organization": company_name}},
                    {"_gte": {"patent_date": start.strftime("%Y-%m-%d")}},
                ]},
                "f": ["patent_id", "patent_title", "patent_date"],
                "s": [{"patent_date": "desc"}],
                "o": {"per_page": 25},
            },
            timeout=20,
        )
        resp.raise_for_status()
        patents = resp.json().get("patents") or []
        return [
            {
                "patent_id": p.get("patent_id", ""),
                "title": (p.get("patent_title") or "")[:500],
                "grant_date": p.get("patent_date"),
            }
            for p in patents if p.get("patent_id")
        ]
    except Exception as exc:
        logger.debug("PatentsView failed for '%s': %s", company_name, exc)
        return []


async def _run_patents_sync(days: int = 100) -> int:
    now = datetime.now(timezone.utc)
    all_symbols = list({t["symbol"] for theme in THEME_CONFIG for t in theme["tickers"]})
    inserted = 0

    async with celery_session() as session:
        from sqlalchemy import select
        processed_companies: set[str] = set()
        for symbol in all_symbols:
            company = _ticker_to_company(symbol)
            if not company or company in processed_companies:
                continue
            processed_companies.add(company)

            patents = await asyncio.to_thread(_fetch_patents_sync, company, days)
            for p in patents:
                if not p["patent_id"]:
                    continue
                exists = (await session.execute(
                    select(PatentSignal.id).where(PatentSignal.patent_id == p["patent_id"])
                )).scalar_one_or_none()
                if exists:
                    continue

                grant_dt = None
                if p["grant_date"]:
                    try:
                        grant_dt = datetime.strptime(p["grant_date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass

                slugs = _themes_for_ticker(symbol)
                session.add(PatentSignal(
                    id=new_uuid(),
                    patent_id=p["patent_id"],
                    ticker=symbol,
                    company_name=company,
                    theme_slug=slugs[0] if slugs else None,
                    title=p["title"],
                    grant_date=grant_dt,
                    created_at=now,
                ))
                inserted += 1

        await session.commit()
    return inserted


@celery.task(name="app.workers.patents.fetch_patent_signals")
def fetch_patent_signals():
    logger.info("fetch_patent_signals: starting")
    count = asyncio.run(_run_patents_sync())
    logger.info("fetch_patent_signals: inserted %d rows", count)
