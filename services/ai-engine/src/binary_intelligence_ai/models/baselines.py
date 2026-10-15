from __future__ import annotations

from enum import StrEnum

import numpy as np
import pandas as pd

class Decision(StrEnum):
    CALL = "CALL"
    PUT = "PUT"
    ABSTAIN = "ABSTAIN"


class FrequencyBaseline:
    """Probabilidade de alta igual à frequência observada somente no treino."""

    def __init__(self) -> None:
        self.probability_up: float | None = None

    def fit(self, outcomes: pd.Series) -> None:
        resolved = outcomes[outcomes.isin(["up", "down"])]
        if resolved.empty:
            raise ValueError("training fold has no resolved binary outcomes")
        self.probability_up = float((resolved == "up").mean())

    def predict(self, row_count: int, *, payout: float) -> tuple[np.ndarray, np.ndarray]:
        if self.probability_up is None:
            raise RuntimeError("baseline must be fitted before prediction")
        threshold = break_even_probability(payout)
        probability_up = np.full(row_count, self.probability_up)
        if self.probability_up > threshold:
            decision = Decision.CALL.value
        elif 1 - self.probability_up > threshold:
            decision = Decision.PUT.value
        else:
            decision = Decision.ABSTAIN.value
        return probability_up, np.full(row_count, decision, dtype=object)


class TechnicalRuleBaseline:
    """Referência explicável; não produz probabilidade calibrada."""

    def __init__(self, *, adx_threshold: float = 25.0) -> None:
        self.adx_threshold = adx_threshold

    def predict(self, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        ready = frame[["ema_12", "ema_26", "adx_14", "rsi_14"]].notna().all(axis=1)
        call = ready & (frame["adx_14"] >= self.adx_threshold) & (frame["ema_12"] > frame["ema_26"]) & (frame["rsi_14"] < 70)
        put = ready & (frame["adx_14"] >= self.adx_threshold) & (frame["ema_12"] < frame["ema_26"]) & (frame["rsi_14"] > 30)
        decisions = np.select(
            [call, put],
            [Decision.CALL.value, Decision.PUT.value],
            default=Decision.ABSTAIN.value,
        )
        return np.full(len(frame), np.nan), decisions


def break_even_probability(payout: float) -> float:
    if not 0 < payout <= 1:
        raise ValueError("net payout must be in (0, 1]")
    return 1 / (1 + payout)
