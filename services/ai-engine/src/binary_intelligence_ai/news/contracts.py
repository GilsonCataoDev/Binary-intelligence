from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EconomicImpact(StrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NewsAvailability(StrEnum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class NewsEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str = Field(min_length=1, max_length=120)
    source_event_id: str = Field(min_length=1, max_length=200)
    headline: str = Field(min_length=1, max_length=500)
    event_type: str = Field(min_length=1, max_length=80)
    published_at: datetime | None = None
    event_at: datetime | None = None
    affected_assets: tuple[str, ...] = Field(min_length=1)
    reported_impact: EconomicImpact = EconomicImpact.UNKNOWN
    ingested_at: datetime
    delayed: bool
    evidence: tuple[str, ...] = Field(min_length=1)

    @field_validator("source", "source_event_id", "headline", "event_type", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("evidence", mode="before")
    @classmethod
    def normalize_evidence(cls, value: object) -> object:
        if not isinstance(value, (list, tuple)):
            return value
        normalized = tuple(item.strip() if isinstance(item, str) else item for item in value)
        if any(not isinstance(item, str) or not item for item in normalized):
            raise ValueError("evidence entries must be non-empty strings")
        return normalized

    @field_validator("affected_assets")
    @classmethod
    def normalize_assets(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(asset.strip().upper() for asset in value if asset.strip()))
        if not normalized:
            raise ValueError("at least one affected asset is required")
        return normalized

    @field_validator("published_at", "event_at", "ingested_at")
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_timeline(self) -> NewsEvent:
        if self.published_at is None and self.event_at is None:
            raise ValueError("published_at or event_at is required")
        if self.published_at is not None and self.ingested_at < self.published_at:
            raise ValueError("ingested_at cannot precede published_at")
        return self


class NewsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    assets: tuple[str, ...] = Field(min_length=1)
    start: datetime
    end: datetime

    @field_validator("assets")
    @classmethod
    def normalize_assets(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(asset.strip().upper() for asset in value if asset.strip()))
        if not normalized:
            raise ValueError("at least one asset is required")
        return normalized

    @field_validator("start", "end")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_range(self) -> NewsQuery:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class NewsContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_version: str = Field(default="1.0.0", pattern=r"^1\.")
    availability: NewsAvailability
    as_of: datetime
    events: tuple[NewsEvent, ...] = ()
    limitation: str | None = None

    @field_validator("as_of")
    @classmethod
    def normalize_as_of(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def explain_missing_coverage(self) -> NewsContext:
        if self.availability != NewsAvailability.AVAILABLE and not self.limitation:
            raise ValueError("degraded or unavailable context requires a limitation")
        for event in self.events:
            if event.ingested_at > self.as_of:
                raise ValueError("context cannot contain events ingested after as_of")
            if event.published_at is not None and event.published_at > self.as_of:
                raise ValueError("context cannot contain news published after as_of")
        return self
