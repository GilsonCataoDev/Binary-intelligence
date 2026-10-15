from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from binary_intelligence_ai.decisions.engine import DecisionOutcome
from binary_intelligence_ai.models.baselines import Decision
from binary_intelligence_ai.risk.controls import RiskLimits, RiskManager
from binary_intelligence_ai.simulation.paper import PaperTradingEngine
from binary_intelligence_ai.simulation.storage import (
    PaperTradeRecord,
    PaperTradeRepository,
    RiskAuditRecord,
    SimulationBase,
)


def test_repository_upserts_settlement_and_keeps_paper_result_separate() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    risk = RiskManager(initial_balance=Decimal("100"), limits=RiskLimits(), now=now)
    paper = PaperTradingEngine(risk)
    outcome = DecisionOutcome(
        decision=Decision.PUT, payout=0.8, probability_used=0.6,
        expected_value=0.08, break_even_probability=1 / 1.8, reasons=("approved",)
    )
    trade = paper.open_trade(
        idempotency_key="unique-1", asset="EURUSD", outcome=outcome, opened_at=now,
        expires_at=now + timedelta(minutes=5), reference_price=Decimal("1.1"),
        payout=Decimal("0.8"), stake=Decimal("1"), model_version="model-v1",
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SimulationBase.metadata.create_all(engine)
    with Session(engine) as session:
        repository = PaperTradeRepository(session)
        repository.save(trade)
        settled = paper.settle_trade(
            trade.id, settled_at=now + timedelta(minutes=5), settlement_price=Decimal("1.0")
        )
        repository.save(settled)
        repository.audit(occurred_at=now, event_type="trade_settled", details={"status": "won"}, trade_id=trade.id)
        record = session.scalar(select(PaperTradeRecord))
        assert record is not None and record.status == "won" and record.result_type == "paper"
        assert len(list(session.scalars(select(RiskAuditRecord)))) == 1
