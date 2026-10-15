from datetime import datetime, timedelta, timezone

from binary_intelligence_ai.backtesting.metrics import TiePolicy
from binary_intelligence_ai.data.contracts import CandleQuery, Timeframe
from binary_intelligence_ai.data.providers import SimulatedCandleProvider
from binary_intelligence_ai.research.viability import (
    ViabilityConfig,
    contiguous_segments,
    net_payout_from_proposal,
    run_viability,
)

START = datetime(2026, 1, 5, tzinfo=timezone.utc)


def _raw(minutes: int, offset: timedelta = timedelta()) -> list[dict]:
    candles = SimulatedCandleProvider(seed=7).get_candles(CandleQuery(
        asset="R_100", timeframe=Timeframe.M1, start=START + offset, end=START + offset + timedelta(minutes=minutes),
    ))
    return [
        {"epoch": int(c.open_time.timestamp()), "open": float(c.open), "high": float(c.high),
         "low": float(c.low), "close": float(c.close)}
        for c in candles
    ]


def test_segments_split_on_gaps_and_drop_open_and_short_pieces() -> None:
    raw = _raw(400) + _raw(100, timedelta(days=2)) + _raw(500, timedelta(days=3))
    now = START + timedelta(days=3, minutes=499, seconds=30)
    segments = contiguous_segments(raw, symbol="R_100", now=now)
    assert [len(s) for s in segments] == [400, 499]
    assert all(s[i].close_time == s[i + 1].open_time for s in segments for i in range(len(s) - 1))


def test_net_payout_from_proposal() -> None:
    assert net_payout_from_proposal({"proposal": {"ask_price": 1, "payout": 1.96}}) == 0.96
    assert net_payout_from_proposal({"error": {"message": "not offered"}}) is None


def test_run_viability_reports_all_strategies_on_simulated_data() -> None:
    raw = _raw(3000)
    segments = contiguous_segments(raw, symbol="R_100", now=START + timedelta(days=3))
    assert len(segments[0]) == 3000
    result = run_viability(segments, ViabilityConfig(
        horizon_minutes=5, payout=0.96, tie_policy=TiePolicy.LOSS, minimum_train_size=1200, test_size=500,
    ))
    assert set(result["strategies"]) == {
        "frequency", "technical_rule", "logistic-v1", "random-forest-v1", "histogram-boosting-v1",
    }
    assert result["folds"] >= 3
    assert abs(result["break_even_hit_rate"] - 1 / 1.96) < 1e-9
    assert "price" not in str(result).lower()
