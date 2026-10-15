from __future__ import annotations

import numpy as np
import pandas as pd

from binary_intelligence_ai.data.contracts import Candle


def build_feature_frame(candles: list[Candle] | tuple[Candle, ...]) -> pd.DataFrame:
    """Calcula features causais; cada linha usa somente ela própria e linhas anteriores."""

    if not candles:
        return pd.DataFrame()

    frame = pd.DataFrame([
        {
            "asset": candle.asset,
            "timeframe": candle.timeframe.value,
            "source": candle.source,
            "open_time": candle.open_time,
            "close_time": candle.close_time,
            "open": float(candle.open),
            "high": float(candle.high),
            "low": float(candle.low),
            "close": float(candle.close),
            "volume": float(candle.volume) if candle.volume is not None else np.nan,
        }
        for candle in candles
    ]).set_index("open_time", drop=False)

    close = frame["close"]
    high = frame["high"]
    low = frame["low"]
    previous_close = close.shift(1)

    frame["return_1"] = close.pct_change(fill_method=None)
    frame["sma_5"] = close.rolling(5, min_periods=5).mean()
    frame["sma_20"] = close.rolling(20, min_periods=20).mean()
    frame["ema_12"] = close.ewm(span=12, adjust=False, min_periods=12).mean()
    frame["ema_26"] = close.ewm(span=26, adjust=False, min_periods=26).mean()
    frame["macd"] = frame["ema_12"] - frame["ema_26"]
    frame["macd_signal"] = frame["macd"].ewm(span=9, adjust=False, min_periods=9).mean()
    frame["macd_histogram"] = frame["macd"] - frame["macd_signal"]

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    average_loss = loss.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + relative_strength))
    frame["rsi_14"] = rsi.mask((average_loss == 0) & (average_gain > 0), 100).mask(
        (average_loss == 0) & (average_gain == 0), 50
    )

    true_range = pd.concat(
        [(high - low), (high - previous_close).abs(), (low - previous_close).abs()], axis=1
    ).max(axis=1)
    frame["atr_14"] = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    frame["atr_pct"] = frame["atr_14"] / close

    upward_move = high.diff()
    downward_move = -low.diff()
    plus_dm = upward_move.where((upward_move > downward_move) & (upward_move > 0), 0.0)
    minus_dm = downward_move.where((downward_move > upward_move) & (downward_move > 0), 0.0)
    smoothed_tr = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / smoothed_tr
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / smoothed_tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    frame["adx_14"] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

    middle = close.rolling(20, min_periods=20).mean()
    deviation = close.rolling(20, min_periods=20).std(ddof=0)
    frame["bollinger_middle_20"] = middle
    frame["bollinger_upper_20"] = middle + 2 * deviation
    frame["bollinger_lower_20"] = middle - 2 * deviation
    frame["bollinger_width"] = (frame["bollinger_upper_20"] - frame["bollinger_lower_20"]) / middle

    frame["support_20"] = low.rolling(20, min_periods=20).min().shift(1)
    frame["resistance_20"] = high.rolling(20, min_periods=20).max().shift(1)
    frame["distance_to_support_atr"] = (close - frame["support_20"]) / frame["atr_14"]
    frame["distance_to_resistance_atr"] = (frame["resistance_20"] - close) / frame["atr_14"]
    frame["breakout_up"] = (close > frame["resistance_20"]).astype(float).where(frame["resistance_20"].notna())
    frame["breakout_down"] = (close < frame["support_20"]).astype(float).where(frame["support_20"].notna())
    previous_resistance = frame["resistance_20"].shift(1)
    previous_support = frame["support_20"].shift(1)
    frame["false_breakout_up"] = (
        (frame["breakout_up"].shift(1) == 1) & (close <= previous_resistance)
    ).astype(float).where(previous_resistance.notna())
    frame["false_breakout_down"] = (
        (frame["breakout_down"].shift(1) == 1) & (close >= previous_support)
    ).astype(float).where(previous_support.notna())
    ema_ready = frame["ema_12"].notna() & frame["ema_26"].notna()
    frame["pullback_up"] = (
        (frame["ema_12"] > frame["ema_26"]) & (low <= frame["ema_12"]) & (close > frame["ema_12"])
    ).astype(float).where(ema_ready)
    frame["pullback_down"] = (
        (frame["ema_12"] < frame["ema_26"]) & (high >= frame["ema_12"]) & (close < frame["ema_12"])
    ).astype(float).where(ema_ready)
    prior_exists = high.shift(1).notna()
    frame["higher_high"] = (high > high.shift(1)).astype(float).where(prior_exists)
    frame["higher_low"] = (low > low.shift(1)).astype(float).where(prior_exists)
    frame["lower_high"] = (high < high.shift(1)).astype(float).where(prior_exists)
    frame["lower_low"] = (low < low.shift(1)).astype(float).where(prior_exists)
    frame["bullish_structure_5"] = (frame["higher_high"] + frame["higher_low"]).rolling(5, min_periods=5).sum()
    frame["bearish_structure_5"] = (frame["lower_high"] + frame["lower_low"]).rolling(5, min_periods=5).sum()
    frame["ema_spread_atr"] = (frame["ema_12"] - frame["ema_26"]) / frame["atr_14"]

    candle_range = (high - low).replace(0, np.nan)
    body = close - frame["open"]
    frame["candle_body_ratio"] = body.abs() / candle_range
    frame["upper_wick_ratio"] = (high - pd.concat([frame["open"], close], axis=1).max(axis=1)) / candle_range
    frame["lower_wick_ratio"] = (pd.concat([frame["open"], close], axis=1).min(axis=1) - low) / candle_range
    frame["candle_direction"] = np.sign(body).astype(int)
    frame["is_doji"] = (frame["candle_body_ratio"] <= 0.1).astype(float).where(candle_range.notna())

    frame["atr_pct_q20"] = frame["atr_pct"].rolling(100, min_periods=50).quantile(0.2)
    frame["atr_pct_q80"] = frame["atr_pct"].rolling(100, min_periods=50).quantile(0.8)
    return frame
