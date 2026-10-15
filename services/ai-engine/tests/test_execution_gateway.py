from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from binary_intelligence_ai.decisions.engine import DecisionOutcome
from binary_intelligence_ai.execution import (
    ExecutionGateway, ExecutionIntent, ExecutionPreflight,
    SimulatedExecutionProvider, UnavailableLiveExecutionProvider,
)
from binary_intelligence_ai.integrations import DerivIntegrationChecklist, evaluate_deriv_integration
from binary_intelligence_ai.models.baselines import Decision
from binary_intelligence_ai.risk.controls import RiskLimits, RiskManager
from binary_intelligence_ai.simulation.paper import PaperTradingEngine


def _intent(now: datetime) -> ExecutionIntent:
    return ExecutionIntent(
        idempotency_key="intent-1", asset="EURUSD",
        outcome=DecisionOutcome(
            decision=Decision.CALL, payout=0.8, probability_used=0.6,
            expected_value=0.08, break_even_probability=1 / 1.8, reasons=("approved",),
        ),
        opened_at=now, expires_at=now + timedelta(minutes=5),
        reference_price=Decimal("1.1"), payout=Decimal("0.8"),
        stake=Decimal("1"), model_version="model-v1",
    )


def _preflight(**updates: bool) -> ExecutionPreflight:
    values = {
        "bot_running": True, "data_fresh": True, "payout_current": True,
        "exposure_allowed": True, "loss_limits_clear": True, "provider_available": True,
        "execution_mode_authorized": True, "emergency_stop_clear": True,
    }
    values.update(updates)
    return ExecutionPreflight(**values)


def test_gateway_dispatches_only_after_all_simulation_checks_pass() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    risk = RiskManager(initial_balance=Decimal("100"), limits=RiskLimits(), now=now)
    gateway = ExecutionGateway(SimulatedExecutionProvider(PaperTradingEngine(risk)))

    trade = gateway.submit(_intent(now), _preflight())

    assert trade.idempotency_key == "intent-1"
    assert trade.result_type == "paper"


def test_gateway_blocks_stale_data_and_real_provider_independently() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    risk = RiskManager(initial_balance=Decimal("100"), limits=RiskLimits(), now=now)
    simulation = ExecutionGateway(SimulatedExecutionProvider(PaperTradingEngine(risk)))
    with pytest.raises(PermissionError, match="stale"):
        simulation.submit(_intent(now), _preflight(data_fresh=False))

    live = ExecutionGateway(UnavailableLiveExecutionProvider())
    with pytest.raises(PermissionError, match="not implemented or authorized"):
        live.submit(_intent(now), _preflight())


def test_deriv_defaults_to_no_go_until_account_checks_are_completed() -> None:
    decision = evaluate_deriv_integration(DerivIntegrationChecklist())

    assert decision.official_api_available
    assert not decision.public_discovery_ready
    assert not decision.demo_trading_ready
    assert not decision.real_trading_ready
    assert "pending: regional eligibility" in decision.reasons


def test_even_a_complete_demo_checklist_cannot_enable_real_trading() -> None:
    complete = DerivIntegrationChecklist(**{
        name: True for name in DerivIntegrationChecklist.model_fields
    })

    decision = evaluate_deriv_integration(complete)

    assert decision.demo_trading_ready
    assert not decision.real_trading_ready
    assert "Phase 12" in decision.reasons[-1]
