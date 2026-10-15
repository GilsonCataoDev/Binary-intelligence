from datetime import datetime, timezone

from binary_intelligence_ai.data.contracts import DataQuality
from binary_intelligence_ai.decisions.engine import DecisionContext, decide
from binary_intelligence_ai.models.baselines import Decision
from binary_intelligence_ai.models.inference import InferenceResult
from binary_intelligence_ai.news.guard import NewsGuardResult


NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def inference(**changes: object) -> InferenceResult:
    values = {
        "asset": "EURUSD", "timestamp": NOW, "market_regime": "ranging", "horizon_seconds": 300,
        "decision": Decision.ABSTAIN, "probability_up": 0.6, "probability_down": 0.4,
        "confidence_calibrated": True, "expected_value": None, "payout": None,
        "reasons": ("awaiting deterministic decision",), "data_quality": DataQuality.VALID,
        "model_version": "candidate-v1", "feature_set_version": "technical-v1",
    }
    values.update(changes)
    return InferenceResult(**values)


def context(**changes: object) -> DecisionContext:
    values = {
        "inference": inference(), "payout": 0.8, "payout_is_current": True, "model_approved": True,
        "news_guard": NewsGuardResult(blocked=False, reasons=(), blocking_event_ids=()),
        "risk_allowed": True,
    }
    values.update(changes)
    return DecisionContext(**values)


def test_decision_uses_payout_break_even_equation() -> None:
    result = decide(context())
    assert result.decision == Decision.CALL
    assert round(result.break_even_probability, 6) == 0.555556
    assert round(result.expected_value or 0, 6) == 0.08


def test_decision_abstains_when_any_independent_guard_fails() -> None:
    result = decide(context(
        model_approved=False,
        news_guard=NewsGuardResult(blocked=True, reasons=("event window",), blocking_event_ids=("event-1",)),
    ))
    assert result.decision == Decision.ABSTAIN
    assert "model is not approved" in result.reasons
    assert "event window" in result.reasons


def test_decision_abstains_when_expected_value_is_not_positive() -> None:
    result = decide(context(inference=inference(probability_up=0.53, probability_down=0.47)))
    assert result.decision == Decision.ABSTAIN
    assert "estimated value is not positive at the current payout" in result.reasons
