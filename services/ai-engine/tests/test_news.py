import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from binary_intelligence_ai.news.contracts import (
    EconomicImpact,
    NewsAvailability,
    NewsContext,
    NewsEvent,
    NewsQuery,
)
from binary_intelligence_ai.news.guard import EventBlackoutConfig, evaluate_news_guard
from binary_intelligence_ai.news.providers import JsonNewsProvider, UnavailableNewsProvider


UTC = timezone.utc
NOW = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)


def make_event(**changes: object) -> NewsEvent:
    values = {
        "source": "OFFICIAL_CALENDAR",
        "source_event_id": "usd-payroll-2026-01",
        "headline": "Payroll release",
        "event_type": "employment",
        "published_at": NOW - timedelta(hours=1),
        "event_at": NOW,
        "affected_assets": ("eurusd", "USDJPY"),
        "reported_impact": EconomicImpact.HIGH,
        "ingested_at": NOW - timedelta(minutes=59),
        "delayed": False,
        "evidence": ("https://example.test/calendar/event",),
    }
    values.update(changes)
    return NewsEvent(**values)


def test_news_event_requires_verifiable_time_and_chronology() -> None:
    with pytest.raises(ValidationError):
        make_event(published_at=None, event_at=None)
    with pytest.raises(ValidationError):
        make_event(ingested_at=NOW - timedelta(hours=2))
    assert make_event().affected_assets == ("EURUSD", "USDJPY")


def test_json_provider_filters_assets_window_and_information_time(tmp_path) -> None:
    visible = make_event()
    future_ingestion = make_event(
        source_event_id="future",
        published_at=NOW,
        event_at=NOW + timedelta(minutes=5),
        ingested_at=NOW + timedelta(minutes=1),
    )
    path = tmp_path / "events.json"
    path.write_text(json.dumps([visible.model_dump(mode="json"), future_ingestion.model_dump(mode="json")]), encoding="utf-8")
    query = NewsQuery(assets=("EURUSD",), start=NOW - timedelta(minutes=5), end=NOW + timedelta(minutes=10))

    context = JsonNewsProvider(path).get_context(query, as_of=NOW)

    assert [event.source_event_id for event in context.events] == [visible.source_event_id]


def test_guard_blocks_high_impact_window_and_missing_coverage() -> None:
    context = NewsContext(availability=NewsAvailability.AVAILABLE, as_of=NOW, events=(make_event(),))
    blocked = evaluate_news_guard(context, asset="eurusd", decision_time=NOW - timedelta(minutes=10))
    clear = evaluate_news_guard(context, asset="EURUSD", decision_time=NOW - timedelta(minutes=16))
    unavailable = UnavailableNewsProvider("no authorized feed configured").get_context(
        NewsQuery(assets=("EURUSD",), start=NOW, end=NOW + timedelta(minutes=1)), as_of=NOW
    )

    assert blocked.blocked and blocked.blocking_event_ids == ("usd-payroll-2026-01",)
    assert not clear.blocked
    assert evaluate_news_guard(unavailable, asset="EURUSD", decision_time=NOW).blocked


def test_breaking_news_never_blocks_before_publication() -> None:
    event = make_event(event_at=None, published_at=NOW, ingested_at=NOW)
    context = NewsContext(availability=NewsAvailability.AVAILABLE, as_of=NOW, events=(event,))
    config = EventBlackoutConfig(minutes_after=10)

    assert not evaluate_news_guard(context, asset="EURUSD", decision_time=NOW - timedelta(seconds=1), config=config).blocked
    assert evaluate_news_guard(context, asset="EURUSD", decision_time=NOW, config=config).blocked
