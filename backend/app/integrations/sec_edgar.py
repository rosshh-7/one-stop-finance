"""
SEC EDGAR Form 4 parser.

URL structure (confirmed from live feed):
  index: /Archives/edgar/data/{CIK}/{ACCESSION_NODASH}/{ACCESSION_DASHES}-index.htm
  xml:   resolved via index.json → item whose name ends in .xml (not .xsd)

All network calls are free — no API key required.
"""
import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx

_FORM4_RSS = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcurrent&type=4&dateb=&owner=include&count=40&search_text=&output=atom"
)
_HEADERS = {
    "User-Agent": "OneStopFinance contact@onestopfinance.com",
    "Accept-Encoding": "gzip",
}

# Matches: /Archives/edgar/data/{CIK}/{NODASH}/{DASHES}-index.htm
_INDEX_URL_RE = re.compile(
    r"https://www\.sec\.gov/Archives/edgar/data/(\d+)/(\d+)/([\d-]+)-index\.htm"
)

_CSUITE = {"chief executive", "ceo", "chief financial", "cfo", "president", "chief operating", "coo"}


def _score_filing(title: str, is_open_market: bool, total_value: float) -> int:
    t = title.lower()
    score = 0
    if any(k in t for k in ("chief executive", "ceo", "chief financial", "cfo")):
        score += 40
    elif any(k in t for k in ("president", "chief operating", "coo")):
        score += 25
    elif "director" in t or "vice president" in t:
        score += 20
    if is_open_market:
        score += 20
    if total_value >= 500_000:
        score += 15
    return min(score, 100)


def _extract_filings(atom_text: str) -> list[tuple[str, str, str]]:
    """
    Returns unique (cik, accession_nodash, accession_dashes) tuples.
    Deduplicates by accession_dashes — the feed lists both Issuer and
    Reporting entries for the same filing.
    """
    seen: set[str] = set()
    results: list[tuple[str, str, str]] = []
    for m in _INDEX_URL_RE.finditer(atom_text):
        cik, nodash, dashes = m.group(1), m.group(2), m.group(3)
        if dashes not in seen:
            seen.add(dashes)
            results.append((cik, nodash, dashes))
    return results


async def _resolve_xml_url(client: httpx.AsyncClient, cik: str, nodash: str) -> str | None:
    """Fetch index.json and return the URL of the primary Form 4 XML document."""
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/index.json"
    try:
        r = await client.get(url, headers=_HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        items = r.json().get("directory", {}).get("item", [])
        for item in items:
            name: str = item.get("name", "")
            # Primary Form 4 XML: ends in .xml, not a schema (.xsd) or wrapper
            if name.endswith(".xml") and not name.endswith(".xsd"):
                return f"https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{name}"
    except Exception:
        pass
    return None


def _val(parent: ET.Element, path: str) -> str:
    """Get text of a <value> child at `path`, or '' if missing."""
    el = parent.find(path)
    return (el.text or "").strip() if el is not None else ""


def _parse_form4_xml(xml_text: str, cik: str, nodash: str, dashes: str) -> list[dict]:
    """
    Parse all open-market buy transactions from a Form 4 XML.
    Returns one dict per transaction (a single filing can have many rows).
    """
    results: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return results

    symbol = _val(root, ".//issuerTradingSymbol").upper()
    issuer_name = _val(root, ".//issuerName")
    insider_name = _val(root, ".//rptOwnerName")

    # Officer title is in reportingOwnerRelationship
    officer_title = _val(root, ".//officerTitle")
    is_director = _val(root, ".//isDirector") == "1"
    is_officer = _val(root, ".//isOfficer") == "1"
    if not officer_title:
        if is_director:
            officer_title = "Director"
        elif is_officer:
            officer_title = "Officer"

    if not symbol or not insider_name:
        return results

    filing_url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{dashes}-index.htm"
    )
    now_iso = datetime.now(timezone.utc).isoformat()

    for i, txn in enumerate(root.iter("nonDerivativeTransaction")):
        # transactionCode is a bare text node inside <transactionCoding>, NOT in a <value> wrapper
        code_el = txn.find("transactionCoding/transactionCode")
        tcode = (code_el.text or "").strip() if code_el is not None else ""

        # Only open-market purchases (code P) and acquisitions (A)
        if tcode != "P":
            continue
        acq = _val(txn, "transactionAmounts/transactionAcquiredDisposedCode/value")
        if acq != "A":
            continue

        try:
            shares = float(_val(txn, "transactionAmounts/transactionShares/value") or "0")
            price = float(_val(txn, "transactionAmounts/transactionPricePerShare/value") or "0")
        except ValueError:
            continue

        total_value = shares * price
        if total_value <= 0:
            continue

        date_str = _val(txn, "transactionDate/value")
        txn_date: datetime | None = None
        if date_str:
            try:
                txn_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        score = _score_filing(officer_title, is_open_market=True, total_value=total_value)

        # Use accession + row index so multiple txns in one filing get unique accession keys
        accession_key = dashes if i == 0 else f"{dashes}-{i}"

        results.append({
            "symbol": symbol,
            "issuer_name": issuer_name,
            "insider_name": insider_name,
            "insider_title": officer_title or "Insider",
            "transaction_type": "buy",
            "shares": shares,
            "price_per_share": price,
            "total_value": total_value,
            "is_open_market": True,
            "is_congress": False,
            "filing_date": now_iso,
            "transaction_date": txn_date.isoformat() if txn_date else None,
            "signal_score": score,
            "sec_filing_url": filing_url,
            "sec_accession_number": accession_key,
        })

    return results


async def fetch_recent_form4_buys(limit: int = 40) -> list[dict]:
    all_results: list[dict] = []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            feed = await client.get(_FORM4_RSS, headers=_HEADERS, timeout=15)
            feed.raise_for_status()
        except Exception:
            return []

        filing_refs = _extract_filings(feed.text)

        for cik, nodash, dashes in filing_refs[:limit]:
            xml_url = await _resolve_xml_url(client, cik, nodash)
            if not xml_url:
                continue
            try:
                r = await client.get(xml_url, headers=_HEADERS, timeout=10)
                if r.status_code != 200:
                    continue
            except Exception:
                continue

            rows = _parse_form4_xml(r.text, cik, nodash, dashes)
            all_results.extend(rows)

    return all_results
