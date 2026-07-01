from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.core.response import build_response
from app.database import get_db
from app.redis import get_redis
from app.features.themes.schemas import (
    SyncTriggerRequest, SyncTriggerResponse,
    ThemeOut, ThemeDetailOut, ThemeScoreOut, ThemeListResponse,
    TickerOut, HistoryPoint, InsiderSignalOut, ContractSignalOut,
    WatchlistResponse, WatchlistItem, WatchlistAddResponse,
)
from app.features.themes.service import get_sync_status, trigger_sync, get_pipeline_status, trigger_pipeline
from app.features.themes import repository as repo

router = APIRouter(prefix="/themes", tags=["themes"])


def _score_out(ts) -> ThemeScoreOut | None:
    if ts is None:
        return None
    return ThemeScoreOut(
        score=ts.score or 0,
        level=ts.level.value if ts.level else "quiet",
        velocity=ts.velocity,
        lifecycle_stage=ts.lifecycle_stage,
        unique_companies_buying=ts.unique_companies_buying or 0,
        unique_companies_selling=ts.unique_companies_selling or 0,
        total_value_accumulated=ts.total_value_accumulated or 0,
        csuite_count=ts.csuite_count or 0,
        congress_signal=ts.congress_signal or False,
        sentiment_signal=ts.sentiment_signal or False,
        unusual_options_count=ts.unusual_options_count or 0,
        contracts_count=ts.contracts_count or 0,
        trend_velocity=ts.trend_velocity,
        options_anomaly=ts.options_anomaly,
        signal_breakdown=ts.signal_breakdown,
        scored_at=ts.scored_at,
        thesis=ts.thesis,
        watch_for=ts.watch_for,
        confidence=ts.confidence,
        synthesized_at=ts.synthesized_at,
    )


def _theme_out(theme) -> ThemeOut:
    bd = (theme.score.signal_breakdown or {}) if theme.score else {}
    top = (bd.get("buying_tickers") or [])[:5]
    if not top:
        top = [tt.symbol for tt in (theme.tickers or [])[:5]]
    return ThemeOut(
        id=theme.id,
        name=theme.name,
        slug=theme.slug,
        description=theme.description,
        category=theme.category,
        benchmark_etf=theme.benchmark_etf,
        score=_score_out(theme.score),
        top_tickers=top,
    )


# ---------------------------------------------------------------------------
# Theme list + trending + cooling  (PUBLIC — no auth required)
# ---------------------------------------------------------------------------

@router.get("/")
async def list_themes(db=Depends(get_db)):
    themes = await repo.get_all_themes(db)
    last_scored = max(
        (t.score.scored_at for t in themes if t.score and t.score.scored_at),
        default=None,
    )
    return build_response(ThemeListResponse(
        themes=[_theme_out(t) for t in themes],
        last_scored_at=last_scored,
    ).model_dump())


@router.get("/trending")
async def trending_themes(db=Depends(get_db)):
    themes = await repo.get_trending_themes(db)
    return build_response({"themes": [_theme_out(t).model_dump() for t in themes]})


@router.get("/cooling")
async def cooling_themes(db=Depends(get_db)):
    themes = await repo.get_cooling_themes(db)
    return build_response({"themes": [_theme_out(t).model_dump() for t in themes]})


# ---------------------------------------------------------------------------
# Signal feeds (PUBLIC)
# ---------------------------------------------------------------------------

@router.get("/signals/insider")
async def insider_signals(days: int = 14, db=Depends(get_db)):
    filings = await repo.get_insider_feed(db, days=days)
    return build_response({
        "signals": [
            InsiderSignalOut(
                symbol=f.symbol,
                issuer_name=f.issuer_name,
                insider_name=f.insider_name,
                insider_title=f.insider_title,
                transaction_type=f.transaction_type.value,
                total_value=f.total_value,
                is_congress=f.is_congress,
                filing_date=f.filing_date,
            ).model_dump() for f in filings
        ]
    })


@router.get("/signals/congress")
async def congress_signals(days: int = 45, db=Depends(get_db)):
    filings = await repo.get_congress_feed(db, days=days)
    return build_response({
        "signals": [
            InsiderSignalOut(
                symbol=f.symbol,
                issuer_name=f.issuer_name,
                insider_name=f.insider_name,
                insider_title=f.insider_title,
                transaction_type=f.transaction_type.value,
                total_value=f.total_value,
                is_congress=True,
                filing_date=f.filing_date,
            ).model_dump() for f in filings
        ]
    })


