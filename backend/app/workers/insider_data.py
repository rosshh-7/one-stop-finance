"""
EDGAR Form 4 insider data collector.

Runs every 15 minutes via Celery Beat.
Fetches open-market insider purchases (P) and sales (S) for the last 7 days,
deduplicates by sec_accession_number, and stores in insider_filings.
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct

from app.celery_app import celery
from app.config import settings
from app.database import celery_session
from app.models.base import new_uuid
from app.models.insider import InsiderFiling, TransactionType
from app.models.theme import ThemeTicker
from app.integrations.sec_edgar import fetch_form4_filings
from app.theme_config import TICKER_THEMES

logger = logging.getLogger(__name__)

_LOOKBACK_DAYS = 7

# Title patterns that mark auto/plan-driven activity, not conviction trades.
# A Form 4 with code P/S can still slip through if it's a trust/plan distribution
# or an automatic dividend reinvestment from a custodian filing on the insider's behalf.
_NOISE_TITLE_PATTERNS = ("plan", "401k", "401(k)", "drip", "automatic", "trust", "custodian")


def _is_noise(rec: dict) -> bool:
    title = (rec.get("insider_title") or "").lower()
    if any(p in title for p in _NOISE_TITLE_PATTERNS):
        return True
    if (rec.get("total_value") or 0) <= 0:
        return True
    return False


def _map_transaction_type(raw: str) -> TransactionType:
    return TransactionType.BUY if raw == "buy" else TransactionType.SELL


async def _load_theme_symbols() -> set[str]:
    """Union of config-defined symbols and any added dynamically (FMP/ETF)."""
    async with celery_session() as session:
        rows = (await session.execute(
            select(distinct(ThemeTicker.symbol)).where(ThemeTicker.is_active == True)
        )).all()
        dynamic = {s for (s,) in rows if s}
    return set(TICKER_THEMES.keys()) | dynamic


async def _persist_filings(records: list[dict], theme_symbols: set[str]) -> tuple[int, int]:
    """Insert new filings, skip duplicates. Returns (inserted, skipped)."""
    inserted = skipped = 0

    async with celery_session() as session:
        for rec in records:
            # Skip tickers not in any theme — we only care about theme tickers
            ticker = (rec.get("ticker") or "").upper()
            if ticker and ticker not in theme_symbols:
                skipped += 1
                continue

            # Noise filter: drop DRIP/401k/plan/custodial filings and $0 records
            if _is_noise(rec):
                skipped += 1
                continue

            # Deduplicate by accession number
            acc = rec.get("sec_accession_number")
            if acc:
                exists = (await session.execute(
                    select(InsiderFiling.id)
                    .where(InsiderFiling.sec_accession_number == acc)
                )).scalar_one_or_none()
                if exists:
                    skipped += 1
                    continue

            tx_type = _map_transaction_type(rec.get("transaction_type", "buy"))
            tx_date_str = rec.get("transaction_date") or rec.get("filing_date") or ""
            filed_str   = rec.get("filing_date") or ""

            def _parse_dt(s: str):
                try:
                    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
                except Exception:
                    return datetime.now(timezone.utc)

            session.add(InsiderFiling(
                id=new_uuid(),
                symbol=ticker or rec.get("company", "")[:10],
                issuer_name=rec.get("company"),
                insider_name=rec.get("insider_name") or "Unknown",
                insider_title=rec.get("insider_title") or None,
                transaction_type=tx_type,
                shares=rec.get("shares"),
                price_per_share=rec.get("price_per_share"),
                total_value=rec.get("total_value"),
                is_open_market=rec.get("is_open_market", True),
                is_congress=rec.get("is_congress", False),
                filing_date=_parse_dt(filed_str),
                transaction_date=_parse_dt(tx_date_str) if tx_date_str else None,
                sec_accession_number=acc,
                sec_filing_url=rec.get("sec_filing_url"),
                signal_score=None,
            ))
            inserted += 1

        await session.commit()

    return inserted, skipped


@celery.task(name="app.workers.insider_data.poll_sec_edgar")
def poll_sec_edgar():
    logger.info("poll_sec_edgar: fetching Form 4 filings (last %d days)", _LOOKBACK_DAYS)

    user_agent = settings.edgar_user_agent
    if not user_agent:
        logger.error("poll_sec_edgar: EDGAR_USER_AGENT not set — skipping")
        return

    # Union of config-defined tickers and any added dynamically (FMP/ETF)
    theme_tickers = asyncio.run(_load_theme_symbols())
    logger.info("poll_sec_edgar: filtering for %d theme tickers", len(theme_tickers))

    raw_records = fetch_form4_filings(
        user_agent=user_agent,
        days=_LOOKBACK_DAYS,
        ticker_filter=theme_tickers,
    )
    if not raw_records:
        logger.info("poll_sec_edgar: no records returned from EDGAR")
        return

    logger.info("poll_sec_edgar: %d raw transactions fetched", len(raw_records))

    inserted, skipped = asyncio.run(_persist_filings(raw_records, theme_tickers))
    logger.info("poll_sec_edgar: %d inserted, %d skipped (dup/off-theme)", inserted, skipped)
