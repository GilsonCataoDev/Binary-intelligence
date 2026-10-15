from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import pandas as pd


class Outcome(StrEnum):
    UP = "up"
    DOWN = "down"
    TIE = "tie"


@dataclass(frozen=True)
class SettlementRule:
    horizon_steps: int = 5
    entry_delay_steps: int = 0
    execution_offset_bps: float = 0.0
    tie_tolerance: float = 0.0

    def __post_init__(self) -> None:
        if self.horizon_steps < 1:
            raise ValueError("horizon_steps must be positive")
        if self.entry_delay_steps < 0:
            raise ValueError("entry_delay_steps cannot be negative")
        if self.tie_tolerance < 0:
            raise ValueError("tie_tolerance cannot be negative")


def add_expiry_labels(frame: pd.DataFrame, rule: SettlementRule = SettlementRule()) -> pd.DataFrame:
    """Adiciona resultado futuro sem alterar as features observáveis na decisão."""

    labeled = frame.copy()
    labeled["analysis_price"] = labeled["close"]
    execution_price = labeled["close"].shift(-rule.entry_delay_steps)
    labeled["reference_price"] = execution_price * (1 + rule.execution_offset_bps / 10_000)
    total_steps = rule.entry_delay_steps + rule.horizon_steps
    labeled["settlement_price"] = labeled["close"].shift(-total_steps)
    labeled["settled_at"] = labeled["close_time"].shift(-total_steps)
    delta = labeled["settlement_price"] - labeled["reference_price"]
    available = labeled["settlement_price"].notna()
    conditions = [
        available & (delta > rule.tie_tolerance),
        available & (delta < -rule.tie_tolerance),
        available & (delta.abs() <= rule.tie_tolerance),
    ]
    labeled["outcome"] = np.select(
        conditions,
        [Outcome.UP.value, Outcome.DOWN.value, Outcome.TIE.value],
        default=None,
    )
    return labeled
