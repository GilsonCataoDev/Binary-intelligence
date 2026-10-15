CREATE TABLE IF NOT EXISTS paper_trades (
    id VARCHAR(36) PRIMARY KEY,
    idempotency_key VARCHAR(200) NOT NULL UNIQUE,
    asset VARCHAR(40) NOT NULL,
    decision VARCHAR(8) NOT NULL CHECK (decision IN ('CALL', 'PUT')),
    opened_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    settled_at TIMESTAMPTZ NULL,
    reference_price NUMERIC(28, 12) NOT NULL CHECK (reference_price > 0),
    settlement_price NUMERIC(28, 12) NULL CHECK (settlement_price > 0),
    payout NUMERIC(8, 6) NOT NULL CHECK (payout > 0 AND payout <= 1),
    stake NUMERIC(28, 12) NOT NULL CHECK (stake > 0),
    status VARCHAR(8) NOT NULL CHECK (status IN ('open', 'won', 'lost', 'push')),
    pnl NUMERIC(28, 12) NULL,
    model_version VARCHAR(120) NOT NULL,
    result_type VARCHAR(16) NOT NULL DEFAULT 'paper' CHECK (result_type = 'paper'),
    CONSTRAINT paper_trade_time_order CHECK (expires_at > opened_at),
    CONSTRAINT paper_trade_settlement_consistency CHECK (
        (status = 'open' AND settled_at IS NULL AND settlement_price IS NULL AND pnl IS NULL)
        OR (status <> 'open' AND settled_at IS NOT NULL AND settlement_price IS NOT NULL AND pnl IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS paper_trades_asset_opened ON paper_trades (asset, opened_at DESC);

CREATE TABLE IF NOT EXISTS risk_audit_events (
    id BIGSERIAL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    trade_id VARCHAR(36) NULL REFERENCES paper_trades(id),
    details JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS risk_audit_events_time ON risk_audit_events (occurred_at DESC);
