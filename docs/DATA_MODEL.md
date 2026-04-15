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

### `audit` — pipeline runs and history

- **audit.pipeline_runs**: run_id, run_timestamp, source_file, source_snapshot_date, pipeline_version, status, duration_seconds, notes
- **audit.pois_history**: id, run_id, osm_id, change_type, name, fclass, super_category, latitude, longitude, geom, content_hash, valid_from, valid_to
- **audit.run_stats**: run_id, total_raw, total_after_filter, inserted, updated, deactivated, reactivated, unchanged

### `geo`

- **geo.city_polygons**: id, name, fclass, geom (MultiPolygon)
- **geo.coastline**: id, name, geom (MultiLineString, 4326) — OSM coastline segments for Morocco. Required for calculating the `dist_coast_km` and `land_buffer_fraction_1km` computations. Load with `python scripts/load_osm_coastline.py`.
- **geo.land**: id, name, geom (MultiPolygon, 4326) — Morocco land polygon. Required for checking if `_is_on_land`  (used when a property is > 1 km from the coast). Load with `python scripts/load_osm_land.py`.

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

Portfolio of real-estate records for checking and verifications; each row is one property location to score. Populated by running `python backend/scripts/load_properties_from_parquet.py` (see [RUNBOOK](RUNBOOK.md#load-properties-from-parquet)). The pipeline only reads from this table.

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
| poi_count_1km, poi_count_400m, n_categories, n_poi_types, entropy, entropy_fclass, aggregate_score | scalars | Same as API score payload. |
| acc_bus_stop, acc_pharmacy, … (13 booleans) | boolean | Accessibility flags within 400 m (bus_stop, pharmacy, school, hospital, supermarket, bank, atm, clinic, fuel, police, park, doctors, taxi). |
| by_category       | jsonb     | POI count per super_category (1 km). |
| nearest_km        | jsonb     | Distance in km to nearest POI per super_category. |
| dist_coast_km     | numeric   | distance in (km) to nearest OSM coastline segment. NULL when `geo.coastline` is not loaded. |
| land_buffer_fraction_1km | numeric | Fraction of the 1 km analysis buffer that lies on land (0.0–1.0). can be Used to normalise density for coastal properties and its kept for future testing to see the impact in the estimation of the price. NULL when `geo.coastline`/`geo.land` are not loaded. |

Index: `property_features(poi_refreshed_at)` for “pending” queries. When the POI dataset is refreshed, the pipeline recomputes all properties and overwrites rows (one row per property_id); `poi_refreshed_at` records the POI version timestamp used (from audit.pipeline_runs).

---

## Future migration strategy

In production the DB is managed elsewhere; for local/dev, schema and data come from a dump or `init_schema_ci.sql` (CI). For **future** schema changes in this repo (new tables, columns, or indexes), prefer one of:

- **Versioned migrations** (e.g. Alembic): introduce a baseline revision matching the current state, then add incremental migrations. Initial data load remains dump + runbook; migrations apply only for DDL changes after the baseline.
- **Documented process**: if migrations are not adopted, apply schema changes via a new dump or manual SQL, and update this doc and the runbook.

Until a migration tool is in place, any schema change must be reflected in the dump or in `init_schema_ci.sql` and documented here.
