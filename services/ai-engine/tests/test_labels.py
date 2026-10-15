from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from binary_intelligence_ai.backtesting.labels import Outcome, SettlementRule, add_expiry_labels


def test_five_step_label_uses_price_observed_exactly_at_expiry() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    frame = pd.DataFrame({
        "close": [100.0, 101.0, 99.0, 100.0, 102.0, 103.0, 101.0],
        "close_time": [start + timedelta(minutes=index + 1) for index in range(7)],
    })
    labeled = add_expiry_labels(frame, SettlementRule(horizon_steps=5))
    assert labeled.iloc[0]["settlement_price"] == 103.0
    assert labeled.iloc[0]["outcome"] == Outcome.UP.value
    assert labeled.iloc[1]["outcome"] == Outcome.TIE.value
    assert labeled.iloc[-5:]["outcome"].isna().all()


def test_tie_tolerance_is_explicit() -> None:
    frame = pd.DataFrame({"close": [100.0, 100.005], "close_time": pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z"])})
    labeled = add_expiry_labels(frame, SettlementRule(horizon_steps=1, tie_tolerance=0.01))
    assert labeled.iloc[0]["outcome"] == Outcome.TIE.value


def test_entry_delay_and_execution_offset_are_explicit_scenarios() -> None:
    frame = pd.DataFrame({
        "close": [100.0, 101.0, 102.0, 103.0],
        "close_time": pd.to_datetime([
            "2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z",
            "2026-01-01T00:02:00Z", "2026-01-01T00:03:00Z",
        ]),
    })
    labeled = add_expiry_labels(frame, SettlementRule(
        horizon_steps=2, entry_delay_steps=1, execution_offset_bps=10
    ))
    assert labeled.iloc[0]["analysis_price"] == 100.0
    assert labeled.iloc[0]["reference_price"] == pytest.approx(101.101)
    assert labeled.iloc[0]["settlement_price"] == 103.0
