from __future__ import annotations

import csv
import json
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .contracts import Candle, CandleQuery, Timeframe


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


JsonGetter = Callable[[str], Any]


class BinanceSpotCandleProvider(MarketDataProvider):
    """Read-only Binance Spot candle provider for BTC/USDT research.

    This provider only reads public market data. It cannot create orders and
    does not model a BTC/USD fill from another venue.
    """

    ENDPOINT = "https://api.binance.com/api/v3/klines"
    INTERVALS = {Timeframe.M1: "1m", Timeframe.M5: "5m"}

    def __init__(self, *, get_json: JsonGetter | None = None) -> None:
        self.get_json = get_json or _get_json

    def get_candles(self, query: CandleQuery) -> list[Candle]:
        if query.asset not in {"BTCUSDT", "BTC/USD", "BTCUSD"}:
            raise ValueError("Binance Spot research provider currently supports BTCUSDT only")
        parameters = urlencode({
            "symbol": "BTCUSDT", "interval": self.INTERVALS[query.timeframe],
            "startTime": int(query.start.timestamp() * 1000),
            "endTime": int(query.end.timestamp() * 1000), "limit": 1000,
        })
        payload = self.get_json(f"{self.ENDPOINT}?{parameters}")
        if not isinstance(payload, list):
            raise ValueError("Binance returned an invalid candle payload")
        ingested_at = datetime.now(timezone.utc)
        candles: list[Candle] = []
        for item in payload:
            if not isinstance(item, list) or len(item) < 6:
                raise ValueError("Binance returned a malformed candle")
            open_time = datetime.fromtimestamp(int(item[0]) / 1000, timezone.utc)
            close_time = open_time + timedelta(seconds=query.timeframe.seconds)
            if not query.start <= open_time < query.end:
                continue
            candles.append(Candle(
                asset="BTCUSDT", timeframe=query.timeframe, open_time=open_time, close_time=close_time,
                open=Decimal(str(item[1])), high=Decimal(str(item[2])), low=Decimal(str(item[3])), close=Decimal(str(item[4])),
                volume=Decimal(str(item[5])), source="BINANCE_SPOT_PUBLIC", ingested_at=ingested_at,
            ))
        return sorted(candles, key=lambda candle: candle.open_time)


class TwelveDataCandleProvider(MarketDataProvider):
    """Read-only Twelve Data candles for XAU/USD research.

    An API key is required. Returned prices are a data-feed reference, not an
    executable broker quote; spreads and financing remain external inputs.
    """

    ENDPOINT = "https://api.twelvedata.com/time_series"
    INTERVALS = {Timeframe.M1: "1min", Timeframe.M5: "5min"}

    def __init__(self, api_key: str, *, get_json: JsonGetter | None = None) -> None:
        if len(api_key.strip()) < 8:
            raise ValueError("TWELVE_DATA_API_KEY is required for XAUUSD research data")
        self.api_key = api_key.strip()
        self.get_json = get_json or _get_json

    def get_candles(self, query: CandleQuery) -> list[Candle]:
        if query.asset not in {"XAUUSD", "XAU/USD"}:
            raise ValueError("Twelve Data research provider currently supports XAUUSD only")
        parameters = urlencode({
            "symbol": "XAU/USD", "interval": self.INTERVALS[query.timeframe], "timezone": "UTC",
            "start_date": query.start.isoformat(), "end_date": query.end.isoformat(), "apikey": self.api_key,
        })
        payload = self.get_json(f"{self.ENDPOINT}?{parameters}")
        if not isinstance(payload, dict) or payload.get("status") == "error":
            message = payload.get("message", "unknown provider error") if isinstance(payload, dict) else "invalid response"
            raise ValueError(f"Twelve Data request failed: {message}")
        values = payload.get("values")
        if not isinstance(values, list):
            raise ValueError("Twelve Data returned no candle values")
        ingested_at = datetime.now(timezone.utc)
        candles: list[Candle] = []
        for item in values:
            if not isinstance(item, dict):
                raise ValueError("Twelve Data returned a malformed candle")
            open_time = _twelve_data_time(str(item.get("datetime", "")))
            close_time = open_time + timedelta(seconds=query.timeframe.seconds)
            if not query.start <= open_time < query.end:
                continue
            volume = item.get("volume")
            candles.append(Candle(
                asset="XAUUSD", timeframe=query.timeframe, open_time=open_time, close_time=close_time,
                open=Decimal(str(item["open"])), high=Decimal(str(item["high"])), low=Decimal(str(item["low"])), close=Decimal(str(item["close"])),
                volume=Decimal(str(volume)) if volume not in (None, "") else None,
                source="TWELVE_DATA_FOREX", ingested_at=ingested_at,
            ))
        return sorted(candles, key=lambda candle: candle.open_time)


def _twelve_data_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Twelve Data returned an invalid candle timestamp") from error
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _get_json(url: str) -> Any:
    request = Request(url, headers={"User-Agent": "BinaryIntelligenceResearch/0.12"})
    with urlopen(request, timeout=10) as response:  # nosec B310 - fixed HTTPS provider endpoints only
        return json.loads(response.read().decode("utf-8"))
