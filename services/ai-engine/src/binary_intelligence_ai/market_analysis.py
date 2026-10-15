from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict

from binary_intelligence_ai.data.contracts import Candle
from binary_intelligence_ai.data.quality import DataQualityReport, validate_candles
from binary_intelligence_ai.features import build_feature_frame
from binary_intelligence_ai.regimes import MarketRegime, MarketState, RegimeConfig, classify_latest


class MarketAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    quality: DataQualityReport
    market_state: MarketState | None
    should_abstain: bool


def analyze_market(
    candles: list[Candle] | tuple[Candle, ...],
    *,
    now: datetime,
    maximum_age: timedelta,
    config: RegimeConfig = RegimeConfig(),
) -> MarketAnalysis:
    quality = validate_candles(candles, now=now, maximum_age=maximum_age)
    if quality.should_abstain:
        return MarketAnalysis(quality=quality, market_state=None, should_abstain=True)

    state = classify_latest(build_feature_frame(candles), config)
    return MarketAnalysis(
        quality=quality,
        market_state=state,
        should_abstain=state.regime is MarketRegime.INSUFFICIENT_DATA,
    )
