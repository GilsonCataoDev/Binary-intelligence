from datetime import datetime, timezone
from pathlib import Path

from binary_intelligence_ai.data.contracts import CandleQuery, Timeframe
from binary_intelligence_ai.data.providers import (
    BinanceSpotCandleProvider,
    CsvCandleProvider,
    SimulatedCandleProvider,
    TwelveDataCandleProvider,
)


def test_simulated_provider_is_deterministic_and_explicitly_labeled() -> None:
    query = CandleQuery(
        asset="EURUSD",
        timeframe=Timeframe.M1,
        start=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 12, 3, tzinfo=timezone.utc),
    )
    provider = SimulatedCandleProvider(seed=42)
    first = provider.get_candles(query)
    second = provider.get_candles(query)
    assert first == second
    assert len(first) == 3
    assert all(candle.source == "SIMULATED" and candle.volume is None for candle in first)


def test_csv_provider_reads_only_requested_half_open_range(tmp_path: Path) -> None:
    csv_path = tmp_path / "candles.csv"
    csv_path.write_text(
        "asset,timeframe,open_time,close_time,open,high,low,close,volume,source\n"
        "EURUSD,1m,2026-01-01T12:00:00Z,2026-01-01T12:01:00Z,1.10,1.12,1.09,1.11,,fixture\n"
        "EURUSD,1m,2026-01-01T12:01:00Z,2026-01-01T12:02:00Z,1.11,1.13,1.10,1.12,0,fixture\n",
        encoding="utf-8",
    )
    query = CandleQuery(
        asset="EURUSD",
        timeframe=Timeframe.M1,
        start=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
    )
    candles = CsvCandleProvider(csv_path).get_candles(query)
    assert len(candles) == 1
    assert candles[0].volume is None


def test_binance_provider_normalizes_public_kline_payload() -> None:
    query = CandleQuery(
        asset="BTCUSDT", timeframe=Timeframe.M5,
        start=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 12, 5, tzinfo=timezone.utc),
    )
    seen: list[str] = []

    def fake_get(url: str) -> object:
        seen.append(url)
        return [[1767268800000, "90000", "90100", "89900", "90050", "12.5"]]

    candles = BinanceSpotCandleProvider(get_json=fake_get).get_candles(query)
    assert "symbol=BTCUSDT" in seen[0] and "interval=5m" in seen[0]
    assert candles[0].asset == "BTCUSDT"
    assert candles[0].source == "BINANCE_SPOT_PUBLIC"
    assert candles[0].volume == 12.5


def test_twelve_data_provider_normalizes_xauusd_and_reverses_descending_payload() -> None:
    query = CandleQuery(
        asset="XAUUSD", timeframe=Timeframe.M5,
        start=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 12, 10, tzinfo=timezone.utc),
    )

    def fake_get(_: str) -> object:
        return {"status": "ok", "values": [
            {"datetime": "2026-01-01 12:05:00", "open": "2651", "high": "2652", "low": "2650", "close": "2651.5"},
            {"datetime": "2026-01-01 12:00:00", "open": "2650", "high": "2651", "low": "2649", "close": "2650.5"},
        ]}

    candles = TwelveDataCandleProvider("research-key", get_json=fake_get).get_candles(query)
    assert [candle.open_time.minute for candle in candles] == [0, 5]
    assert all(candle.asset == "XAUUSD" and candle.volume is None for candle in candles)