@router.get("/signals/contracts")
async def contract_signals(days: int = 30, db=Depends(get_db)):
    contracts = await repo.get_contract_feed(db, days=days)
    return build_response({
        "signals": [
            ContractSignalOut(
                recipient_name=c.recipient_name,
                symbol=c.symbol,
                award_amount=c.award_amount,
                agency_name=c.agency_name,
                description=c.description,
                award_date=c.award_date,
                theme_id=c.theme_id,
            ).model_dump() for c in contracts
        ]
    })


# ---------------------------------------------------------------------------
# Theme detail + history (PUBLIC)
# ---------------------------------------------------------------------------

@router.get("/{slug}")
async def theme_detail(slug: str, db=Depends(get_db)):
    theme = await repo.get_theme_by_slug(db, slug)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    history = await repo.get_theme_history(db, theme.id)

    return build_response(ThemeDetailOut(
        id=theme.id,
        name=theme.name,
        slug=theme.slug,
        description=theme.description,
        category=theme.category,
        benchmark_etf=theme.benchmark_etf,
        score=_score_out(theme.score),
        top_tickers=((theme.score.signal_breakdown or {}).get("buying_tickers") or [])[:5] if theme.score else [],
        tickers=[TickerOut(
            symbol=tt.symbol,
            company_name=tt.company_name,
            market_cap_tier=tt.market_cap_tier,
        ) for tt in (theme.tickers or []) if tt.is_active],
        history=[HistoryPoint(
            scored_at=h.scored_at,
            score=h.score,
            velocity=h.velocity,
            lifecycle_stage=h.lifecycle_stage,
        ) for h in history],
    ).model_dump())


@router.get("/{slug}/history")
async def theme_history(slug: str, weeks: int = 12, db=Depends(get_db)):
    theme = await repo.get_theme_by_slug(db, slug)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    history = await repo.get_theme_history(db, theme.id, weeks=weeks)
    return build_response({
        "history": [
            HistoryPoint(
                scored_at=h.scored_at,
                score=h.score,
                velocity=h.velocity,
                lifecycle_stage=h.lifecycle_stage,
            ).model_dump() for h in history
        ]
    })


# ---------------------------------------------------------------------------
# Pipeline endpoint (PUBLIC — triggers on-demand full data run)
# ---------------------------------------------------------------------------

@router.get("/pipeline/status")
async def pipeline_status(redis=Depends(get_redis)):
    result = await get_pipeline_status(redis)
    return build_response(result)


@router.post("/pipeline/run")
async def pipeline_run(redis=Depends(get_redis)):
    result = await trigger_pipeline(redis)
    return build_response(result)


# ---------------------------------------------------------------------------
# Sync endpoints (AUTH REQUIRED — prevents abuse)
# ---------------------------------------------------------------------------

@router.get("/sync/status")
async def sync_status(
    _=Depends(get_current_user),
    redis=Depends(get_redis),
):
    result = await get_sync_status(redis)
    return build_response(result.model_dump())


@router.post("/sync")
async def sync(
    body: SyncTriggerRequest,
    _=Depends(get_current_user),
    redis=Depends(get_redis),
):
    triggered, skipped = await trigger_sync(redis, body.source)
    return build_response(
        SyncTriggerResponse(triggered=triggered, skipped=skipped).model_dump()
    )


# ---------------------------------------------------------------------------
# Watchlist endpoints (AUTH REQUIRED)
# ---------------------------------------------------------------------------

@router.get("/watchlist")
async def get_watchlist(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    items = await repo.get_user_watchlist(db, current_user.id)
    return build_response(WatchlistResponse(items=[
        WatchlistItem(
            theme_id=item.theme_id,
            slug=item.theme.slug,
            name=item.theme.name,
            added_at=item.added_at,
        ) for item in items
    ]).model_dump())


@router.post("/watchlist/{slug}")
async def add_to_watchlist(
    slug: str,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    theme = await repo.get_theme_by_slug(db, slug)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    added = await repo.add_to_watchlist(db, current_user.id, theme.id)
    return build_response(WatchlistAddResponse(
        theme_id=theme.id,
        slug=theme.slug,
        added=added,
    ).model_dump())


@router.delete("/watchlist/{slug}")
async def remove_from_watchlist(
    slug: str,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    theme = await repo.get_theme_by_slug(db, slug)
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    await repo.remove_from_watchlist(db, current_user.id, theme.id)
    return build_response({"removed": True})
