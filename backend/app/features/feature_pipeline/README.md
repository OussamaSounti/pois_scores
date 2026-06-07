# feature_pipeline/

Offline batch jobs that populate `production.property_features` by scoring
every property against POI data. Optimised for large-scale runs (100k+
properties) with parallel workers, batch upserts, and progress tracking.

## Two Flows

| Flow                 | Trigger            | POI Source                          | poi_source value |
|----------------------|--------------------|-------------------------------------|------------------|
| `weekly_continuous`  | Prefect weekly     | `active.production_pois_current`    | `'current'`      |
| `historical_batch`   | Manual one-shot    | `history.production_poi_history`    | `'history'`      |

**weekly_continuous** picks up properties that have no
`production.property_features` row aligned to the latest POI refresh
timestamp. It is idempotent: if no new properties arrived, the flow
exits immediately.

**historical_batch** scores every property with a `transaction_date`
against the historical POI snapshot at that exact date. It is designed
for bulk backfill of millions of historical transactions.

## CLI Usage

```bash
# From the backend/ directory with the venv activated:

# Weekly delta (default: 4 workers, chunk_size=200)
python -m app.features.feature_pipeline weekly_continuous

# Historical backfill (default: 4 workers, chunk_size=1000)
python -m app.features.feature_pipeline historical_batch

# Full options
python -m app.features.feature_pipeline historical_batch \
    --chunk-size 500 \
    --workers 8 \
    --skip-errors
```

### CLI Flags

| Flag             | Default                     | Description                                          |
|------------------|-----------------------------|------------------------------------------------------|
| `--chunk-size N` | 200 (weekly) / 1000 (hist.) | Properties per chunk before upsert                   |
| `--workers N`    | `PIPELINE_WORKERS` env (4)  | Parallel worker threads                              |
| `--skip-errors`  | off                         | Log and skip failing properties instead of aborting   |

## Running at Scale (150k+ Properties)

### Recommended settings

```bash
# Historical backfill for ~150k properties
python -m app.features.feature_pipeline historical_batch \
    --chunk-size 500 \
    --skip-errors

# Monitor progress via structured log output:
# [historical chunk 45] 22500/150000 (15.0%) | 38.2 prop/s | chunk 13.10s | ETA 56min
```

### Environment variables for tuning

Set these in your `.env` file or export before running:

```dotenv
PIPELINE_WORKERS=4        # parallel scoring threads (match CPU cores)
DB_POOL_SIZE=8            # SQLAlchemy pool_size (>= PIPELINE_WORKERS)
DB_MAX_OVERFLOW=10        # extra connections beyond pool_size
```

### How it works internally

1. **Pending detection** — counts properties without a matching
   `property_features` row.
2. **Keyset pagination** — fetches chunks using `WHERE p.id > :last_id`
   (constant O(1) index seek, no OFFSET degradation).
3. **Parallel scoring** — a `ThreadPoolExecutor` dispatches chunks to
   worker threads. Each worker gets its own DB session from the pool.
4. **Combined CTE query** — each property is scored with a single
   SQL round-trip that fetches 1km/400m POIs and nearest-by-category,
   plus one coastline/land query. (2 queries per property, not 5.)
5. **Batch upsert** — each chunk is written with one `executemany`
   INSERT ON CONFLICT statement instead of per-row inserts.
6. **Progress tracking** — ETA, throughput (prop/s), and percentage
   are logged after every chunk.

### Resumability

Both flows are **idempotent**. If a run is interrupted, re-running the
same command picks up where it left off because the pending-detection
query skips properties that already have a valid `property_features` row.

### Run history

Each execution is recorded in **`production.feature_pipeline_runs`**
(start/end, status, counts, config snapshot). Skipped properties when using
`--skip-errors` are stored in **`production.feature_pipeline_failures`**.
Tables are **created automatically** on the first pipeline run if missing;
you can also apply them explicitly with
`python scripts/schema/apply_feature_pipeline.py`.

```sql
SELECT flow_name, status, started_at, processed, skipped, pending_before, pending_after
FROM production.feature_pipeline_runs
ORDER BY started_at DESC
LIMIT 10;
```

### Error handling

- **Default (strict):** one property failure aborts the entire chunk.
  Successful properties in that chunk are lost. Re-run picks them up.
- **`--skip-errors`:** failures are logged with full traceback,
  skipped, and the rest of the chunk proceeds. The final log line
  reports `skipped=N`.

## Docker / Prefect

```bash
# Via Docker Compose (pipeline profile)
docker compose --profile pipeline run --rm pipeline \
    python -m app.features.feature_pipeline historical_batch --skip-errors

# Via Prefect (flow.py registered flows)
# weekly_recompute_flow is auto-scheduled; historical_backfill_flow is manual.
```

## Files

| File                   | Role                                                  |
|------------------------|-------------------------------------------------------|
| `__main__.py`          | CLI dispatcher — parses args and calls the right flow |
| `flow.py`              | Prefect flow definitions with idempotency checks      |
| `historical_batch.py`  | Historical backfill with parallel workers             |
| `weekly_continuous.py` | Weekly delta with parallel workers                    |
| `db_utils.py`          | Row mapping (`score_dict_to_feature_row`) and upsert helpers |
| `run_context.py`       | `PipelineRunTracker` — writes `production.feature_pipeline_runs` |
| `progress.py`          | `ProgressTracker` — ETA, rate, and percentage logging |

## Public API (via `__init__.py`)

```python
from app.features.feature_pipeline import run_historical_batch, run_weekly_continuous

# Programmatic usage with all options:
run_historical_batch(chunk_size=500, skip_errors=True, workers=4)
run_weekly_continuous(chunk_size=200, skip_errors=True, workers=4)
```

## Dependencies

- `app.features.scores` — `compute_scores`, `compute_scores_at_date`
- `app.repositories.property_features` — pending detection and batch upsert
- `app.core.constants` — column definitions, chunk sizes, POI source enums
- `app.core.config` — pipeline version, log level, pool/worker settings
- `app.core.db` — session factory and connection pool

## Further reading

| Doc | Topic |
|-----|-------|
| [docs/RUNBOOK.md](../../../../docs/RUNBOOK.md) | Operations and Prefect |
| [docs/DATA_MODEL.md](../../../../docs/DATA_MODEL.md) | `property_features` columns |
| [scripts/README.md](../../../../scripts/README.md) | CLI command reference |
