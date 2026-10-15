from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from binary_intelligence_ai.data.contracts import Candle, Timeframe


def make_candle(**overrides: object) -> Candle:
    values: dict[str, object] = {
        "asset": " eurusd ",
        "timeframe": Timeframe.M1,
        "open_time": datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        "close_time": datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
        "open": Decimal("1.10"),
        "high": Decimal("1.12"),
        "low": Decimal("1.09"),
        "close": Decimal("1.11"),
        "volume": None,
        "source": " fixture ",
        "ingested_at": datetime(2026, 1, 1, 12, 2, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return Candle.model_validate(values)


def test_candle_normalizes_identifiers() -> None:
    candle = make_candle()
    assert candle.asset == "EURUSD"
    assert candle.source == "FIXTURE"


@pytest.mark.parametrize(
    ("field", "value"),
    [("high", Decimal("1.09")), ("low", Decimal("1.115")), ("open", Decimal("0"))],
)
def test_candle_rejects_invalid_prices(field: str, value: Decimal) -> None:
    with pytest.raises(ValidationError):
        make_candle(**{field: value})


def test_candle_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        make_candle(open_time=datetime(2026, 1, 1, 12, 0))


def test_candle_rejects_wrong_duration() -> None:
    with pytest.raises(ValidationError, match="duration"):
        make_candle(close_time=datetime(2026, 1, 1, 12, 2, tzinfo=timezone.utc))
