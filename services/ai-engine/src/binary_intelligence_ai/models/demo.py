from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from binary_intelligence_ai.backtesting import BacktestConfig, compare_baselines
from binary_intelligence_ai.backtesting.splits import WalkForwardConfig
from binary_intelligence_ai.data.contracts import CandleQuery, Timeframe
from binary_intelligence_ai.data.providers import SimulatedCandleProvider
from binary_intelligence_ai.models.evaluation import evaluate_model_candidates
from binary_intelligence_ai.models.promotion import assess_candidate


def main() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = SimulatedCandleProvider(seed=2026).get_candles(CandleQuery(
        asset="EURUSD", timeframe=Timeframe.M1, start=start, end=start + timedelta(minutes=1_000)
    ))
    config = BacktestConfig(
        walk_forward=WalkForwardConfig(minimum_train_size=500, test_size=100, gap=5)
    )
    baseline = compare_baselines(candles, config)["frequency"]
    candidates = evaluate_model_candidates(candles, backtest=config)
    payload = {
        "warning": "SIMULATED data; holdout not confirmed; no model can be promoted",
        "baseline": baseline.report.model_dump(mode="json"),
        "candidates": {
            name: {
                "report": run.report.model_dump(mode="json"),
                "promotion": assess_candidate(baseline, run).model_dump(mode="json"),
            }
            for name, run in candidates.items()
        },
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
