"""
Theme Intelligence scoring engine.

score_all_themes() runs via Celery Beat every 15 minutes.
It reads from insider_filings, gov_contracts, trend_signals, and options_signals,
then computes a 0-100 score + velocity + lifecycle stage for each active theme,
upserts theme_scores, and inserts a theme_score_history row.

sync_* tasks are triggered manually via POST /api/v1/themes/sync.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import redis as redis_sync
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery
from app.config import settings
from app.database import celery_session
from app.models.base import new_uuid
from app.models.theme import (
    ConvergenceLevel, Theme, ThemeScore, ThemeScoreHistory,
    GovContract, TrendSignal, OptionsSignal, ThemeETFSignal,
    ActivistStake, InstitutionalHolding, ShortInterest,
    NihGrant, PatentSignal, MacroSignal, EightKSignal, FormDSignal,
)
from app.models.insider import InsiderFiling, TransactionType
from app.theme_config import CSUITE_KEYWORDS

logger = logging.getLogger(__name__)

REDIS_PREFIX = "theme:sync"
_LOOKBACK_DAYS = 14
_CONTRACT_LOOKBACK_DAYS = 30
_TREND_LOOKBACK_DAYS = 7


def _redis():
    return redis_sync.from_url(settings.redis_url, decode_responses=True)


def _mark_done(r, source: str) -> None:
    r.set(f"{REDIS_PREFIX}:{source}:status", "idle")
    r.set(f"{REDIS_PREFIX}:{source}:last_run", datetime.now(timezone.utc).isoformat())
    r.delete(f"{REDIS_PREFIX}:{source}:error")


def _mark_error(r, source: str, msg: str) -> None:
    r.set(f"{REDIS_PREFIX}:{source}:status", "error")
    r.set(f"{REDIS_PREFIX}:{source}:error", msg)


# ---------------------------------------------------------------------------
# Core scoring logic
# ---------------------------------------------------------------------------

def _is_csuite(title: str | None) -> bool:
    t = (title or "").lower()
    return any(kw in t for kw in CSUITE_KEYWORDS)


def _compute_lifecycle(score: float, velocity: float, selling_companies: int) -> str:
    if selling_companies >= 3:
        return "COOLING"
    if score < 50 and velocity > 10:
        return "EMERGING"
    if score < 70 and velocity > 0:
        return "BUILDING"
    if score >= 70 and abs(velocity) <= 5:
        return "PEAK"
    if velocity < -5:
        return "FADING"
    return "STABLE"


def _score_theme(
    theme_symbols: set[str],
    buys: list,
    sells: list,
    congress_symbols: set[str],
    contracts_count: int,
    trend_velocity: float,
    options_anomaly: float,
    sentiment_score: float = 0.0,
    etf_flow: dict | None = None,
    etf_options: dict | None = None,
    activist_stake_count: int = 0,
    institutional_new_positions: int = 0,
    short_high_and_buying: bool = False,
    ai_ecosystem_count: int = 0,
    ai_ecosystem_usd: float = 0.0,
    macro_aligned: bool = False,
    nih_grant_count: int = 0,
) -> dict:
    theme_buys = [b for b in buys if b.symbol in theme_symbols]
    theme_sells = [s for s in sells if s.symbol in theme_symbols]

    buying_companies = len(set(b.symbol for b in theme_buys))
    selling_companies = len(set(s.symbol for s in theme_sells))

    has_congress = bool(congress_symbols & theme_symbols)
    csuite_count = sum(1 for b in theme_buys if _is_csuite(b.insider_title))
    total_value = sum(b.total_value or 0 for b in theme_buys)
    large_buys = sum(1 for b in theme_buys if (b.total_value or 0) > 1_000_000)

    flow = etf_flow or {}
    opts = etf_options or {}
    vol_ratio        = float(flow.get("vol_ratio")        or 0.0)
    price_change_pct = float(flow.get("price_change_pct") or 0.0)
    put_call_ratio   = flow.get("put_call_ratio")  # may be None
    if put_call_ratio is None:
        put_call_ratio = opts.get("put_call_ratio")
    otm_call_oi      = int(opts.get("otm_call_oi")   or 0)
    total_call_oi    = int(opts.get("total_call_oi") or 0)
    iv_percentile    = float(opts.get("iv_percentile") or 0.0)
    otm_ratio        = (otm_call_oi / total_call_oi) if total_call_oi > 0 else 0.0

    # Base score — driven by unique companies buying
    if buying_companies >= 6:
        base = 90.0
    elif buying_companies == 5:
        base = 82.0
    elif buying_companies == 4:
        base = 72.0
    elif buying_companies == 3:
        base = 60.0
    elif buying_companies == 2:
        base = 38.0
    elif buying_companies == 1:
        base = 18.0
    else:
        base = 0.0

    # Bonus stack
    bonus = 0.0
    if csuite_count >= 1:           bonus += 10.0
    if total_value > 5_000_000:     bonus += 8.0
    elif total_value > 1_000_000:   bonus += 4.0
    if large_buys >= 1:             bonus += 5.0
    if has_congress:                bonus += 8.0
    if contracts_count >= 3:        bonus += 6.0
    elif contracts_count >= 1:      bonus += 3.0
    if trend_velocity >= 20:        bonus += 5.0
    elif trend_velocity >= 10:      bonus += 3.0
    if options_anomaly >= 2.0:      bonus += 7.0
    elif options_anomaly >= 1.5:    bonus += 4.0

    # ETF flow bonus — volume vs 30d baseline + price action
    flow_score = 0.0
    if vol_ratio >= 4.0:   flow_score = 90.0
    elif vol_ratio >= 3.0: flow_score = 75.0
    elif vol_ratio >= 2.0: flow_score = 55.0
    elif vol_ratio >= 1.5: flow_score = 30.0
    if flow_score > 0:
        if price_change_pct > 2.0:   flow_score = min(100.0, flow_score + 10.0)
        elif price_change_pct < 0.0: flow_score = max(0.0,  flow_score - 20.0)
        # Translate to themed bonus points (weight ~20% of final)
        bonus += round(flow_score * 0.20, 1)

    # ETF options bonus — put/call + OTM call open interest
    options_score = 0.0
    if put_call_ratio is not None:
        if put_call_ratio < 0.5:   options_score += 60.0
        elif put_call_ratio < 0.75: options_score += 40.0
        elif put_call_ratio < 1.0:  options_score += 20.0
    if otm_ratio > 0.4:   options_score += 30.0
    elif otm_ratio > 0.2: options_score += 15.0
    options_score = min(100.0, options_score)
    if options_score > 0:
        bonus += round(options_score * 0.10, 1)  # weight ~10% of final

    # News sentiment bonus
    if sentiment_score >= 0.5:    bonus += 5.0
    elif sentiment_score >= 0.2:  bonus += 3.0
    elif sentiment_score <= -0.5: bonus -= 5.0
    elif sentiment_score <= -0.2: bonus -= 3.0

    # Activist stake (+12) — 13D filed on a theme ticker = conviction builder
    if activist_stake_count >= 1: bonus += 12.0

    # Institutional new positions (+5) — 13F new entries this quarter
    if institutional_new_positions >= 2: bonus += 5.0
    elif institutional_new_positions == 1: bonus += 2.0

    # Short squeeze setup (+8) — high short interest + insider buying
    if short_high_and_buying: bonus += 8.0

    # AI ecosystem signals (+6/+10/+15) — Form D + 8-K AI deals
    if ai_ecosystem_count >= 3:   bonus += 15.0
    elif ai_ecosystem_count == 2: bonus += 10.0
    elif ai_ecosystem_count == 1: bonus += 6.0
    if ai_ecosystem_usd >= 1_000_000_000: bonus += 8.0

    # Macro alignment (+4) — FRED sector data trending correctly
    if macro_aligned: bonus += 4.0

    # NIH grants (+3) — biotech theme only
    if nih_grant_count >= 5:   bonus += 3.0
    elif nih_grant_count >= 2: bonus += 1.5

    # ---- Multi-signal convergence bonus -----------------------------------
    # Mirrors the foundation's "4+ signals above 50 → +8" rule.
    # Each signal type produces a 0–100 score; we count how many fire above 50
    # and add a discrete +8 boost when independent corroboration exists.
    insider_signal = base
    congress_signal_score = 70.0 if has_congress else 0.0
    contract_signal_score = (
        85.0 if contracts_count >= 3 else
        55.0 if contracts_count >= 1 else 0.0
    )
    trend_signal_score = (
        75.0 if trend_velocity >= 20 else
        55.0 if trend_velocity >= 10 else 0.0
    )
    stock_options_signal_score = (
        80.0 if options_anomaly >= 2.0 else
        55.0 if options_anomaly >= 1.5 else 0.0
    )
    sentiment_signal_score = 55.0 if sentiment_score >= 0.2 else 0.0

    activist_signal_score = 80.0 if activist_stake_count >= 1 else 0.0
    institutional_signal_score = 60.0 if institutional_new_positions >= 2 else 0.0
    ai_ecosystem_signal_score = 75.0 if ai_ecosystem_count >= 2 else (55.0 if ai_ecosystem_count == 1 else 0.0)
    short_squeeze_signal_score = 65.0 if short_high_and_buying else 0.0

    component_scores = [
        insider_signal,
        congress_signal_score,
        contract_signal_score,
        trend_signal_score,
        stock_options_signal_score,
        flow_score,
        options_score,
        sentiment_signal_score,
        activist_signal_score,
        institutional_signal_score,
        ai_ecosystem_signal_score,
        short_squeeze_signal_score,
    ]
    signals_fired = sum(1 for s in component_scores if s > 50.0)
    convergence_bonus = 8.0 if signals_fired >= 4 else 0.0
    bonus += convergence_bonus

    final = min(100.0, base + bonus)

    # Cooling modifier
    if selling_companies >= 3:
        final *= 0.70
    elif selling_companies == 2:
        final *= 0.85

    # Convergence level
    if final >= 70:
        level = ConvergenceLevel.ALERT
    elif final >= 45:
        level = ConvergenceLevel.WATCH
    else:
        level = ConvergenceLevel.QUIET

    return {
        "score": round(final, 1),
        "level": level,
        "unique_companies_buying": buying_companies,
        "unique_companies_selling": selling_companies,
        "total_value_accumulated": round(total_value, 2),
        "csuite_count": csuite_count,
        "congress_signal": has_congress,
        "unusual_options_count": 1 if options_anomaly >= 2.0 else 0,
        "contracts_count": contracts_count,
        "trend_velocity": round(trend_velocity, 1),
        "options_anomaly": round(options_anomaly, 2),
        "sentiment_signal": sentiment_score >= 0.2,
        "signal_breakdown": {
            "buying_tickers":         sorted(set(b.symbol for b in theme_buys)),
            "selling_tickers":        sorted(set(s.symbol for s in theme_sells)),
            "total_usd":              round(total_value, 0),
            "large_buys_count":       large_buys,
            "congress_tickers":       sorted(congress_symbols & theme_symbols),
            "contracts_count":        contracts_count,
            "sentiment_score":        round(sentiment_score, 3),
            "etf_vol_ratio":          round(vol_ratio, 2) if vol_ratio else None,
            "etf_price_change_pct":   round(price_change_pct, 2) if vol_ratio else None,
            "etf_flow_score":         round(flow_score, 1),
            "etf_put_call_ratio":     round(put_call_ratio, 3) if put_call_ratio is not None else None,
            "etf_otm_call_oi":        otm_call_oi or None,
            "etf_iv_percentile":      round(iv_percentile, 1) if iv_percentile else None,
            "etf_options_score":      round(options_score, 1),
            "signals_fired":          signals_fired,
            "convergence_bonus":      convergence_bonus,
            # New Phase 2 signals
            "activist_stake_count":       activist_stake_count,
            "institutional_new_positions": institutional_new_positions,
            "short_high_and_buying":      short_high_and_buying,
            "ai_ecosystem_count":         ai_ecosystem_count,
            "ai_ecosystem_usd":           round(ai_ecosystem_usd, 0),
            "macro_aligned":              macro_aligned,
            "nih_grant_count":            nih_grant_count,
        },
    }


def _load_sentiment_map() -> dict[str, float]:
    """Read all per-theme sentiment entries from Redis (theme:sentiment:<slug>)."""
    import json as _json
    r = _redis()
    out: dict[str, float] = {}
    try:
        for key in r.scan_iter(match="theme:sentiment:*"):
            slug = key.split(":")[-1]
            raw = r.get(key)
            if not raw:
                continue
            try:
                payload = _json.loads(raw)
                out[slug] = float(payload.get("score") or 0.0)
            except Exception:
                continue
    except Exception as exc:
        logger.debug("sentiment redis scan failed: %s", exc)
    return out


async def _load_etf_signals_map(
    session, theme_ids: list[str], max_age_hours: int = 48,
) -> tuple[dict[str, dict], dict[str, dict]]:
    """
    Latest ThemeETFSignal per theme (only signals within max_age_hours), split
    into flow + options dicts keyed by theme_id.
    """
    if not theme_ids:
        return {}, {}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    rows = (await session.execute(
        select(ThemeETFSignal)
        .where(ThemeETFSignal.theme_id.in_(theme_ids))
        .where(ThemeETFSignal.signal_date >= cutoff)
        .order_by(ThemeETFSignal.signal_date.desc())
    )).scalars().all()

    flow_map: dict[str, dict] = {}
    options_map: dict[str, dict] = {}
    for row in rows:
        if row.theme_id in flow_map:
            continue  # already have latest for this theme
        flow_map[row.theme_id] = {
            "vol_ratio":        row.vol_ratio,
            "price_change_pct": row.price_change_pct,
        }
        options_map[row.theme_id] = {
            "put_call_ratio": row.put_call_ratio,
            "otm_call_oi":    row.otm_call_oi,
            "total_call_oi":  row.total_call_oi,
            "iv_percentile":  row.iv_percentile,
        }
    return flow_map, options_map


async def _run_scoring():
    now = datetime.now(timezone.utc)
    buy_cutoff     = now - timedelta(days=_LOOKBACK_DAYS)
    contract_cutoff = now - timedelta(days=_CONTRACT_LOOKBACK_DAYS)
    trend_cutoff   = now - timedelta(days=_TREND_LOOKBACK_DAYS)

    sentiment_map = _load_sentiment_map()

    async with celery_session() as session:
        themes = (await session.execute(
            select(Theme).where(Theme.is_active == True)
        )).scalars().all()

        if not themes:
            logger.info("score_all_themes: no active themes — run seed script first")
            return 0

        buys = (await session.execute(
            select(InsiderFiling)
            .where(InsiderFiling.filing_date >= buy_cutoff)
            .where(InsiderFiling.transaction_type == TransactionType.BUY)
            .where(InsiderFiling.is_open_market == True)
        )).scalars().all()

        sells = (await session.execute(
            select(InsiderFiling)
            .where(InsiderFiling.filing_date >= buy_cutoff)
            .where(InsiderFiling.transaction_type == TransactionType.SELL)
            .where(InsiderFiling.is_open_market == True)
        )).scalars().all()

        congress_buys = (await session.execute(
            select(InsiderFiling)
            .where(InsiderFiling.filing_date >= buy_cutoff)
            .where(InsiderFiling.is_congress == True)
        )).scalars().all()
        congress_symbols = {c.symbol for c in congress_buys}

        contracts = (await session.execute(
            select(GovContract).where(GovContract.award_date >= contract_cutoff)
        )).scalars().all()

        trend_rows = (await session.execute(
            select(TrendSignal).where(TrendSignal.week_start >= trend_cutoff)
        )).scalars().all()

        options_rows = (await session.execute(
            select(OptionsSignal).where(OptionsSignal.signal_date >= buy_cutoff)
        )).scalars().all()

        flow_map, options_map = await _load_etf_signals_map(session, [t.id for t in themes])

        # Load new Phase 2 signal data
        activist_cutoff = now - timedelta(days=30)
        activist_rows = (await session.execute(
            select(ActivistStake).where(ActivistStake.filed_date >= activist_cutoff)
        )).scalars().all()

        quarter_label = f"{now.year}Q{(now.month - 1) // 3 + 1}"
        institutional_rows = (await session.execute(
            select(InstitutionalHolding)
            .where(InstitutionalHolding.quarter == quarter_label)
            .where(InstitutionalHolding.is_new_position == True)
        )).scalars().all()

        # Latest short interest per ticker
        short_rows = (await session.execute(
            select(ShortInterest).order_by(ShortInterest.settlement_date.desc())
        )).scalars().all()
        short_map: dict[str, float] = {}
        for sr in short_rows:
            if sr.ticker not in short_map and sr.short_ratio:
                short_map[sr.ticker] = sr.short_ratio

        ai_ecosystem_cutoff = now - timedelta(days=30)
        eightk_rows = (await session.execute(
            select(EightKSignal).where(EightKSignal.filed_date >= ai_ecosystem_cutoff)
        )).scalars().all()
        formd_rows = (await session.execute(
            select(FormDSignal).where(FormDSignal.filed_date >= ai_ecosystem_cutoff)
        )).scalars().all()

        macro_rows = (await session.execute(
            select(MacroSignal).order_by(MacroSignal.observation_date.desc())
        )).scalars().all()
        # Latest macro value per series
        macro_map: dict[str, MacroSignal] = {}
        for mr in macro_rows:
            if mr.series_id not in macro_map:
                macro_map[mr.series_id] = mr

        nih_rows = (await session.execute(
            select(NihGrant).where(NihGrant.theme_slug == "biotech-genomics")
        )).scalars().all()

        scored = 0
        for theme in themes:
            theme_symbols = {tt.symbol for tt in theme.tickers if tt.is_active}
            tc = sum(1 for c in contracts if c.theme_id == theme.id)

            tv_rows = [t for t in trend_rows if t.theme_id == theme.id]
            trend_velocity = (
                sum(t.velocity or 0 for t in tv_rows) / len(tv_rows) if tv_rows else 0.0
            )

            opt_rows = [o for o in options_rows if o.symbol in theme_symbols]
            options_anomaly = max((o.anomaly_ratio or 0) for o in opt_rows) if opt_rows else 0.0

            # Phase 2 per-theme signals
            theme_activist = sum(1 for a in activist_rows if a.ticker in theme_symbols)
            theme_institutional = sum(1 for ih in institutional_rows if ih.ticker in theme_symbols)

            buying_symbols = {b.symbol for b in buys if b.symbol in theme_symbols}
            theme_short_high_and_buying = any(
                short_map.get(sym, 0) > 0.3 and sym in buying_symbols
                for sym in theme_symbols
            )

            theme_ai_eightk = [r for r in eightk_rows if r.ticker in theme_symbols]
            theme_ai_formd = [r for r in formd_rows if theme.slug in (r.theme_slugs or [])]
            ai_eco_count = len(theme_ai_eightk) + len(theme_ai_formd)
            ai_eco_usd = (
                sum(r.deal_amount or 0 for r in theme_ai_eightk)
                + sum(r.amount_raised or 0 for r in theme_ai_formd)
            )

            # Macro alignment: series relevant to this theme trending positively
            theme_macro_series = [
                mr for mr in macro_map.values()
                if theme.slug in (mr.theme_relevance or [])
            ]
            theme_macro_aligned = any(
                (mr.pct_change or 0) > 0 for mr in theme_macro_series
            ) if theme_macro_series else False

            theme_nih = len(nih_rows) if theme.slug == "biotech-genomics" else 0

            result = _score_theme(
                theme_symbols, buys, sells, congress_symbols,
                tc, trend_velocity, options_anomaly,
                sentiment_score=sentiment_map.get(theme.slug, 0.0),
                etf_flow=flow_map.get(theme.id),
                etf_options=options_map.get(theme.id),
                activist_stake_count=theme_activist,
                institutional_new_positions=theme_institutional,
                short_high_and_buying=theme_short_high_and_buying,
                ai_ecosystem_count=ai_eco_count,
                ai_ecosystem_usd=ai_eco_usd,
                macro_aligned=theme_macro_aligned,
                nih_grant_count=theme_nih,
            )

            existing = (await session.execute(
                select(ThemeScore).where(ThemeScore.theme_id == theme.id)
            )).scalar_one_or_none()

            prev_score = existing.score if existing else 0.0
            velocity = round(result["score"] - prev_score, 1)
            lifecycle = _compute_lifecycle(result["score"], velocity, result["unique_companies_selling"])

            if existing:
                existing.score = result["score"]
                existing.level = result["level"]
                existing.unique_companies_buying = result["unique_companies_buying"]
                existing.unique_companies_selling = result["unique_companies_selling"]
                existing.total_value_accumulated = result["total_value_accumulated"]
                existing.csuite_count = result["csuite_count"]
                existing.congress_signal = result["congress_signal"]
                existing.unusual_options_count = result["unusual_options_count"]
                existing.contracts_count = result["contracts_count"]
                existing.trend_velocity = result["trend_velocity"]
                existing.options_anomaly = result["options_anomaly"]
                existing.sentiment_signal = result["sentiment_signal"]
                existing.velocity = velocity
                existing.lifecycle_stage = lifecycle
                existing.signal_breakdown = result["signal_breakdown"]
                existing.scored_at = now
            else:
                session.add(ThemeScore(
                    id=new_uuid(),
                    theme_id=theme.id,
                    velocity=velocity,
                    lifecycle_stage=lifecycle,
                    scored_at=now,
                    level=result["level"],
                    score=result["score"],
                    unique_companies_buying=result["unique_companies_buying"],
                    unique_companies_selling=result["unique_companies_selling"],
                    total_value_accumulated=result["total_value_accumulated"],
                    csuite_count=result["csuite_count"],
                    congress_signal=result["congress_signal"],
                    unusual_options_count=result["unusual_options_count"],
                    contracts_count=result["contracts_count"],
                    trend_velocity=result["trend_velocity"],
                    options_anomaly=result["options_anomaly"],
                    sentiment_signal=result["sentiment_signal"],
                    signal_breakdown=result["signal_breakdown"],
                ))

            session.add(ThemeScoreHistory(
                id=new_uuid(),
                theme_id=theme.id,
                score=result["score"],
                velocity=velocity,
                lifecycle_stage=lifecycle,
                unique_companies_buying=result["unique_companies_buying"],
                signal_breakdown=result["signal_breakdown"],
                scored_at=now,
            ))
            scored += 1

        await session.commit()
        return scored


@celery.task(name="app.workers.theme_intelligence.score_all_themes")
def score_all_themes():
    logger.info("score_all_themes: starting")
    scored = asyncio.run(_run_scoring())
    logger.info("score_all_themes: scored %d themes", scored)


# ---------------------------------------------------------------------------
# Manual sync tasks
# ---------------------------------------------------------------------------

@celery.task(name="app.workers.theme_intelligence.sync_fmp")
def sync_fmp():
    """FMP ticker classification — classifies unknown insider tickers into themes.

    Requires FMP_API_KEY (profile lookup). Anthropic key is optional — without
    it, classification falls back to deterministic multi-word keyword matching.
    """
    r = _redis()
    logger.info("sync_fmp: starting")
    try:
        if not settings.fmp_api_key:
            logger.info("sync_fmp: FMP_API_KEY not set — skipping (add key to .env to enable)")
            _mark_done(r, "fmp")
            return
        asyncio.run(_run_fmp_sync())
        _mark_done(r, "fmp")
    except Exception as exc:
        logger.error("sync_fmp: failed — %s", exc)
        _mark_error(r, "fmp", str(exc))
        raise


@celery.task(name="app.workers.theme_intelligence.sync_trends")
def sync_trends():
    """Google Trends keyword velocity — stores weekly interest scores per theme."""
    r = _redis()
    logger.info("sync_trends: starting")
    try:
        asyncio.run(_run_trends_sync())
        _mark_done(r, "trends")
    except Exception as exc:
        logger.error("sync_trends: failed — %s", exc)
        _mark_error(r, "trends", str(exc))
        raise


@celery.task(name="app.workers.theme_intelligence.sync_polygon")
def sync_polygon():
    """Polygon EOD options volume — detects unusual volume vs 30d average."""
    r = _redis()
    logger.info("sync_polygon: starting")
    try:
        asyncio.run(_run_polygon_sync())
        _mark_done(r, "polygon")
    except Exception as exc:
        logger.error("sync_polygon: failed — %s", exc)
        _mark_error(r, "polygon", str(exc))
        raise


@celery.task(name="app.workers.theme_intelligence.sync_etf")
def sync_etf():
    """ETF holdings expansion — adds ETF constituent tickers to theme coverage."""
    r = _redis()
    logger.info("sync_etf: starting")
    try:
        asyncio.run(_run_etf_sync())
        _mark_done(r, "etf")
    except Exception as exc:
        logger.error("sync_etf: failed — %s", exc)
        _mark_error(r, "etf", str(exc))
        raise


# ---------------------------------------------------------------------------
# Sync implementation functions
# ---------------------------------------------------------------------------

async def _run_trends_sync():
    """
    Fetch Google Trends interest scores for all theme keywords.
    Batches 5 keywords per request. Caches results for 7 days in trend_signals.
    """
    import time as _time
    from pytrends.request import TrendReq
    from app.theme_config import THEME_TREND_KEYWORDS

    now = datetime.now(timezone.utc)
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    pytrends = TrendReq(hl="en-US", tz=0, timeout=(10, 30))

    inserted = 0
    async with celery_session() as session:
        for theme_name, keywords in THEME_TREND_KEYWORDS.items():
            # Find theme_id
            from sqlalchemy import select as sa_select
            from app.models.theme import Theme as ThemeModel, TrendSignal
            theme_row = (await session.execute(
                sa_select(ThemeModel).where(ThemeModel.name == theme_name)
            )).scalar_one_or_none()
            if not theme_row:
                continue

            # Check if already synced this week
            existing = (await session.execute(
                sa_select(TrendSignal)
                .where(TrendSignal.theme_id == theme_row.id)
                .where(TrendSignal.week_start >= week_start)
            )).scalar_one_or_none()
            if existing:
                continue

            for i in range(0, len(keywords), 5):
                batch = keywords[i:i + 5]
                try:
                    await asyncio.to_thread(
                        pytrends.build_payload, batch, timeframe="now 7-d"
                    )
                    df = await asyncio.to_thread(pytrends.interest_over_time)
                    _time.sleep(2)  # Google soft rate limit — polite pacing

                    if df is None or df.empty:
                        continue

                    for kw in batch:
                        if kw not in df.columns:
                            continue
                        interest_now = float(df[kw].iloc[-1]) if len(df) > 0 else 0.0
                        interest_prev = float(df[kw].iloc[-8]) if len(df) >= 8 else interest_now
                        velocity = interest_now - interest_prev

                        session.add(TrendSignal(
                            id=new_uuid(),
                            theme_id=theme_row.id,
                            keyword=kw,
                            interest_score=interest_now,
                            prev_week_score=interest_prev,
                            velocity=velocity,
                            week_start=week_start,
                            created_at=now,
                        ))
                        inserted += 1
                except Exception as exc:
                    logger.warning("pytrends batch failed for %s: %s", batch, exc)
                    _time.sleep(5)

        await session.commit()
    logger.info("sync_trends: %d keyword trend rows inserted", inserted)


async def _run_polygon_sync():
    """
    Fetch EOD options/stock volume from Polygon for all theme tickers.
    Computes anomaly_ratio = today_volume / 30d_avg. Rate-limited to 5 req/min.
    """
    from app.config import settings
    from app.integrations.polygon import fetch_all_theme_volumes
    from app.theme_config import THEME_CONFIG
    from app.models.theme import OptionsSignal

    api_key = settings.polygon_api_key
    if not api_key:
        logger.info("sync_polygon: POLYGON_API_KEY not set — skipping")
        return

    # Collect all unique theme tickers
    all_symbols = list({
        t["symbol"]
        for theme in THEME_CONFIG
        for t in theme["tickers"]
    })

    logger.info("sync_polygon: fetching volume for %d tickers", len(all_symbols))
    volume_data = await fetch_all_theme_volumes(all_symbols, api_key)

    now = datetime.now(timezone.utc)
    inserted = 0
    async with celery_session() as session:
        for v in volume_data:
            if (v.get("anomaly_ratio") or 0) < 1.2:
                continue  # only store notable anomalies

            from sqlalchemy import select as sa_select
            exists = (await session.execute(
                sa_select(OptionsSignal.id)
                .where(OptionsSignal.symbol == v["symbol"])
                .where(OptionsSignal.signal_date >= now.replace(hour=0, minute=0, second=0))
            )).scalar_one_or_none()
            if exists:
                continue

            session.add(OptionsSignal(
                id=new_uuid(),
                symbol=v["symbol"],
                call_volume=None,
                put_volume=None,
                total_volume=v.get("total_volume"),
                avg_30d_volume=v.get("avg_30d_volume"),
                anomaly_ratio=v.get("anomaly_ratio"),
                signal_date=v.get("signal_date", now),
                created_at=now,
            ))
            inserted += 1

        await session.commit()
    logger.info("sync_polygon: %d anomaly signals stored", inserted)


async def _run_etf_sync():
    """
    Fetch ETF holdings via yfinance and add new constituent tickers to theme_tickers.
    Expands theme coverage beyond the manual THEME_TICKER_MAP.
    """
    import yfinance as yf
    from app.theme_config import THEME_CONFIG
    from app.models.theme import Theme as ThemeModel, ThemeTicker
    from sqlalchemy import select as sa_select

    added = 0
    async with celery_session() as session:
        for cfg in THEME_CONFIG:
            etf_sym = cfg.get("benchmark_etf")
            if not etf_sym:
                continue

            theme_row = (await session.execute(
                sa_select(ThemeModel).where(ThemeModel.slug == cfg["slug"])
            )).scalar_one_or_none()
            if not theme_row:
                continue

            existing_syms = {
                tt.symbol for tt in (await session.execute(
                    sa_select(ThemeTicker).where(ThemeTicker.theme_id == theme_row.id)
                )).scalars().all()
            }

            try:
                fund = await asyncio.to_thread(yf.Ticker, etf_sym)
                top = await asyncio.to_thread(lambda: fund.funds_data.top_holdings)
                if top is None or (hasattr(top, 'empty') and top.empty):
                    continue
                tickers_from_etf = [str(sym).upper() for sym in top.index if sym]
            except Exception as exc:
                logger.debug("ETF holdings fetch failed for %s: %s", etf_sym, exc)
                continue

            for sym in tickers_from_etf:
                if sym not in existing_syms and len(sym) <= 10:
                    session.add(ThemeTicker(
                        id=new_uuid(),
                        theme_id=theme_row.id,
                        symbol=sym,
                        company_name=None,
                        market_cap_tier="mid",
                        is_active=True,
                    ))
                    added += 1

        await session.commit()
    logger.info("sync_etf: %d new tickers added from ETF holdings", added)


async def _run_fmp_sync(max_tickers: int = 30):
    """
    Classify unknown insider tickers into themes.

    1. Pull symbols from insider_filings not already in theme_tickers.
    2. Cap at max_tickers per run — FMP free tier = 250 req/day.
    3. Fetch FMP profile; skip excluded sectors/industries (food/retail/etc).
    4. If Anthropic key is set → Claude Haiku classification.
       Otherwise → deterministic keyword fallback against theme_keywords.
    5. Upsert theme_tickers rows for each match.
    """
    from app.integrations.fmp import fetch_company_profile
    from app.integrations.anthropic_classify import classify_ticker
    from app.theme_keywords import is_excluded_profile, keyword_classify
    from app.models.theme import Theme as ThemeModel, ThemeTicker
    from sqlalchemy import select as sa_select, distinct

    fmp_key = settings.fmp_api_key
    anth_key = settings.anthropic_api_key

    async with celery_session() as session:
        # Already-mapped symbols
        mapped = {
            row for (row,) in (await session.execute(
                sa_select(distinct(ThemeTicker.symbol))
            )).all()
        }

        # Candidate symbols from insider_filings
        candidates_rows = (await session.execute(
            sa_select(distinct(InsiderFiling.symbol))
        )).all()
        candidates = [
            s for (s,) in candidates_rows
            if s and s not in mapped and 1 <= len(s) <= 10 and s.isalpha()
        ]
        if not candidates:
            logger.info("sync_fmp: no unknown insider tickers to classify")
            return

        candidates = candidates[:max_tickers]
        logger.info("sync_fmp: classifying %d unknown tickers", len(candidates))

        # Theme list passed to Haiku
        theme_rows = (await session.execute(
            sa_select(ThemeModel).where(ThemeModel.is_active == True)
        )).scalars().all()
        themes_for_prompt = [
            {"slug": t.slug, "name": t.name, "description": t.description or ""}
            for t in theme_rows
        ]
        slug_to_id = {t.slug: t.id for t in theme_rows}

        added = excluded = 0
        for sym in candidates:
            profile = await fetch_company_profile(sym, fmp_key)
            if not profile:
                continue

            # False-positive guard before any LLM call
            if is_excluded_profile(profile):
                excluded += 1
                continue

            slugs: list[str]
            if anth_key:
                slugs = await classify_ticker(profile, themes_for_prompt, anth_key)
                if not slugs:
                    # Haiku returned [] — try keyword fallback as a safety net
                    slugs = keyword_classify(profile)
            else:
                slugs = keyword_classify(profile)

            if not slugs:
                continue

            for slug in slugs:
                theme_id = slug_to_id.get(slug)
                if not theme_id:
                    continue
                exists = (await session.execute(
                    sa_select(ThemeTicker.id)
                    .where(ThemeTicker.theme_id == theme_id)
                    .where(ThemeTicker.symbol == sym)
                )).scalar_one_or_none()
                if exists:
                    continue
                session.add(ThemeTicker(
                    id=new_uuid(),
                    theme_id=theme_id,
                    symbol=sym,
                    company_name=profile.get("company_name"),
                    market_cap_tier=profile.get("market_cap_tier"),
                    is_active=True,
                ))
                added += 1

        await session.commit()
    logger.info(
        "sync_fmp: %d theme_ticker rows added (excluded %d non-tech, processed %d)",
        added, excluded, len(candidates),
    )


async def _run_etf_signals_sync(max_etfs: int = 25):
    """
    Fetch volume + options snapshots for every theme's benchmark ETF.
    Stores one ThemeETFSignal row per (theme, day) — idempotent within the day.
    yfinance has no rate limit but is slow; ~25 ETFs/run is fine daily.
    """
    from app.integrations.etf_signals_client import fetch_etf_signal
    from sqlalchemy import select as sa_select

    now = datetime.now(timezone.utc)
    today_floor = now.replace(hour=0, minute=0, second=0, microsecond=0)

    async with celery_session() as session:
        themes = (await session.execute(
            sa_select(Theme).where(Theme.is_active == True)
        )).scalars().all()

        # One ETF symbol can serve multiple themes — fetch once, fan out
        etf_to_themes: dict[str, list[Theme]] = {}
        for t in themes:
            sym = (t.benchmark_etf or "").upper().strip()
            if sym:
                etf_to_themes.setdefault(sym, []).append(t)

        symbols = list(etf_to_themes.keys())[:max_etfs]
        logger.info("sync_etf_signals: fetching %d unique theme ETFs", len(symbols))

        inserted = 0
        for sym in symbols:
            sig = await fetch_etf_signal(sym)
            if not sig:
                continue
            for theme in etf_to_themes[sym]:
                exists = (await session.execute(
                    sa_select(ThemeETFSignal.id)
                    .where(ThemeETFSignal.theme_id == theme.id)
                    .where(ThemeETFSignal.signal_date >= today_floor)
                )).scalar_one_or_none()
                if exists:
                    continue
                session.add(ThemeETFSignal(
                    id=new_uuid(),
                    theme_id=theme.id,
                    etf_symbol=sym,
                    signal_date=now,
                    volume=sig.get("volume"),
                    avg_30d_volume=sig.get("avg_30d_volume"),
                    vol_ratio=sig.get("vol_ratio"),
                    price_change_pct=sig.get("price_change_pct"),
                    put_call_ratio=sig.get("put_call_ratio"),
                    otm_call_oi=sig.get("otm_call_oi"),
                    total_call_oi=sig.get("total_call_oi"),
                    iv_percentile=sig.get("iv_percentile"),
                    created_at=now,
                ))
                inserted += 1

        await session.commit()
    logger.info("sync_etf_signals: %d ThemeETFSignal rows inserted", inserted)


@celery.task(name="app.workers.theme_intelligence.sync_etf_signals")
def sync_etf_signals():
    """Theme-ETF flow + options snapshot — daily via Beat or via pipeline."""
    r = _redis()
    logger.info("sync_etf_signals: starting")
    try:
        asyncio.run(_run_etf_signals_sync())
        _mark_done(r, "etf_signals")
    except Exception as exc:
        logger.error("sync_etf_signals: failed — %s", exc)
        _mark_error(r, "etf_signals", str(exc))
        raise


# ---------------------------------------------------------------------------
# Full pipeline — triggered by the dashboard "Run Pipeline" button
# ---------------------------------------------------------------------------

PIPELINE_KEY = "theme:pipeline"

def _pipeline_set(r, field: str, value: str) -> None:
    r.hset(PIPELINE_KEY, field, value)


def _should_run_weekly(r, source: str) -> bool:
    """Returns True if the source hasn't been synced in the last 7 days."""
    return _staler_than(r, source, 7 * 86_400)


