-- Feature engineering pipeline: input/output. POI version from audit.pipeline_runs (external).
-- Run once when adding the pipeline (local/dev) or schema is managed in production.
CREATE SCHEMA IF NOT EXISTS production;
CREATE SCHEMA IF NOT EXISTS geo;

-- ---------------------------------------------------------------------------
-- osm_history schema
-- Holds versioned POI history for temporal enrichment queries.
-- Data is loaded via: python data/import_data.py
-- The table osm_history.poi_history_active is created and populated by that
-- script; this block only ensures the schema exists so queries referencing
-- it do not fail when the import has not yet been run in a given environment.
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS osm_history;

-- ---------------------------------------------------------------------------
-- geo.coastline
-- Holds the reference coastline geometry used to compute dist_coast_km.
-- Populate with a single INSERT after running this script, e.g.:
--   INSERT INTO geo.coastline (name, geom)
--   VALUES ('morocco', ST_GeomFromGeoJSON('<GeoJSON MultiLineString>'));
-- A GiST index is created for fast ST_Distance lookups.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS geo.coastline (
    id   serial PRIMARY KEY,
    name text,
    geom geometry(MultiLineString, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_geo_coastline_geom
    ON geo.coastline USING GIST (geom);

-- ---------------------------------------------------------------------------
-- geo.land
-- Land polygon(s) used to compute the true fraction of the 1 km analysis
-- buffer that lies on land via PostGIS area intersection.  This is more
-- accurate than the straight-coastline formula for capes, peninsulas, bays,
-- and other non-linear coastal shapes.
-- Populate with: python scripts/load_land_polygons.py
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS geo.land (
    id   serial PRIMARY KEY,
    name text,
    geom geometry(MultiPolygon, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_geo_land_geom
    ON geo.land USING GIST (geom);

-- Input: portfolio of properties (id, coordinates, optional metadata).
CREATE TABLE IF NOT EXISTS production.properties (
    id bigint PRIMARY KEY,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    metadata jsonb
);

-- Output: one row per property, flattened spatial indicators (ML input).
CREATE TABLE IF NOT EXISTS production.property_features (
    property_id bigint PRIMARY KEY REFERENCES production.properties(id) ON DELETE CASCADE,
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
    -- Accessibility (one column per key in spatial.ACCESSIBILITY_KEY_TYPES)
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
    -- Dynamic keys stored as JSONB (pandas/ML can read; stable schema)
    by_category jsonb NOT NULL DEFAULT '{}',
    nearest_km  jsonb NOT NULL DEFAULT '{}',
    -- Coastal signals (NULL when geo.coastline table is not yet populated)
    dist_coast_km          double precision,
    land_buffer_fraction_1km double precision,
    -- Temporal enrichment: date used for POI lookup and which table was queried
    -- NULL for properties scored against production.pois_current (current mode)
    transaction_date       date,
    poi_source             text  -- 'history' | 'current'
);

CREATE INDEX IF NOT EXISTS idx_property_features_poi_refreshed_at
    ON production.property_features(poi_refreshed_at);
