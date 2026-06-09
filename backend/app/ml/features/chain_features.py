"""
Feature engineering for the options chain price predictor.
Converts raw options snapshot + OHLCV into a normalised feature dict.
"""

import pandas as pd


def build_features(options: dict | None, ohlcv: pd.DataFrame | None) -> dict:
    feats: dict[str, float] = {}

    close = _extract_close(ohlcv)

    if options:
        pcr = options.get("put_call_ratio", 1.0)
        feats["pcr_score"] = _clamp((1.0 - pcr) / 0.5, -1, 1)

        feats["iv_skew"] = options.get("avg_put_iv", 30) - options.get("avg_call_iv", 30)

        max_pain = options.get("max_pain")
        if close is not None and max_pain:
            price = float(close.iloc[-1])
            feats["max_pain_diff"] = _clamp((max_pain - price) / price * 10, -1, 1)
        else:
            feats["max_pain_diff"] = 0.0

        gex = options.get("net_gex", 0)
        feats["gex_score"] = 1.0 if gex > 0 else -0.5

    if close is not None and len(close) >= 20:
        rsi = _rsi(close, 14)
        feats["rsi_score"] = _clamp((50 - rsi) / 30, -1, 1)

        macd, signal = _macd(close)
        feats["macd_score"] = 1.0 if macd > signal else -1.0

        sma20 = float(close.rolling(20).mean().iloc[-1])
        price = float(close.iloc[-1])
        feats["price_vs_sma20"] = _clamp((price - sma20) / sma20 * 20, -1, 1)

        if len(close) >= 50:
            sma50 = float(close.rolling(50).mean().iloc[-1])
            feats["price_vs_sma50"] = _clamp((price - sma50) / sma50 * 20, -1, 1)

        volume = _extract_column(ohlcv, "Volume")
        if volume is not None and len(volume) >= 20:
            vol_avg = float(volume.rolling(20).mean().iloc[-1])
            last_vol = float(volume.iloc[-1])
            if vol_avg > 0:
                feats["volume_ratio"] = _clamp((last_vol / vol_avg - 1), -1, 1)

    return feats


def _extract_close(ohlcv: pd.DataFrame | None) -> pd.Series | None:
    return _extract_column(ohlcv, "Close")


def _extract_column(ohlcv: pd.DataFrame | None, col: str) -> pd.Series | None:
    if ohlcv is None or ohlcv.empty:
        return None
    try:
        # yfinance may return multi-level columns: (field, ticker)
        if isinstance(ohlcv.columns, pd.MultiIndex):
            series = ohlcv[col].squeeze()
        else:
            series = ohlcv[col]
        return series.dropna()
    except (KeyError, Exception):
        return None


def _rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def _macd(series: pd.Series) -> tuple[float, float]:
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1])


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))
