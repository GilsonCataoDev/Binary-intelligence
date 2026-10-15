from __future__ import annotations

import csv
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from .contracts import Candle, CandleQuery


class MarketDataProvider(ABC):
    @abstractmethod
    def get_candles(self, query: CandleQuery) -> list[Candle]:
        """Return candles in ascending open_time order without fabricating gaps."""


class CsvCandleProvider(MarketDataProvider):
    REQUIRED_COLUMNS = {"asset", "timeframe", "open_time", "close_time", "open", "high", "low", "close", "source"}

    def __init__(self, path: Path) -> None:
        self.path = path

    def get_candles(self, query: CandleQuery) -> list[Candle]:
        ingested_at = datetime.now(timezone.utc)
        with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = self.REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")
            candles = [self._parse(row, ingested_at) for row in reader]
        return [
            candle
            for candle in candles
            if candle.asset == query.asset
            and candle.timeframe == query.timeframe
            and query.start <= candle.open_time < query.end
        ]

    @staticmethod
    def _parse(row: dict[str, str], ingested_at: datetime) -> Candle:
        volume = row.get("volume", "").strip()
        return Candle(
            asset=row["asset"],
            timeframe=row["timeframe"],
            open_time=datetime.fromisoformat(row["open_time"].replace("Z", "+00:00")),
            close_time=datetime.fromisoformat(row["close_time"].replace("Z", "+00:00")),
            open=Decimal(row["open"]),
            high=Decimal(row["high"]),
            low=Decimal(row["low"]),
            close=Decimal(row["close"]),
            volume=Decimal(volume) if volume else None,
            source=row["source"],
            ingested_at=ingested_at,
        )


class SimulatedCandleProvider(MarketDataProvider):
    """Gerador determinístico para desenvolvimento; os dados nunca representam mercado real."""

    def __init__(self, *, seed: int = 0, source: str = "SIMULATED") -> None:
        self.seed = seed
        self.source = source

    def get_candles(self, query: CandleQuery) -> list[Candle]:
        rng = random.Random(f"{self.seed}:{query.asset}:{query.timeframe}:{query.start.isoformat()}")
        cursor = query.start
        price = Decimal("100")
        candles: list[Candle] = []
        step = timedelta(seconds=query.timeframe.seconds)
        while cursor + step <= query.end:
            change = Decimal(str(round(rng.uniform(-0.35, 0.35), 6)))
            close = max(Decimal("0.000001"), price + change)
            wick = Decimal(str(round(rng.uniform(0, 0.12), 6)))
            candles.append(Candle(
                asset=query.asset,
                timeframe=query.timeframe,
                open_time=cursor,
                close_time=cursor + step,
                open=price,
                high=max(price, close) + wick,
                low=max(Decimal("0.000001"), min(price, close) - wick),
                close=close,
                volume=None,
                source=self.source,
                ingested_at=query.end,
            ))
            cursor += step
            price = close
        return candles
