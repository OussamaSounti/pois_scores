# Data model

**What:** PostgreSQL schemas and tables used by the API and feature pipeline.  
**Why:** The backend reads these tables only — it does not create or alter the external POI schema. Use this document to look up correct schema, table, and column names.

**Source of truth in code:** [`backend/app/core/tables.py`](../backend/app/core/tables.py)  
**POI export details:** [`data/README.md`](../data/README.md) (taxonomy, dump format)  
**Schema SQL:** [`scripts/schema/`](../scripts/schema/)

---

## Schema overview

| Schema | Owner | Purpose |
|--------|-------|---------|
| `active` | External POI pipeline | Current POI snapshot, audit, taxonomy |
| `history` | External POI pipeline | SCD2 versioned POI timeline |
| `production` | This app | Properties, precomputed features, pipeline run ledger |
| `geo` | This app (local bootstrap) | Coastline and land reference polygons |

```mermaid
flowchart LR
  subgraph external [External POI pipeline]
    POI[active.production_pois_current]
    HIST[history.production_poi_history]
    AUDIT[active.audit_pipeline_runs]
  end

  subgraph app [This app]
    PROPS[production.properties]
    FEAT[production.property_features]
    RUNS[production.feature_pipeline_runs]
    GEO[geo.coastline / geo.land]
  end

  POI --> API[FastAPI scores/pois]
  HIST --> API
  POI --> Pipeline[feature_pipeline]
  HIST --> Pipeline
  AUDIT --> Pipeline
  PROPS --> Pipeline
  GEO --> Pipeline
  Pipeline --> FEAT
  Pipeline --> RUNS
  FEAT --> API
```

---

## POI tables (external — read only)

### `active.production_pois_current`

**What the API and pipeline query for live POI data.** Flat snapshot: one row per POI.

| Column | Type | Description |
|--------|------|-------------|
| `osm_id` | text | Primary key — OpenStreetMap element ID |
| `name` | text | POI name (default `'Unnamed'`) |
| `fclass` | text | Fine class (e.g. `bus_stop`, `pharmacy`) |
| `super_category` | text | Category (e.g. Transport, Healthcare) |
| `lat` | double precision | WGS84 latitude |
| `lon` | double precision | WGS84 longitude |
| `geom` | geometry(Point, 4326) | PostGIS point for spatial queries |

**Indexes:** GiST on `geom`; btree on `super_category`.

There is **no** `is_active` column — all rows in this table are the current snapshot.

Use `lat` / `lon` for simple distance logic; use `geom` with PostGIS (`ST_DWithin`, `ST_Distance`) for radius queries.

### `history.production_poi_history`

**What the pipeline uses for temporal scoring** at a property's `transaction_date`. SCD2 versioned timeline.

| Column | Type | Description |
|--------|------|-------------|
| `osm_id` | text | OpenStreetMap element ID |
| `name` | text | POI name |
| `fclass` | text | Fine class |
| `super_category` | text | Category |
| `lat` | double precision | WGS84 latitude |
| `lon` | double precision | WGS84 longitude |
| `geom` | geometry(Point, 4326) | PostGIS point |
| `valid_from` | timestamptz | Version start (inclusive) |
| `valid_to` | timestamptz | Version end (exclusive) |
| `is_canonical` | boolean | `true` = deduplicated row for queries |

**Query filter (required):** always include `is_canonical = true` and `valid_from <= as_of < valid_to`. See `POI_HISTORY_SCD2_WHERE` in `tables.py`.

**Source:** populated by the external POI pipeline or restored from [`data/poi_db_export.sql`](../data/poi_db_export.sql). There is no CSV import in this repo.

### `active.audit_pipeline_runs`

**What the weekly pipeline reads** to detect a new POI refresh.

| Column | Type | Description |
|--------|------|-------------|
| `run_timestamp` | timestamptz | When the external POI pipeline finished |
| (other columns) | — | Run metadata maintained by the external pipeline |

The feature pipeline uses `max(run_timestamp)` as the current POI version (`poi_refreshed_at`). This app does **not** write to this table.

For taxonomy (`active.categories`, `active.category_mapping`) and full export details, see [`data/README.md`](../data/README.md).

---

## Geo reference (app-owned — local bootstrap)

Created by [`scripts/schema/feature_pipeline.sql`](../scripts/schema/feature_pipeline.sql). Populate once per fresh database.

