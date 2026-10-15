from datetime import datetime, timedelta, timezone

from binary_intelligence_ai.data.contracts import CandleQuery, Timeframe
from binary_intelligence_ai.data.providers import SimulatedCandleProvider
from binary_intelligence_ai.market_analysis import analyze_market
from binary_intelligence_ai.regimes import MarketRegime


def test_analysis_abstains_when_history_is_too_short() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(minutes=30)
    candles = SimulatedCandleProvider(seed=1).get_candles(CandleQuery(
        asset="EURUSD", timeframe=Timeframe.M1, start=start, end=end
    ))
    result = analyze_market(candles, now=end, maximum_age=timedelta(minutes=1))
    assert result.should_abstain is True
    assert result.market_state is not None
    assert result.market_state.regime is MarketRegime.INSUFFICIENT_DATA


def test_analysis_classifies_valid_warmed_up_series() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(minutes=140)
    candles = SimulatedCandleProvider(seed=2).get_candles(CandleQuery(
        asset="EURUSD", timeframe=Timeframe.M1, start=start, end=end
    ))
    result = analyze_market(candles, now=end, maximum_age=timedelta(minutes=1))
    assert result.should_abstain is False
    assert result.market_state is not None
    assert result.market_state.regime is not MarketRegime.INSUFFICIENT_DATA


def test_analysis_abstains_before_computing_features_on_open_candle() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = SimulatedCandleProvider(seed=3).get_candles(CandleQuery(
        asset="EURUSD",
        timeframe=Timeframe.M1,
        start=start,
        end=start + timedelta(minutes=3),
    ))
    result = analyze_market(candles, now=start + timedelta(minutes=2, seconds=30), maximum_age=timedelta(minutes=1))
    assert result.should_abstain is True
    assert result.market_state is None
