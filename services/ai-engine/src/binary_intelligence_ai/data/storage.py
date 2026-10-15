from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .contracts import Candle, Timeframe


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
