# Runbook — Morocco Spatial Dashboard

**What:** Day-2 operations — database, ingest, pipeline, and verification.  
**Why:** Copy-paste commands for local dev and production-like runs.

- **Production:** Database is set up and refreshed by an external POI pipeline. Connect via `DATABASE_URL`; no restore step.
- **Local / dev:** Restore a POI dump or use the minimal CI schema. See [GETTING_STARTED](GETTING_STARTED.md).

Command reference: [scripts/README.md](../scripts/README.md)

---

## Start the database (local)

```bash
docker compose up -d db
docker compose ps   # ensure db is healthy
```

Connection from host: `postgresql://poi_user:poi_password@localhost:5432/poi_db`

---

## Restore the POI dump (local / dev only)

Load schema and data from a PostgreSQL dump (`.dump` or `.sql`). See [`data/README.md`](../data/README.md) for export format.

### Custom format (`.dump`)

```bash
docker compose cp path/to/file.dump db:/tmp/file.dump
docker compose exec db pg_restore -d poi_db -U poi_user -v /tmp/file.dump
```

### Plain SQL (`.sql`)

```bash
docker compose cp path/to/file.sql db:/tmp/file.sql
docker compose exec db psql -d poi_db -U poi_user -f /tmp/file.sql
```

### One-off container (alternative)

```bash
docker run --rm -v "C:\path\to\dumps:/dumps" --network pois_scores_v2_default postgis/postgis:16-3.5-alpine pg_restore -h db -d poi_db -U poi_user -v /dumps/file.dump
```

Network name: `<project_dir>_default`. Verify with `docker network ls`.

---

## Apply schemas (local / CI)

| Task | Command |
|------|---------|
| POI contract tables (`active.*`, `history.*`) | `python scripts/schema/apply_init.py` |
| App tables (`production.*`, `geo.*`) | `python scripts/schema/apply_feature_pipeline.py` |

Via Docker backend:

```bash
docker compose run --rm backend python scripts/schema/apply_feature_pipeline.py
```

---

## Inspect the schema

```bash
docker compose exec db psql -d poi_db -U poi_user
```

Useful commands: `\dt active.*`, `\d active.production_pois_current`, `\dx` (PostGIS).

Table and column reference: [DATA_MODEL.md](DATA_MODEL.md).

---

## Debug DB connection

- From host: `psql "postgresql://poi_user:poi_password@localhost:5432/poi_db"`
- From another Compose container: hostname `db`, port `5432`
- Ensure `DATABASE_URL` in `.env` matches user, password, host, port, database

---

## Load geo reference data (required once per fresh DB)

Populates `geo.coastline` and `geo.land`. Without them, `dist_coast_km` and `land_buffer_fraction_1km` are NULL.

From project root (Postgres must be up):

```bash
python scripts/ingest/load_osm_coastline.py
python scripts/ingest/load_osm_land.py
```

Override connection:

```powershell
$env:DATABASE_URL="postgresql://poi_user:poi_password@localhost:5432/poi_db"
python scripts/ingest/load_osm_coastline.py
```

Requires `pip install -r backend/requirements-ingest.txt` (see [backend/REQUIREMENTS.md](../backend/REQUIREMENTS.md)).

---

## Load properties from Parquet

Populates `production.properties` for dashboard and pipeline use.

```bash
python scripts/ingest/load_properties_from_parquet.py \
  --parquet input/casablanca_transactions_sample.parquet
```

| Flag | Default | Description |
|------|---------|-------------|
| `--parquet` | *(required)* | Path to `.parquet` file |
| `--batch-size` | `500` | Rows per upsert batch |
| `--dry-run` | off | Parse and validate only |

Reads `DATABASE_URL` from environment or `.env`. Adds missing columns on first run; upserts on `transaction_id`.

---

## pgAdmin (local)

Included in `docker-compose.yml`. URL: http://localhost:5050 — login `admin@admin.com` / `admin`.

| Field | Value |
|-------|-------|
| Host | `db` |
| Port | `5432` |
| Database | `poi_db` |
| Username | `poi_user` |
| Password | `poi_password` |

---

## Feature engineering pipeline

Computes spatial indicators for every property in `production.properties` and writes to `production.property_features`.

### Apply pipeline schema (once)

```bash
python scripts/schema/apply_feature_pipeline.py
```

Or via Docker:

```bash
docker compose run --rm backend python scripts/schema/apply_feature_pipeline.py
```

### Run the pipeline

The pipeline service uses Docker profile `pipeline` — it is **not** started by `docker compose up -d`.

**Docker (recommended):**

```bash
docker compose --profile pipeline run --rm pipeline
```

**CLI (from `backend/` with venv):**

```bash
python -m app.features.feature_pipeline weekly_continuous
python -m app.features.feature_pipeline historical_batch
```

See [feature_pipeline README](../backend/app/features/feature_pipeline/README.md) for flags and tuning.

**Scheduled (e.g. nightly):**

```bash
0 2 * * * cd /path/to/repo && docker compose --profile pipeline run --rm pipeline
```

### How pending detection works

- **Weekly flow:** reads `max(active.audit_pipeline_runs.run_timestamp)` as the current POI version. Recomputes properties missing a `property_features` row for that version.
- **Historical flow:** scores each property at its `transaction_date` using `history.production_poi_history` (SCD2 filter).

After an external POI refresh, the next weekly run recomputes the portfolio.

---

## Prefect automation

Prefect flows live in [`backend/app/features/feature_pipeline/flow.py`](../backend/app/features/feature_pipeline/flow.py):

| Flow | Purpose |
|------|---------|
| `weekly_recompute_flow` | Wraps `weekly_continuous` |
| `historical_backfill_flow` | Wraps `historical_batch` |

### Local setup

```bash
cd backend
pip install -r requirements-pipeline.txt
export DATABASE_URL="postgresql://..."
python -c "from app.features.feature_pipeline.flow import weekly_recompute_flow; weekly_recompute_flow()"
```

### Prefect Cloud (optional)

1. `prefect cloud login`
2. Set variables: `prefect variable set database_url "postgresql://..."`
3. Deploy flows from the private GitLab repo with managed work pool
4. Schedule after expected external POI refresh (e.g. day 1 at 02:00)

The flow assumes the external POI pipeline writes a new row to `active.audit_pipeline_runs`. If that table is not updated, the weekly flow may skip (no new POI version).

---

## Verification checklist

Before pushing or releasing (see [CONTRIBUTING.md](../CONTRIBUTING.md)):

| Check | Command |
|-------|--------|
| Backend lint | `ruff check backend/` |
| Backend format | `ruff format --check backend/` |
| Backend tests + coverage | `cd backend && pytest tests/ -v --cov=app --cov-fail-under=70` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend format | `cd frontend && npm run format:check` |
| Frontend tests | `cd frontend && npm run test` |
| Frontend build | `cd frontend && npm run build` |
| Pre-commit | `pre-commit run --all-files` |

Integration tests need Postgres with schema (`apply_init.py` or dump restore).

---

## Schema change policy

- **Production POI schema:** managed externally.
- **App schema:** update SQL in `scripts/schema/`, then [DATA_MODEL.md](DATA_MODEL.md) and this runbook in the same MR.
- **Table renames:** update `backend/app/core/tables.py` first.
