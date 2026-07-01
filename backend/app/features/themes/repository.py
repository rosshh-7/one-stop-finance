from datetime import datetime, timedelta, timezone

from sqlalchemy import select, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.theme import Theme, ThemeScore, ThemeScoreHistory, GovContract, UserThemeWatchlist
from app.models.insider import InsiderFiling, TransactionType
from app.models.base import new_uuid


async def get_all_themes(db: AsyncSession) -> list[Theme]:
    result = await db.execute(
        select(Theme)
        .where(Theme.is_active == True)
        .outerjoin(ThemeScore, Theme.id == ThemeScore.theme_id)
        .order_by(desc(ThemeScore.score))
    )
    return list(result.scalars().unique().all())


async def get_theme_by_slug(db: AsyncSession, slug: str) -> Theme | None:
    result = await db.execute(
        select(Theme).where(Theme.slug == slug, Theme.is_active == True)
    )
    return result.scalar_one_or_none()


async def get_trending_themes(db: AsyncSession, limit: int = 5) -> list[Theme]:
    result = await db.execute(
        select(Theme)
        .join(ThemeScore, Theme.id == ThemeScore.theme_id)
        .where(Theme.is_active == True)
        .where(ThemeScore.velocity > 0)
        .where(ThemeScore.score > 20)
        .order_by(desc(ThemeScore.velocity))
        .limit(limit)
    )
    return list(result.scalars().unique().all())


async def get_cooling_themes(db: AsyncSession) -> list[Theme]:
    result = await db.execute(
        select(Theme)
        .join(ThemeScore, Theme.id == ThemeScore.theme_id)
        .where(Theme.is_active == True)
        .where(ThemeScore.lifecycle_stage == "COOLING")
        .order_by(ThemeScore.velocity)
    )
    return list(result.scalars().unique().all())


async def get_theme_history(
    db: AsyncSession,
    theme_id: str,
    weeks: int = 12,
) -> list[ThemeScoreHistory]:
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    result = await db.execute(
        select(ThemeScoreHistory)
        .where(ThemeScoreHistory.theme_id == theme_id)
        .where(ThemeScoreHistory.scored_at >= cutoff)
        .order_by(ThemeScoreHistory.scored_at)
    )
    return list(result.scalars().all())


async def get_insider_feed(
    db: AsyncSession,
    days: int = 14,
    limit: int = 50,
) -> list[InsiderFiling]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(InsiderFiling)
        .where(InsiderFiling.filing_date >= cutoff)
        .where(InsiderFiling.transaction_type.in_([TransactionType.BUY, TransactionType.SELL]))
        .where(InsiderFiling.is_open_market == True)
        .order_by(desc(InsiderFiling.filing_date))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_congress_feed(
    db: AsyncSession,
    days: int = 45,
    limit: int = 50,
) -> list[InsiderFiling]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(InsiderFiling)
        .where(InsiderFiling.filing_date >= cutoff)
        .where(InsiderFiling.is_congress == True)
        .order_by(desc(InsiderFiling.filing_date))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_contract_feed(
    db: AsyncSession,
    days: int = 30,
    limit: int = 50,
) -> list[GovContract]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(GovContract)
        .where(GovContract.award_date >= cutoff)
        .order_by(desc(GovContract.award_date))
        .limit(limit)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Watchlist repository functions
# ---------------------------------------------------------------------------

async def get_user_watchlist(db: AsyncSession, user_id: str) -> list[UserThemeWatchlist]:
    result = await db.execute(
        select(UserThemeWatchlist)
        .where(UserThemeWatchlist.user_id == user_id)
        .order_by(desc(UserThemeWatchlist.added_at))
    )
    return list(result.scalars().all())


async def add_to_watchlist(db: AsyncSession, user_id: str, theme_id: str) -> bool:
    existing = (await db.execute(
        select(UserThemeWatchlist)
        .where(UserThemeWatchlist.user_id == user_id)
        .where(UserThemeWatchlist.theme_id == theme_id)
    )).scalar_one_or_none()
    if existing:
        return False
    db.add(UserThemeWatchlist(
        id=new_uuid(),
        user_id=user_id,
        theme_id=theme_id,
        added_at=datetime.now(timezone.utc),
    ))
    await db.commit()
    return True


async def remove_from_watchlist(db: AsyncSession, user_id: str, theme_id: str) -> None:
    await db.execute(
        delete(UserThemeWatchlist)
        .where(UserThemeWatchlist.user_id == user_id)
        .where(UserThemeWatchlist.theme_id == theme_id)
    )
    await db.commit()
