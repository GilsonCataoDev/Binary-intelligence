CREATE TABLE IF NOT EXISTS news_events (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(120) NOT NULL,
    source_event_id VARCHAR(200) NOT NULL,
    headline VARCHAR(500) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    published_at TIMESTAMPTZ NULL,
    event_at TIMESTAMPTZ NULL,
    affected_assets JSONB NOT NULL,
    reported_impact VARCHAR(16) NOT NULL CHECK (reported_impact IN ('unknown', 'low', 'medium', 'high')),
    ingested_at TIMESTAMPTZ NOT NULL,
    delayed BOOLEAN NOT NULL,
    evidence JSONB NOT NULL,
    raw_payload JSONB NULL,
    CONSTRAINT news_events_identity UNIQUE (source, source_event_id),
    CONSTRAINT news_events_timestamp_required CHECK (published_at IS NOT NULL OR event_at IS NOT NULL),
    CONSTRAINT news_events_ingestion_order CHECK (published_at IS NULL OR ingested_at >= published_at)
);

CREATE INDEX IF NOT EXISTS news_events_event_time
    ON news_events (event_at DESC);

CREATE INDEX IF NOT EXISTS news_events_ingested_at
    ON news_events (ingested_at DESC);

COMMENT ON TABLE news_events IS
    'Metadados auditáveis de notícias e eventos; raw_payload depende da licença e retenção da fonte.';
