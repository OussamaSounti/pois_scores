# scores/

**Calculation Engine** — pure score-math service that computes POI-based
location scores. Used by both the on-demand HTTP API and the offline
`feature_pipeline/`.

## Endpoints

| Method | Path          | Purpose                                     |
|--------|---------------|---------------------------------------------|
| GET    | /scores       | Score a single (lat, lon), optional `as_of` |
| POST   | /scores       | Same via JSON body                          |
| POST   | /scores/batch | Score multiple locations in one request      |

## Files

| File         | Role                                                       |
|--------------|------------------------------------------------------------|
| `router.py`  | FastAPI router for single + batch score endpoints          |
| `service.py` | Core math: density, diversity, accessibility, aggregate    |
| `schemas.py` | Pydantic request/response models (`ScoresPayload`, etc.)   |

## Scoring Pipeline (per location)

Each call to `compute_scores()` or `compute_scores_at_date()` executes:

1. **Combined POI CTE query** (1 round-trip) — fetches all POIs within
   25 km, splits into 1 km / 400 m buckets in Python, and computes
   nearest-by-category from the same result set.
2. **Coastal query** (1 round-trip) — distance to coastline + land
   fraction for density correction.
3. **Pure math** (in-memory) — entropy, diversity, accessibility,
   aggregate score.

Total: **2 DB round-trips per location** (reduced from 5 in the
original design).

## Public API (via `__init__.py`)

```python
from app.features.scores import compute_scores, compute_scores_at_date
```

## Dependencies

- `app.core.constants` — taxonomy constants
- `app.core.spatial` — coastal distance, entropy, land fraction
- `app.features.pois` — POI query functions and `PoiRow` dataclass

## Consumed By

- `feature_pipeline/` — calls `compute_scores` and `compute_scores_at_date`
  to populate `production.property_features`
