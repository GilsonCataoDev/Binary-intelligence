from datetime import datetime, timedelta, timezone

import pandas as pd

from binary_intelligence_ai.data.contracts import CandleQuery, Timeframe
from binary_intelligence_ai.data.providers import SimulatedCandleProvider
from binary_intelligence_ai.features import build_feature_frame


def simulated_candles(count: int = 120):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SimulatedCandleProvider(seed=7).get_candles(CandleQuery(
        asset="EURUSD",
        timeframe=Timeframe.M1,
        start=start,
        end=start + timedelta(minutes=count),
    ))


def test_features_do_not_change_when_future_candles_are_added() -> None:
    candles = simulated_candles()
    prefix = build_feature_frame(candles[:80])
    complete = build_feature_frame(candles)
    pd.testing.assert_series_equal(prefix.iloc[-1], complete.iloc[79], check_names=False)


def test_support_and_resistance_exclude_current_candle() -> None:
    frame = build_feature_frame(simulated_candles(30))
    row = frame.iloc[20]
    history = frame.iloc[:20]
    assert row["support_20"] == history["low"].min()
    assert row["resistance_20"] == history["high"].max()


def test_unavailable_warm_up_features_remain_missing() -> None:
    frame = build_feature_frame(simulated_candles(10))
    assert pd.isna(frame.iloc[0]["higher_high"])
    assert pd.isna(frame.iloc[-1]["breakout_up"])
    assert pd.isna(frame.iloc[-1]["pullback_up"])
