"""
Lightweight headline sentiment scorer — no ML deps, no external API.

`score_headlines` returns a value in roughly [-1, +1] using a weighted
positive/negative keyword count, normalised by headline count.

Good enough for theme-level aggregate sentiment; not intended as a
sentence-level classifier.
"""
import re

_POSITIVE_WORDS = {
    "surge", "soar", "rally", "gain", "beat", "record", "growth",
    "boost", "jump", "rise", "strong", "bullish", "upside", "outperform",
    "award", "contract", "upgrade", "expand", "invest", "breakthrough",
    "win", "exceed", "profit", "revenue", "demand", "partnership",
    "accelerate", "momentum", "milestone", "deal", "approve", "launch",
}

_NEGATIVE_WORDS = {
    "drop", "fall", "decline", "loss", "miss", "warn", "cut", "downgrade",
    "slump", "plunge", "bearish", "downside", "underperform", "layoff",
    "recall", "fine", "penalty", "lawsuit", "investigation", "probe",
    "delay", "risk", "concern", "weak", "disappoint", "shortage",
    "halt", "slowdown", "default", "writedown", "scandal",
}

_TOKEN_RE = re.compile(r"[a-zA-Z']+")


def _score_one(headline: str) -> int:
    tokens = {t.lower() for t in _TOKEN_RE.findall(headline or "")}
    pos = len(tokens & _POSITIVE_WORDS)
    neg = len(tokens & _NEGATIVE_WORDS)
    return pos - neg


def score_headlines(headlines: list[str]) -> dict:
    """
    Returns {score: float in [-1,1], headlines_count: int, pos_hits: int, neg_hits: int}.
    Score is normalised by headline count so a few strong headlines don't
    drown out a longer feed of neutral noise.
    """
    if not headlines:
        return {"score": 0.0, "headlines_count": 0, "pos_hits": 0, "neg_hits": 0}

    raw = [_score_one(h) for h in headlines]
    pos_hits = sum(s for s in raw if s > 0)
    neg_hits = sum(-s for s in raw if s < 0)
    net = sum(raw) / len(raw)
    # Squash to [-1, 1]
    score = max(-1.0, min(1.0, net / 2.0))
    return {
        "score":           round(score, 3),
        "headlines_count": len(headlines),
        "pos_hits":        pos_hits,
        "neg_hits":        neg_hits,
    }
