# pois/

**Data Provider** — owns every read against the external POI contract tables.

Provides an HTTP endpoint for POI listing and exposes query functions consumed
by the `scores/` calculation engine.

## Endpoints

| Method | Path  | Purpose                                              |
|--------|-------|------------------------------------------------------|
| GET    | /pois | POIs within a radius of (lat, lon), with optional `as_of` for historical lookup |

## Files

| File         | Role                                                    |
|--------------|---------------------------------------------------------|
| `router.py`  | FastAPI router for the POI list endpoint                |
| `service.py` | Delegates to `PoiRepository`; exposes individual and combined query functions |
| `schemas.py` | Pydantic response models (`PoiItemOut`, `PoisListResponse`) |

## Data Sources

- `active.production_pois_current` — flat current POI snapshot (no `is_canonical` filter needed)
- `history.production_poi_history` — SCD2 temporal table (requires `is_canonical = true`)

## Public API (via `__init__.py`)

```python
from app.features.pois import (
    PoiRow,
    query_pois_radius,
    query_pois_radius_at_date,
    query_pois_combined,           # 1km + 400m + nearest in one round-trip
    query_pois_combined_at_date,   # same, for historical scoring
    get_pois_with_distance,
    get_pois_with_distance_at_date,
)
```

## Dependencies

- `app.repositories.poi` — `PoiRepository` with raw SQL queries
- `app.core.constants` — taxonomy constants (`N_SUPER_CATEGORIES`, `N_FCLASS_TYPES`, `ACCESSIBILITY_KEY_TYPES`)

## Consumed By

- `scores/service.py` — uses combined POI query functions and `PoiRow` for score computation
