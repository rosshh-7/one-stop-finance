"""
Claude Sonnet theme synthesis worker.

Runs daily for all themes with score > 45.
Generates a 2-3 sentence plain-language thesis, a confirmation signal to watch
next week, and a confidence level.

Uses claude-sonnet-4-6 for quality — Haiku is reserved for high-volume
ticker classification. These 25 outputs are user-facing and directly affect
trust in the platform.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

import httpx

from app.celery_app import celery
from app.config import settings
from app.database import celery_session
from app.models.theme import Theme, ThemeScore

logger = logging.getLogger(__name__)

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_MODEL = "claude-sonnet-4-6"
_MIN_SCORE = 45.0


def _build_prompt(theme_name: str, score: float, breakdown: dict) -> str:
    signals = []
    if breakdown.get("buying_tickers"):
        tickers = ", ".join(breakdown["buying_tickers"][:5])
        signals.append(f"Insider buying: {breakdown.get('unique_companies_buying', 0)} companies ({tickers})")
    if breakdown.get("total_usd", 0) > 0:
        usd_m = breakdown["total_usd"] / 1_000_000
        signals.append(f"Total accumulated: ${usd_m:.1f}M")
    if breakdown.get("csuite_count", 0) > 0:
        signals.append(f"C-suite buyers: {breakdown['csuite_count']}")
    if breakdown.get("congress_tickers"):
        signals.append(f"Congressional trades: {', '.join(breakdown['congress_tickers'][:3])}")
    if breakdown.get("contracts_count", 0) > 0:
        signals.append(f"Government contracts: {breakdown['contracts_count']} in last 30 days")
    if (breakdown.get("etf_vol_ratio") or 0) >= 1.5:
        signals.append(f"ETF volume anomaly: {breakdown['etf_vol_ratio']:.1f}x 30-day avg")
    if (breakdown.get("etf_put_call_ratio") or 0) < 0.75:
        signals.append(f"Options positioning: put/call ratio {breakdown['etf_put_call_ratio']:.2f} (bullish)")
    if (breakdown.get("sentiment_score") or 0) >= 0.2:
        signals.append(f"News sentiment: positive ({breakdown['sentiment_score']:.2f})")
    if breakdown.get("activist_stake_count", 0) > 0:
        signals.append(f"Activist stakes (13D/G): {breakdown['activist_stake_count']} new filings")
    if breakdown.get("institutional_new_positions", 0) > 0:
        signals.append(f"New institutional positions (13F): {breakdown['institutional_new_positions']}")
    if breakdown.get("ai_ecosystem_count", 0) > 0:
        signals.append(f"AI ecosystem deals (8-K/Form D): {breakdown['ai_ecosystem_count']}")
    if breakdown.get("short_high_and_buying"):
        signals.append("Short squeeze setup: high short interest + insider buying detected")
    if breakdown.get("nih_grant_count", 0) > 0:
        signals.append(f"NIH grants: {breakdown['nih_grant_count']} recent awards")

    signals_text = "\n".join(f"- {s}" for s in signals) if signals else "- No major signals this period"

    return f"""You are a financial analyst writing concise theme intelligence summaries for sophisticated investors.

Theme: {theme_name}
Convergence Score: {score:.0f}/100
Active Signals:
{signals_text}

Write a JSON response with exactly these three fields:
- "thesis": 2-3 sentences explaining WHY multiple independent signals are converging on this theme right now. Be specific about the signals. No generic statements.
- "watch_for": One specific confirmation signal investors should look for in the next 7-14 days (an earnings report, a contract announcement, an ETF flow threshold, etc.)
- "confidence": exactly one of "high", "medium", or "low" — high means 4+ independent signals, medium means 2-3, low means 1.

Respond with only valid JSON, no markdown, no explanation."""


async def _synthesize_one(theme_name: str, score: float, breakdown: dict, api_key: str) -> dict | None:
    prompt = _build_prompt(theme_name, score, breakdown)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _ANTHROPIC_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": _MODEL,
                    "max_tokens": 400,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            content = resp.json()["content"][0]["text"].strip()
            # Strip possible code fences
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            parsed = json.loads(content)
            return {
                "thesis": str(parsed.get("thesis", ""))[:1000],
                "watch_for": str(parsed.get("watch_for", ""))[:500],
                "confidence": parsed.get("confidence", "medium") if parsed.get("confidence") in ("high", "medium", "low") else "medium",
            }
    except Exception as exc:
        logger.warning("synthesis failed for %s: %s", theme_name, exc)
        return None


async def _run_synthesis() -> int:
    api_key = settings.anthropic_api_key
    if not api_key:
        logger.info("synthesize_themes: ANTHROPIC_API_KEY not set — skipping")
        return 0

    now = datetime.now(timezone.utc)
    updated = 0

    async with celery_session() as session:
        from sqlalchemy import select
        scores = (await session.execute(
            select(ThemeScore)
            .join(Theme, ThemeScore.theme_id == Theme.id)
            .where(Theme.is_active == True)
            .where(ThemeScore.score >= _MIN_SCORE)
        )).scalars().all()

        # Load theme names
        theme_ids = [s.theme_id for s in scores]
        themes = (await session.execute(
            select(Theme).where(Theme.id.in_(theme_ids))
        )).scalars().all()
        theme_name_map = {t.id: t.name for t in themes}

        for score_row in scores:
            theme_name = theme_name_map.get(score_row.theme_id, "Unknown Theme")
            breakdown = score_row.signal_breakdown or {}

            result = await _synthesize_one(theme_name, score_row.score, breakdown, api_key)
            if result:
                score_row.thesis = result["thesis"]
                score_row.watch_for = result["watch_for"]
                score_row.confidence = result["confidence"]
                score_row.synthesized_at = now
                updated += 1

        await session.commit()
    return updated


@celery.task(name="app.workers.synthesis.synthesize_themes")
def synthesize_themes():
    logger.info("synthesize_themes: starting")
    count = asyncio.run(_run_synthesis())
    logger.info("synthesize_themes: synthesized %d themes", count)
