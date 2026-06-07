# repositories/

Data-access layer — all SQL lives here.

Service modules (`app.features.*.service`) contain business logic only. They
call repository methods; they never embed raw table strings or `SELECT` statements.
Routers stay focused on input/output validation and delegate to services.

Table names are centralized in `app.core.tables` — repositories import constants
like `T_PROPERTIES` and `T_POIS_CURRENT` rather than hardcoding
`"production.properties"` inline.

## Files

| File                    | Repository                 | Tables                                              |
|-------------------------|----------------------------|-----------------------------------------------------|
| `poi.py`                | `PoiRepository`            | `active.production_pois_current`, `history.production_poi_history` |
| `property.py`           | `PropertyRepository`       | `production.properties`, `production.property_features` (read) |
| `property_features.py`  | `PropertyFeaturesRepository` | `production.property_features` (write + pending selection) |
| `feature_pipeline_runs.py` | `FeaturePipelineRunRepository` | `production.feature_pipeline_runs`, `production.feature_pipeline_failures` |
| `geo.py`                | `GeoReferenceRepository`   | `geo.coastline`, `geo.land`                         |
| `audit.py`              | `AuditRepository`          | `active.audit_pipeline_runs`                        |

## Dependency Rule

```
app.core.tables  <──  app.repositories  <──  app.features.*.service  <──  router
```

- `app.repositories` may import from `app.core` (especially `tables.py`, `constants.py`).
- `app.repositories` must **not** import from `app.features.*`.
- Feature services instantiate repos with the session they receive from FastAPI:

```python
from app.repositories.poi import PoiRepository

def query_pois_radius(session: Session, lat: float, lon: float, radius_m: float):
    return PoiRepository(session).query_radius(lat, lon, radius_m)
```

## Public API (via `__init__.py`)

```python
from app.repositories import (
    AuditRepository,
    FeaturePipelineRunRepository,
    GeoReferenceRepository,
    PoiRepository,
    PoiRow,
    PropertyFeaturesRepository,
    PropertyRepository,
)
```

## When to add a new repository

Add or extend a repository when:

- A new table is queried from application code.
- An existing query moves out of a service or pipeline module.

Keep PostGIS-heavy raw SQL inside repositories. ORM models are optional; if
added later, define each table name once in the model and point
`app.core.tables` at the same value.

## Renaming a table

1. Update the constant in `app/core/tables.py`.
2. No service or router changes required — repositories pick up the new name
   automatically.
3. Update [docs/DATA_MODEL.md](../../../docs/DATA_MODEL.md) in the same MR.

## Further reading

| Doc | Topic |
|-----|-------|
| [docs/DATA_MODEL.md](../../../docs/DATA_MODEL.md) | Schema and column reference |
| [../README.md](../README.md) | App layer overview |
| [docs/ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) | Data flows |
