"""
Congressional trades collector.

Sources:
  - HouseStockWatcher: https://housestockwatcher.com/api
  - SenatStockWatcher:  https://senatestockwatcher.com/api

Both return public disclosure filings from the STOCK Act.
45-day disclosure lag is a legal requirement — treat as corroboration, not lead signal.

Runs daily via Celery Beat.
"""
import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.celery_app import celery
from app.config import settings
from app.database import celery_session
from app.models.base import new_uuid
from app.models.insider import InsiderFiling, TransactionType

logger = logging.getLogger(__name__)

# Primary sources (HouseStockWatcher / SenatStockWatcher)
_HOUSE_URL  = "https://housestockwatcher.com/api"
_SENATE_URL = "https://senatestockwatcher.com/api"

# Fallback — Capitol Trades public API (no key required)
_CAPITOL_TRADES_URL = "https://api.capitoltrades.com/trades?pageSize=100&page=1"

# Amount range strings from the disclosure forms → midpoint USD
_AMOUNT_MAP = {
    "$1,001 - $15,000":      8_000,
    "$15,001 - $50,000":    32_500,
    "$50,001 - $100,000":   75_000,
    "$100,001 - $250,000": 175_000,
    "$250,001 - $500,000": 375_000,
    "$500,001 - $1,000,000": 750_000,
    "Over $1,000,000":    1_250_000,
    "Over $5,000,000":    6_000_000,
}


def _parse_amount(raw: str) -> float | None:
    if not raw:
        return None
    for k, v in _AMOUNT_MAP.items():
        if k.lower() in raw.lower():
            return float(v)
    return None


def _parse_date(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%B %d, %Y"):
        try:
            return datetime.strptime(raw[:20], fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return datetime.now(timezone.utc)


async def _fetch_json(url: str) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers={"User-Agent": settings.edgar_user_agent})
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("Congress API fetch failed (%s): %s", url, exc)
        return []


async def _persist_trades(trades: list[dict], chamber: str) -> tuple[int, int]:
    inserted = skipped = 0

    async with celery_session() as session:
        for trade in trades:
            ticker = (trade.get("ticker") or "").strip().upper()
            if not ticker or ticker in ("--", "N/A", ""):
                skipped += 1
                continue

            # Only buys — congress sells are less signal
            tx_raw = (trade.get("type") or trade.get("transaction_type") or "").lower()
            if "purchase" in tx_raw or "buy" in tx_raw:
                tx_type = TransactionType.BUY
            elif "sale" in tx_raw or "sell" in tx_raw:
                tx_type = TransactionType.SELL
            else:
                skipped += 1
                continue

            # Use disclosure_date + ticker + representative as dedup key
            rep = trade.get("representative") or trade.get("senator") or "Unknown"
            disc_date_raw = trade.get("disclosure_date") or trade.get("filed_at") or ""
            tx_date_raw   = trade.get("transaction_date") or disc_date_raw

            # Simple dedup: check same ticker + representative + tx_date already stored
            disc_dt = _parse_date(disc_date_raw)
            tx_dt   = _parse_date(tx_date_raw)

            exists = (await session.execute(
                select(InsiderFiling.id)
                .where(InsiderFiling.symbol == ticker)
                .where(InsiderFiling.insider_name == rep)
                .where(InsiderFiling.filing_date == disc_dt)
                .where(InsiderFiling.is_congress == True)
            )).scalar_one_or_none()

            if exists:
                skipped += 1
                continue

            amount_raw = trade.get("amount") or trade.get("amount_range") or ""
            total_value = _parse_amount(amount_raw)

            session.add(InsiderFiling(
                id=new_uuid(),
                symbol=ticker,
                issuer_name=trade.get("asset_description") or ticker,
                insider_name=rep,
                insider_title=chamber,
                transaction_type=tx_type,
                shares=None,
                price_per_share=None,
                total_value=total_value,
                is_open_market=True,
                is_congress=True,
                filing_date=disc_dt,
                transaction_date=tx_dt,
                sec_accession_number=None,
                sec_filing_url=trade.get("ptr_link") or None,
                signal_score=None,
            ))
            inserted += 1

        await session.commit()

    return inserted, skipped


async def _fetch_capitol_trades() -> list[dict]:
    """
    Fallback: Capitol Trades public API.
    Maps their schema to our normalised trade format.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                _CAPITOL_TRADES_URL,
                headers={"User-Agent": settings.edgar_user_agent},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("Capitol Trades fallback failed: %s", exc)
        return []

    trades = data.get("data") or data if isinstance(data, list) else []
    normalised = []
    for t in trades:
        normalised.append({
            "ticker":          (t.get("ticker") or t.get("instrument", {}).get("symbol") or "").upper(),
            "type":            t.get("type") or t.get("action") or "",
            "amount":          t.get("amount") or t.get("amount_range") or "",
            "representative":  t.get("politician", {}).get("name") if isinstance(t.get("politician"), dict)
                               else t.get("politician") or t.get("politician_name") or "Unknown",
            "disclosure_date": t.get("published_at") or t.get("filed_at") or t.get("disclosure_date") or "",
            "transaction_date": t.get("trade_date") or t.get("transaction_date") or "",
            "asset_description": t.get("asset") or t.get("description") or "",
        })
    return normalised


async def _run():
    house_data  = await _fetch_json(_HOUSE_URL)
    senate_data = await _fetch_json(_SENATE_URL)

    # If primary sources fail, try Capitol Trades fallback
    if not house_data and not senate_data:
        logger.info("Congress primary sources unavailable — trying Capitol Trades fallback")
        fallback = await _fetch_capitol_trades()
        if fallback:
            logger.info("Congress fallback: %d trades from Capitol Trades", len(fallback))
            f_in, f_sk = await _persist_trades(fallback, "Congress")
            logger.info("Congress fallback: %d inserted, %d skipped", f_in, f_sk)
        else:
            logger.warning("Congress: all sources unavailable — no data collected this run")
        return

    logger.info("Congress collector: %d house, %d senate records", len(house_data), len(senate_data))
    h_in, h_sk = await _persist_trades(house_data, "House")
    s_in, s_sk = await _persist_trades(senate_data, "Senate")
    logger.info(
        "Congress: house %d inserted/%d skipped | senate %d inserted/%d skipped",
        h_in, h_sk, s_in, s_sk,
    )


@celery.task(name="app.workers.congress_data.fetch_congress_trades")
def fetch_congress_trades():
    logger.info("fetch_congress_trades: starting")
    asyncio.run(_run())
