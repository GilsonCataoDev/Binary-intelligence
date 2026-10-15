from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from binary_intelligence_ai.decisions.engine import DecisionOutcome
from binary_intelligence_ai.simulation.paper import PaperTradingEngine


class ExecutionMode(StrEnum):
    SIMULATION = "simulation"
    REAL = "real"


class ExecutionIntent(BaseModel):
    model_config = ConfigDict(frozen=True)

    idempotency_key: str = Field(min_length=1, max_length=200)
    asset: str = Field(min_length=1, max_length=40)
    outcome: DecisionOutcome
    opened_at: datetime
    expires_at: datetime
    reference_price: Decimal = Field(gt=0)
    payout: Decimal = Field(gt=0, le=1)
    stake: Decimal = Field(gt=0)
    model_version: str = Field(min_length=1, max_length=120)


class ExecutionPreflight(BaseModel):
    model_config = ConfigDict(frozen=True)

    bot_running: bool
    data_fresh: bool
    payout_current: bool
    exposure_allowed: bool
    loss_limits_clear: bool
    provider_available: bool
    execution_mode_authorized: bool
    emergency_stop_clear: bool


class ExecutionReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)

    idempotency_key: str
    provider: str
    mode: ExecutionMode
    provider_reference: str
    accepted_at: datetime
    result_type: Literal["paper", "real"]


class ExecutionProvider(ABC):
    mode: ExecutionMode

    @abstractmethod
    def submit(self, intent: ExecutionIntent) -> ExecutionReceipt:
        """Submit an idempotent intent after the gateway preflight."""


class SimulatedExecutionProvider(ExecutionProvider):
    mode = ExecutionMode.SIMULATION

    def __init__(self, paper_engine: PaperTradingEngine) -> None:
        self.paper_engine = paper_engine

    def submit(self, intent: ExecutionIntent) -> ExecutionReceipt:
        trade = self.paper_engine.open_trade(
            idempotency_key=intent.idempotency_key,
            asset=intent.asset,
            outcome=intent.outcome,
            opened_at=intent.opened_at,
            expires_at=intent.expires_at,
            reference_price=intent.reference_price,
            payout=intent.payout,
            stake=intent.stake,
            model_version=intent.model_version,
        )
        return ExecutionReceipt(
            idempotency_key=intent.idempotency_key,
            provider="paper-engine",
            mode=self.mode,
            provider_reference=trade.id,
            accepted_at=trade.opened_at,
            result_type="paper",
        )


class UnavailableLiveExecutionProvider(ExecutionProvider):
    mode = ExecutionMode.REAL

    def submit(self, intent: ExecutionIntent) -> ExecutionReceipt:
        raise PermissionError("real execution provider is unavailable")


class ExecutionGateway:
    """Independent safety boundary that cannot dispatch real orders in this release."""

    def __init__(self, provider: ExecutionProvider) -> None:
        self.provider = provider

    def submit(self, intent: ExecutionIntent, preflight: ExecutionPreflight) -> ExecutionReceipt:
        blockers = _preflight_blockers(preflight)
        if self.provider.mode == ExecutionMode.REAL:
            blockers.append("real execution is not implemented or authorized in this release")
        if blockers:
            raise PermissionError("; ".join(blockers))
        return self.provider.submit(intent)


def _preflight_blockers(preflight: ExecutionPreflight) -> list[str]:
    checks = (
        (preflight.bot_running, "bot is not running"),
        (preflight.data_fresh, "market data is stale"),
        (preflight.payout_current, "current payout is unavailable"),
        (preflight.exposure_allowed, "exposure limit rejected the intent"),
        (preflight.loss_limits_clear, "loss limit rejected the intent"),
        (preflight.provider_available, "execution provider is unavailable"),
        (preflight.execution_mode_authorized, "execution mode is not explicitly authorized"),
        (preflight.emergency_stop_clear, "emergency stop is active"),
    )
    return [reason for allowed, reason in checks if not allowed]
