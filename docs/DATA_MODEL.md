# Data model

Schema and data: **in production** from the existing database (refreshed by an external pipeline); **for local/dev** from a dump or from the minimal init script (`init_schema_ci.sql`). The backend **reads** these tables only; it does not create or alter the POI schema. Use this document to query the correct schema, table, and column names.

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

### `audit`

- **audit.pipeline_runs**: run_id, run_timestamp, source_file, source_snapshot_date, pipeline_version, status, duration_seconds, notes — queried by the pipeline to get the current POI version (`max(run_timestamp)`). Maintained by the external POI refresh pipeline; this app does not write to it.

### `geo`

- **geo.coastline**: id, name, geom (MultiLineString, 4326) — OSM coastline segments for Morocco. Required for computing `dist_coast_km` and `land_buffer_fraction_1km`. Load with `python scripts/load_osm_coastline.py`.
- **geo.land**: id, name, geom (MultiPolygon, 4326) — Morocco land polygon. Required for checking whether a point is on land. Load with `python scripts/load_osm_land.py`.

### `osm_history`

- **osm_history.poi_history_active**: versioned POI snapshots used by the `as_of` parameter on score endpoints. Populated by running `python data/import_data.py`. The schema is created by `schema_feature_pipeline.sql`; the table is created and populated by the import script. When not loaded, `as_of` requests fall back to `production.pois_current`.

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

Portfolio of real-estate records for checking and verifications; each row is one property location to score. Populated by running `python backend/scripts/load_properties_from_parquet.py` (see [RUNBOOK](RUNBOOK.md#load-properties-from-parquet)). The pipeline only reads from this table.

> **Local/dev note:** `schema_feature_pipeline.sql` creates a minimal version of this table with only `id`, `latitude`, `longitude`, and `metadata`. The full column set below reflects the production table and what `load_properties_from_parquet.py` populates.

| Column               | Type             | Nullable | Description |
|----------------------|------------------|----------|-------------|
| id                   | bigint           | NOT NULL | Primary key |
| latitude             | double precision | NOT NULL | WGS84 latitude |
| longitude            | double precision | NOT NULL | WGS84 longitude |
| metadata             | jsonb            | YES      | Arbitrary key-value metadata |
| transaction_id       | text             | YES      | Source transaction identifier |
| transaction_date     | date             | YES      | Date of the transaction |
| transaction_year     | integer          | YES      | Year extracted from transaction_date |
| transaction_month    | integer          | YES      | Month extracted from transaction_date |
| transaction_quarter  | integer          | YES      | Quarter extracted from transaction_date |
| asset_price          | numeric          | YES      | Transaction price (MAD) |
| asset_surface        | numeric          | YES      | Floor area (m²) |
| asset_psqm           | numeric          | YES      | Price per m² (MAD/m²) |
| asset_rooms          | integer          | YES      | Number of rooms |
| asset_floor          | integer          | YES      | Floor number |
| asset_type           | text             | YES      | Asset type (e.g. apartment, villa) |
| district_uid         | text             | YES      | Admin district UID (join key) |
| district_name        | text             | YES      | Admin district name |
| neighbourhood_uid    | text             | YES      | Neighbourhood UID |
| neighbour_name       | text             | YES      | Neighbourhood name |
| iris_uid             | text             | YES      | IRIS zone UID |
| iris_code            | text             | YES      | IRIS zone code |
| ilot_uid             | text             | YES      | Îlot UID |
| ilot_objectid        | text             | YES      | Îlot object ID |

The four `*_uid` columns (`district_uid`, `neighbourhood_uid`, `iris_uid`, `ilot_uid`) power the hierarchy drill-down in `/api/v1/properties/stats` and `/api/v1/properties ` map filter .

**POI version (for the feature pipeline):** The pipeline uses **`audit.pipeline_runs.run_timestamp`** (e.g. `max(run_timestamp)`) as the current POI version. That table is maintained by the external POI refresh pipeline; this app does not write to it.

### `production.property_features` (output, ML input)

One row per property; each column is a spatial indicator. The ML team reads this table (e.g. with `pandas.read_sql`) as the direct input to the property valuation model; no API calls needed.

| Column            | Type      | Description |
|-------------------|-----------|-------------|
| property_id       | bigint    | PK, FK → properties(id) |
| poi_refreshed_at  | timestamptz | POI version used to compute this row; **use for reproducibility** (e.g. train and evaluate on same version). |
| pipeline_version  | text      | Version of the pipeline that wrote the row. |
| computed_at       | timestamptz | When the row was computed. |
| poi_count_1km     | integer   | Number of POIs within 1 km. |
| poi_count_400m    | integer   | Number of POIs within 400 m. |
| n_categories      | integer   | Number of distinct super_categories within 1 km. |
| n_poi_types       | integer   | Number of distinct fclass values within 1 km. |
| entropy           | double precision | Shannon entropy of super_category distribution (bits). |
| entropy_fclass    | double precision | Shannon entropy of fclass distribution (bits). |
| aggregate_score   | double precision | Aggregate POI score 0–100 (NULL if not computed). |
| acc_bus_stop, acc_pharmacy, … (13 booleans) | boolean | Accessibility flags within 400 m (bus_stop, pharmacy, school, hospital, supermarket, bank, atm, clinic, fuel, police, park, doctors, taxi). |
| by_category       | jsonb     | POI count per super_category (1 km). |
| nearest_km        | jsonb     | Distance in km to nearest POI per super_category. |
| dist_coast_km     | double precision | Distance in km to nearest OSM coastline segment. NULL when `geo.coastline` is not loaded. |
| land_buffer_fraction_1km | double precision | Fraction of the 1 km analysis buffer that lies on land (0.0–1.0). Used to normalise density for coastal properties. NULL when `geo.coastline`/`geo.land` are not loaded. |
| transaction_date  | date      | Date used for temporal POI lookup. NULL when scored against the current POI snapshot. |
| poi_source        | text      | `'history'` when scored from `osm_history.poi_history_active`; `'current'` when scored from `production.pois_current`. |

Index: `property_features(poi_refreshed_at)` for “pending” queries. When the POI dataset is refreshed, the pipeline recomputes all properties and overwrites rows (one row per property_id); `poi_refreshed_at` records the POI version timestamp used (from audit.pipeline_runs).

---

## Future migration strategy

In production the DB is managed elsewhere; for local/dev, schema and data come from a dump or `init_schema_ci.sql` (CI). For **future** schema changes in this repo (new tables, columns, or indexes), prefer one of:

- **Versioned migrations** (e.g. Alembic): introduce a baseline revision matching the current state, then add incremental migrations. Initial data load remains dump + runbook; migrations apply only for DDL changes after the baseline.
- **Documented process**: if migrations are not adopted, apply schema changes via a new dump or manual SQL, and update this doc and the runbook.

Until a migration tool is in place, any schema change must be reflected in the dump or in `init_schema_ci.sql` and documented here.
