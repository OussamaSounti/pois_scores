-- Minimal schema for CI (empty tables).
-- Real data comes from the dump in local/dev/production.
-- osm_history data is loaded via: python data/import_data.py
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS production;
CREATE SCHEMA IF NOT EXISTS osm_history;

-- Minimal osm_history.poi_history_active for CI (empty table, same columns as prod).
CREATE TABLE IF NOT EXISTS osm_history.poi_history_active (
    typed_id        text,
    osm_id          text,
    osm_type        text,
    name            text,
    fclass          text,
    super_category  text,
    geom            geometry(Point, 4326),
    lat             float8,
    lon             float8,
    version         integer,
    visible         boolean,
    valid_from      timestamptz,
    valid_to        timestamptz,
    valid_range     tstzrange,
    matched_tag_key text,
    poi_source      text
);

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
