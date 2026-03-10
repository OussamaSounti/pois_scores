# Data model (from restored dump)

The POI schema is **not** defined by application migrations. It comes from the colleague’s PostgreSQL dump. This file should be filled **after** the first restore so the backend and docs stay aligned with the real database.

## How to fill this

1. Restore the dump (see [RUNBOOK.md](RUNBOOK.md)).
2. Connect: `docker compose exec db psql -d poi_db -U poi_user`
3. Run `\dt` and note the POI-related table(s).
4. For each table, run `\d table_name` and copy the column list and types here.
5. Note whether PostGIS is used (e.g. a `geometry` column) or only `latitude`/`longitude`.

---

## Tables (to be filled after restore)

### Example placeholder

| Table  | Purpose        | Notes |
|--------|----------------|-------|
| `pois` | POI records    | *(Replace with actual table name and columns)* |

### POI table columns (example — replace with actual from `\d`)

| Column          | Type     | Description        |
|-----------------|----------|--------------------|
| id              | bigint   | Primary key        |
| name            | text     | POI name           |
| fclass          | text     | e.g. bus_stop      |
| super_category  | text     | e.g. Transport     |
| latitude        | numeric  |                    |
| longitude       | numeric  |                    |

If the dump uses different names (e.g. `lat`/`lon`, `type` instead of `fclass`), document them here. The backend will use these names for queries.

---

## Spatial indexing

- If the dump includes a **PostGIS** geometry column and spatial index, note it here (e.g. `geography(Point, 4326)`, index name).
- If the dump has only **latitude/longitude** columns, the backend will use bounding-box + Haversine; note that here.

*(Update this section after inspecting the restored schema.)*
