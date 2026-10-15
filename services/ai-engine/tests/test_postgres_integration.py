import os

import pytest
from sqlalchemy import create_engine, func, select
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
