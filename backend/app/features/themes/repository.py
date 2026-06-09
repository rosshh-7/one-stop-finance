from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.theme import Theme, ThemeScore


async def get_all_theme_scores(db: AsyncSession) -> list[dict]:
    stmt = (
        select(Theme)
        .where(Theme.is_active == True)
        .options(selectinload(Theme.score))
        .order_by(Theme.name)
    )
    result = await db.execute(stmt)
    themes = result.scalars().all()

    rows = []
    for theme in themes:
        ts: ThemeScore | None = theme.score
        score = ts.score if ts else 0.0
        level = ts.level.value if ts else "quiet"
        unique_cos = ts.unique_companies_buying if ts else 0
        total_val = ts.total_value_accumulated if ts else 0.0
        scored_at = ts.scored_at if ts else None

        # Derive primary signal label from signal_breakdown
        primary = _primary_signal(ts)

        rows.append({
            "name": theme.name,
            "slug": theme.slug,
            "benchmark_etf": theme.benchmark_etf,
            "score": round(score, 1),
            "level": level,
            "unique_companies_buying": unique_cos,
            "total_value_accumulated": total_val,
            "primary_signal": primary,
            "scored_at": scored_at.isoformat() if scored_at else None,
        })

    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


def _primary_signal(ts: ThemeScore | None) -> str:
    if ts is None:
        return "none"
    if ts.csuite_count and ts.csuite_count > 0:
        return "c-suite buys"
    if ts.unusual_options_count and ts.unusual_options_count > 0:
        return "unusual options"
    if ts.congress_signal:
        return "congress"
    if ts.sentiment_signal:
        return "sentiment"
    if ts.unique_companies_buying and ts.unique_companies_buying > 0:
        return "insider buys"
    return "none"
