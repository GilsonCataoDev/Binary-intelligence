CREATE TABLE IF NOT EXISTS backtest_runs (
    id VARCHAR(36) PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    strategy VARCHAR(80) NOT NULL,
    data_source VARCHAR(80) NOT NULL,
    asset VARCHAR(40) NOT NULL,
    timeframe VARCHAR(8) NOT NULL,
    config_json JSONB NOT NULL,
    metrics_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS backtest_predictions (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    settled_at TIMESTAMPTZ NOT NULL,
    analysis_price NUMERIC(28, 12) NOT NULL,
    reference_price NUMERIC(28, 12) NOT NULL,
    settlement_price NUMERIC(28, 12) NOT NULL,
    outcome VARCHAR(8) NOT NULL CHECK (outcome IN ('up', 'down', 'tie')),
    probability_up NUMERIC(18, 12) NULL CHECK (probability_up BETWEEN 0 AND 1),
    decision VARCHAR(8) NOT NULL CHECK (decision IN ('CALL', 'PUT', 'ABSTAIN')),
    market_regime VARCHAR(24) NOT NULL,
    fold INTEGER NOT NULL CHECK (fold >= 0),
    CONSTRAINT backtest_prediction_identity UNIQUE (run_id, timestamp)
);

CREATE INDEX IF NOT EXISTS backtest_predictions_run_time
    ON backtest_predictions (run_id, timestamp);
