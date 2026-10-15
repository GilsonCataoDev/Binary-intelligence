from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from binary_intelligence_ai.decisions.engine import DecisionOutcome
from binary_intelligence_ai.models.baselines import Decision
from binary_intelligence_ai.risk.controls import RiskManager


class TradeStatus(StrEnum):
    OPEN = "open"
    WON = "won"
    LOST = "lost"
    PUSH = "push"


class PaperTrade(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    idempotency_key: str = Field(min_length=1, max_length=200)
    asset: str = Field(min_length=1, max_length=40)
    decision: Decision
    opened_at: datetime
    expires_at: datetime
    settled_at: datetime | None = None
    reference_price: Decimal = Field(gt=0)
    settlement_price: Decimal | None = Field(default=None, gt=0)
    payout: Decimal = Field(gt=0, le=1)
    stake: Decimal = Field(gt=0)
    status: TradeStatus
    pnl: Decimal | None = None
    model_version: str = Field(min_length=1, max_length=120)

    @field_validator("opened_at", "expires_at", "settled_at")
    @classmethod
    def utc_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)

    @field_validator("idempotency_key", "model_version", mode="before")
    @classmethod
    def strip_identifier(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("asset", mode="before")
    @classmethod
    def normalize_asset(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_trade(self) -> PaperTrade:
        if self.decision == Decision.ABSTAIN:
            raise ValueError("an abstention cannot create a paper trade")
        if self.expires_at <= self.opened_at:
            raise ValueError("expiration must be after opening")
        if self.status == TradeStatus.OPEN and (
            self.settled_at is not None or self.settlement_price is not None or self.pnl is not None
        ):
            raise ValueError("open trade cannot have settlement fields")
        if self.status != TradeStatus.OPEN and (
            self.settled_at is None or self.settlement_price is None or self.pnl is None
        ):
            raise ValueError("settled trade requires settlement price and pnl")
        return self


class PaperTradingEngine:
    def __init__(self, risk: RiskManager) -> None:
        self.risk = risk
        self._trades: dict[str, PaperTrade] = {}
        self._keys: dict[str, str] = {}

    @property
    def trades(self) -> tuple[PaperTrade, ...]:
        return tuple(self._trades.values())

    def open_trade(
        self,
        *,
        idempotency_key: str,
        asset: str,
        outcome: DecisionOutcome,
        opened_at: datetime,
        expires_at: datetime,
        reference_price: Decimal,
        payout: Decimal,
        stake: Decimal,
        model_version: str,
    ) -> PaperTrade:
        if idempotency_key in self._keys:
            return self._trades[self._keys[idempotency_key]]
        if outcome.decision == Decision.ABSTAIN:
            raise ValueError("ABSTAIN cannot create a paper trade")
        if Decimal(str(outcome.payout)) != payout:
            raise ValueError("paper trade payout differs from the approved decision")
        risk_decision = self.risk.check(stake=stake, now=opened_at)
        if not risk_decision.allowed:
            raise PermissionError("; ".join(risk_decision.reasons))
        trade = PaperTrade(
            id=str(uuid4()),
            idempotency_key=idempotency_key,
            asset=asset.strip().upper(),
            decision=outcome.decision,
            opened_at=opened_at,
            expires_at=expires_at,
            reference_price=reference_price,
            payout=payout,
            stake=stake,
            status=TradeStatus.OPEN,
            model_version=model_version,
        )
        self._trades[trade.id] = trade
        self._keys[idempotency_key] = trade.id
        self.risk.record_open(stake)
        return trade

    def settle_trade(self, trade_id: str, *, settled_at: datetime, settlement_price: Decimal) -> PaperTrade:
        trade = self._trades[trade_id]
        settled_at = _utc(settled_at)
        if trade.status != TradeStatus.OPEN:
            return trade
        if settled_at < trade.expires_at:
            raise ValueError("trade cannot settle before expiration")
        if settlement_price <= 0:
            raise ValueError("settlement price must be positive")
        won = (
            trade.decision == Decision.CALL and settlement_price > trade.reference_price
        ) or (
            trade.decision == Decision.PUT and settlement_price < trade.reference_price
        )
        tied = settlement_price == trade.reference_price
        status = TradeStatus.PUSH if tied else TradeStatus.WON if won else TradeStatus.LOST
        pnl = Decimal("0") if tied else trade.stake * trade.payout if won else -trade.stake
        values = trade.model_dump()
        values.update(settled_at=settled_at, settlement_price=settlement_price, status=status, pnl=pnl)
        settled = PaperTrade.model_validate(values)
        self._trades[trade_id] = settled
        self.risk.record_settlement(stake=trade.stake, pnl=pnl, now=settled_at)
        return settled


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value.astimezone(timezone.utc)
