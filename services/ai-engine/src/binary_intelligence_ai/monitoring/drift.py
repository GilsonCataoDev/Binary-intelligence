from __future__ import annotations

from enum import StrEnum

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class MonitoringStatus(StrEnum):
    HEALTHY = "healthy"
    WARNING = "warning"
    BLOCKED = "blocked"
    INSUFFICIENT_DATA = "insufficient_data"


class DriftConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_feature_observations: int = Field(default=100, ge=20)
    minimum_performance_observations: int = Field(default=100, ge=20)
    warning_psi: float = Field(default=0.10, gt=0)
    blocking_psi: float = Field(default=0.25, gt=0)
    warning_ece: float = Field(default=0.08, gt=0, le=1)
    blocking_ece: float = Field(default=0.12, gt=0, le=1)
    warning_brier: float = Field(default=0.26, gt=0, le=1)
    blocking_brier: float = Field(default=0.30, gt=0, le=1)


class MonitoringAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: MonitoringStatus
    should_pause: bool
    feature_psi: dict[str, float]
    maximum_psi: float | None
    observations: int
    brier_score: float | None
    expected_calibration_error: float | None
    reasons: tuple[str, ...]


def population_stability_index(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)
    reference = reference[np.isfinite(reference)]
    current = current[np.isfinite(current)]
    if reference.size == 0 or current.size == 0:
        raise ValueError("PSI requires finite reference and current observations")
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    if edges.size < 3:
        return 0.0 if np.allclose(np.mean(reference), np.mean(current)) else 1.0
    edges[0], edges[-1] = -np.inf, np.inf
    expected = np.histogram(reference, bins=edges)[0] / reference.size
    actual = np.histogram(current, bins=edges)[0] / current.size
    expected = np.clip(expected, 1e-6, None)
    actual = np.clip(actual, 1e-6, None)
    return float(np.sum((actual - expected) * np.log(actual / expected)))


def assess_monitoring(
    reference_features: pd.DataFrame,
    current_features: pd.DataFrame,
    *,
    probabilities_up: np.ndarray | None = None,
    outcomes_up: np.ndarray | None = None,
    config: DriftConfig = DriftConfig(),
) -> MonitoringAssessment:
    reasons: list[str] = []
    feature_psi: dict[str, float] = {}
    common = sorted(set(reference_features.select_dtypes(include="number")) & set(current_features.select_dtypes(include="number")))
    enough_features = len(reference_features) >= config.minimum_feature_observations and len(current_features) >= config.minimum_feature_observations
    if not common:
        reasons.append("no common numeric features are available")
    elif not enough_features:
        reasons.append("feature sample is too small for drift assessment")
    else:
        for column in common:
            try:
                feature_psi[column] = population_stability_index(
                    reference_features[column].to_numpy(), current_features[column].to_numpy()
                )
            except ValueError:
                reasons.append(f"feature {column} has no finite observations")

    observations = 0
    brier: float | None = None
    ece: float | None = None
    if probabilities_up is not None and outcomes_up is not None:
        probabilities = np.asarray(probabilities_up, dtype=float)
        outcomes = np.asarray(outcomes_up, dtype=float)
        if probabilities.shape != outcomes.shape:
            raise ValueError("probabilities and outcomes must have the same shape")
        valid = np.isfinite(probabilities) & np.isfinite(outcomes) & np.isin(outcomes, [0.0, 1.0])
        probabilities, outcomes = probabilities[valid], outcomes[valid]
        observations = int(probabilities.size)
        if observations >= config.minimum_performance_observations:
            brier = float(np.mean((probabilities - outcomes) ** 2))
            ece = _expected_calibration_error(probabilities, outcomes)
        else:
            reasons.append("resolved outcome sample is too small for performance assessment")
    else:
        reasons.append("resolved outcomes are not available")

    maximum_psi = max(feature_psi.values(), default=None)
    blocked = (
        (maximum_psi is not None and maximum_psi >= config.blocking_psi)
        or (brier is not None and brier >= config.blocking_brier)
        or (ece is not None and ece >= config.blocking_ece)
    )
    warning = (
        (maximum_psi is not None and maximum_psi >= config.warning_psi)
        or (brier is not None and brier >= config.warning_brier)
        or (ece is not None and ece >= config.warning_ece)
    )
    if maximum_psi is not None and maximum_psi >= config.blocking_psi:
        reasons.append("feature drift reached the blocking threshold")
    if brier is not None and brier >= config.blocking_brier:
        reasons.append("Brier score reached the blocking threshold")
    if ece is not None and ece >= config.blocking_ece:
        reasons.append("calibration error reached the blocking threshold")

    insufficient = not feature_psi or brier is None or ece is None
    status = (
        MonitoringStatus.BLOCKED if blocked else
        MonitoringStatus.WARNING if warning else
        MonitoringStatus.INSUFFICIENT_DATA if insufficient else
        MonitoringStatus.HEALTHY
    )
    return MonitoringAssessment(
        status=status,
        should_pause=blocked,
        feature_psi=feature_psi,
        maximum_psi=maximum_psi,
        observations=observations,
        brier_score=brier,
        expected_calibration_error=ece,
        reasons=tuple(reasons),
    )


def _expected_calibration_error(probabilities: np.ndarray, outcomes: np.ndarray, bins: int = 10) -> float:
    indexes = np.minimum((probabilities * bins).astype(int), bins - 1)
    weighted_error = 0.0
    for index in range(bins):
        selected = indexes == index
        if selected.any():
            weighted_error += selected.sum() * abs(probabilities[selected].mean() - outcomes[selected].mean())
    return float(weighted_error / len(probabilities))