### `geo.coastline`

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `name` | text | Optional label |
| `geom` | geometry(MultiLineString, 4326) | Coastline segments |

Load: `python scripts/ingest/load_osm_coastline.py`

### `geo.land`

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `name` | text | Optional label |
| `geom` | geometry(MultiPolygon, 4326) | Land polygon(s) |

Load: `python scripts/ingest/load_osm_land.py`

Without these tables, `dist_coast_km` and `land_buffer_fraction_1km` are NULL.

---

## Feature pipeline tables (app-owned)

Created by [`scripts/schema/apply_feature_pipeline.py`](../scripts/schema/apply_feature_pipeline.py). See [RUNBOOK](RUNBOOK.md#feature-engineering-pipeline).

### `production.properties` (pipeline input)

Slim index of locations to score. Only pipeline-needed columns — rich transaction data lives in the source transactions table (e.g. `analytics.transactions` in prod, `staging.transactions` in dev).

| Column | Type | Description |
|--------|------|-------------|
| `transaction_id` | bigint | Primary key — join key to source transactions |
| `latitude` | double precision | WGS84 latitude |
| `longitude` | double precision | WGS84 longitude |
| `transaction_date` | date | Used by `historical_batch` for temporal POI lookup |

Dev: [`scripts/ingest/load_properties_from_parquet.py`](../scripts/ingest/load_properties_from_parquet.py) loads parquet into `staging.transactions` and syncs slim rows here. Prod: external ETL copies coords from the 1M-row transactions table. Set `TRANSACTIONS_TABLE` so the Properties dashboard can join attributes at read time.

### `production.property_features` (output — ML input)

One row per property; flattened spatial indicators. The ML team reads this table directly — no API calls needed.

| Column | Type | Description |
|--------|------|-------------|
| `transaction_id` | bigint | PK, FK → `properties(transaction_id)` — join directly to source transactions |
| `poi_refreshed_at` | timestamptz | POI version used — **use for reproducibility** |
| `pipeline_version` | text | Pipeline code version |
| `computed_at` | timestamptz | When the row was written |
| `poi_count_1km` | integer | POIs within 1 km |
| `poi_count_400m` | integer | POIs within 400 m |
| `n_categories` | integer | Distinct super_categories within 1 km |
| `n_poi_types` | integer | Distinct fclass values within 1 km |
| `entropy` | double precision | Shannon entropy of super_category (bits) |
| `entropy_fclass` | double precision | Shannon entropy of fclass (bits) |
| `aggregate_score` | double precision | Aggregate score 0–100 (nullable) |
| `acc_*` (13 booleans) | boolean | Accessibility within 400 m |
| `by_category` | jsonb | POI count per super_category (1 km) |
| `nearest_km` | jsonb | Distance to nearest POI per super_category |
| `dist_coast_km` | double precision | Distance to coastline (NULL if geo not loaded) |
| `land_buffer_fraction_1km` | double precision | Fraction of 1 km buffer on land |
| `transaction_date` | date | Date used for temporal POI lookup (nullable) |
| `poi_source` | text | `'history'` or `'current'` |

Index: `property_features(poi_refreshed_at)` for pending-property queries.

### `production.feature_pipeline_runs` and `production.feature_pipeline_failures`

Run ledger for pipeline executions. Defined in [`scripts/schema/feature_pipeline_runs.sql`](../scripts/schema/feature_pipeline_runs.sql).

Key columns on `feature_pipeline_runs`: `run_id`, `flow_name`, `status`, `started_at`, `finished_at`, `processed`, `failed`, `poi_refreshed_at`, `triggered_by`.

See [`backend/app/features/feature_pipeline/README.md`](../backend/app/features/feature_pipeline/README.md) for query examples.

---

## CI minimal schema

For tests without a full dump, CI applies [`scripts/schema/init_schema_ci.sql`](../scripts/schema/init_schema_ci.sql), which creates empty `active.production_pois_current` and `history.production_poi_history` with the contract columns above.

---

## Schema change policy

- **Production POI schema:** managed by the external pipeline — changes happen outside this repo.
- **App schema (`production.*`, `geo.*`):** apply via `scripts/schema/` SQL and update this doc in the same MR.
- **When renaming tables:** update `backend/app/core/tables.py` first, then this file, [RUNBOOK](RUNBOOK.md), and [scripts/README.md](../scripts/README.md).
