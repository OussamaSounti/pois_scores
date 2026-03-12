-- Feature engineering pipeline: input/output and POI versioning.
-- Run once after dump restore (or when adding the pipeline). Uses production schema.
CREATE SCHEMA IF NOT EXISTS production;

-- Input: portfolio of properties (id, coordinates, optional metadata).
CREATE TABLE IF NOT EXISTS production.properties (
    id bigint PRIMARY KEY,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    metadata jsonb
);

-- POI versioning: data team inserts one row per POI refresh; pipeline uses max(imported_at).
CREATE TABLE IF NOT EXISTS production.poi_imports (
    id serial PRIMARY KEY,
    imported_at timestamptz NOT NULL DEFAULT now(),
    label text
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
    nearest_km jsonb NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_property_features_poi_refreshed_at
    ON production.property_features(poi_refreshed_at);
