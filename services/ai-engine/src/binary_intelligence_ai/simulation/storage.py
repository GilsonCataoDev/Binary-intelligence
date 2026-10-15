from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Numeric, String, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .paper import PaperTrade


class SimulationBase(DeclarativeBase):
    pass


class PaperTradeRecord(SimulationBase):
    __tablename__ = "paper_trades"
    __table_args__ = (UniqueConstraint("idempotency_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    asset: Mapped[str] = mapped_column(String(40), nullable=False)
    decision: Mapped[str] = mapped_column(String(8), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reference_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    settlement_price: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    payout: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)
    stake: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    result_type: Mapped[str] = mapped_column(String(16), nullable=False, default="paper")


class RiskAuditRecord(SimulationBase):
    __tablename__ = "risk_audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    trade_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class PaperTradeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, trade: PaperTrade) -> None:
        record = self.session.scalar(select(PaperTradeRecord).where(
            PaperTradeRecord.idempotency_key == trade.idempotency_key
        ))
        values = trade.model_dump(mode="python")
        if record is None:
            record = PaperTradeRecord(
                id=trade.id,
                idempotency_key=trade.idempotency_key,
                asset=trade.asset,
                decision=trade.decision.value,
                opened_at=trade.opened_at,
                expires_at=trade.expires_at,
                reference_price=trade.reference_price,
                payout=trade.payout,
                stake=trade.stake,
                status=trade.status.value,
                model_version=trade.model_version,
                result_type="paper",
            )
            self.session.add(record)
        record.settled_at = values["settled_at"]
        record.settlement_price = values["settlement_price"]
        record.status = trade.status.value
        record.pnl = values["pnl"]
        self.session.commit()

    def audit(self, *, occurred_at: datetime, event_type: str, details: dict[str, Any], trade_id: str | None = None) -> None:
        self.session.add(RiskAuditRecord(
            occurred_at=occurred_at,
            event_type=event_type,
            trade_id=trade_id,
            details=details,
        ))
        self.session.commit()
