from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from .contracts import Candle, DataQuality, Timeframe


class QualityIssueCode(StrEnum):
    DUPLICATE = "duplicate"
    GAP = "gap"
    OPEN_CANDLE = "open_candle"
    STALE = "stale"
    MIXED_SERIES = "mixed_series"
    OUT_OF_ORDER = "out_of_order"


class QualityIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: QualityIssueCode
    message: str
    open_time: datetime | None = None


class DataQualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: DataQuality
    checked_at: datetime
    candle_count: int
    issues: tuple[QualityIssue, ...]

    @property
    def should_abstain(self) -> bool:
        return self.status is not DataQuality.VALID


def validate_candles(
    candles: list[Candle] | tuple[Candle, ...],
    *,
    now: datetime,
    maximum_age: timedelta,
) -> DataQualityReport:
    """Valida uma única série sem reordenar ou preencher dados silenciosamente."""

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include a timezone")
    checked_at = now.astimezone(timezone.utc)
    issues: list[QualityIssue] = []

    if not candles:
        issues.append(QualityIssue(code=QualityIssueCode.STALE, message="no candles received"))
        return _report(checked_at, candles, issues)

    first = candles[0]
    expected_key = (first.source, first.asset, first.timeframe)
    previous: Candle | None = None
    seen: set[datetime] = set()

    for candle in candles:
        if (candle.source, candle.asset, candle.timeframe) != expected_key:
            issues.append(QualityIssue(
                code=QualityIssueCode.MIXED_SERIES,
                message="batch contains more than one source, asset, or timeframe",
                open_time=candle.open_time,
            ))
        if candle.open_time in seen:
            issues.append(QualityIssue(
                code=QualityIssueCode.DUPLICATE,
                message="duplicate candle open_time",
                open_time=candle.open_time,
            ))
        seen.add(candle.open_time)
        if candle.close_time > checked_at:
            issues.append(QualityIssue(
                code=QualityIssueCode.OPEN_CANDLE,
                message="candle has not closed at validation time",
                open_time=candle.open_time,
            ))
        if previous is not None:
            if candle.open_time < previous.open_time:
                issues.append(QualityIssue(
                    code=QualityIssueCode.OUT_OF_ORDER,
                    message="candles are not chronologically ordered",
                    open_time=candle.open_time,
                ))
            elif candle.open_time > previous.close_time:
                issues.append(QualityIssue(
                    code=QualityIssueCode.GAP,
                    message="temporal gap between candles",
                    open_time=candle.open_time,
                ))
        previous = candle

    newest_closed = max(c.close_time for c in candles if c.close_time <= checked_at) if any(
        c.close_time <= checked_at for c in candles
    ) else None
    if newest_closed is None or checked_at - newest_closed > maximum_age:
        issues.append(QualityIssue(code=QualityIssueCode.STALE, message="latest closed candle is stale"))

    return _report(checked_at, candles, issues)


def _report(
    checked_at: datetime,
    candles: list[Candle] | tuple[Candle, ...],
    issues: list[QualityIssue],
) -> DataQualityReport:
    status = DataQuality.VALID
    if issues:
        status = DataQuality.STALE if all(i.code is QualityIssueCode.STALE for i in issues) else DataQuality.INVALID
    return DataQualityReport(
        status=status,
        checked_at=checked_at,
        candle_count=len(candles),
        issues=tuple(issues),
    )
