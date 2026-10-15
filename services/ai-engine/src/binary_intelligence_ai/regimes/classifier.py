from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class MarketRegime(StrEnum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    INSUFFICIENT_DATA = "insufficient_data"


class VolatilityState(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    INSUFFICIENT_DATA = "insufficient_data"


class MarketState(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset: str
    timeframe: str
    as_of: datetime
    regime: MarketRegime
    volatility: VolatilityState
    trend_strength: float | None = Field(default=None, ge=0, le=100)
    previous_regime: MarketRegime | None = None
    regime_changed: bool = False
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RegimeConfig:
    adx_trend_threshold: float = 25.0


def classify_latest(frame: pd.DataFrame, config: RegimeConfig = RegimeConfig()) -> MarketState:
    if frame.empty:
        raise ValueError("feature frame cannot be empty")
    latest = frame.iloc[-1]
    required = ["ema_12", "ema_26", "adx_14", "atr_pct", "atr_pct_q20", "atr_pct_q80"]
    missing = [name for name in required if pd.isna(latest.get(name))]
    if missing:
        return MarketState(
            asset=str(latest["asset"]),
            timeframe=str(latest["timeframe"]),
            as_of=latest["close_time"],
            regime=MarketRegime.INSUFFICIENT_DATA,
            volatility=VolatilityState.INSUFFICIENT_DATA,
            reasons=(f"missing warm-up features: {', '.join(missing)}",),
        )

    adx = float(latest["adx_14"])
    regime, regime_reason = _regime_for_row(latest, config)

    atr_pct = float(latest["atr_pct"])
    if atr_pct >= float(latest["atr_pct_q80"]):
        volatility = VolatilityState.HIGH
        volatility_reason = "ATR percentage is at or above its trailing 80th percentile"
    elif atr_pct <= float(latest["atr_pct_q20"]):
        volatility = VolatilityState.LOW
        volatility_reason = "ATR percentage is at or below its trailing 20th percentile"
    else:
        volatility = VolatilityState.NORMAL
        volatility_reason = "ATR percentage is inside its trailing 20th–80th percentile band"

    complete_history = frame.dropna(subset=required)
    previous_regime = None
    if len(complete_history) >= 2:
        previous_regime, _ = _regime_for_row(complete_history.iloc[-2], config)
    regime_changed = previous_regime is not None and previous_regime is not regime
    transition_reason = (
        f"regime changed from {previous_regime.value} to {regime.value}"
        if regime_changed and previous_regime is not None
        else "no regime transition on the latest closed candle"
    )

    return MarketState(
        asset=str(latest["asset"]),
        timeframe=str(latest["timeframe"]),
        as_of=latest["close_time"],
        regime=regime,
        volatility=volatility,
        trend_strength=adx,
        previous_regime=previous_regime,
        regime_changed=regime_changed,
        reasons=(regime_reason, volatility_reason, transition_reason),
    )


def _regime_for_row(row: pd.Series, config: RegimeConfig) -> tuple[MarketRegime, str]:
    adx = float(row["adx_14"])
    if adx >= config.adx_trend_threshold and row["ema_12"] > row["ema_26"]:
        return MarketRegime.TRENDING_UP, "ADX meets threshold and EMA 12 is above EMA 26"
    if adx >= config.adx_trend_threshold and row["ema_12"] < row["ema_26"]:
        return MarketRegime.TRENDING_DOWN, "ADX meets threshold and EMA 12 is below EMA 26"
    return MarketRegime.RANGING, "ADX is below the configured trend threshold"
