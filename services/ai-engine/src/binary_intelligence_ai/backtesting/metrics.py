from __future__ import annotations

import math
from enum import StrEnum

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from binary_intelligence_ai.backtesting.labels import Outcome
from binary_intelligence_ai.models.baselines import Decision


class TiePolicy(StrEnum):
    PUSH = "push"
    LOSS = "loss"


class CalibrationBin(BaseModel):
    model_config = ConfigDict(frozen=True)
    lower: float
    upper: float
    count: int
    predicted_mean: float
    observed_frequency: float


class BacktestMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)
    observations: int
    operations: int
    abstentions: int
    wins: int
    losses: int
    ties: int
    hit_rate: float | None
    hit_rate_ci95: tuple[float, float] | None
    net_return_units: float
    expectation_per_operation: float | None
    maximum_drawdown_units: float
    brier_score: float | None
    log_loss: float | None
    calibration: tuple[CalibrationBin, ...]
    pnl_distribution: dict[str, int]
    net_return_by_asset: dict[str, float]
    net_return_by_hour: dict[str, float]
    net_return_by_regime: dict[str, float]
    payout_sensitivity: dict[str, float]


def evaluate_records(
    records: pd.DataFrame,
    *,
    payout: float,
    tie_policy: TiePolicy,
    sensitivity_payouts: tuple[float, ...] = (0.7, 0.8, 0.9),
) -> BacktestMetrics:
    evaluated = records.copy()
    evaluated["pnl"] = _pnl(evaluated, payout=payout, tie_policy=tie_policy)
    traded = evaluated[evaluated["decision"] != Decision.ABSTAIN.value]
    wins = int((traded["pnl"] > 0).sum())
    losses = int((traded["pnl"] < 0).sum())
    ties = int((traded["outcome"] == Outcome.TIE.value).sum())
    operations = len(traded)
    decisive = wins + losses
    hit_rate = wins / decisive if decisive else None
    cumulative = traded["pnl"].cumsum()
    drawdown = cumulative.cummax().clip(lower=0) - cumulative

    probability_rows = evaluated[
        evaluated["probability_up"].notna()
        & evaluated["outcome"].isin([Outcome.UP.value, Outcome.DOWN.value])
    ].copy()
    brier = None
    log_loss = None
    calibration: tuple[CalibrationBin, ...] = ()
    if not probability_rows.empty:
        actual = (probability_rows["outcome"] == Outcome.UP.value).astype(float).to_numpy()
        predicted = probability_rows["probability_up"].astype(float).to_numpy()
        brier = float(np.mean((predicted - actual) ** 2))
        clipped = np.clip(predicted, 1e-15, 1 - 1e-15)
        log_loss = float(-np.mean(actual * np.log(clipped) + (1 - actual) * np.log(1 - clipped)))
        calibration = _calibration_bins(predicted, actual)

    return BacktestMetrics(
        observations=len(evaluated),
        operations=operations,
        abstentions=int((evaluated["decision"] == Decision.ABSTAIN.value).sum()),
        wins=wins,
        losses=losses,
        ties=ties,
        hit_rate=hit_rate,
        hit_rate_ci95=_wilson_interval(wins, decisive) if decisive else None,
        net_return_units=_clean_float(traded["pnl"].sum()),
        expectation_per_operation=_clean_float(traded["pnl"].mean()) if operations else None,
        maximum_drawdown_units=_clean_float(drawdown.max()) if operations else 0.0,
        brier_score=brier,
        log_loss=log_loss,
        calibration=calibration,
        pnl_distribution={str(key): int(value) for key, value in traded["pnl"].value_counts().sort_index().items()},
        net_return_by_asset=_group_returns(evaluated, "asset"),
        net_return_by_hour=_group_returns(evaluated, "hour"),
        net_return_by_regime=_group_returns(evaluated, "market_regime"),
        payout_sensitivity={
            f"{scenario:.2f}": _clean_float(_pnl(evaluated, payout=scenario, tie_policy=tie_policy).sum())
            for scenario in sensitivity_payouts
        },
    )


def _pnl(records: pd.DataFrame, *, payout: float, tie_policy: TiePolicy) -> pd.Series:
    if not 0 < payout <= 1:
        raise ValueError("net payout must be in (0, 1]")
    call_win = (records["decision"] == Decision.CALL.value) & (records["outcome"] == Outcome.UP.value)
    put_win = (records["decision"] == Decision.PUT.value) & (records["outcome"] == Outcome.DOWN.value)
    traded = records["decision"] != Decision.ABSTAIN.value
    tie = traded & (records["outcome"] == Outcome.TIE.value)
    pnl = pd.Series(0.0, index=records.index)
    pnl.loc[traded] = -1.0
    pnl.loc[call_win | put_win] = payout
    if tie_policy is TiePolicy.PUSH:
        pnl.loc[tie] = 0.0
    return pnl


def _wilson_interval(successes: int, total: int) -> tuple[float, float]:
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return center - margin, center + margin


def _calibration_bins(predicted: np.ndarray, actual: np.ndarray) -> tuple[CalibrationBin, ...]:
    result: list[CalibrationBin] = []
    for lower in np.linspace(0, 0.9, 10):
        upper = lower + 0.1
        mask = (predicted >= lower) & (predicted <= upper if upper >= 1 else predicted < upper)
        if mask.any():
            result.append(CalibrationBin(
                lower=float(lower), upper=float(upper), count=int(mask.sum()),
                predicted_mean=float(predicted[mask].mean()),
                observed_frequency=float(actual[mask].mean()),
            ))
    return tuple(result)


def _group_returns(records: pd.DataFrame, column: str) -> dict[str, float]:
    if column not in records:
        return {}
    traded = records[records["decision"] != Decision.ABSTAIN.value]
    return {str(key): _clean_float(value) for key, value in traded.groupby(column, dropna=False)["pnl"].sum().items()}


def _clean_float(value: float) -> float:
    return round(float(value), 12)
