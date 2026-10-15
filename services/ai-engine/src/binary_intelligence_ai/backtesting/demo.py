from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from binary_intelligence_ai.backtesting.runner import BacktestConfig, compare_baselines
from binary_intelligence_ai.backtesting.splits import WalkForwardConfig
from binary_intelligence_ai.data.contracts import CandleQuery, Timeframe
from binary_intelligence_ai.data.providers import SimulatedCandleProvider


def main() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = SimulatedCandleProvider(seed=2026).get_candles(CandleQuery(
        asset="EURUSD",
        timeframe=Timeframe.M1,
        start=start,
        end=start + timedelta(minutes=1_000),
    ))
    runs = compare_baselines(candles, BacktestConfig(
        walk_forward=WalkForwardConfig(minimum_train_size=500, test_size=100, gap=5),
    ))
    payload = {
        "warning": "SIMULATED data and hypothetical payout; not evidence of profitability",
        "reports": {name: run.report.model_dump(mode="json") for name, run in runs.items()},
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
