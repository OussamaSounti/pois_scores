# backend/

FastAPI API, feature pipeline, and tests — single Python package (`app`).

---

## Run modes

| Mode | Command | Requirements |
|------|---------|--------------|
| **API** | `uvicorn app.main:app --reload --port 8000` | `requirements-dev.txt` |
| **Pipeline** | `python -m app.features.feature_pipeline weekly_continuous` | `requirements-pipeline.txt` |
| **Tests** | `pytest tests/ -v` | `requirements-dev.txt` |

Set `DATABASE_URL`. Venv setup: [REQUIREMENTS.md](REQUIREMENTS.md).

---

## Docker

```bash
docker compose up -d backend                              # API
docker compose --profile pipeline run --rm pipeline       # batch pipeline
```

Pipeline image uses `INSTALL_TARGET=pipeline` (includes Prefect).

---

## Code layout

```
backend/app/
  main.py              FastAPI entry (routers + health/metrics)
  core/                config, db, tables.py, spatial, metrics
  repositories/        all SQL — services never embed queries
  features/
    scores/            score math (shared by API + pipeline)
    pois/              POI radius queries
    geo/               GeoJSON overlays
    feature_pipeline/  batch CLI + Prefect flows
tests/unit/            no DB
tests/integration/     needs Postgres + schema
```

**Dependency rule:** `core` → `repositories` → `features.*.service` → `router`.  
`core` never imports from `features`.

---

## Scripts (repo root)

Schema and ingest scripts import `app.*` — run from project root:

```bash
python scripts/schema/apply_feature_pipeline.py
python scripts/ingest/load_properties_from_parquet.py --parquet input/file.parquet
```

See [scripts/README.md](../scripts/README.md) and [docs/GUIDE.md](../docs/GUIDE.md).

---

## Pipeline

Most complex module — has its own README: [feature_pipeline/README.md](app/features/feature_pipeline/README.md).

---

## Docs

| Doc | Topic |
|-----|-------|
| [docs/GUIDE.md](../docs/GUIDE.md) | Setup and operations |
| [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) | System design |
| [docs/DATA_MODEL.md](../docs/DATA_MODEL.md) | Database tables |
