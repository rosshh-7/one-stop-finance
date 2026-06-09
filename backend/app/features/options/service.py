import asyncio
import math
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf

from app.features.options.schemas import (
    OptionContract, OptionsChainResponse, StockScore, ScannerResponse,
)

# Liquid large-cap stocks to scan
SCAN_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "LLY", "JPM",
    "V", "UNH", "XOM", "MA", "JNJ", "COST", "HD", "PG", "BAC", "MRK",
    "AMD", "ORCL", "CRM", "NFLX", "ADBE", "INTC", "WMT", "DIS", "GS", "CVX",
    "PLTR", "COIN", "SOFI", "UBER", "HOOD", "MSTR", "IONQ", "SMCI", "MELI", "NOW",
]


def _safe_float(val, default: float = 0.0) -> float:
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def _safe_int(val, default: int = 0) -> int:
    try:
        return int(val) if pd.notna(val) else default
    except (TypeError, ValueError):
        return default


def _underlying_price(ticker: yf.Ticker) -> float:
    try:
        info = ticker.fast_info
        return _safe_float(getattr(info, "last_price", None))
    except Exception:
        return 0.0


def _parse_chain(df: pd.DataFrame, spot: float, option_type: str) -> list[OptionContract]:
    contracts = []
    for _, row in df.iterrows():
        strike = _safe_float(row.get("strike"))
        iv = _safe_float(row.get("impliedVolatility"))
        itm = bool(row.get("inTheMoney", False))

        if spot > 0 and strike > 0:
            moneyness = spot / strike
            raw_delta = max(0.01, min(0.99, moneyness / (moneyness + 1)))
            delta = raw_delta if option_type == "call" else raw_delta - 1.0
        else:
            delta = 0.5 if option_type == "call" else -0.5

        contracts.append(OptionContract(
            strike=strike,
            bid=_safe_float(row.get("bid")),
            ask=_safe_float(row.get("ask")),
            last=_safe_float(row.get("lastPrice")),
            volume=_safe_int(row.get("volume")),
            open_interest=_safe_int(row.get("openInterest")),
            implied_volatility=round(iv * 100, 2),
            delta=round(delta, 3),
            in_the_money=itm,
        ))
    return sorted(contracts, key=lambda c: c.strike)


def _compute_max_pain(calls_df: pd.DataFrame, puts_df: pd.DataFrame) -> float:
    try:
        all_strikes = sorted(set(calls_df["strike"].tolist()) | set(puts_df["strike"].tolist()))
        if not all_strikes:
            return 0.0

        min_pain = float("inf")
        max_pain_strike = all_strikes[0]

        for s in all_strikes:
            call_pain = sum(
                max(0.0, s - k) * oi
                for k, oi in zip(calls_df["strike"], calls_df["openInterest"].fillna(0))
            )
            put_pain = sum(
                max(0.0, k - s) * oi
                for k, oi in zip(puts_df["strike"], puts_df["openInterest"].fillna(0))
            )
            total = call_pain + put_pain
            if total < min_pain:
                min_pain = total
                max_pain_strike = s

        return float(max_pain_strike)
    except Exception:
        return 0.0


