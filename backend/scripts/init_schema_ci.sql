-- Minimal production.pois_current schema for CI (empty table).
-- Real data comes from the dump in local/dev/production.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS production;

CREATE TABLE IF NOT EXISTS production.pois_current (
    id bigserial PRIMARY KEY,
    osm_id text NOT NULL,
    name text NOT NULL DEFAULT 'Unnamed',
    fclass text NOT NULL,
    super_category text NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    geom geometry(Point, 4326),
    content_hash text NOT NULL,
    first_seen_at timestamp with time zone NOT NULL DEFAULT now(),
    last_seen_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    is_active boolean NOT NULL DEFAULT true,
    source_snapshot_date date
);
