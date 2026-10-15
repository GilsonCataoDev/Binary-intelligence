from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from binary_intelligence_ai.models.holdout import HoldoutEvidence
from binary_intelligence_ai.models.promotion import PromotionAssessment
from binary_intelligence_ai.monitoring import MonitoringAssessment


class ModelStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    RETIRED = "retired"
    PAUSED = "paused"
    ROLLED_BACK = "rolled_back"


class ModelVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1, max_length=120)
    feature_set_version: str = Field(min_length=1, max_length=120)
    dataset_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_uri: str
    artifact_checksum: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: ModelStatus = ModelStatus.CANDIDATE
    metrics: dict[str, float] = Field(default_factory=dict)


class ModelEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    occurred_at: datetime
    event_type: str
    model_version: str
    previous_version: str | None = None
    reason: str


class ModelRegistry:
    """Registro controlado pelo operador; modelos não promovem nem ajustam risco sozinhos."""

    def __init__(self) -> None:
        self._versions: dict[str, ModelVersion] = {}
        self._events: list[ModelEvent] = []
        self._activation_order: list[str] = []

    @property
    def versions(self) -> tuple[ModelVersion, ...]:
        return tuple(self._versions.values())

    @property
    def events(self) -> tuple[ModelEvent, ...]:
        return tuple(self._events)

    @property
    def active(self) -> ModelVersion | None:
        return next((item for item in self._versions.values() if item.status == ModelStatus.ACTIVE), None)

    def register(self, version: ModelVersion) -> None:
        if version.version in self._versions:
            raise ValueError(f"model version {version.version} is already registered")
        if version.status != ModelStatus.CANDIDATE:
            raise ValueError("new model versions must be registered as candidates")
        self._versions[version.version] = version
        self._record("registered", version.version, "candidate registered")

    def promote(self, version: str, assessment: PromotionAssessment, evidence: HoldoutEvidence) -> None:
        target = self._require(version)
        if target.status != ModelStatus.CANDIDATE:
            raise ValueError("only candidate models can be promoted")
        if not assessment.approved or not assessment.holdout_confirmed:
            raise ValueError("promotion assessment is not approved with holdout evidence")
        if assessment.candidate != version or evidence.candidate_version != version:
            raise ValueError("promotion evidence belongs to another model version")
        if evidence.dataset_fingerprint != target.dataset_fingerprint:
            raise ValueError("holdout dataset fingerprint does not match the registry")
        previous = self.active
        if previous is not None:
            self._versions[previous.version] = previous.model_copy(update={"status": ModelStatus.RETIRED})
        self._versions[version] = target.model_copy(update={"status": ModelStatus.ACTIVE})
        self._activation_order.append(version)
        self._record("promoted", version, "approved untouched holdout", previous.version if previous else None)

    def pause_active(self, assessment: MonitoringAssessment) -> None:
        active = self.active
        if active is None:
            raise ValueError("there is no active model to pause")
        if not assessment.should_pause:
            raise ValueError("monitoring assessment does not require a pause")
        self._versions[active.version] = active.model_copy(update={"status": ModelStatus.PAUSED})
        self._record("paused", active.version, "; ".join(assessment.reasons) or "monitoring threshold breached")

    def rollback(self, *, reason: str) -> ModelVersion:
        current = self.active
        source = current
        if source is None and self._activation_order:
            latest = self._versions[self._activation_order[-1]]
            source = latest if latest.status == ModelStatus.PAUSED else None
        if source is None:
            raise ValueError("there is no active or paused model to roll back")
        prior = next(
            (
                name for name in reversed(self._activation_order[:-1])
                if name != source.version and self._versions[name].status in {
                    ModelStatus.RETIRED, ModelStatus.PAUSED, ModelStatus.ROLLED_BACK,
                }
            ),
            None,
        )
        if prior is None:
            raise ValueError("there is no previously active model available for rollback")
        self._versions[source.version] = source.model_copy(update={"status": ModelStatus.ROLLED_BACK})
        target = self._versions[prior]
        self._versions[prior] = target.model_copy(update={"status": ModelStatus.ACTIVE})
        self._activation_order.append(prior)
        self._record("rolled_back", prior, reason, source.version)
        return self._versions[prior]

    def _require(self, version: str) -> ModelVersion:
        if version not in self._versions:
            raise KeyError(f"unknown model version {version}")
        return self._versions[version]

    def _record(self, event_type: str, version: str, reason: str, previous: str | None = None) -> None:
        self._events.append(ModelEvent(
            occurred_at=datetime.now(timezone.utc), event_type=event_type,
            model_version=version, previous_version=previous, reason=reason,
        ))