def _score_stock_sync(symbol: str) -> StockScore | None:
    """Fetch nearest-expiry chain and compute a bullish/bearish score for a single stock."""
    try:
        ticker = yf.Ticker(symbol)
        expiries = list(ticker.options)
        if not expiries:
            return None

        chain = ticker.option_chain(expiries[0])
        calls_df = chain.calls.copy()
        puts_df = chain.puts.copy()
        spot = _underlying_price(ticker)
        if spot <= 0:
            return None

        # Put/Call ratio by open interest
        call_oi = _safe_int(calls_df["openInterest"].sum()) if "openInterest" in calls_df else 0
        put_oi = _safe_int(puts_df["openInterest"].sum()) if "openInterest" in puts_df else 0
        pcr = put_oi / call_oi if call_oi > 0 else 1.0

        # Volume totals
        call_vol = _safe_int(calls_df["volume"].sum()) if "volume" in calls_df else 0
        put_vol = _safe_int(puts_df["volume"].sum()) if "volume" in puts_df else 0

        max_pain = _compute_max_pain(calls_df, puts_df)
        mp_pct = ((max_pain - spot) / spot * 100) if spot > 0 else 0.0

        # --- Scoring (each component -40..+40 / -30..+30 / -30..+30) ---
        # 1. PCR: low PCR → calls dominating → bullish
        pcr_score = max(-40.0, min(40.0, (1.0 - pcr) * 40.0))

        # 2. Max pain relative to spot: above spot = gravitational pull up = bullish
        mp_score = max(-30.0, min(30.0, mp_pct * 5.0))

        # 3. Call/Put volume bias
        total_vol = call_vol + put_vol
        if total_vol > 0:
            vol_bias = (call_vol - put_vol) / total_vol
            vol_score = vol_bias * 30.0
        else:
            vol_score = 0.0

        score = round(pcr_score + mp_score + vol_score, 1)

        if score >= 30:
            signal = "Strong Bullish"
        elif score >= 5:
            signal = "Bullish"
        elif score <= -30:
            signal = "Strong Bearish"
        elif score <= -5:
            signal = "Bearish"
        else:
            signal = "Neutral"

        return StockScore(
            symbol=symbol,
            score=score,
            signal=signal,
            put_call_ratio=round(pcr, 3),
            max_pain=round(max_pain, 2),
            underlying_price=round(spot, 2),
            max_pain_pct=round(mp_pct, 2),
            call_volume=call_vol,
            put_volume=put_vol,
        )
    except Exception:
        return None


async def scan_universe() -> ScannerResponse:
    """Score all stocks in SCAN_UNIVERSE concurrently (max 8 at a time)."""
    sem = asyncio.Semaphore(8)

    async def _fetch(sym: str) -> StockScore | None:
        async with sem:
            return await asyncio.to_thread(_score_stock_sync, sym)

    results = await asyncio.gather(*[_fetch(s) for s in SCAN_UNIVERSE], return_exceptions=True)

    scores: list[StockScore] = [r for r in results if isinstance(r, StockScore)]
    scores.sort(key=lambda s: s.score, reverse=True)

    bullish = [s for s in scores if s.score > 0][:10]
    bearish = [s for s in reversed(scores) if s.score < 0][:10]

    return ScannerResponse(
        bullish=bullish,
        bearish=bearish,
        scanned_at=datetime.now(timezone.utc).isoformat(),
    )


def _fetch_chain_sync(symbol: str, expiry: str | None) -> OptionsChainResponse | None:
    ticker = yf.Ticker(symbol)

    try:
        expiries = list(ticker.options)
    except Exception:
        return None

    if not expiries:
        return None

    selected = expiry if expiry in expiries else expiries[0]

    try:
        chain = ticker.option_chain(selected)
    except Exception:
        return None

    calls_df = chain.calls.copy()
    puts_df = chain.puts.copy()

    spot = _underlying_price(ticker)
    max_pain = _compute_max_pain(calls_df, puts_df)

    call_oi = _safe_int(calls_df["openInterest"].sum()) if "openInterest" in calls_df else 0
    put_oi = _safe_int(puts_df["openInterest"].sum()) if "openInterest" in puts_df else 0
    pcr = round(put_oi / call_oi, 3) if call_oi > 0 else 0.0

    calls = _parse_chain(calls_df, spot, "call")
    puts = _parse_chain(puts_df, spot, "put")

    return OptionsChainResponse(
        symbol=symbol,
        expiry=selected,
        expiries=expiries[:12],
        underlying_price=round(spot, 2),
        max_pain=round(max_pain, 2),
        put_call_ratio=pcr,
        total_contracts=len(calls) + len(puts),
        calls=calls,
        puts=puts,
    )


async def fetch_options_chain(symbol: str, expiry: str | None) -> OptionsChainResponse | None:
    return await asyncio.to_thread(_fetch_chain_sync, symbol, expiry)
