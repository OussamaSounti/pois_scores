-- Minimal CI schema for the external POI contract.
-- Real data comes from the upstream pipeline dump in dev/production.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS active;
CREATE SCHEMA IF NOT EXISTS history;

-- ---------------------------------------------------------------------------
-- active.production_pois_current — flat current snapshot
-- Production dumps may use latitude/longitude; queries derive coords from geom.
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
-- Matches the upstream pipeline export. Queries filter is_canonical = true,
-- :as_of <@ valid_range, and deduplicate by dedup_group (see PoiRepository).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS history.production_poi_history (
    typed_id          text NOT NULL,
    osm_id            text NOT NULL,
    osm_type          text NOT NULL DEFAULT 'node',
    name              text,
    fclass            text NOT NULL,
    super_category    text NOT NULL,
    geom              geometry(Point, 4326),
    lat               double precision NOT NULL,
    lon               double precision NOT NULL,
    version           integer NOT NULL DEFAULT 1,
    visible           boolean NOT NULL DEFAULT true,
    valid_from        timestamptz NOT NULL,
    valid_to          timestamptz NOT NULL,
    valid_range       tstzrange GENERATED ALWAYS AS (
        tstzrange(valid_from, valid_to, '[)')
    ) STORED,
    matched_tag_key   text,
    poi_source        text,
    tags_json         jsonb,
    dedup_group       text NOT NULL,
    is_canonical      boolean NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_phist_geom_geog
    ON history.production_poi_history USING GIST (((geom)::geography));

CREATE INDEX IF NOT EXISTS idx_phist_valid_range
    ON history.production_poi_history USING GIST (valid_range);

CREATE INDEX IF NOT EXISTS idx_phist_dedup_group
    ON history.production_poi_history USING btree (dedup_group);

CREATE INDEX IF NOT EXISTS idx_phist_is_canonical
    ON history.production_poi_history USING btree (is_canonical)
    WHERE is_canonical = true;
