CREATE TABLE IF NOT EXISTS model_versions (
    version VARCHAR(120) PRIMARY KEY,
    feature_set_version VARCHAR(120) NOT NULL,
    dataset_fingerprint CHAR(64) NOT NULL CHECK (dataset_fingerprint ~ '^[0-9a-f]{64}$'),
    artifact_uri VARCHAR(500) NOT NULL,
    artifact_checksum CHAR(64) NOT NULL CHECK (artifact_checksum ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('candidate', 'active', 'retired', 'paused', 'rolled_back')),
    metrics_json JSONB NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS model_versions_single_active
    ON model_versions ((status)) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS model_events (
    id BIGSERIAL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(40) NOT NULL,
    model_version VARCHAR(120) NOT NULL REFERENCES model_versions(version),
    previous_version VARCHAR(120) NULL REFERENCES model_versions(version),
    reason VARCHAR(1000) NOT NULL
);

CREATE INDEX IF NOT EXISTS model_events_time ON model_events (occurred_at DESC);

CREATE TABLE IF NOT EXISTS monitoring_assessments (
    id BIGSERIAL PRIMARY KEY,
    assessed_at TIMESTAMPTZ NOT NULL,
    model_version VARCHAR(120) NOT NULL REFERENCES model_versions(version),
    status VARCHAR(24) NOT NULL CHECK (status IN ('healthy', 'warning', 'blocked', 'insufficient_data')),
    should_pause BOOLEAN NOT NULL,
    maximum_psi DOUBLE PRECISION NULL,
    observations INTEGER NOT NULL CHECK (observations >= 0),
    brier_score DOUBLE PRECISION NULL CHECK (brier_score BETWEEN 0 AND 1),
    expected_calibration_error DOUBLE PRECISION NULL CHECK (expected_calibration_error BETWEEN 0 AND 1),
    details JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS monitoring_assessments_model_time
    ON monitoring_assessments (model_version, assessed_at DESC);
