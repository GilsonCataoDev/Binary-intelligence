from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from binary_intelligence_ai.data.contracts import Timeframe
from binary_intelligence_ai.data.storage import Base, CandleRepository

from test_contracts import make_candle


def test_repository_is_idempotent_and_queries_half_open_range() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    candle = make_candle()

    with Session(engine) as session:
        repository = CandleRepository(session)
        assert repository.save([candle]) == 1
        assert repository.save([candle]) == 0
        records = repository.list_range(
            source="fixture",
            asset="eurusd",
            timeframe=Timeframe.M1,
            start=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            end=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
        )
        assert len(records) == 1
        assert records[0].close == candle.close
