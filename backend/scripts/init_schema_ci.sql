-- Minimal production.pois schema for CI (empty table).
-- Real data comes from the dump in local/dev/production.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS production;

CREATE TABLE IF NOT EXISTS production.pois (
    id bigserial PRIMARY KEY,
    osm_id text,
    name text NOT NULL DEFAULT 'Unnamed',
    fclass text NOT NULL,
    super_category text NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    geom geometry(Point, 4326)
);
