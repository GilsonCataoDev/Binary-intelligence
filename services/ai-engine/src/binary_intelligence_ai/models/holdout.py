from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from binary_intelligence_ai.backtesting.runner import (
    BacktestConfig, BacktestRun, build_backtest_run, prediction_records, prepare_backtest_dataset,
)
from binary_intelligence_ai.data.contracts import Candle
from binary_intelligence_ai.models.baselines import Decision, FrequencyBaseline, break_even_probability
from binary_intelligence_ai.models.candidates import CalibrationConfig, CalibratedCandidate, CandidateSpec


class HoldoutEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_version: str
    baseline_version: str
    training_end: datetime
    holdout_start: datetime
    holdout_observations: int = Field(gt=0)


@dataclass(frozen=True)
class HoldoutEvaluation:
    baseline: BacktestRun
    candidate: BacktestRun
    evidence: HoldoutEvidence


def evaluate_untouched_holdout(
    candles: list[Candle] | tuple[Candle, ...],
    *,
    candidate_spec: CandidateSpec,
    backtest: BacktestConfig,
    holdout_fraction: float = 0.2,
    random_state: int = 2026,
) -> HoldoutEvaluation:
    if not 0.1 <= holdout_fraction <= 0.4:
        raise ValueError("holdout fraction must be between 0.1 and 0.4")
    dataset = prepare_backtest_dataset(candles, backtest)
    split_at = int(len(dataset) * (1 - holdout_fraction))
    gap = backtest.settlement.horizon_steps + backtest.settlement.entry_delay_steps
    train = dataset.iloc[: split_at - gap]
    holdout = dataset.iloc[split_at:].copy()
    if len(train) < backtest.walk_forward.minimum_train_size or holdout.empty:
        raise ValueError("not enough observations for untouched holdout")

    candidate = CalibratedCandidate(
        candidate_spec,
        calibration=CalibrationConfig(gap=gap),
        random_state=random_state,
    )
    candidate.fit(train)
    candidate_probability = candidate.predict_probability_up(holdout)
    candidate_decision = _decisions(candidate_probability, backtest.payout)
    candidate_records = prediction_records(holdout, candidate_probability, candidate_decision, 0)

    baseline = FrequencyBaseline()
    baseline.fit(train["outcome"])
    baseline_probability, baseline_decision = baseline.predict(len(holdout), payout=backtest.payout)
    baseline_records = prediction_records(holdout, baseline_probability, baseline_decision, 0)

    baseline_run = build_backtest_run("frequency", baseline_records, candles, backtest, 1)
    candidate_run = build_backtest_run(candidate_spec.version, candidate_records, candles, backtest, 1)
    evidence = HoldoutEvidence(
        dataset_fingerprint=_dataset_fingerprint(candles),
        observation_fingerprint=records_fingerprint(candidate_records),
        candidate_version=candidate_spec.version,
        baseline_version="frequency",
        training_end=pd.Timestamp(train.iloc[-1]["close_time"]).to_pydatetime(),
        holdout_start=pd.Timestamp(holdout.iloc[0]["close_time"]).to_pydatetime(),
        holdout_observations=len(holdout),
    )
    return HoldoutEvaluation(baseline=baseline_run, candidate=candidate_run, evidence=evidence)


def records_fingerprint(records: pd.DataFrame) -> str:
    columns = [
        "timestamp", "settled_at", "analysis_price", "reference_price", "settlement_price",
        "outcome", "market_regime", "asset", "fold",
    ]
    canonical = records.loc[:, columns].sort_values("timestamp").to_json(date_format="iso", orient="records")
    return sha256(canonical.encode("utf-8")).hexdigest()


def _dataset_fingerprint(candles: list[Candle] | tuple[Candle, ...]) -> str:
    digest = sha256()
    for candle in candles:
        digest.update(candle.model_dump_json().encode("utf-8"))
    return digest.hexdigest()


def _decisions(probability: np.ndarray, payout: float) -> np.ndarray:
    threshold = break_even_probability(payout)
    return np.select(
        [probability > threshold, (1 - probability) > threshold],
        [Decision.CALL.value, Decision.PUT.value],
        default=Decision.ABSTAIN.value,
    )
