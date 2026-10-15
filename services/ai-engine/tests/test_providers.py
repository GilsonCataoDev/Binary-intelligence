from datetime import datetime, timezone
from pathlib import Path

from binary_intelligence_ai.data.contracts import CandleQuery, Timeframe
from binary_intelligence_ai.data.providers import CsvCandleProvider, SimulatedCandleProvider


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
