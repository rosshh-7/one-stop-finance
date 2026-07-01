"""
USASpending.gov government contracts collector.

Fetches federal contract awards and maps them to themes by keyword-matching
the description and recipient name against theme keywords.

Free API — no key required. Runs daily via Celery Beat.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from app.celery_app import celery
from app.config import settings
from app.database import celery_session
from app.models.base import new_uuid
from app.models.theme import Theme, GovContract

logger = logging.getLogger(__name__)

_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
_LOOKBACK_DAYS = 30

# Keywords that map award descriptions → theme slugs
_THEME_KEYWORDS: dict[str, list[str]] = {
    "defense-aerospace":  [
        "missile", "radar", "combat", "fighter", "destroyer", "submarine",
        "aircraft", "munition", "armament", "defense system", "military",
        "hypersonic", "drone", "unmanned aerial", "surveillance", "sonar",
    ],
    "space-satellite": [
        "satellite", "launch vehicle", "space launch", "spacecraft", "orbital",
        "earth observation", "gps", "low earth orbit", "cubesat", "space",
    ],
    "nuclear-energy": [
        "nuclear reactor", "uranium", "nuclear fuel", "naval reactor",
        "small modular reactor", "nuclear power", "radiological",
    ],
    "grid-power-infra": [
        "grid modernization", "power grid", "transmission line", "substation",
        "smart grid", "microgrid", "energy storage grid", "transformer",
    ],
    "cybersecurity": [
        "cybersecurity", "cyber defense", "zero trust", "endpoint security",
        "network security", "intrusion detection", "information security",
        "security operations center", "cyber threat",
    ],
    "ai-infrastructure": [
        "artificial intelligence", "machine learning", "deep learning",
        "large language model", "AI system", "autonomous system",
        "computer vision", "natural language processing",
    ],
    "biotech-genomics": [
        "biodefense", "biological threat", "mRNA vaccine", "genomic",
        "pathogen", "biosurveillance", "bioterrorism", "pandemic preparedness",
    ],
    "drone-autonomous": [
        "unmanned aerial vehicle", "uav", "drone", "uncrewed", "autonomous vehicle",
        "counter-drone", "ground robotics", "autonomous robot",
    ],
    "digital-defense-leo": [
        "low earth orbit", "leo satellite", "military satellite", "starshield",
        "protected tactical", "wideband", "milsatcom",
    ],
    "quantum-computing": [
        "quantum computing", "quantum communication", "post-quantum cryptography",
        "quantum sensing", "qubit",
    ],
}


def _match_theme(description: str, recipient: str) -> str | None:
    text = (description + " " + recipient).lower()
    for slug, keywords in _THEME_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return slug
    return None


async def _get_theme_id(session, slug: str) -> str | None:
    row = (await session.execute(
        select(Theme.id).where(Theme.slug == slug)
    )).scalar_one_or_none()
    return row


async def _run():
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    end   = now.strftime("%Y-%m-%d")

    payload = {
        "filters": {
            "time_period": [{"start_date": start, "end_date": end}],
            "award_type_codes": ["A", "B", "C", "D"],
        },
        "fields": [
            "Award ID", "Recipient Name", "Award Amount",
            "Awarding Agency", "Award Description", "Action Date",
        ],
        "sort": "Award Amount",
        "order": "desc",
        "limit": 100,
        "page": 1,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("USASpending fetch failed: %s", exc)
        return

    awards = data.get("results") or []
    logger.info("contracts_data: %d awards fetched from USASpending", len(awards))

    inserted = skipped = 0
    async with celery_session() as session:
        for award in awards:
            usaspending_id = award.get("Award ID") or ""
            recipient = award.get("Recipient Name") or ""
            description = award.get("Award Description") or ""
            amount = award.get("Award Amount") or 0
            agency = award.get("Awarding Agency") or ""
            action_date_raw = award.get("Action Date") or ""

            if not usaspending_id:
                skipped += 1
                continue

            # Deduplicate by usaspending_id
            exists = (await session.execute(
                select(GovContract.id).where(GovContract.usaspending_id == usaspending_id)
            )).scalar_one_or_none()
            if exists:
                skipped += 1
                continue

            # Match to a theme
            theme_slug = _match_theme(description, recipient)
            theme_id = await _get_theme_id(session, theme_slug) if theme_slug else None

            try:
                award_date = datetime.strptime(action_date_raw[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                award_date = now

            session.add(GovContract(
                id=new_uuid(),
                theme_id=theme_id,
                recipient_name=recipient[:255] if recipient else None,
                symbol=None,
                award_amount=float(amount),
                agency_name=agency[:255] if agency else None,
                description=description[:1000] if description else None,
                award_date=award_date,
                usaspending_id=usaspending_id[:100],
                created_at=now,
            ))
            inserted += 1

        await session.commit()

    logger.info("contracts_data: %d inserted, %d skipped", inserted, skipped)


@celery.task(name="app.workers.contracts_data.fetch_gov_contracts")
def fetch_gov_contracts():
    logger.info("fetch_gov_contracts: starting (last %d days)", _LOOKBACK_DAYS)
    asyncio.run(_run())
