# geo/

Serves static reference geometries (land polygons, coastline lines) as
GeoJSON for the frontend map layer.

## Endpoints

| Method | Path           | Purpose                                         |
|--------|----------------|-------------------------------------------------|
| GET    | /geo/land      | `geo.land` rows as a GeoJSON FeatureCollection  |
| GET    | /geo/coastline | `geo.coastline` rows as a GeoJSON FeatureCollection |

## Files

| File         | Role                                              |
|--------------|---------------------------------------------------|
| `router.py`  | FastAPI router exposing the two GeoJSON endpoints  |
| `service.py` | PostGIS queries that convert table rows to GeoJSON |

## Dependencies

- `app.core.db` (database session)

## Data Sources

- `geo.land` — OSM land polygons loaded by `scripts/ingest/load_osm_*.py`
- `geo.coastline` — OSM coastline lines loaded by the same scripts

This module is **standalone** — no other feature imports from it and it
imports nothing from other features.
