# Guide — setup, operations, and deployment

Everything you need to run, operate, and deploy the Morocco Spatial Dashboard.

**Prerequisites:** Docker, Git, Python 3.12+ for scripts outside Docker. See [backend/REQUIREMENTS.md](../backend/REQUIREMENTS.md).

**CLI reference:** [scripts/README.md](../scripts/README.md)

---

## Part 1 — First run (local)

```mermaid
flowchart LR
  A[Docker up] --> B[Geo ingest]
  B --> C[Schema]
  C --> D[POI data]
  D --> E[Properties]
  E --> F[Pipeline optional]
  F --> G[Dashboard]
```

### 1. Environment and Docker

```bash
cp .env.example .env
docker compose up -d
docker compose ps
```

| Service | URL |
|---------|-----|
| Backend API + OpenAPI | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 (`admin@admin.com` / `admin`) |
| Dashboard | http://localhost:3000 (after step 7) |

Health: `curl http://localhost:8000/health`

Start only Postgres first: `docker compose up -d db`

### 2. Geo reference (required once)

Without `geo.coastline` and `geo.land`, coastal score fields stay NULL.

```bash
cd backend && python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements-ingest.txt
cd ..
python scripts/ingest/load_osm_coastline.py
python scripts/ingest/load_osm_land.py
```

### 3. Apply app schema

```bash
python scripts/schema/apply_feature_pipeline.py   # production.* + geo.*
python scripts/schema/apply_init.py               # empty POI tables (CI/tests)
```

### 4. POI data

**Option A — full dump (recommended):** restore `data/poi_db_export.sql` — see [POI_EXPORT.md](POI_EXPORT.md).

**Option B — empty CI schema:** `python scripts/schema/apply_init.py` (scores return zeros until data is loaded).

**Production:** skip — `active.*` / `history.*` are populated by the POI cleaning & preprocessing pipeline (upcoming in this repo; see [ARCHITECTURE.md](ARCHITECTURE.md)).

### 5. Load properties (optional)

```bash
python scripts/ingest/load_properties_from_parquet.py \
  --parquet input/transactions.parquet   # your own GeoParquet (EPSG:4326); input/ is gitignored
```

### 6. Feature pipeline (optional)

```bash
docker compose --profile pipeline run --rm pipeline
```

Or: `python -m app.features.feature_pipeline weekly_continuous` (from `backend/` with pipeline deps).  
Details: [feature_pipeline README](../backend/app/features/feature_pipeline/README.md).

### 7. Dashboard

```bash
cd frontend && npm install && npm run dev
```

Tabs: **Single** (live score for one location), **Batch** (score many locations from CSV/JSON).  
Set `VITE_API_URL` in `frontend/.env` if API is not on `localhost:8000`.

### API without Docker

```bash
cd backend && pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

---

## Part 2 — Operations

**Production:** POI tables are refreshed monthly by the POI cleaning & preprocessing pipeline. The scoring app connects via `DATABASE_URL` only.

Connection string (local): `postgresql://poi_user:poi_password@localhost:5432/poi_db`

### Restore POI dump (local/dev)

See [POI_EXPORT.md](POI_EXPORT.md) for dump format.

```bash
# Custom .dump
docker compose cp path/to/file.dump db:/tmp/file.dump
docker compose exec db pg_restore -d poi_db -U poi_user -v /tmp/file.dump

# Plain .sql
docker compose cp path/to/file.sql db:/tmp/file.sql
docker compose exec db psql -d poi_db -U poi_user -f /tmp/file.sql
```

### Schema apply

| Task | Command |
|------|---------|
| POI contract (`active.*`, `history.*`) | `python scripts/schema/apply_init.py` |
| App tables (`production.*`, `geo.*`) | `python scripts/schema/apply_feature_pipeline.py` |

### Inspect / debug DB

```bash
docker compose exec db psql -d poi_db -U poi_user
# \dt active.*   \d active.production_pois_current   \dx
```

