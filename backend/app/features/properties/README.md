# properties/

Map markers, property detail, and hierarchical statistics for the frontend.

Reads from `production.properties` joined with `production.property_features`
(this codebase's own tables, not the external POI contract).

## Endpoints

| Method | Path                 | Purpose                                         |
|--------|----------------------|-------------------------------------------------|
| GET    | /properties          | Properties in bounding box for map rendering     |
| GET    | /properties/stats    | Grouped stats by admin hierarchy level           |
| GET    | /properties/{id}     | Single property with latest feature payload      |

## Files

| File         | Role                                                        |
|--------------|-------------------------------------------------------------|
| `router.py`  | FastAPI router for map, stats, and detail endpoints         |
| `service.py` | SQL queries for bbox listing, detail, and aggregated stats  |
| `schemas.py` | Pydantic response models (`PropertyMapItemOut`, etc.)       |

## Public API (via `__init__.py`)

```python
from app.features.properties import (
    list_properties_for_map,
    get_property_detail,
    get_properties_stats,
)
```

## Dependencies

- `app.core.constants` — hierarchy levels, map limits, taxonomy constants
- `app.core.db` (database session)

This module is **standalone** — it imports nothing from other features.
