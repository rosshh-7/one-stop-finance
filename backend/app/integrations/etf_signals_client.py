"""
yfinance-backed ETF flow + options collector for theme benchmark ETFs.

Flow (per ETF):
  - 35 days of daily OHLCV → most recent day's volume vs trailing 30-day avg
  - vol_ratio + price_change_pct (last close vs prior close)

Options (per ETF):
  - Nearest expiry >= 14 days out
  - put_call_ratio (open-interest based)
  - otm_call_oi (calls > 5% out of the money)
  - iv_percentile (mean IV of nearest 5 ATM calls × 100)

All yfinance calls run via asyncio.to_thread — yfinance is blocking.
"""
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_OTM_THRESHOLD = 0.05  # calls > 5% OTM = speculative


def _fetch_flow_sync(symbol: str) -> dict | None:
    import yfinance as yf
    try:
        hist = yf.Ticker(symbol).history(period="35d", interval="1d", auto_adjust=False)
    except Exception as exc:
        logger.debug("yfinance history failed for %s: %s", symbol, exc)
        return None
    if hist is None or hist.empty or len(hist) < 5:
        return None

    volumes = [int(v) for v in hist["Volume"].fillna(0).tolist()]
    closes = [float(c) for c in hist["Close"].fillna(0).tolist()]
    today_vol = volumes[-1] or 0
    prior = volumes[:-1]
    avg_30d = (sum(prior) / len(prior)) if prior else 0
    vol_ratio = (today_vol / avg_30d) if avg_30d > 0 else None

    if len(closes) >= 2 and closes[-2] > 0:
        price_change_pct = round((closes[-1] - closes[-2]) / closes[-2] * 100, 3)
    else:
        price_change_pct = 0.0

    return {
        "volume":           today_vol,
        "avg_30d_volume":   int(avg_30d),
        "vol_ratio":        round(vol_ratio, 3) if vol_ratio is not None else None,
        "price_change_pct": price_change_pct,
    }


def _fetch_options_sync(symbol: str) -> dict | None:
    import yfinance as yf
    try:
        stock = yf.Ticker(symbol)
        expirations = stock.options or []
    except Exception as exc:
        logger.debug("yfinance options list failed for %s: %s", symbol, exc)
        return None

    if not expirations:
        return None

    today = datetime.now(timezone.utc).date()
    target = None
    for exp in expirations:
        try:
            exp_dt = datetime.strptime(exp, "%Y-%m-%d").date()
            if (exp_dt - today).days >= 14:
                target = exp
                break
        except Exception:
            continue
    if target is None:
        target = expirations[0]

    try:
        chain = stock.option_chain(target)
        calls = chain.calls
        puts = chain.puts
    except Exception as exc:
        logger.debug("yfinance option_chain failed for %s: %s", symbol, exc)
        return None
    if calls is None or puts is None or calls.empty or puts.empty:
        return None

    total_call_oi = int(calls["openInterest"].fillna(0).sum())
    total_put_oi = int(puts["openInterest"].fillna(0).sum())
    put_call_ratio = (total_put_oi / total_call_oi) if total_call_oi > 0 else None

    # Current price for OTM bucketing
    try:
        fi = stock.fast_info
        current_price = float(fi.get("lastPrice") or fi.get("previous_close") or 0)
    except Exception:
        current_price = 0.0

    if current_price > 0:
        otm_floor = current_price * (1 + _OTM_THRESHOLD)
        otm_calls = calls[calls["strike"] > otm_floor]
        otm_call_oi = int(otm_calls["openInterest"].fillna(0).sum())
    else:
        otm_call_oi = 0

    # IV percentile proxy — mean IV of nearest 5 ATM calls × 100
    iv_percentile = None
    try:
        ref_price = current_price if current_price > 0 else float(calls["strike"].median())
        nearest = calls.iloc[(calls["strike"] - ref_price).abs().argsort()[:5]]
        iv_vals = nearest["impliedVolatility"].dropna()
        if len(iv_vals) > 0:
            iv_percentile = round(float(iv_vals.mean()) * 100, 2)
    except Exception:
        pass

    return {
        "put_call_ratio": round(put_call_ratio, 4) if put_call_ratio is not None else None,
        "otm_call_oi":    otm_call_oi,
        "total_call_oi":  total_call_oi,
        "iv_percentile":  iv_percentile,
        "expiry_used":    target,
    }


async def fetch_etf_signal(symbol: str) -> dict | None:
    """Combined flow + options snapshot for one ETF."""
    flow = await asyncio.to_thread(_fetch_flow_sync, symbol)
    if flow is None:
        return None
    options = await asyncio.to_thread(_fetch_options_sync, symbol)
    return {
        "symbol": symbol,
        **flow,
        **(options or {
            "put_call_ratio": None, "otm_call_oi": None,
            "total_call_oi": None, "iv_percentile": None,
        }),
    }
