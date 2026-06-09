"""
Central feature flag config.
Change "free" → "pro" for any feature to gate it behind a Pro subscription.
No other code changes needed — require_feature() and ProGate read from here.
"""

FEATURE_FLAGS: dict[str, str] = {
    "theme_intelligence":  "free",
    "options_chain":       "free",
    "insider_trades":      "free",
    "sentiment_analysis":  "free",
    "trend_reversal":      "free",
    "onchain_prediction":  "free",
}


def get_required_tier(feature: str) -> str:
    return FEATURE_FLAGS.get(feature, "pro")
