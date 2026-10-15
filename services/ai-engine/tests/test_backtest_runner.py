from datetime import datetime, timedelta, timezone

from binary_intelligence_ai.backtesting import BacktestConfig, compare_baselines
from binary_intelligence_ai.backtesting.splits import WalkForwardConfig
from binary_intelligence_ai.data.contracts import CandleQuery, Timeframe
from binary_intelligence_ai.data.providers import SimulatedCandleProvider


def test_baselines_run_end_to_end_on_explicitly_simulated_data() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = SimulatedCandleProvider(seed=11).get_candles(CandleQuery(
        asset="EURUSD",
        timeframe=Timeframe.M1,
        start=start,
        end=start + timedelta(minutes=400),
    ))
    runs = compare_baselines(candles, BacktestConfig(
        walk_forward=WalkForwardConfig(minimum_train_size=200, test_size=50, gap=5),
        payout=0.8,
    ))
    assert set(runs) == {"frequency", "technical_rule"}
    assert runs["frequency"].report.data_source == "SIMULATED"
    assert runs["frequency"].report.folds == 4
    assert runs["frequency"].report.payout_is_hypothetical is True
    assert runs["frequency"].report.entry_delay_steps == 0
    assert runs["frequency"].report.execution_offset_bps == 0
    assert runs["frequency"].report.metrics.brier_score is not None
    assert runs["technical_rule"].report.metrics.brier_score is None
