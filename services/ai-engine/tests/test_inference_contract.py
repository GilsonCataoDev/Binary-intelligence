from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from binary_intelligence_ai.data.contracts import DataQuality
from binary_intelligence_ai.models.baselines import Decision
from binary_intelligence_ai.models.inference import InferenceResult


def result(**changes: object) -> InferenceResult:
    values = {
        "asset": "eurusd",
        "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "market_regime": "ranging",
        "horizon_seconds": 300,
        "decision": Decision.ABSTAIN,
        "probability_up": 0.52,
        "probability_down": 0.48,
        "confidence_calibrated": True,
        "expected_value": None,
        "payout": None,
        "reasons": ("insufficient expected value",),
        "data_quality": DataQuality.VALID,
        "model_version": "logistic-v1",
        "feature_set_version": "technical-v1",
    }
    values.update(changes)
    return InferenceResult(**values)


def test_inference_contract_normalizes_and_preserves_audit_fields() -> None:
    inference = result()
    assert inference.asset == "EURUSD"
    assert inference.probability_up + inference.probability_down == 1


def test_inference_contract_rejects_incoherent_probabilities() -> None:
    with pytest.raises(ValidationError):
        result(probability_down=0.49)


def test_inference_contract_forces_abstention_for_bad_data() -> None:
    with pytest.raises(ValidationError):
        result(data_quality=DataQuality.STALE, decision=Decision.CALL)
