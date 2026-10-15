from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from binary_intelligence_ai.monitoring import MonitoringAssessment

from .registry import ModelEvent, ModelVersion


class ModelRegistryBase(DeclarativeBase):
    pass


class ModelVersionRecord(ModelRegistryBase):
    __tablename__ = "model_versions"

    version: Mapped[str] = mapped_column(String(120), primary_key=True)
    feature_set_version: Mapped[str] = mapped_column(String(120), nullable=False)
    dataset_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    artifact_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column("metrics_json", JSON, nullable=False)


class ModelEventRecord(ModelRegistryBase):
    __tablename__ = "model_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    previous_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)


class MonitoringAssessmentRecord(ModelRegistryBase):
    __tablename__ = "monitoring_assessments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    should_pause: Mapped[bool] = mapped_column(nullable=False)
    maximum_psi: Mapped[float | None] = mapped_column(nullable=True)
    observations: Mapped[int] = mapped_column(nullable=False)
    brier_score: Mapped[float | None] = mapped_column(nullable=True)
    expected_calibration_error: Mapped[float | None] = mapped_column(nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ModelRegistryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_version(self, version: ModelVersion) -> None:
        record = self.session.get(ModelVersionRecord, version.version)
        values = version.model_dump(mode="python")
        if record is None:
            record = ModelVersionRecord(**values)
            self.session.add(record)
        else:
            for key, value in values.items():
                setattr(record, key, value.value if hasattr(value, "value") else value)
        record.status = version.status.value
        self.session.commit()

    def append_event(self, event: ModelEvent) -> None:
        self.session.add(ModelEventRecord(**event.model_dump(mode="python")))
        self.session.commit()

    def save_assessment(
        self, *, model_version: str, assessed_at: datetime, assessment: MonitoringAssessment
    ) -> None:
        self.session.add(MonitoringAssessmentRecord(
            assessed_at=assessed_at,
            model_version=model_version,
            status=assessment.status.value,
            should_pause=assessment.should_pause,
            maximum_psi=assessment.maximum_psi,
            observations=assessment.observations,
            brier_score=assessment.brier_score,
            expected_calibration_error=assessment.expected_calibration_error,
            details={"feature_psi": assessment.feature_psi, "reasons": list(assessment.reasons)},
        ))
        self.session.commit()

    def status(self, version: str) -> str | None:
        return self.session.scalar(select(ModelVersionRecord.status).where(ModelVersionRecord.version == version))
