import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.celery_app import celery
from app.database import async_session_factory
from app.integrations.sec_edgar import fetch_recent_form4_buys
from app.models.insider import InsiderFiling, TransactionType

logger = logging.getLogger(__name__)


async def _ingest_filings() -> int:
    filings = await fetch_recent_form4_buys(limit=40)
    if not filings:
        logger.warning("SEC EDGAR returned no filings")
        return 0

    inserted = 0
    async with async_session_factory() as session:
        for f in filings:
            accession = f.get("sec_accession_number")
            if accession:
                existing = await session.execute(
                    select(InsiderFiling).where(InsiderFiling.sec_accession_number == accession)
                )
                if existing.scalar_one_or_none():
                    continue

            txn_type_raw = f.get("transaction_type", "buy")
            try:
                txn_type = TransactionType(txn_type_raw)
            except ValueError:
                txn_type = TransactionType.BUY

            filing_date_raw = f.get("filing_date")
            filing_date = (
                datetime.fromisoformat(filing_date_raw)
                if filing_date_raw
                else datetime.now(timezone.utc)
            )

            txn_date_raw = f.get("transaction_date")
            txn_date = datetime.fromisoformat(txn_date_raw) if txn_date_raw else None

            record = InsiderFiling(
                symbol=f["symbol"],
                issuer_name=f.get("issuer_name"),
                insider_name=f["insider_name"],
                insider_title=f.get("insider_title"),
                transaction_type=txn_type,
                shares=f.get("shares"),
                price_per_share=f.get("price_per_share"),
                total_value=f.get("total_value"),
                is_open_market=f.get("is_open_market", True),
                is_congress=f.get("is_congress", False),
                filing_date=filing_date,
                transaction_date=txn_date,
                signal_score=f.get("signal_score"),
                sec_filing_url=f.get("sec_filing_url"),
                sec_accession_number=accession,
            )
            session.add(record)
            try:
                await session.flush()
                inserted += 1
            except IntegrityError:
                await session.rollback()
                continue

        await session.commit()

    logger.info("Inserted %d new insider filings", inserted)
    return inserted


@celery.task(name="app.workers.insider_data.poll_sec_edgar")
def poll_sec_edgar():
    inserted = asyncio.get_event_loop().run_until_complete(_ingest_filings())
    return {"inserted": inserted}
