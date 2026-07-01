"""
NIH Reporter grant collector — Biotech & Genomics theme only.

Queries the NIH Reporter API for recent grants matching biotech/genomics keywords.
Grant count feeds a scoring bonus for the biotech-genomics theme.
Runs quarterly via Celery Beat.

API docs: https://api.reporter.nih.gov
"""
import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.celery_app import celery
from app.database import celery_session
from app.models.base import new_uuid
from app.models.theme import NihGrant

logger = logging.getLogger(__name__)

_NIH_API = "https://api.reporter.nih.gov/v2/projects/search"

_BIOTECH_KEYWORDS = [
    "CRISPR", "gene editing", "gene therapy", "genomics", "RNA therapy",
    "cell therapy", "cancer immunotherapy", "synthetic biology", "mRNA",
    "base editing", "prime editing",
]

_THEME_SLUGS = ["biotech-genomics"]


def _fetch_nih_sync(keyword: str, fiscal_year: int) -> list[dict]:
    try:
        resp = httpx.post(
            _NIH_API,
            json={
                "criteria": {
                    "advanced_text_search": {"operator": "and", "search_field": "terms", "search_text": keyword},
                    "fiscal_years": [fiscal_year],
                },
                "limit": 50,
                "offset": 0,
            },
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        grants = []
        for r in results:
            grants.append({
                "nih_project_id": str(r.get("appl_id", "")),
                "project_title": (r.get("project_title") or "")[:500],
                "fiscal_year": r.get("fiscal_year"),
                "total_cost": float(r.get("award_amount") or 0) or None,
                "keywords": [keyword],
            })
        return grants
    except Exception as exc:
        logger.debug("NIH Reporter API failed for '%s': %s", keyword, exc)
        return []


async def _run_nih_sync() -> int:
    now = datetime.now(timezone.utc)
    fiscal_year = now.year
    inserted = 0

    async with celery_session() as session:
        from sqlalchemy import select
        for keyword in _BIOTECH_KEYWORDS:
            grants = await asyncio.to_thread(_fetch_nih_sync, keyword, fiscal_year)
            for g in grants:
                if not g["nih_project_id"]:
                    continue
                exists = (await session.execute(
                    select(NihGrant.id).where(NihGrant.nih_project_id == g["nih_project_id"])
                )).scalar_one_or_none()
                if exists:
                    continue
                session.add(NihGrant(
                    id=new_uuid(),
                    nih_project_id=g["nih_project_id"],
                    project_title=g["project_title"],
                    fiscal_year=g["fiscal_year"],
                    total_cost=g["total_cost"],
                    keywords=g["keywords"],
                    theme_slug="biotech-genomics",
                    created_at=now,
                ))
                inserted += 1

        await session.commit()
    return inserted


@celery.task(name="app.workers.nih_grants.fetch_nih_grants")
def fetch_nih_grants():
    logger.info("fetch_nih_grants: starting")
    count = asyncio.run(_run_nih_sync())
    logger.info("fetch_nih_grants: inserted %d rows", count)
