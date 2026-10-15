from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from binary_intelligence_ai.models.holdout import HoldoutEvidence
from binary_intelligence_ai.models.promotion import PromotionAssessment
from binary_intelligence_ai.models.registry import ModelRegistry, ModelStatus, ModelVersion
from binary_intelligence_ai.models.storage import (
    ModelRegistryBase, ModelRegistryRepository, ModelVersionRecord, MonitoringAssessmentRecord,
)
from binary_intelligence_ai.monitoring import MonitoringStatus, assess_monitoring


def _version(name: str, fingerprint: str = "a" * 64) -> ModelVersion:
    return ModelVersion(
        version=name,
        feature_set_version="technical-v1",
        dataset_fingerprint=fingerprint,
        artifact_uri=f"models/{name}.joblib",
        artifact_checksum="b" * 64,
        metrics={"brier_score": 0.2},
    )


def _approval(name: str, fingerprint: str = "a" * 64) -> tuple[PromotionAssessment, HoldoutEvidence]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assessment = PromotionAssessment(
        baseline="frequency", candidate=name, approved=True, holdout_confirmed=True,
        brier_improvement=0.01, fold_win_rate=1.0, expected_calibration_error=0.03,
        reasons=(),
    )
    evidence = HoldoutEvidence(
        dataset_fingerprint=fingerprint,
        observation_fingerprint="c" * 64,
        candidate_version=name,
        baseline_version="frequency",
        training_end=start,
        holdout_start=start + timedelta(days=1),
        holdout_observations=300,
    )
    return assessment, evidence


def test_distribution_shift_and_calibration_failure_pause_the_model() -> None:
    rng = np.random.default_rng(7)
    reference = pd.DataFrame({"rsi": rng.normal(50, 5, 300), "volatility": rng.normal(1, 0.1, 300)})
    current = pd.DataFrame({"rsi": rng.normal(90, 2, 300), "volatility": rng.normal(3, 0.1, 300)})

    assessment = assess_monitoring(
        reference, current,
        probabilities_up=np.full(300, 0.99), outcomes_up=np.zeros(300),
    )

    assert assessment.status == MonitoringStatus.BLOCKED
    assert assessment.should_pause
    assert assessment.maximum_psi is not None and assessment.maximum_psi >= 0.25
    assert assessment.brier_score is not None and assessment.brier_score >= 0.30


def test_monitoring_reports_insufficient_data_without_inventing_metrics() -> None:
    frame = pd.DataFrame({"rsi": np.arange(10)})

    assessment = assess_monitoring(frame, frame)

    assert assessment.status == MonitoringStatus.INSUFFICIENT_DATA
    assert not assessment.should_pause
    assert assessment.brier_score is None


def test_calibration_failure_blocks_without_feature_drift() -> None:
    rng = np.random.default_rng(19)
    reference = pd.DataFrame({"rsi": rng.normal(50, 5, 300)})

    assessment = assess_monitoring(
        reference, reference.copy(),
        probabilities_up=np.full(300, 0.99), outcomes_up=np.zeros(300),
    )

    assert assessment.maximum_psi == 0
    assert assessment.expected_calibration_error is not None
    assert assessment.expected_calibration_error >= 0.12
    assert assessment.status == MonitoringStatus.BLOCKED


def test_registry_rejects_unapproved_candidate_and_rolls_back() -> None:
    registry = ModelRegistry()
    first, second = _version("model-v1"), _version("model-v2")
    registry.register(first)
    rejected, evidence = _approval("model-v1")
    rejected = rejected.model_copy(update={"approved": False})
    with pytest.raises(ValueError, match="not approved"):
        registry.promote("model-v1", rejected, evidence)

    approved, evidence = _approval("model-v1")
    registry.promote("model-v1", approved, evidence)
    registry.register(second)
    approved, evidence = _approval("model-v2")
    registry.promote("model-v2", approved, evidence)
    drift = assess_monitoring(
        pd.DataFrame({"x": np.arange(300)}),
        pd.DataFrame({"x": np.arange(300) + 1000}),
        probabilities_up=np.full(300, 0.99), outcomes_up=np.zeros(300),
    )
    registry.pause_active(drift)

    restored = registry.rollback(reason="monitoring threshold breached")

    assert restored.version == "model-v1"
    assert restored.status == ModelStatus.ACTIVE
    assert next(item for item in registry.versions if item.version == "model-v2").status == ModelStatus.ROLLED_BACK
    assert registry.events[-1].event_type == "rolled_back"


def test_registry_repository_persists_version_status() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    ModelRegistryBase.metadata.create_all(engine)
    with Session(engine) as session:
        repository = ModelRegistryRepository(session)
        version = _version("model-v1")
        repository.save_version(version)
        repository.save_version(version.model_copy(update={"status": ModelStatus.ACTIVE}))
        frame = pd.DataFrame({"rsi": np.arange(10)})
        repository.save_assessment(
            model_version="model-v1",
            assessed_at=datetime.now(timezone.utc),
            assessment=assess_monitoring(frame, frame),
        )

        record = session.scalar(select(ModelVersionRecord))
        assert record is not None and record.status == "active"
        monitoring = session.scalar(select(MonitoringAssessmentRecord))
        assert monitoring is not None and monitoring.status == "insufficient_data"
