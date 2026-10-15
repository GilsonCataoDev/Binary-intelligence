from datetime import datetime, timedelta, timezone

from binary_intelligence_ai.data.contracts import DataQuality
from binary_intelligence_ai.data.quality import QualityIssueCode, validate_candles

from test_contracts import make_candle


NOW = datetime(2026, 1, 1, 12, 4, tzinfo=timezone.utc)


def test_contiguous_closed_candles_are_valid() -> None:
    first = make_candle()
    second = make_candle(
        open_time=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
        close_time=datetime(2026, 1, 1, 12, 2, tzinfo=timezone.utc),
    )
    report = validate_candles([first, second], now=NOW, maximum_age=timedelta(minutes=3))
    assert report.status is DataQuality.VALID
    assert report.should_abstain is False


def test_duplicate_and_gap_make_batch_invalid() -> None:
    first = make_candle()
    duplicate = make_candle()
    after_gap = make_candle(
        open_time=datetime(2026, 1, 1, 12, 2, tzinfo=timezone.utc),
        close_time=datetime(2026, 1, 1, 12, 3, tzinfo=timezone.utc),
    )
    report = validate_candles([first, duplicate, after_gap], now=NOW, maximum_age=timedelta(minutes=3))
    assert report.status is DataQuality.INVALID
    assert {issue.code for issue in report.issues} >= {QualityIssueCode.DUPLICATE, QualityIssueCode.GAP}


def test_open_candle_requires_abstention() -> None:
    candle = make_candle(
        open_time=datetime(2026, 1, 1, 12, 4, tzinfo=timezone.utc),
        close_time=datetime(2026, 1, 1, 12, 5, tzinfo=timezone.utc),
    )
    report = validate_candles([candle], now=NOW, maximum_age=timedelta(minutes=3))
    assert report.status is DataQuality.INVALID
    assert report.should_abstain is True


def test_old_series_is_stale() -> None:
    report = validate_candles([make_candle()], now=NOW, maximum_age=timedelta(minutes=2))
    assert report.status is DataQuality.STALE
    assert report.issues[0].code is QualityIssueCode.STALE
