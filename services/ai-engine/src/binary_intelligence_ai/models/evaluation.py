from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from binary_intelligence_ai.backtesting.runner import (
    BacktestConfig,
    BacktestRun,
    build_backtest_run,
    prediction_records,
    prepare_backtest_dataset,
)
from binary_intelligence_ai.backtesting.splits import walk_forward_splits
from binary_intelligence_ai.data.contracts import Candle
from binary_intelligence_ai.models.baselines import Decision, break_even_probability
from binary_intelligence_ai.models.candidates import (
    DEFAULT_CANDIDATES,
    CalibrationConfig,
    CalibratedCandidate,
    CandidateSpec,
)


@dataclass(frozen=True)
class ModelEvaluationConfig:
    candidates: tuple[CandidateSpec, ...] = DEFAULT_CANDIDATES
    calibration_fraction: float = 0.2
    random_state: int = 2026


def evaluate_model_candidates(
    candles: list[Candle] | tuple[Candle, ...],
    *,
    backtest: BacktestConfig,
    evaluation: ModelEvaluationConfig = ModelEvaluationConfig(),
) -> dict[str, BacktestRun]:
    dataset = prepare_backtest_dataset(candles, backtest)
    splits = list(walk_forward_splits(len(dataset), backtest.walk_forward))
    if not splits:
        raise ValueError("not enough observations for model evaluation")

    results: dict[str, BacktestRun] = {}
    for spec in evaluation.candidates:
        parts: list[pd.DataFrame] = []
        for fold, (train_index, test_index) in enumerate(splits):
            train = dataset.iloc[train_index]
            test = dataset.iloc[test_index].copy()
            candidate = CalibratedCandidate(
                spec,
                calibration=CalibrationConfig(
                    fraction=evaluation.calibration_fraction,
                    gap=backtest.settlement.horizon_steps + backtest.settlement.entry_delay_steps,
                ),
                random_state=evaluation.random_state + fold,
            )
            candidate.fit(train)
            probability = candidate.predict_probability_up(test)
            decisions = _decisions(probability, payout=backtest.payout)
            parts.append(prediction_records(test, probability, decisions, fold))
        results[spec.version] = build_backtest_run(
            spec.version, pd.concat(parts), candles, backtest, len(splits)
        )
    return results


def _decisions(probability_up: np.ndarray, *, payout: float) -> np.ndarray:
    threshold = break_even_probability(payout)
    return np.select(
        [probability_up > threshold, (1 - probability_up) > threshold],
        [Decision.CALL.value, Decision.PUT.value],
        default=Decision.ABSTAIN.value,
    )
