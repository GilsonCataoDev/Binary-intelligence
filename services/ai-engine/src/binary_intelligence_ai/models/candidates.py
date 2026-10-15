from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_SET_VERSION = "technical-v1"
MODEL_FEATURES = (
    "return_1", "sma_5", "sma_20", "ema_12", "ema_26", "macd", "macd_signal",
    "macd_histogram", "rsi_14", "atr_14", "atr_pct", "adx_14", "bollinger_width",
    "distance_to_support_atr", "distance_to_resistance_atr", "breakout_up", "breakout_down",
    "false_breakout_up", "false_breakout_down", "pullback_up", "pullback_down",
    "bullish_structure_5", "bearish_structure_5", "ema_spread_atr", "candle_body_ratio",
    "upper_wick_ratio", "lower_wick_ratio", "candle_direction", "is_doji",
)


class CandidateKind(StrEnum):
    LOGISTIC = "logistic"
    RANDOM_FOREST = "random_forest"
    HISTOGRAM_BOOSTING = "histogram_boosting"


@dataclass(frozen=True)
class CandidateSpec:
    kind: CandidateKind
    version: str


DEFAULT_CANDIDATES = (
    CandidateSpec(CandidateKind.LOGISTIC, "logistic-v1"),
    CandidateSpec(CandidateKind.RANDOM_FOREST, "random-forest-v1"),
    CandidateSpec(CandidateKind.HISTOGRAM_BOOSTING, "histogram-boosting-v1"),
)


@dataclass(frozen=True)
class CalibrationConfig:
    fraction: float = 0.2
    gap: int = 5
    minimum_samples: int = 40

    def __post_init__(self) -> None:
        if not 0.1 <= self.fraction <= 0.4:
            raise ValueError("calibration fraction must be between 0.1 and 0.4")
        if self.gap < 0 or self.minimum_samples < 10:
            raise ValueError("invalid calibration gap or minimum_samples")


class CalibratedCandidate:
    """Modelo base com calibração de Platt em período cronológico separado."""

    def __init__(
        self,
        spec: CandidateSpec,
        *,
        calibration: CalibrationConfig,
        random_state: int = 2026,
    ) -> None:
        self.spec = spec
        self.calibration = calibration
        self.random_state = random_state
        self.estimator = _build_estimator(spec.kind, random_state)
        self.calibrator = LogisticRegression(random_state=random_state)
        self.training_rows = 0
        self.calibration_rows = 0
        self.training_end: pd.Timestamp | None = None
        self.calibration_start: pd.Timestamp | None = None

    def fit(self, frame: pd.DataFrame) -> None:
        split_at = int(len(frame) * (1 - self.calibration.fraction))
        base = frame.iloc[:split_at]
        calibration = frame.iloc[split_at + self.calibration.gap :]
        base = _resolved(base)
        calibration = _resolved(calibration)
        if len(base) < self.calibration.minimum_samples or len(calibration) < self.calibration.minimum_samples:
            raise ValueError("not enough resolved samples for temporal training and calibration")

        base_y = (base["outcome"] == "up").astype(int)
        calibration_y = (calibration["outcome"] == "up").astype(int)
        if base_y.nunique() < 2 or calibration_y.nunique() < 2:
            raise ValueError("both classes are required in training and calibration periods")

        self.estimator.fit(base.loc[:, MODEL_FEATURES], base_y)
        raw_probability = self.estimator.predict_proba(calibration.loc[:, MODEL_FEATURES])[:, 1]
        self.calibrator.fit(_logit(raw_probability).reshape(-1, 1), calibration_y)
        self.training_rows = len(base)
        self.calibration_rows = len(calibration)
        self.training_end = pd.Timestamp(base.iloc[-1]["close_time"])
        self.calibration_start = pd.Timestamp(calibration.iloc[0]["close_time"])

    def predict_probability_up(self, frame: pd.DataFrame) -> np.ndarray:
        if self.training_rows == 0:
            raise RuntimeError("candidate must be fitted before prediction")
        raw_probability = self.estimator.predict_proba(frame.loc[:, MODEL_FEATURES])[:, 1]
        return self.calibrator.predict_proba(_logit(raw_probability).reshape(-1, 1))[:, 1]


def _build_estimator(kind: CandidateKind, random_state: int) -> Pipeline:
    if kind is CandidateKind.LOGISTIC:
        model = LogisticRegression(max_iter=1_000, random_state=random_state)
        return Pipeline([
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
            ("model", model),
        ])
    if kind is CandidateKind.RANDOM_FOREST:
        model = RandomForestClassifier(
            n_estimators=80,
            max_depth=6,
            min_samples_leaf=10,
            random_state=random_state,
            n_jobs=1,
        )
        return Pipeline([("imputer", SimpleImputer(strategy="median", add_indicator=True)), ("model", model)])
    model = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=100,
        max_depth=3,
        min_samples_leaf=20,
        l2_regularization=1.0,
        random_state=random_state,
    )
    return Pipeline([("imputer", SimpleImputer(strategy="median", add_indicator=True)), ("model", model)])


def _resolved(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[frame["outcome"].isin(["up", "down"])]


def _logit(probability: np.ndarray) -> np.ndarray:
    clipped = np.clip(probability, 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped))
