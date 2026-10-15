from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from binary_intelligence_ai.risk.controls import RiskLimits, RiskManager


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def manager(**limits: object) -> RiskManager:
    return RiskManager(
        initial_balance=Decimal("100"),
        limits=RiskLimits(**limits),
        now=NOW,
    )


def test_exposure_and_consecutive_loss_limits_are_independent() -> None:
    risk = manager(maximum_exposure=Decimal("1"), maximum_consecutive_losses=2)
    assert risk.check(stake=Decimal("1"), now=NOW).allowed
    risk.record_open(Decimal("1"))
    assert not risk.check(stake=Decimal("1"), now=NOW).allowed
    risk.record_settlement(stake=Decimal("1"), pnl=Decimal("-1"), now=NOW)
    risk.record_open(Decimal("1"))
    risk.record_settlement(stake=Decimal("1"), pnl=Decimal("-1"), now=NOW)
    assert "consecutive loss limit reached" in risk.check(stake=Decimal("1"), now=NOW).reasons


def test_daily_counters_reset_without_resetting_balance_or_peak() -> None:
    risk = manager(maximum_daily_operations=1)
    risk.record_open(Decimal("1"))
    risk.record_settlement(stake=Decimal("1"), pnl=Decimal("-1"), now=NOW)
    assert not risk.check(stake=Decimal("1"), now=NOW).allowed
    assert risk.check(stake=Decimal("1"), now=NOW + timedelta(days=1)).allowed
    assert risk.snapshot.balance == Decimal("99")


def test_emergency_stop_requires_explicit_clearance() -> None:
    risk = manager()
    risk.emergency_stop()
    assert not risk.check(stake=Decimal("1"), now=NOW).allowed
    with pytest.raises(PermissionError):
        risk.clear_emergency_stop(explicitly_authorized=False)
    risk.clear_emergency_stop(explicitly_authorized=True)
    assert risk.check(stake=Decimal("1"), now=NOW).allowed


def test_settlement_after_midnight_is_recorded_on_new_utc_day() -> None:
    risk = manager()
    risk.record_open(Decimal("1"))
    tomorrow = NOW + timedelta(days=1)
    risk.record_settlement(stake=Decimal("1"), pnl=Decimal("-1"), now=tomorrow)
    assert risk.snapshot.session_date == tomorrow.date()
    assert risk.snapshot.daily_pnl == Decimal("-1")
