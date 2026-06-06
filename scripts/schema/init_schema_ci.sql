-- Minimal CI schema for the external POI contract.
-- Real data comes from the upstream pipeline dump in dev/production.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS active;
CREATE SCHEMA IF NOT EXISTS history;

-- ---------------------------------------------------------------------------
-- active.production_pois_current — flat current snapshot
-- Contract columns only: osm_id, name, fclass, super_category, lat, lon, geom.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS active.production_pois_current (
    osm_id          text PRIMARY KEY,
    name            text NOT NULL DEFAULT 'Unnamed',
    fclass          text NOT NULL,
    super_category  text NOT NULL,
    lat             double precision NOT NULL,
    lon             double precision NOT NULL,
    geom            geometry(Point, 4326)
);

CREATE INDEX IF NOT EXISTS idx_production_pois_current_geom
    ON active.production_pois_current USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_production_pois_current_super_category
    ON active.production_pois_current (super_category);

-- ---------------------------------------------------------------------------
-- history.production_poi_history — SCD2
-- Contract columns: osm_id, name, fclass, super_category, lat, lon, geom,
-- valid_from, valid_to, is_canonical. Queries MUST filter is_canonical=true
-- to deduplicate point/polygon doubles for the same physical POI.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS history.production_poi_history (
    osm_id          text NOT NULL,
    name            text,
    fclass          text NOT NULL,
    super_category  text NOT NULL,
    lat             double precision NOT NULL,
    lon             double precision NOT NULL,
    geom            geometry(Point, 4326),
    valid_from      timestamptz NOT NULL,
    valid_to        timestamptz NOT NULL,
    is_canonical    boolean NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_production_poi_history_geom
    ON history.production_poi_history USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_production_poi_history_valid
    ON history.production_poi_history (valid_from, valid_to)
    WHERE is_canonical = true;
