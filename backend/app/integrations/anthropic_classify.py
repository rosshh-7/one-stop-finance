"""
Claude Haiku ticker → theme classifier.

Given a company profile and the list of available themes, returns the slugs
the ticker belongs to (0 or more). Uses the Anthropic Messages API directly
via httpx — no SDK dependency.
"""
import json
import logging

import httpx

logger = logging.getLogger(__name__)

_API_URL = "https://api.anthropic.com/v1/messages"
_MODEL = "claude-haiku-4-5-20251001"
_VERSION = "2023-06-01"


def _build_prompt(profile: dict, themes: list[dict]) -> str:
    theme_list = "\n".join(
        f"- {t['slug']}: {t['name']} — {t.get('description', '')}"
        for t in themes
    )
    return (
        "You are classifying a public company into investment themes.\n\n"
        f"AVAILABLE THEMES (slug: name — description):\n{theme_list}\n\n"
        "COMPANY:\n"
        f"  Symbol:      {profile['symbol']}\n"
        f"  Name:        {profile['company_name']}\n"
        f"  Sector:      {profile['sector']}\n"
        f"  Industry:    {profile['industry']}\n"
        f"  Description: {profile['description']}\n\n"
        "Return ONLY a JSON array of theme slugs the company genuinely belongs to.\n"
        "Pick 0–3 themes. If no theme fits, return an empty array `[]`.\n"
        "Do NOT include explanation, markdown, or any text outside the JSON array.\n"
        "Example responses: [\"semiconductors\"] or [\"ai-infrastructure\",\"cloud-saas\"] or []"
    )


async def classify_ticker(
    profile: dict,
    themes: list[dict],
    api_key: str,
) -> list[str]:
    """
    Returns the list of theme slugs the ticker matches (possibly empty).
    Returns [] on any API/parse error — classification failures should not
    crash the sync.
    """
    if not api_key or not profile:
        return []

    payload = {
        "model": _MODEL,
        "max_tokens": 120,
        "messages": [
            {"role": "user", "content": _build_prompt(profile, themes)}
        ],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": _VERSION,
        "content-type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(_API_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.debug("Haiku classify failed for %s: %s", profile.get("symbol"), exc)
        return []

    try:
        blocks = data.get("content") or []
        raw_text = next((b.get("text", "") for b in blocks if b.get("type") == "text"), "")
        raw_text = raw_text.strip()
        # Strip code fences if Haiku decides to add them despite instructions
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.lower().startswith("json"):
                raw_text = raw_text[4:]
            raw_text = raw_text.strip()
        slugs = json.loads(raw_text)
        if not isinstance(slugs, list):
            return []
        valid = {t["slug"] for t in themes}
        return [s for s in slugs if isinstance(s, str) and s in valid][:3]
    except Exception as exc:
        logger.debug("Haiku response parse failed for %s: %s", profile.get("symbol"), exc)
        return []
