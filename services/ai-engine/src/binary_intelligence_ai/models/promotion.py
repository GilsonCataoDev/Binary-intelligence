from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict

from binary_intelligence_ai.backtesting.runner import BacktestRun
from binary_intelligence_ai.models.baselines import break_even_probability


@dataclass(frozen=True)
class PromotionCriteria:
    minimum_observations: int = 300
    minimum_brier_improvement: float = 0.002
    maximum_log_loss_increase: float = 0.0
    maximum_expected_calibration_error: float = 0.08
    minimum_fold_win_rate: float = 0.6
    require_hit_rate_ci_above_break_even: bool = True


class PromotionAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)
    baseline: str
    candidate: str
    approved: Literal[False]
    holdout_confirmed: Literal[False]
    brier_improvement: float | None
    fold_win_rate: float | None
    expected_calibration_error: float | None
    reasons: tuple[str, ...]


def assess_candidate(
    baseline: BacktestRun,
    candidate: BacktestRun,
    criteria: PromotionCriteria = PromotionCriteria(),
) -> PromotionAssessment:
    reasons: list[str] = []
    mismatch = _comparison_mismatch(baseline, candidate)
    if mismatch:
        reasons.append(f"candidate and baseline are not comparable: {mismatch}")
    baseline_metrics = baseline.report.metrics
    candidate_metrics = candidate.report.metrics
    brier_improvement = None
    if baseline_metrics.brier_score is None or candidate_metrics.brier_score is None:
        reasons.append("Brier score unavailable")
    else:
        brier_improvement = baseline_metrics.brier_score - candidate_metrics.brier_score
        if brier_improvement < criteria.minimum_brier_improvement:
            reasons.append("Brier improvement is below the required margin")

    if candidate_metrics.observations < criteria.minimum_observations:
        reasons.append("out-of-sample observation count is too small")
    if (
        baseline_metrics.log_loss is None
        or candidate_metrics.log_loss is None
        or candidate_metrics.log_loss > baseline_metrics.log_loss + criteria.maximum_log_loss_increase
    ):
        reasons.append("log loss does not meet the baseline criterion")

    expected_calibration_error = _expected_calibration_error(candidate)
    if expected_calibration_error is None or expected_calibration_error > criteria.maximum_expected_calibration_error:
        reasons.append("expected calibration error exceeds the limit")

    fold_win_rate = _fold_win_rate(baseline, candidate)
    if fold_win_rate is None or fold_win_rate < criteria.minimum_fold_win_rate:
        reasons.append("candidate does not beat baseline across enough folds")

    if criteria.require_hit_rate_ci_above_break_even:
        interval = candidate_metrics.hit_rate_ci95
        threshold = break_even_probability(candidate.report.payout)
        if interval is None or interval[0] <= threshold:
            reasons.append("hit-rate confidence interval does not clear break-even")
    reasons.append("untouched holdout evaluation pipeline has not been implemented")

    return PromotionAssessment(
        baseline=baseline.report.strategy,
        candidate=candidate.report.strategy,
        approved=not reasons,
        holdout_confirmed=False,
        brier_improvement=brier_improvement,
        fold_win_rate=fold_win_rate,
        expected_calibration_error=expected_calibration_error,
        reasons=tuple(reasons),
    )


def _expected_calibration_error(run: BacktestRun) -> float | None:
    bins = run.report.metrics.calibration
    total = sum(item.count for item in bins)
    if total == 0:
        return None
    return sum(item.count * abs(item.predicted_mean - item.observed_frequency) for item in bins) / total


def _fold_win_rate(baseline: BacktestRun, candidate: BacktestRun) -> float | None:
    wins: list[bool] = []
    common_folds = sorted(set(baseline.records["fold"]) & set(candidate.records["fold"]))
    for fold in common_folds:
        base = baseline.records[baseline.records["fold"] == fold]
        challenger = candidate.records[candidate.records["fold"] == fold]
        merged = base[["timestamp", "outcome", "probability_up"]].merge(
            challenger[["timestamp", "probability_up"]], on="timestamp", suffixes=("_base", "_candidate")
        )
        resolved = merged[merged["outcome"].isin(["up", "down"])]
        if resolved.empty:
            continue
        actual = (resolved["outcome"] == "up").astype(float).to_numpy()
        base_brier = np.mean((resolved["probability_up_base"].to_numpy() - actual) ** 2)
        candidate_brier = np.mean((resolved["probability_up_candidate"].to_numpy() - actual) ** 2)
        wins.append(candidate_brier < base_brier)
    return sum(wins) / len(wins) if wins else None


def _comparison_mismatch(baseline: BacktestRun, candidate: BacktestRun) -> str | None:
    fields = (
        "data_source", "asset", "timeframe", "horizon_steps", "entry_delay_steps",
        "execution_offset_bps", "tie_tolerance", "minimum_train_size", "test_size",
        "gap", "folds", "payout", "payout_is_hypothetical", "tie_policy",
    )
    for field in fields:
        if getattr(baseline.report, field) != getattr(candidate.report, field):
            return f"report field {field} differs"

    identity = [
        "timestamp", "settled_at", "analysis_price", "reference_price",
        "settlement_price", "outcome", "market_regime", "fold",
    ]
    baseline_records = baseline.records.loc[:, identity].sort_values("timestamp").reset_index(drop=True)
    candidate_records = candidate.records.loc[:, identity].sort_values("timestamp").reset_index(drop=True)
    if not baseline_records.equals(candidate_records):
        return "out-of-sample observations differ"
    return None
