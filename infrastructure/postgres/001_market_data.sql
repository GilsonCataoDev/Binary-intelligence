CREATE TABLE IF NOT EXISTS market_candles (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(80) NOT NULL,
    asset VARCHAR(40) NOT NULL,
    timeframe VARCHAR(8) NOT NULL CHECK (timeframe IN ('1m', '5m')),
    open_time TIMESTAMPTZ NOT NULL,
    close_time TIMESTAMPTZ NOT NULL,
    open NUMERIC(28, 12) NOT NULL CHECK (open > 0),
    high NUMERIC(28, 12) NOT NULL CHECK (high > 0),
    low NUMERIC(28, 12) NOT NULL CHECK (low > 0),
    close NUMERIC(28, 12) NOT NULL CHECK (close > 0),
    volume NUMERIC(28, 12) NULL CHECK (volume IS NULL OR volume >= 0),
    ingested_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT market_candles_identity UNIQUE (source, asset, timeframe, open_time),
    CONSTRAINT market_candles_time_order CHECK (close_time > open_time),
    CONSTRAINT market_candles_ohlc CHECK (
        high >= GREATEST(open, close) AND low <= LEAST(open, close) AND low <= high
    )
);

CREATE INDEX IF NOT EXISTS market_candles_lookup
    ON market_candles (asset, timeframe, open_time DESC);

COMMENT ON TABLE market_candles IS
    'Candles normalizados e auditáveis; retenção depende da licença da fonte.';
