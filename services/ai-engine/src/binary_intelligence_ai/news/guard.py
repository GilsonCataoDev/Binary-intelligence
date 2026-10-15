from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field

from .contracts import EconomicImpact, NewsAvailability, NewsContext, NewsEvent


class EventBlackoutConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    minutes_before: int = Field(default=15, ge=0, le=1440)
    minutes_after: int = Field(default=15, ge=0, le=1440)
    blocked_impacts: frozenset[EconomicImpact] = frozenset({EconomicImpact.HIGH})
    block_when_unavailable: bool = True
    maximum_context_age_seconds: int = Field(default=300, ge=0, le=86400)


class NewsGuardResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    blocked: bool
    reasons: tuple[str, ...]
    blocking_event_ids: tuple[str, ...]


def evaluate_news_guard(
    context: NewsContext,
    *,
    asset: str,
    decision_time: datetime,
    config: EventBlackoutConfig = EventBlackoutConfig(),
) -> NewsGuardResult:
    decision_time = _utc(decision_time)
    reasons: list[str] = []
    blocking_ids: list[str] = []
    if context.as_of > decision_time:
        reasons.append("news context contains information from after the decision time")
    elif (decision_time - context.as_of).total_seconds() > config.maximum_context_age_seconds:
        reasons.append("news context is stale for the decision time")
    if context.availability != NewsAvailability.AVAILABLE and config.block_when_unavailable:
        reasons.append(f"news context is {context.availability.value}: {context.limitation}")

    normalized_asset = asset.strip().upper()
    for event in context.events:
        if normalized_asset not in event.affected_assets or event.reported_impact not in config.blocked_impacts:
            continue
        if _inside_blackout(event, decision_time, config):
            blocking_ids.append(event.source_event_id)
    if blocking_ids:
        reasons.append("decision falls inside an economic-event safety window")
    return NewsGuardResult(
        blocked=bool(reasons),
        reasons=tuple(reasons),
        blocking_event_ids=tuple(blocking_ids),
    )


def _inside_blackout(event: NewsEvent, decision_time: datetime, config: EventBlackoutConfig) -> bool:
    if event.event_at is not None:
        return (
            event.event_at - timedelta(minutes=config.minutes_before)
            <= decision_time
            <= event.event_at + timedelta(minutes=config.minutes_after)
        )
    assert event.published_at is not None
    return event.published_at <= decision_time <= event.published_at + timedelta(minutes=config.minutes_after)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("decision_time must include a timezone")
    return value.astimezone(timezone.utc)
