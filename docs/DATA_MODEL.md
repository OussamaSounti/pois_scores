# Data model (from restored dump)

The POI schema comes from the PostgreSQL dump. The backend **reads** these tables only; it does not create or alter them. Use this document to query the correct schema, table, and column names.

---

## Main table for POI scores: `production.pois_current`

All score endpoints (single location and batch) should query **`production.pois_current`**. This is the canonical POI table for the API. The API uses only **active** rows (`is_active = true`).

| Column             | Type             | Nullable | Default   | Description        |
|--------------------|------------------|----------|-----------|--------------------|
| id                 | bigint           | NOT NULL | sequence  | Primary key        |
| osm_id             | text             | NOT NULL | —         | OpenStreetMap ID   |
| name               | text             | NOT NULL | `'Unnamed'` | POI name        |
| fclass             | text             | NOT NULL | —         | Fine class (e.g. bus_stop, pharmacy) |
| super_category     | text             | NOT NULL | —         | Category (e.g. Transport, Healthcare) |
| latitude           | double precision | NOT NULL | —         | Latitude           |
| longitude          | double precision | NOT NULL | —         | Longitude          |
| geom               | geometry         | —        | —         | PostGIS geometry (used in spatial indexes) |
| content_hash       | text             | NOT NULL | —         | Hash for change detection |
| first_seen_at      | timestamptz      | NOT NULL | now()     | First import time  |
| last_seen_at       | timestamptz      | NOT NULL | now()     | Last seen time     |
| updated_at         | timestamptz      | NOT NULL | now()     | Last update        |
| is_active          | boolean          | NOT NULL | true      | Only active rows are used by the API |
| source_snapshot_date | date           | YES      | —         | Snapshot date of source data |

**Indexes**

| Index                   | Type  | Definition                          |
|-------------------------|-------|-------------------------------------|
| idx_prod_content_hash   | btree | (content_hash)                       |
| idx_prod_fclass         | btree | (fclass)                            |
| idx_prod_geom           | gist  | (geom)                              |
| idx_prod_geom_geog       | gist  | (geom::geography)                   |
| idx_prod_is_active      | btree | (is_active)                         |
| idx_prod_name           | btree | (name)                              |
| idx_prod_super_category | btree | (super_category)                    |

Use `latitude` / `longitude` for simple distance or bbox logic; use `geom` (and the gist indexes) for PostGIS spatial queries (e.g. ST_DWithin, ST_Distance).

---

## Other schemas from the dump (reference)

The dump also includes **audit**, **geo**, and **staging** schemas. The API is built on **`production.pois_current`**; the tables below are for context and pipeline/ETL use.

### `audit` — pipeline runs and history

- **audit.pipeline_runs**: run_id, run_timestamp, source_file, source_snapshot_date, pipeline_version, status, duration_seconds, notes
- **audit.pois_history**: id, run_id, osm_id, change_type, name, fclass, super_category, latitude, longitude, geom, content_hash, valid_from, valid_to
- **audit.run_stats**: run_id, total_raw, total_after_filter, inserted, updated, deactivated, reactivated, unchanged

### `geo`

- **geo.city_polygons**: id, name, fclass, geom (MultiPolygon)

### `staging`

- **staging.pois_stage**: osm_id, name, fclass, super_category, latitude, longitude, geom, content_hash
- **staging.raw_pois**: osm_id, name, fclass, latitude, longitude, geom, source_layer

---

## Spatial indexing

- **`production.pois_current`** (main table for the API): has both **latitude** and **longitude** (double precision) and a PostGIS **geom** column. Indexes include:
  - **btree** on `is_active` (filter active POIs).
  - **btree** on `fclass`, `name`, `super_category`, `content_hash`.
  - **gist** on `geom` and on `geom::geography` for PostGIS spatial queries (e.g. `ST_DWithin`, `ST_Distance`).

For the score API, use **`production.pois_current`** with `is_active = true` and either:
- btree + app-side Haversine, or  
- PostGIS on `geom` / `geom::geography` for “within radius” and distance.

---

## Feature pipeline tables (ML input)

These tables are **not** in the dump; they are created by the script [schema_feature_pipeline.sql](../backend/scripts/schema_feature_pipeline.sql) (see [RUNBOOK](RUNBOOK.md#feature-engineering-pipeline)). The pipeline reads from `production.properties` and **`production.pois_current`** (active POIs), and writes to `production.property_features`.

### `production.properties` (input)

Portfolio of properties; each row is one location to score.

| Column     | Type             | Description        |
|------------|------------------|--------------------|
| id         | bigint           | Primary key        |
| latitude   | double precision | NOT NULL           |
| longitude  | double precision | NOT NULL           |
| metadata   | jsonb            | Optional metadata  |

Populated by your ETL or admin process; the pipeline only reads from this table.

### `production.poi_imports` (versioning)

One row per POI data refresh. The pipeline uses `max(imported_at)` as the current POI version. The data team (or their import script) should insert a row here whenever they load new POI data.

| Column      | Type        | Description                    |
|-------------|-------------|--------------------------------|
| id          | serial      | Primary key                    |
| imported_at | timestamptz | When the POI dataset was loaded |
| label       | text        | Optional label (e.g. '2025-03') |

### `production.property_features` (output, ML input)

One row per property; each column is a spatial indicator. The ML team reads this table (e.g. with `pandas.read_sql`) as the direct input to the property valuation model; no API calls needed.

| Column            | Type      | Description |
|-------------------|-----------|-------------|
| property_id       | bigint    | PK, FK → properties(id) |
| poi_refreshed_at  | timestamptz | POI version used to compute this row; **use for reproducibility** (e.g. train and evaluate on same version). |
| pipeline_version  | text      | Version of the pipeline that wrote the row. |
| computed_at       | timestamptz | When the row was computed. |
| poi_count_1km, poi_count_400m, n_categories, n_poi_types, entropy, entropy_fclass, aggregate_score | scalars | Same as API score payload. |
| acc_bus_stop, acc_pharmacy, … (14 booleans) | boolean | Accessibility flags within 400 m. |
| by_category       | jsonb     | POI count per super_category (1 km). |
| nearest_km        | jsonb     | Distance in km to nearest POI per super_category. |

Index: `property_features(poi_refreshed_at)` for “pending” queries. When the POI dataset is refreshed, the pipeline recomputes all properties and overwrites rows (one row per property_id); `poi_refreshed_at` always records which POI import produced the features.

---

## Future migration strategy

Today, schema and data are loaded from a **dump** (see [RUNBOOK](RUNBOOK.md#restore-the-poi-dump)); CI uses `init_schema_ci.sql` to create a minimal table set when no dump is present. For **future** schema changes (new tables, columns, or indexes), prefer one of:

- **Versioned migrations** (e.g. Alembic): introduce a baseline revision matching the current state, then add incremental migrations. Initial data load remains dump + runbook; migrations apply only for DDL changes after the baseline.
- **Documented process**: if migrations are not adopted, apply schema changes via a new dump or manual SQL, and update this doc and the runbook.

Until a migration tool is in place, any schema change must be reflected in the dump or in `init_schema_ci.sql` and documented here.