Table reference: [DATA_MODEL.md](DATA_MODEL.md).

### pgAdmin

http://localhost:5050 — Host `db`, port `5432`, database `poi_db`, user `poi_user`.

### Feature pipeline

```bash
docker compose --profile pipeline run --rm pipeline
python -m app.features.feature_pipeline weekly_continuous
python -m app.features.feature_pipeline historical_batch
```

- **Weekly:** pending properties vs latest `max(active.audit_pipeline_runs.run_timestamp)`.
- **Historical:** scores at each property's `transaction_date` via SCD2 history.

Schedule: `0 2 * * * cd /path/to/repo && docker compose --profile pipeline run --rm pipeline`

### Prefect (optional)

Flows in `backend/app/features/feature_pipeline/flow.py`: `weekly_recompute_flow`, `historical_backfill_flow`.

```bash
cd backend && pip install -r requirements-pipeline.txt
python -c "from app.features.feature_pipeline.flow import weekly_recompute_flow; weekly_recompute_flow()"
```

Schedule after each POI cleaning & preprocessing run (e.g. day 1 at 02:00). Requires a new row in `active.audit_pipeline_runs`.

### Schema change policy

Update `backend/app/core/tables.py` → [DATA_MODEL.md](DATA_MODEL.md) → this guide → [scripts/README.md](../scripts/README.md) in the same MR.

---

## Part 3 — Deployment

### Development

```bash
cp .env.example .env && docker compose up -d
cd frontend && npm install && npm run dev
```

Backend without Docker: `docker compose up -d db` then `uvicorn app.main:app --reload` from `backend/`.

### Production-like

- **Backend + DB:** `docker compose up -d` — set `DATABASE_URL` to managed Postgres.
- **Frontend:** `cd frontend && npm run build` — serve `dist/` via nginx; set `VITE_API_URL` at build time.
- **CORS:** set `CORS_ORIGINS` to dashboard origin(s). See `.env.example`.

| Variable | Used by | Description |
|----------|---------|-------------|
| `DATABASE_URL` | Backend, scripts | Postgres connection |
| `LOG_LEVEL` | Backend | `info` in prod, `debug` locally |
| `CORS_ORIGINS` | Backend | Comma-separated allowed origins |
| `PIPELINE_VERSION` | Pipeline | Label in `property_features` |
| `VITE_API_URL` | Frontend build | Public API URL |

No secrets in the repo — use `.env` or platform config.

---

## Part 4 — Release and rollback

### Branch flow

- Feature branches from `main` → Merge Request → CI must pass (lint, test, build).
- Tag releases from `main`: `git tag v0.1.0 && git push origin v0.1.0` — document in [CHANGELOG.md](../CHANGELOG.md).

### Deploy

CI builds the backend Docker image on `main` but does **not** auto-deploy. Deploy manually from a tag or `main`.

### Rollback

| Layer | Action |
|-------|--------|
| Application | Redeploy previous Docker image / tag |
| Database | Not touched by app rollback — POI tables are owned by the POI pipeline |
| Pipeline | Idempotent — re-run to recompute features |

---

## Verification checklist

| Check | Command |
|-------|---------|
| Backend lint | `ruff check backend/` |
| Backend format | `ruff format --check backend/` |
| Backend tests | `cd backend && pytest tests/ -v --cov=app --cov-fail-under=70` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend test | `cd frontend && npm run test` |
| Frontend build | `cd frontend && npm run build` |
| Pre-commit | `pre-commit run --all-files` |

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full standards.

---

## See also

| Doc | Topic |
|-----|-------|
| [PLATFORM_REFERENCE.md](PLATFORM_REFERENCE.md) | Pipeline steps, API, DB, Prefect, repo status |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design (short) |
| [DATA_MODEL.md](DATA_MODEL.md) | Tables and columns |
| [POI_EXPORT.md](POI_EXPORT.md) | POI dump and taxonomy |
