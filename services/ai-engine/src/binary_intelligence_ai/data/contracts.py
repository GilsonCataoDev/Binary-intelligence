from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Timeframe(StrEnum):
    M1 = "1m"
    M5 = "5m"

    @property
    def seconds(self) -> int:
        return {self.M1: 60, self.M5: 300}[self]


class DataQuality(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    STALE = "stale"


class Candle(BaseModel):
    """Candle encerrado, identificado por fonte e intervalo em UTC."""

    model_config = ConfigDict(frozen=True)

    asset: str = Field(min_length=1, max_length=40)
    timeframe: Timeframe
    open_time: datetime
    close_time: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal | None = Field(default=None, ge=0)
    source: str = Field(min_length=1, max_length=80)
    ingested_at: datetime

    @field_validator("asset", "source")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("open_time", "close_time", "ingested_at")
    @classmethod
    def require_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_interval_and_prices(self) -> Candle:
        if self.close_time <= self.open_time:
            raise ValueError("close_time must be after open_time")
        if (self.close_time - self.open_time).total_seconds() != self.timeframe.seconds:
            raise ValueError("candle duration does not match timeframe")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("OHLC values are inconsistent")
        if self.low > self.high:
            raise ValueError("low cannot exceed high")
        return self


class CandleQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    asset: str = Field(min_length=1, max_length=40)
    timeframe: Timeframe
    start: datetime
    end: datetime

    @field_validator("asset")
    @classmethod
    def normalize_asset(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("start", "end")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_range(self) -> CandleQuery:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class CandleBatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_version: str = Field(default="1.0.0", pattern=r"^1\.")
    candles: tuple[Candle, ...]
