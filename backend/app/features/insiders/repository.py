from datetime import datetime, timedelta, timezone

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insider import InsiderFiling, TransactionType


async def get_top_insider_buys(db: AsyncSession, limit: int = 5, days: int = 30) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stmt = (
        select(InsiderFiling)
        .where(
            InsiderFiling.transaction_type == TransactionType.BUY,
            InsiderFiling.is_open_market == True,
            InsiderFiling.filing_date >= cutoff,
            InsiderFiling.total_value.isnot(None),
        )
        .order_by(desc(InsiderFiling.signal_score), desc(InsiderFiling.total_value))
        .limit(limit)
    )
    result = await db.execute(stmt)
    filings = result.scalars().all()

    return [
        {
            "symbol": f.symbol,
            "issuer_name": f.issuer_name,
            "insider_name": f.insider_name,
            "insider_title": f.insider_title,
            "transaction_type": f.transaction_type.value,
            "total_value": f.total_value,
            "signal_score": f.signal_score,
            "transaction_date": f.transaction_date.isoformat() if f.transaction_date else None,
            "sec_filing_url": f.sec_filing_url,
        }
        for f in filings
    ]
