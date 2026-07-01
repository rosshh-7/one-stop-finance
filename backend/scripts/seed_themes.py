"""
Seed all 25 themes and their tickers from theme_config.py into the database.

Usage (inside the api container or with DB accessible):
    cd backend && python -m scripts.seed_themes

Idempotent — safe to run multiple times.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import async_session_factory
from app.models.base import new_uuid
from app.models.theme import Theme, ThemeTicker, ThemeScore, ConvergenceLevel
from app.theme_config import THEME_CONFIG


async def seed():
    async with async_session_factory() as session:
        added_themes = added_tickers = added_scores = 0

        for cfg in THEME_CONFIG:
            # Upsert theme
            existing = (await session.execute(
                select(Theme).where(Theme.slug == cfg["slug"])
            )).scalar_one_or_none()

            if existing:
                existing.name = cfg["name"]
                existing.description = cfg["description"]
                existing.category = cfg["category"]
                existing.benchmark_etf = cfg["benchmark_etf"]
                existing.is_active = True
                theme = existing
            else:
                theme = Theme(
                    id=new_uuid(),
                    name=cfg["name"],
                    slug=cfg["slug"],
                    description=cfg["description"],
                    category=cfg["category"],
                    benchmark_etf=cfg["benchmark_etf"],
                    is_active=True,
                )
                session.add(theme)
                await session.flush()
                added_themes += 1

            # Seed empty ThemeScore row if missing
            score_row = (await session.execute(
                select(ThemeScore).where(ThemeScore.theme_id == theme.id)
            )).scalar_one_or_none()

            if not score_row:
                session.add(ThemeScore(
                    id=new_uuid(),
                    theme_id=theme.id,
                    score=0.0,
                    level=ConvergenceLevel.QUIET,
                    unique_companies_buying=0,
                    unique_companies_selling=0,
                    total_value_accumulated=0.0,
                    csuite_count=0,
                    congress_signal=False,
                    unusual_options_count=False,
                    sentiment_signal=False,
                    contracts_count=0,
                    velocity=0.0,
                    lifecycle_stage="STABLE",
                ))
                added_scores += 1

            # Upsert tickers
            existing_syms = {
                tt.symbol for tt in (await session.execute(
                    select(ThemeTicker).where(ThemeTicker.theme_id == theme.id)
                )).scalars().all()
            }

            for ticker_cfg in cfg["tickers"]:
                if ticker_cfg["symbol"] not in existing_syms:
                    session.add(ThemeTicker(
                        id=new_uuid(),
                        theme_id=theme.id,
                        symbol=ticker_cfg["symbol"],
                        company_name=ticker_cfg["company_name"],
                        market_cap_tier=ticker_cfg["market_cap_tier"],
                        is_active=True,
                    ))
                    added_tickers += 1

        await session.commit()
        print(
            f"Seed complete — {added_themes} themes added, "
            f"{added_tickers} tickers added, "
            f"{added_scores} score rows added"
        )
        print(f"Total themes configured: {len(THEME_CONFIG)}")


if __name__ == "__main__":
    asyncio.run(seed())
