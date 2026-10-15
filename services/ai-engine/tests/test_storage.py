from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from binary_intelligence_ai.data.contracts import Timeframe
from binary_intelligence_ai.data.storage import (
    BacktestPredictionRecord,
    BacktestRepository,
    BacktestRunRecord,
    Base,
    CandleRepository,
)

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


def test_backtest_repository_preserves_report_and_predictions() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    report = {
        "strategy": "frequency", "data_source": "SIMULATED", "asset": "EURUSD", "timeframe": "1m",
        "horizon_steps": 5, "entry_delay_steps": 0, "execution_offset_bps": 0.0,
        "tie_tolerance": 0.0, "minimum_train_size": 20, "test_size": 10,
        "gap": 5, "folds": 1, "payout": 0.8, "payout_is_hypothetical": True, "tie_policy": "push",
        "metrics": {"operations": 1, "net_return_units": 0.8},
    }
    prediction = {
        "timestamp": datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        "settled_at": datetime(2026, 1, 1, 12, 5, tzinfo=timezone.utc),
        "analysis_price": 100, "reference_price": 100, "settlement_price": 101, "outcome": "up",
        "probability_up": 0.6, "decision": "CALL", "market_regime": "trending_up", "fold": 0,
    }
    with Session(engine) as session:
        run_id = BacktestRepository(session).save(report, [prediction])
        assert session.get(BacktestRunRecord, run_id) is not None
        assert len(list(session.scalars(select(BacktestPredictionRecord)))) == 1
