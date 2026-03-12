# Data model (from restored dump)

The POI schema comes from the PostgreSQL dump. The backend **reads** these tables only; it does not create or alter them. Use this document to query the correct schema, table, and column names.

---

## Main table for POI scores: `production.pois`

All score endpoints (single location and batch) should query **`production.pois`**. This is the canonical POI table for the API.

| Column          | Type             | Nullable | Default   | Description        |
|-----------------|------------------|----------|-----------|--------------------|
| id              | bigint           | NOT NULL | sequence  | Primary key        |
| osm_id          | text             | YES      | —         | OpenStreetMap ID   |
| name            | text             | NOT NULL | `'Unnamed'` | POI name        |
| fclass          | text             | NOT NULL | —         | Fine class (e.g. bus_stop, pharmacy) |
| super_category  | text             | NOT NULL | —         | Category (e.g. Transport, Healthcare) |
| latitude        | double precision | NOT NULL | —         | Latitude           |
| longitude       | double precision | NOT NULL | —         | Longitude          |
| geom            | geometry         | —        | —         | PostGIS geometry (used in spatial indexes) |

**Indexes**

| Index                   | Type  | Definition                          |
|-------------------------|-------|-------------------------------------|
| idx_prod_coords         | btree | (latitude, longitude)               |
| idx_prod_fclass         | —     | fclass                              |
| idx_prod_geom           | gist  | (geom)                              |
| idx_prod_geom_geog      | gist  | (geom::geography)                   |
| idx_prod_name           | —     | name                                |
| idx_prod_super_category | —     | super_category                      |

Use `latitude` / `longitude` for simple distance or bbox logic; use `geom` (and the gist indexes) for PostGIS spatial queries (e.g. ST_DWithin, ST_Distance).

---

## Other POI-related tables (reference)

These live in the **`poi`** schema. The API is built on **`production.pois`**; the tables below are documented for context and possible future use.

### `poi.categories`

Lookup table for category codes and names.

| Column       | Type        | Nullable | Default | Description   |
|--------------|-------------|----------|---------|---------------|
| id           | integer     | NOT NULL | —       | Primary key   |
| code         | varchar(50) | NOT NULL | —       | Category code |
| name         | varchar(100)| NOT NULL | —       | Display name  |
| parent_code  | varchar(50) | YES      | —       | FK → poi.categories(code) |
| description  | text        | YES      | —       |               |
| created_at   | timestamptz | YES      | now()   |               |

**Relationship:** `parent_code` → `poi.categories(code)` (self-reference). Referenced by `poi.points_of_interest(category_code)`.

### `poi.points_of_interest`

Alternative POI table with geometry and address fields; not the main table for the score API.

| Column         | Type               | Nullable | Default | Description   |
|----------------|--------------------|----------|---------|---------------|
| id             | bigint             | NOT NULL | —       | Primary key   |
| osm_id         | varchar(20)        | YES      | —       |               |
| name           | varchar(255)       | YES      | —       |               |
| category_code  | varchar(50)        | YES      | —       | FK → poi.categories(code) |
| geom           | geometry(Point,4326)| NOT NULL | —       | PostGIS point |
| address        | text               | YES      | —       |               |
| city           | varchar(100)       | YES      | —       |               |
| province       | varchar(100)       | YES      | —       |               |
| region         | varchar(100)       | YES      | —       |               |
| tags           | jsonb              | YES      | '{}'    |               |
| source         | varchar(50)        | YES      | 'osm'   |               |
| created_at     | timestamptz        | YES      | —       |               |
| updated_at     | timestamptz        | YES      | —       |               |

**Indexes:** idx_poi_category, idx_poi_city, idx_poi_geom gist (geom), idx_poi_name_trgm, idx_poi_tags.

**Relationship:** `category_code` → `poi.categories(code)`.

---

## Spatial indexing

- **`production.pois`** (main table for the API): has both **latitude** and **longitude** (double precision) and a PostGIS **geom** column. Indexes include:
  - **btree** on `(latitude, longitude)` for bbox/distance-style queries.
  - **gist** on `geom` and on `geom::geography` for PostGIS spatial queries (e.g. `ST_DWithin`, `ST_Distance`).
- **`poi.points_of_interest`**: uses **geometry(Point, 4326)** in `geom` (not null), with a **gist** index on `geom` for spatial queries.

For the score API, prefer **`production.pois`** and use either:
- btree + app-side Haversine, or  
- PostGIS on `geom` / `geom::geography` for “within radius” and distance, depending on backend choice.

---

## Feature pipeline tables (ML input)

These tables are created by the feature engineering pipeline (see [RUNBOOK](RUNBOOK.md#feature-engineering-pipeline)). The pipeline reads from `production.properties` and `production.pois`, and writes to `production.property_features`.

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

| Column      | Type      | Description                    |
|-------------|-----------|--------------------------------|
| id          | serial    | Primary key                    |
| imported_at | timestamptz | When the POI dataset was loaded |
| label       | text      | Optional label (e.g. '2025-03') |

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
