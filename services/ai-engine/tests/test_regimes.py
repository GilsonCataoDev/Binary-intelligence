from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from binary_intelligence_ai.regimes import MarketRegime, VolatilityState, classify_latest


@pytest.mark.parametrize(
    ("ema_12", "ema_26", "adx", "expected"),
    [
        (102.0, 100.0, 30.0, MarketRegime.TRENDING_UP),
        (98.0, 100.0, 30.0, MarketRegime.TRENDING_DOWN),
        (102.0, 100.0, 20.0, MarketRegime.RANGING),
    ],
)
def test_regime_rules_are_explicit(ema_12: float, ema_26: float, adx: float, expected: MarketRegime) -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    frame = pd.DataFrame([{
        "asset": "EURUSD", "timeframe": "1m", "close_time": now,
        "ema_12": ema_12, "ema_26": ema_26, "adx_14": adx,
        "atr_pct": 0.01, "atr_pct_q20": 0.005, "atr_pct_q80": 0.02,
    }])
    state = classify_latest(frame)
    assert state.regime is expected
    assert state.volatility is VolatilityState.NORMAL


def test_classifier_reports_latest_transition() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    frame = pd.DataFrame([
        {
            "asset": "EURUSD", "timeframe": "1m", "close_time": now,
            "ema_12": 102.0, "ema_26": 100.0, "adx_14": 30.0,
            "atr_pct": 0.01, "atr_pct_q20": 0.005, "atr_pct_q80": 0.02,
        },
        {
            "asset": "EURUSD", "timeframe": "1m", "close_time": now + timedelta(minutes=1),
            "ema_12": 98.0, "ema_26": 100.0, "adx_14": 30.0,
            "atr_pct": 0.03, "atr_pct_q20": 0.005, "atr_pct_q80": 0.02,
        },
    ])
    state = classify_latest(frame)
    assert state.previous_regime is MarketRegime.TRENDING_UP
    assert state.regime is MarketRegime.TRENDING_DOWN
    assert state.regime_changed is True
    assert state.volatility is VolatilityState.HIGH
