import os

import pytest
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from binary_intelligence_ai.data.storage import CandleRecord


@pytest.mark.skipif(
    "BINARY_AI_TEST_DATABASE_URL" not in os.environ,
    reason="PostgreSQL integration URL not provided",
)
def test_postgres_migration_created_market_candles() -> None:
    engine = create_engine(os.environ["BINARY_AI_TEST_DATABASE_URL"])
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(CandleRecord)) == 0
    tables = set(inspect(engine).get_table_names())
    assert {
        "market_candles", "backtest_runs", "backtest_predictions", "news_events",
        "paper_trades", "risk_audit_events", "model_versions", "model_events",
        "monitoring_assessments",
    } <= tables
    prediction_columns = {column["name"] for column in inspect(engine).get_columns("backtest_predictions")}
    assert "analysis_price" in prediction_columns
