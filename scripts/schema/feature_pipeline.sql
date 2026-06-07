-- Feature engineering pipeline schema (this codebase's own tables).
-- POI source tables (active.production_pois_current, history.production_poi_history)
-- are NOT defined here -- they are produced by the upstream OSM pipeline and
-- created by scripts/schema/init_schema_ci.sql for CI.

CREATE SCHEMA IF NOT EXISTS production;
CREATE SCHEMA IF NOT EXISTS geo;
CREATE SCHEMA IF NOT EXISTS history;  -- present as a guard; populated by upstream

-- ---------------------------------------------------------------------------
-- geo.coastline — reference coastline used to compute dist_coast_km.
-- Populate with: python scripts/ingest/load_osm_coastline.py
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS geo.coastline (
    id   serial PRIMARY KEY,
    name text,
    geom geometry(MultiLineString, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_geo_coastline_geom
    ON geo.coastline USING GIST (geom);

-- ---------------------------------------------------------------------------
-- geo.land — land polygon(s) used to compute the true fraction of the
-- 1 km analysis buffer on land via PostGIS area intersection.
-- Populate with: python scripts/ingest/load_osm_land.py
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS geo.land (
    id   serial PRIMARY KEY,
    name text,
    geom geometry(MultiPolygon, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_geo_land_geom
    ON geo.land USING GIST (geom);

-- Input: slim pipeline index keyed by the external transaction id (one sale event).
-- Rich attributes (price, admin hierarchy, geometry) live in the source
-- transactions table (another schema); populated by external ETL or the dev parquet loader.
CREATE TABLE IF NOT EXISTS production.properties (
    transaction_id bigint PRIMARY KEY,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    transaction_date date
);

CREATE INDEX IF NOT EXISTS idx_properties_transaction_date
    ON production.properties (transaction_date);

-- Output: one row per transaction, flattened spatial indicators (ML input).
-- transaction_id is denormalized so ML/analytics can join directly to the
-- source transactions table without going through production.properties.
CREATE TABLE IF NOT EXISTS production.property_features (
    transaction_id bigint PRIMARY KEY REFERENCES production.properties(transaction_id) ON DELETE CASCADE,
    poi_refreshed_at timestamptz NOT NULL,
    pipeline_version text NOT NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    -- Scalars
    poi_count_1km integer NOT NULL,
    poi_count_400m integer NOT NULL,
    n_categories integer NOT NULL,
    n_poi_types integer NOT NULL,
    entropy double precision NOT NULL,
    entropy_fclass double precision NOT NULL,
    aggregate_score double precision,
    -- Accessibility (one column per key in features.pois.service.ACCESSIBILITY_KEY_TYPES)
    acc_bus_stop boolean NOT NULL,
    acc_pharmacy boolean NOT NULL,
    acc_school boolean NOT NULL,
    acc_hospital boolean NOT NULL,
    acc_supermarket boolean NOT NULL,
    acc_bank boolean NOT NULL,
    acc_atm boolean NOT NULL,
    acc_clinic boolean NOT NULL,
    acc_fuel boolean NOT NULL,
    acc_police boolean NOT NULL,
    acc_park boolean NOT NULL,
    acc_doctors boolean NOT NULL,
    acc_taxi boolean NOT NULL,
    -- Dynamic keys stored as JSONB.
    by_category jsonb NOT NULL DEFAULT '{}',
    nearest_km  jsonb NOT NULL DEFAULT '{}',
    -- Coastal signals (NULL when geo.coastline is not yet populated).
    dist_coast_km            double precision,
    land_buffer_fraction_1km double precision,
    -- Temporal enrichment: date used for POI lookup and which table was queried.
    -- NULL for properties scored against active.production_pois_current.
    transaction_date         date,
    poi_source               text  -- 'history' | 'current'
);

CREATE INDEX IF NOT EXISTS idx_property_features_poi_refreshed_at
    ON production.property_features(poi_refreshed_at);

-- Run ledger tables: scripts/schema/feature_pipeline_runs.sql
-- (also auto-created on first pipeline run)
