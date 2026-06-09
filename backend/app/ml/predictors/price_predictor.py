"""
Heuristic price direction predictor using weighted signal scoring.

Each feature score is in [-1, +1] where +1 = fully bullish, -1 = fully bearish.
The weighted sum → direction label + confidence percentage.

Replace score() with a real sklearn/XGBoost model in Phase 3+.
"""

from typing import Literal

SIGNAL_WEIGHTS: dict[str, tuple[float, str]] = {
    "pcr_score":       (0.25, "Put/Call Ratio"),
    "rsi_score":       (0.20, "RSI"),
    "macd_score":      (0.15, "MACD"),
    "max_pain_diff":   (0.18, "Max Pain Pull"),
    "price_vs_sma20":  (0.10, "Price vs 20-Day MA"),
    "price_vs_sma50":  (0.07, "Price vs 50-Day MA"),
    "gex_score":       (0.05, "Gamma Exposure"),
}


def score(features: dict[str, float]) -> dict:
    weighted_sum = 0.0
    total_weight = 0.0
    signals = []

    for key, (weight, label) in SIGNAL_WEIGHTS.items():
        if key not in features:
            continue
        val = features[key]
        weighted_sum += val * weight
        total_weight += weight

        direction: Literal["bullish", "bearish", "neutral"] = (
            "bullish" if val > 0.1 else "bearish" if val < -0.1 else "neutral"
        )
        signals.append({
            "name": label,
            "raw_value": round(val, 4),
            "display_value": _display(key, val, features),
            "direction": direction,
            "weight": weight,
        })

    if total_weight == 0:
        return {"direction": "neutral", "confidence": 0.0, "bull_score": 0.0, "bear_score": 0.0, "signals": []}

    normalised = weighted_sum / total_weight  # -1 to +1

    bull_score = round(max(0, normalised) * 100, 1)
    bear_score = round(max(0, -normalised) * 100, 1)
    confidence = round(abs(normalised) * 100, 1)

    if normalised > 0.15:
        direction = "bullish"
    elif normalised < -0.15:
        direction = "bearish"
    else:
        direction = "neutral"

    return {
        "direction": direction,
        "confidence": confidence,
        "bull_score": bull_score,
        "bear_score": bear_score,
        "signals": signals,
    }


def _display(key: str, val: float, feats: dict) -> str:
    if key == "pcr_score":
        # back-calculate approximate PCR
        pcr = round(1.0 - val * 0.5, 2)
        return f"PCR {pcr}"
    if key == "rsi_score":
        rsi = round(50 - val * 30, 1)
        return f"RSI {rsi}"
    if key == "macd_score":
        return "MACD above signal" if val > 0 else "MACD below signal"
    if key == "max_pain_diff":
        pct = round(val * 10, 2)
        return f"{'+' if pct >= 0 else ''}{pct}% from max pain"
    if key in ("price_vs_sma20", "price_vs_sma50"):
        pct = round(val * 5, 2)
        ma = "20d" if "20" in key else "50d"
        return f"{'+' if pct >= 0 else ''}{pct}% vs {ma} MA"
    if key == "gex_score":
        return "Positive GEX (pinning)" if val > 0 else "Negative GEX (volatile)"
    return str(round(val, 3))
