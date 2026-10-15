from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RiskLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    maximum_exposure: Decimal = Field(default=Decimal("1"), gt=0)
    daily_loss_limit: Decimal = Field(default=Decimal("3"), gt=0)
    maximum_drawdown: Decimal = Field(default=Decimal("5"), gt=0)
    maximum_daily_operations: int = Field(default=20, gt=0)
    maximum_consecutive_losses: int = Field(default=3, gt=0)
    maximum_operational_errors: int = Field(default=3, gt=0)
    maximum_stake: Decimal = Field(default=Decimal("1"), gt=0)


class RiskSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_date: date
    balance: Decimal
    peak_balance: Decimal
    open_exposure: Decimal
    daily_pnl: Decimal
    daily_operations: int
    consecutive_losses: int
    operational_errors: int
    paused: bool
    emergency_stopped: bool


class RiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed: bool
    reasons: tuple[str, ...]


class RiskManager:
    def __init__(self, *, initial_balance: Decimal, limits: RiskLimits, now: datetime) -> None:
        if initial_balance <= 0:
            raise ValueError("initial balance must be positive")
        current = _utc(now)
        self.limits = limits
        self._session_date = current.date()
        self._balance = initial_balance
        self._peak_balance = initial_balance
        self._open_exposure = Decimal("0")
        self._daily_pnl = Decimal("0")
        self._daily_operations = 0
        self._consecutive_losses = 0
        self._operational_errors = 0
        self._paused = False
        self._emergency_stopped = False

    @property
    def snapshot(self) -> RiskSnapshot:
        return RiskSnapshot(
            session_date=self._session_date,
            balance=self._balance,
            peak_balance=self._peak_balance,
            open_exposure=self._open_exposure,
            daily_pnl=self._daily_pnl,
            daily_operations=self._daily_operations,
            consecutive_losses=self._consecutive_losses,
            operational_errors=self._operational_errors,
            paused=self._paused,
            emergency_stopped=self._emergency_stopped,
        )

    def check(self, *, stake: Decimal, now: datetime, data_stale: bool = False, volatility_extreme: bool = False) -> RiskDecision:
        self._roll_day(_utc(now).date())
        reasons: list[str] = []
        if stake <= 0 or stake > self.limits.maximum_stake:
            reasons.append("stake exceeds the configured fixed limit")
        if self._emergency_stopped:
            reasons.append("emergency stop is active")
        if self._paused:
            reasons.append("risk manager is paused")
        if self._open_exposure + max(stake, Decimal("0")) > self.limits.maximum_exposure:
            reasons.append("maximum exposure would be exceeded")
        if -self._daily_pnl >= self.limits.daily_loss_limit:
            reasons.append("daily loss limit reached")
        if self._peak_balance - self._balance >= self.limits.maximum_drawdown:
            reasons.append("maximum drawdown reached")
        if self._daily_operations >= self.limits.maximum_daily_operations:
            reasons.append("daily operation limit reached")
        if self._consecutive_losses >= self.limits.maximum_consecutive_losses:
            reasons.append("consecutive loss limit reached")
        if self._operational_errors >= self.limits.maximum_operational_errors:
            reasons.append("operational circuit breaker is active")
        if data_stale:
            reasons.append("market data is stale")
        if volatility_extreme:
            reasons.append("extreme volatility safety block")
        return RiskDecision(allowed=not reasons, reasons=tuple(reasons))

    def record_open(self, stake: Decimal) -> None:
        self._open_exposure += stake
        self._daily_operations += 1

    def record_settlement(self, *, stake: Decimal, pnl: Decimal, now: datetime) -> None:
        self._roll_day(_utc(now).date())
        self._open_exposure = max(Decimal("0"), self._open_exposure - stake)
        self._balance += pnl
        self._daily_pnl += pnl
        self._peak_balance = max(self._peak_balance, self._balance)
        self._consecutive_losses = self._consecutive_losses + 1 if pnl < 0 else 0

    def record_operational_error(self) -> None:
        self._operational_errors += 1

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def emergency_stop(self) -> None:
        self._emergency_stopped = True

    def clear_emergency_stop(self, *, explicitly_authorized: bool) -> None:
        if not explicitly_authorized:
            raise PermissionError("explicit authorization is required")
        self._emergency_stopped = False

    def _roll_day(self, current_date: date) -> None:
        if current_date <= self._session_date:
            return
        self._session_date = current_date
        self._daily_pnl = Decimal("0")
        self._daily_operations = 0
        self._consecutive_losses = 0
        self._operational_errors = 0


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(timezone.utc)
