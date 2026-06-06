# feature_pipeline/

Offline batch jobs that populate `production.property_features` by scoring
every property against POI data.

## Two Flows

| Flow                 | Trigger            | POI Source                          | poi_source value |
|----------------------|--------------------|-------------------------------------|------------------|
| `weekly_continuous`  | Prefect weekly     | `active.production_pois_current`    | `'current'`      |
| `historical_batch`   | Manual one-shot    | `history.production_poi_history`    | `'history'`      |

## CLI Usage

```bash
python -m app.features.feature_pipeline weekly_continuous [--chunk-size N]
python -m app.features.feature_pipeline historical_batch  [--chunk-size N]
```

## Files

| File                   | Role                                                  |
|------------------------|-------------------------------------------------------|
| `__main__.py`          | CLI dispatcher for the two flows                      |
| `flow.py`              | Prefect flow definitions with idempotency checks      |
| `historical_batch.py`  | Bulk backfill: scores properties at their transaction date |
| `weekly_continuous.py` | Delta flow: scores newly-arrived properties            |
| `db_utils.py`          | Row mapping (`score_dict_to_feature_row`) and upsert helpers |

## Public API (via `__init__.py`)

```python
from app.features.feature_pipeline import run_historical_batch, run_weekly_continuous
```

## Dependencies

- `app.features.scores` — `compute_scores`, `compute_scores_at_date`
- `app.core.constants` — column definitions, chunk sizes
- `app.core.config` — pipeline version, log level
- `app.core.db` — session factory
