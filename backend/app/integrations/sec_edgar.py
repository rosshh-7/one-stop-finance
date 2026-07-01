"""
SEC EDGAR Form 4 integration.

Strategy: query per-company rather than scanning all Form 4s.
  1. For each theme ticker, find the company in EDGAR.
  2. Fetch only that company's Form 4 filings for the date range.
  3. Parse for open-market P (purchase) and S (sale) transactions.

This is orders of magnitude faster than scanning all 8000+ daily Form 4s.
Respects SEC's 10 req/sec limit via 0.15s sleeps.
"""
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

_SLEEP = 0.15          # ~6 req/sec — under SEC's 10 req/sec limit
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
_FILING_BASE = "https://www.sec.gov/Archives/edgar/data"

_ticker_cik_cache: dict[str, str] = {}  # ticker → zero-padded CIK


def _get_ticker_cik_map() -> dict[str, str]:
    """Fetch EDGAR's ticker→CIK mapping (cached per process)."""
    global _ticker_cik_cache
    if _ticker_cik_cache:
        return _ticker_cik_cache

    try:
        resp = httpx.get(
            _TICKERS_URL,
            headers={"User-Agent": "OneStopFinance contact@onestopfinance.com"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        # Each entry: {"0": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"}}
        for entry in data.values():
            ticker = str(entry.get("ticker", "")).upper().strip()
            cik = str(entry.get("cik_str", "")).zfill(10)
            if ticker:
                _ticker_cik_cache[ticker] = cik
        logger.info("EDGAR: loaded %d ticker→CIK mappings", len(_ticker_cik_cache))
    except Exception as exc:
        logger.error("EDGAR ticker→CIK fetch failed: %s", exc)

    return _ticker_cik_cache


def _get_company_form4s(cik: str, days: int, user_agent: str) -> list[dict]:
    """
    Fetch recent Form 4 filing accession numbers for a company via EDGAR submissions API.
    Returns list of {accession_number, filing_date} dicts.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    url = f"{_SUBMISSIONS_BASE}/CIK{cik}.json"

    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": user_agent},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.debug("EDGAR submissions failed for CIK %s: %s", cik, exc)
        return []

    filings_data = data.get("filings", {}).get("recent", {})
    forms        = filings_data.get("form", [])
    dates        = filings_data.get("filingDate", [])
    accessions   = filings_data.get("accessionNumber", [])
    primary_docs = filings_data.get("primaryDocument", [])

    results = []
    for form, date, acc, doc in zip(forms, dates, accessions, primary_docs):
        if form == "4" and date >= cutoff:
            results.append({
                "accession_number": acc,
                "filing_date": date,
                "primary_doc": doc,
                "cik": cik,
            })
    return results


def _parse_form4_xml(cik: str, accession: str, doc: str, user_agent: str) -> list[dict]:
    """
    Fetch and parse a Form 4 XML filing. Returns normalised transaction records.
    Transaction codes: P = open-market purchase, S = open-market sale.

    EDGAR's submissions API returns primaryDocument as "xslF345X06/filename.xml"
    (the XSLT-rendered HTML viewer path). The actual raw Form 4 XML is at the
    same accession but without the xslF345X06/ directory prefix.
    """
    acc_nodash = accession.replace("-", "")
    # Strip XSLT viewer directory prefix — we want the raw XML, not the HTML render
    doc_clean = doc.split("/")[-1]
    url = f"{_FILING_BASE}/{int(cik)}/{acc_nodash}/{doc_clean}"

    try:
        resp = httpx.get(url, headers={"User-Agent": user_agent}, timeout=15)
        resp.raise_for_status()
        content = resp.text
    except Exception as exc:
        logger.debug("EDGAR XML fetch failed (%s): %s", accession, exc)
        return []

    import xml.etree.ElementTree as ET
    records = []
    try:
        root = ET.fromstring(content)

        # Extract issuer info
        issuer_el = root.find(".//issuer")
        ticker  = ""
        company = ""
        if issuer_el is not None:
            ticker  = (issuer_el.findtext("issuerTradingSymbol") or "").upper().strip()
            company = (issuer_el.findtext("issuerName") or "").strip()

        # Extract reporting person
        rp = root.find(".//reportingOwner")
        insider_name  = ""
        insider_title = ""
        if rp is not None:
            insider_name  = (rp.findtext(".//rptOwnerName") or "").strip()
            insider_title = (rp.findtext(".//officerTitle") or "").strip()

        # Non-derivative transactions
        for tx in root.findall(".//nonDerivativeTransaction"):
            code_el = tx.find(".//transactionCode")
            if code_el is None:
                continue
            code = (code_el.text or "").strip().upper()
            if code not in ("P", "S"):
                continue

            shares_el = tx.find(".//transactionShares/value")
            price_el  = tx.find(".//transactionPricePerShare/value")
            date_el   = tx.find(".//transactionDate/value")

            try:
                shares = float(shares_el.text or 0) if shares_el is not None else 0
                price  = float(price_el.text  or 0) if price_el  is not None else 0
            except (ValueError, TypeError):
                continue

            if price <= 0 or shares <= 0:
                continue

            records.append({
                "ticker":            ticker,
                "company":           company,
                "insider_name":      insider_name,
                "insider_title":     insider_title,
                "transaction_type":  "buy" if code == "P" else "sell",
                "shares":            shares,
                "price_per_share":   price,
                "total_value":       shares * price,
                "is_open_market":    True,
                "is_congress":       False,
                "transaction_date":  (date_el.text or "")[:10] if date_el is not None else "",
                "filing_date":       "",  # filled in by caller
                "sec_accession_number": accession,
                "sec_filing_url":    url,
            })
    except ET.ParseError as exc:
        logger.debug("XML parse error for %s: %s", accession, exc)

    return records


def fetch_form4_filings(
    user_agent: str,
    days: int = 7,
    ticker_filter: set[str] | None = None,
) -> list[dict]:
    """
    Fetch Form 4 insider transactions for the given tickers.

    Queries EDGAR per-company (not the global filings feed).
    Only fetches XMLs for tickers in ticker_filter (or all theme tickers if None).
    """
    cik_map = _get_ticker_cik_map()
    tickers = list(ticker_filter) if ticker_filter else list(cik_map.keys())

    # Only process tickers we have CIKs for
    tickers_with_cik = [(t, cik_map[t]) for t in tickers if t in cik_map]
    logger.info(
        "EDGAR: scanning %d tickers (of %d requested) for Form 4 filings",
        len(tickers_with_cik), len(tickers),
    )

    all_records: list[dict] = []
    filing_count = 0

    for ticker, cik in tickers_with_cik:
        time.sleep(_SLEEP)
        form4s = _get_company_form4s(cik, days, user_agent)
        if not form4s:
            continue

        for f4 in form4s:
            time.sleep(_SLEEP)
            records = _parse_form4_xml(
                cik=f4["cik"],
                accession=f4["accession_number"],
                doc=f4["primary_doc"],
                user_agent=user_agent,
            )
            # Stamp filing date from submissions API (more reliable than XML)
            for r in records:
                r["filing_date"] = f4["filing_date"]
                if not r.get("ticker"):
                    r["ticker"] = ticker

            all_records.extend(records)
            filing_count += 1

    logger.info(
        "EDGAR: parsed %d Form 4 filings → %d transactions across %d tickers",
        filing_count, len(all_records), len(tickers_with_cik),
    )
    return all_records
