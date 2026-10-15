from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from binary_intelligence_ai.backtesting.labels import SettlementRule, add_expiry_labels
from binary_intelligence_ai.backtesting.metrics import BacktestMetrics, TiePolicy, evaluate_records
from binary_intelligence_ai.backtesting.splits import WalkForwardConfig, walk_forward_splits
from binary_intelligence_ai.data.contracts import Candle
from binary_intelligence_ai.data.quality import validate_candles
from binary_intelligence_ai.features import build_feature_frame
from binary_intelligence_ai.models import FrequencyBaseline, TechnicalRuleBaseline


class BacktestReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    strategy: str
    data_source: str
    asset: str
    timeframe: str
    horizon_steps: int
    entry_delay_steps: int
    execution_offset_bps: float
    tie_tolerance: float
    minimum_train_size: int
    test_size: int
    gap: int
    folds: int
    payout: float
    payout_is_hypothetical: bool = True
    tie_policy: TiePolicy
    metrics: BacktestMetrics


@dataclass(frozen=True)
class BacktestRun:
    report: BacktestReport
    records: pd.DataFrame


@dataclass(frozen=True)
class BacktestConfig:
    settlement: SettlementRule = SettlementRule()
    walk_forward: WalkForwardConfig = WalkForwardConfig()
    payout: float = 0.8
    tie_policy: TiePolicy = TiePolicy.PUSH

    def __post_init__(self) -> None:
        required_gap = self.settlement.entry_delay_steps + self.settlement.horizon_steps
        if self.walk_forward.gap < required_gap:
            raise ValueError("walk-forward gap must cover entry delay and settlement horizon")


def compare_baselines(candles: list[Candle] | tuple[Candle, ...], config: BacktestConfig) -> dict[str, BacktestRun]:
    if not candles:
        raise ValueError("backtest requires candles")
    quality = validate_candles(
        candles,
        now=candles[-1].close_time,
        maximum_age=timedelta(seconds=candles[-1].timeframe.seconds),
    )
    if quality.should_abstain:
        raise ValueError(f"invalid backtest data: {[issue.code.value for issue in quality.issues]}")

    dataset = add_expiry_labels(build_feature_frame(candles), config.settlement)
    dataset = dataset[dataset["outcome"].notna()].copy()
    dataset["hour"] = pd.to_datetime(dataset["close_time"], utc=True).dt.hour
    dataset["market_regime"] = np.select(
        [
            (dataset["adx_14"] >= 25) & (dataset["ema_12"] > dataset["ema_26"]),
            (dataset["adx_14"] >= 25) & (dataset["ema_12"] < dataset["ema_26"]),
        ],
        ["trending_up", "trending_down"],
        default="ranging",
    )
    splits = list(walk_forward_splits(len(dataset), config.walk_forward))
    if not splits:
        raise ValueError("not enough labeled observations for walk-forward configuration")

    frequency_parts: list[pd.DataFrame] = []
    technical_parts: list[pd.DataFrame] = []
    technical = TechnicalRuleBaseline()
    for fold, (train_index, test_index) in enumerate(splits):
        train = dataset.iloc[train_index]
        test = dataset.iloc[test_index].copy()

        frequency = FrequencyBaseline()
        frequency.fit(train["outcome"])
        probability, decision = frequency.predict(len(test), payout=config.payout)
        frequency_parts.append(_prediction_records(test, probability, decision, fold))

        technical_probability, technical_decision = technical.predict(test)
        technical_parts.append(_prediction_records(test, technical_probability, technical_decision, fold))

    return {
        "frequency": _run("frequency", pd.concat(frequency_parts), candles, config, len(splits)),
        "technical_rule": _run("technical_rule", pd.concat(technical_parts), candles, config, len(splits)),
    }


def _prediction_records(frame: pd.DataFrame, probability: np.ndarray, decision: np.ndarray, fold: int) -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp": frame["close_time"].to_numpy(),
        "settled_at": frame["settled_at"].to_numpy(),
        "analysis_price": frame["analysis_price"].to_numpy(),
        "reference_price": frame["reference_price"].to_numpy(),
        "settlement_price": frame["settlement_price"].to_numpy(),
        "outcome": frame["outcome"].to_numpy(),
        "probability_up": probability,
        "decision": decision,
        "hour": frame["hour"].to_numpy(),
        "market_regime": frame["market_regime"].to_numpy(),
        "asset": frame["asset"].to_numpy(),
        "fold": fold,
    })


def _run(name: str, records: pd.DataFrame, candles: list[Candle] | tuple[Candle, ...], config: BacktestConfig, folds: int) -> BacktestRun:
    records = records.reset_index(drop=True)
    metrics = evaluate_records(records, payout=config.payout, tie_policy=config.tie_policy)
    first = candles[0]
    return BacktestRun(
        report=BacktestReport(
            strategy=name,
            data_source=first.source,
            asset=first.asset,
            timeframe=first.timeframe.value,
            horizon_steps=config.settlement.horizon_steps,
            entry_delay_steps=config.settlement.entry_delay_steps,
            execution_offset_bps=config.settlement.execution_offset_bps,
            tie_tolerance=config.settlement.tie_tolerance,
            minimum_train_size=config.walk_forward.minimum_train_size,
            test_size=config.walk_forward.test_size,
            gap=config.walk_forward.gap,
            folds=folds,
            payout=config.payout,
            tie_policy=config.tie_policy,
            metrics=metrics,
        ),
        records=records,
    )
