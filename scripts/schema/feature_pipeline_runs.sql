-- Pipeline run ledger (production schema).
-- Applied by apply_feature_pipeline.py and auto-created on first pipeline run.

CREATE SCHEMA IF NOT EXISTS production;

CREATE TABLE IF NOT EXISTS production.feature_pipeline_runs (
    run_id            uuid PRIMARY KEY,
    flow_name         text NOT NULL,
    status            text NOT NULL,
    started_at        timestamptz NOT NULL DEFAULT now(),
    finished_at       timestamptz,
    duration_seconds  double precision,

    pipeline_version  text NOT NULL,
    poi_refreshed_at  timestamptz,
    poi_source        text,

    config            jsonb NOT NULL DEFAULT '{}',
    pending_before    integer,
    processed         integer NOT NULL DEFAULT 0,
    skipped           integer NOT NULL DEFAULT 0,
    failed            integer NOT NULL DEFAULT 0,
    pending_after     integer,

    prefect_run_id    text,
    triggered_by      text NOT NULL,
    skip_reason       text,
    error_summary     text
);

CREATE INDEX IF NOT EXISTS idx_feature_pipeline_runs_flow_started
    ON production.feature_pipeline_runs (flow_name, started_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_feature_pipeline_runs_one_running
    ON production.feature_pipeline_runs (flow_name)
    WHERE status = 'running';

CREATE TABLE IF NOT EXISTS production.feature_pipeline_failures (
    id            bigserial PRIMARY KEY,
    run_id        uuid NOT NULL REFERENCES production.feature_pipeline_runs(run_id),
    transaction_id bigint NOT NULL,
    flow_name     text NOT NULL,
    error_message text,
    failed_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feature_pipeline_failures_run
    ON production.feature_pipeline_failures (run_id);
