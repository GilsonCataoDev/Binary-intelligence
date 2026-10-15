from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import math
from typing import Any, Mapping
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .contracts import Candle, Timeframe
from binary_intelligence_ai.news.contracts import NewsEvent


class Base(DeclarativeBase):
    pass


class CandleRecord(Base):
    __tablename__ = "market_candles"
    __table_args__ = (UniqueConstraint("source", "asset", "timeframe", "open_time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    asset: Mapped[str] = mapped_column(String(40), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(28, 12), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestRunRecord(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    strategy: Mapped[str] = mapped_column(String(80), nullable=False)
    data_source: Mapped[str] = mapped_column(String(80), nullable=False)
    asset: Mapped[str] = mapped_column(String(40), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class BacktestPredictionRecord(Base):
    __tablename__ = "backtest_predictions"
    __table_args__ = (UniqueConstraint("run_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    analysis_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    reference_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    settlement_price: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    outcome: Mapped[str] = mapped_column(String(8), nullable=False)
    probability_up: Mapped[Decimal | None] = mapped_column(Numeric(18, 12), nullable=True)
    decision: Mapped[str] = mapped_column(String(8), nullable=False)
    market_regime: Mapped[str] = mapped_column(String(24), nullable=False)
    fold: Mapped[int] = mapped_column(Integer, nullable=False)


class NewsEventRecord(Base):
    __tablename__ = "news_events"
    __table_args__ = (UniqueConstraint("source", "source_event_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    affected_assets: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    reported_impact: Mapped[str] = mapped_column(String(16), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delayed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class CandleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, candles: list[Candle] | tuple[Candle, ...]) -> int:
        """Persist new candles idempotently; return the number inserted."""

        inserted = 0
        for candle in candles:
            exists = self.session.scalar(select(CandleRecord.id).where(
                CandleRecord.source == candle.source,
                CandleRecord.asset == candle.asset,
                CandleRecord.timeframe == candle.timeframe.value,
                CandleRecord.open_time == candle.open_time,
            ))
            if exists is not None:
                continue
            self.session.add(CandleRecord(
                source=candle.source,
                asset=candle.asset,
                timeframe=candle.timeframe.value,
                open_time=candle.open_time,
                close_time=candle.close_time,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
                ingested_at=candle.ingested_at,
            ))
            inserted += 1
        self.session.commit()
        return inserted

    def list_range(self, *, source: str, asset: str, timeframe: Timeframe, start: datetime, end: datetime) -> list[CandleRecord]:
        statement = select(CandleRecord).where(
            CandleRecord.source == source.strip().upper(),
            CandleRecord.asset == asset.strip().upper(),
            CandleRecord.timeframe == timeframe.value,
            CandleRecord.open_time >= start,
            CandleRecord.open_time < end,
        ).order_by(CandleRecord.open_time)
        return list(self.session.scalars(statement))


class BacktestRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, report: Mapping[str, Any], predictions: list[Mapping[str, Any]]) -> str:
        run_id = str(uuid4())
        config_keys = {
            "horizon_steps", "entry_delay_steps", "execution_offset_bps", "tie_tolerance",
            "minimum_train_size", "test_size", "gap",
            "folds", "payout", "payout_is_hypothetical", "tie_policy",
        }
        self.session.add(BacktestRunRecord(
            id=run_id,
            created_at=datetime.now(timezone.utc),
            strategy=str(report["strategy"]),
            data_source=str(report["data_source"]),
            asset=str(report["asset"]),
            timeframe=str(report["timeframe"]),
            config_json={key: report[key] for key in config_keys},
            metrics_json=dict(report["metrics"]),
        ))
        for prediction in predictions:
            probability = prediction.get("probability_up")
            if isinstance(probability, float) and math.isnan(probability):
                probability = None
            self.session.add(BacktestPredictionRecord(
                run_id=run_id,
                timestamp=_as_datetime(prediction["timestamp"]),
                settled_at=_as_datetime(prediction["settled_at"]),
                analysis_price=Decimal(str(prediction["analysis_price"])),
                reference_price=Decimal(str(prediction["reference_price"])),
                settlement_price=Decimal(str(prediction["settlement_price"])),
                outcome=str(prediction["outcome"]),
                probability_up=Decimal(str(probability)) if probability is not None else None,
                decision=str(prediction["decision"]),
                market_regime=str(prediction["market_regime"]),
                fold=int(prediction["fold"]),
            ))
        self.session.commit()
        return run_id


class NewsEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, events: list[NewsEvent] | tuple[NewsEvent, ...]) -> int:
        inserted = 0
        for event in events:
            exists = self.session.scalar(select(NewsEventRecord.id).where(
                NewsEventRecord.source == event.source,
                NewsEventRecord.source_event_id == event.source_event_id,
            ))
            if exists is not None:
                continue
            self.session.add(NewsEventRecord(
                source=event.source,
                source_event_id=event.source_event_id,
                headline=event.headline,
                event_type=event.event_type,
                published_at=event.published_at,
                event_at=event.event_at,
                affected_assets=list(event.affected_assets),
                reported_impact=event.reported_impact.value,
                ingested_at=event.ingested_at,
                delayed=event.delayed,
                evidence=list(event.evidence),
                raw_payload=None,
            ))
            inserted += 1
        self.session.commit()
        return inserted

    def list_relevant(
        self, *, asset: str, start: datetime, end: datetime, as_of: datetime
    ) -> list[NewsEventRecord]:
        records = self.session.scalars(select(NewsEventRecord).where(
            NewsEventRecord.ingested_at <= as_of,
        ).order_by(NewsEventRecord.ingested_at)).all()
        normalized_asset = asset.strip().upper()
        return [
            record for record in records
            if normalized_asset in record.affected_assets
            and start <= _as_utc(record.event_at or record.published_at or record.ingested_at) < end
        ]


def _as_datetime(value: Any) -> datetime:
    converted = value.to_pydatetime() if hasattr(value, "to_pydatetime") else value
    if not isinstance(converted, datetime):
        raise TypeError("prediction timestamp must be a datetime")
    return converted


def _as_utc(value: datetime) -> datetime:
    """Restore UTC when a test database drops timezone metadata."""

    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
