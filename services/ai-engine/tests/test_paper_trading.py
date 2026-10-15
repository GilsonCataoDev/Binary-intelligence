from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from binary_intelligence_ai.decisions.engine import DecisionOutcome
from binary_intelligence_ai.models.baselines import Decision
from binary_intelligence_ai.risk.controls import RiskLimits, RiskManager
from binary_intelligence_ai.simulation.paper import PaperTradingEngine, TradeStatus


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def engine() -> PaperTradingEngine:
    risk = RiskManager(initial_balance=Decimal("100"), limits=RiskLimits(), now=NOW)
    return PaperTradingEngine(risk)


def approved_call() -> DecisionOutcome:
    return DecisionOutcome(
        decision=Decision.CALL,
        payout=0.8,
        probability_used=0.6,
        expected_value=0.08,
        break_even_probability=1 / 1.8,
        reasons=("positive expected value",),
    )


def test_paper_trade_is_idempotent_and_settles_at_expiration() -> None:
    paper = engine()
    arguments = {
        "idempotency_key": "prediction-1", "asset": "eurusd", "outcome": approved_call(),
        "opened_at": NOW, "expires_at": NOW + timedelta(minutes=5),
        "reference_price": Decimal("1.1000"), "payout": Decimal("0.8"),
        "stake": Decimal("1"), "model_version": "approved-v1",
    }
    trade = paper.open_trade(**arguments)
    assert paper.open_trade(**arguments).id == trade.id
    assert len(paper.trades) == 1
    with pytest.raises(ValueError):
        paper.settle_trade(trade.id, settled_at=NOW + timedelta(minutes=4), settlement_price=Decimal("1.2"))

    settled = paper.settle_trade(
        trade.id, settled_at=NOW + timedelta(minutes=5), settlement_price=Decimal("1.2")
    )
    assert settled.status == TradeStatus.WON
    assert settled.pnl == Decimal("0.8")
    assert paper.risk.snapshot.balance == Decimal("100.8")
    assert paper.risk.snapshot.open_exposure == 0


def test_abstention_never_creates_a_trade() -> None:
    paper = engine()
    outcome = approved_call().model_copy(update={"decision": Decision.ABSTAIN})
    with pytest.raises(ValueError):
        paper.open_trade(
            idempotency_key="prediction-2", asset="EURUSD", outcome=outcome,
            opened_at=NOW, expires_at=NOW + timedelta(minutes=5),
            reference_price=Decimal("1"), payout=Decimal("0.8"), stake=Decimal("1"),
            model_version="approved-v1",
        )


def test_trade_rejects_payout_different_from_decision() -> None:
    paper = engine()
    with pytest.raises(ValueError, match="payout differs"):
        paper.open_trade(
            idempotency_key="prediction-3", asset="EURUSD", outcome=approved_call(),
            opened_at=NOW, expires_at=NOW + timedelta(minutes=5),
            reference_price=Decimal("1"), payout=Decimal("0.7"), stake=Decimal("1"),
            model_version="approved-v1",
        )