def _should_run_daily(r, source: str) -> bool:
    """Returns True if the source hasn't been synced in the last 24 hours."""
    return _staler_than(r, source, 86_400)


def _staler_than(r, source: str, max_age_sec: float) -> bool:
    last = r.get(f"{REDIS_PREFIX}:{source}:last_run")
    if not last:
        return True
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()
        return age > max_age_sec
    except Exception:
        return True


@celery.task(name="app.workers.theme_intelligence.run_pipeline", bind=True)
def run_pipeline(self):
    """
    Full data collection pipeline — runs all collectors then rescores.
    Triggered on-demand from the dashboard. Runs weekly-cadence sources
    (trends, ETF) only when their cache is stale to respect rate limits.
    """
    r = _redis()
    now = datetime.now(timezone.utc).isoformat()

    _pipeline_set(r, "status",     "running")
    _pipeline_set(r, "started_at", now)
    _pipeline_set(r, "error",      "")
    _pipeline_set(r, "current_step", "Starting...")

    logger.info("run_pipeline: starting full collection pipeline")

    try:
        from app.workers.insider_data import poll_sec_edgar
        from app.workers.congress_data import fetch_congress_trades
        from app.workers.contracts_data import fetch_gov_contracts

        # Step 1 — EDGAR insider filings
        _pipeline_set(r, "current_step", "edgar")
        logger.info("run_pipeline: step 1 — EDGAR insider filings")
        poll_sec_edgar()

        # Step 2 — Congressional trades
        _pipeline_set(r, "current_step", "congress")
        logger.info("run_pipeline: step 2 — congressional trades")
        fetch_congress_trades()

        # Step 3 — Government contracts
        _pipeline_set(r, "current_step", "contracts")
        logger.info("run_pipeline: step 3 — government contracts")
        fetch_gov_contracts()

        # Step 3.5 — Classify new insider tickers (FMP key required; Haiku optional)
        if settings.fmp_api_key:
            _pipeline_set(r, "current_step", "fmp")
            logger.info("run_pipeline: step 3.5 — FMP ticker classification")
            asyncio.run(_run_fmp_sync())
            _mark_done(r, "fmp")
        else:
            logger.info("run_pipeline: step 3.5 — FMP classification skipped (FMP_API_KEY missing)")

        # Step 4 — Google Trends (only if stale)
        if _should_run_weekly(r, "trends"):
            _pipeline_set(r, "current_step", "trends")
            logger.info("run_pipeline: step 4 — Google Trends (stale, syncing)")
            asyncio.run(_run_trends_sync())
            _mark_done(r, "trends")
        else:
            logger.info("run_pipeline: step 4 — Google Trends skipped (fresh)")

        # Step 5 — ETF holdings (only if stale)
        if _should_run_weekly(r, "etf"):
            _pipeline_set(r, "current_step", "etf")
            logger.info("run_pipeline: step 5 — ETF holdings (stale, syncing)")
            asyncio.run(_run_etf_sync())
            _mark_done(r, "etf")
        else:
            logger.info("run_pipeline: step 5 — ETF holdings skipped (fresh)")

        # Step 5.5 — Polygon EOD options volume (daily, only if key + stale)
        if settings.polygon_api_key and _should_run_daily(r, "polygon"):
            _pipeline_set(r, "current_step", "polygon")
            logger.info("run_pipeline: step 5.5 — Polygon EOD volumes (stale, syncing)")
            asyncio.run(_run_polygon_sync())
            _mark_done(r, "polygon")
        else:
            logger.info("run_pipeline: step 5.5 — Polygon skipped (fresh or no key)")

        # Step 5.6 — Theme-ETF flow + options snapshot (daily, yfinance, no key)
        if _should_run_daily(r, "etf_signals"):
            _pipeline_set(r, "current_step", "etf_signals")
            logger.info("run_pipeline: step 5.6 — Theme-ETF flow + options (stale, syncing)")
            asyncio.run(_run_etf_signals_sync())
            _mark_done(r, "etf_signals")
        else:
            logger.info("run_pipeline: step 5.6 — Theme-ETF signals skipped (fresh)")

        # Step 6 — Score all themes
        _pipeline_set(r, "current_step", "scoring")
        logger.info("run_pipeline: step 6 — scoring all themes")
        scored = asyncio.run(_run_scoring())
        logger.info("run_pipeline: scored %d themes", scored)

        _pipeline_set(r, "status",       "done")
        _pipeline_set(r, "last_run",     datetime.now(timezone.utc).isoformat())
        _pipeline_set(r, "current_step", "")
        logger.info("run_pipeline: pipeline complete")

    except Exception as exc:
        logger.error("run_pipeline: failed at step %s — %s",
                     r.hget(PIPELINE_KEY, "current_step"), exc)
        _pipeline_set(r, "status", "error")
        _pipeline_set(r, "error",  str(exc))
        _pipeline_set(r, "current_step", "")
        raise
