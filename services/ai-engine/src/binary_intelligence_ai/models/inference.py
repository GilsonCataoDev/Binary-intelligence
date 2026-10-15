from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from binary_intelligence_ai.data.contracts import DataQuality
from binary_intelligence_ai.models.baselines import Decision


class InferenceResult(BaseModel):
    """Versioned boundary for an auditable model response."""

    model_config = ConfigDict(frozen=True)

    contract_version: str = Field(default="1.0.0", pattern=r"^1\.")
    asset: str = Field(min_length=1, max_length=40)
    timestamp: datetime
    market_regime: str = Field(min_length=1, max_length=40)
    horizon_seconds: int = Field(gt=0)
    decision: Decision
    probability_up: float = Field(ge=0, le=1)
    probability_down: float = Field(ge=0, le=1)
    confidence_calibrated: bool
    expected_value: float | None = None
    payout: float | None = Field(default=None, gt=0, le=1)
    reasons: tuple[str, ...]
    data_quality: DataQuality
    model_version: str = Field(min_length=1, max_length=120)
    feature_set_version: str = Field(min_length=1, max_length=120)

    @field_validator("asset", mode="before")
    @classmethod
    def normalize_asset(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("market_regime", "model_version", "feature_set_version", mode="before")
    @classmethod
    def strip_identifier(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)

    @field_validator("reasons", mode="before")
    @classmethod
    def normalize_reasons(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)):
            return value
        normalized = tuple(reason.strip() if isinstance(reason, str) else reason for reason in value)
        if any(not isinstance(reason, str) or not reason for reason in normalized):
            raise ValueError("reasons must contain non-empty strings")
        return normalized

    @model_validator(mode="after")
    def validate_semantics(self) -> InferenceResult:
        if abs(self.probability_up + self.probability_down - 1.0) > 1e-9:
            raise ValueError("up and down probabilities must sum to one")
        if self.data_quality != DataQuality.VALID and self.decision != Decision.ABSTAIN:
            raise ValueError("invalid or stale data requires ABSTAIN")
        if self.decision == Decision.ABSTAIN and not self.reasons:
            raise ValueError("ABSTAIN requires at least one reason")
        if (self.expected_value is None) != (self.payout is None):
            raise ValueError("expected_value and payout must be supplied together")
        return self
