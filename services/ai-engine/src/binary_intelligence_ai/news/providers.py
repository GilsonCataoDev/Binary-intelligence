from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from .contracts import NewsAvailability, NewsContext, NewsEvent, NewsQuery


class NewsProvider(ABC):
    @abstractmethod
    def get_context(self, query: NewsQuery, *, as_of: datetime) -> NewsContext:
        """Return only information available by as_of, without inventing coverage."""


class JsonNewsProvider(NewsProvider):
    """Reproducible local fixture provider; never represents a live feed."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def get_context(self, query: NewsQuery, *, as_of: datetime) -> NewsContext:
        as_of = _utc(as_of)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        events = tuple(NewsEvent.model_validate(item) for item in payload)
        selected = tuple(
            event for event in events
            if set(event.affected_assets) & set(query.assets)
            and _in_window(event, query)
            and (event.published_at is None or event.published_at <= as_of)
            and event.ingested_at <= as_of
        )
        return NewsContext(availability=NewsAvailability.AVAILABLE, as_of=as_of, events=selected)


class UnavailableNewsProvider(NewsProvider):
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def get_context(self, query: NewsQuery, *, as_of: datetime) -> NewsContext:
        return NewsContext(
            availability=NewsAvailability.UNAVAILABLE,
            as_of=_utc(as_of),
            limitation=self.reason,
        )


def _in_window(event: NewsEvent, query: NewsQuery) -> bool:
    reference = event.event_at or event.published_at
    return reference is not None and query.start <= reference < query.end


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("as_of must include a timezone")
    return value.astimezone(timezone.utc)
