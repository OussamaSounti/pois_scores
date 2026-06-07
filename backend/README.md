# backend/

**What:** Python backend — FastAPI API, feature pipeline, and tests.  
**Why:** Single package (`app`) serves both the HTTP API and offline batch scoring.

---

## Three ways to run it

| Mode | Command | Requirements file |
|------|---------|-------------------|
| **API** | `uvicorn app.main:app --reload --port 8000` | `requirements-dev.txt` (includes API deps) |
| **Pipeline CLI** | `python -m app.features.feature_pipeline weekly_continuous` | `requirements-pipeline.txt` |
| **Tests** | `pytest tests/ -v` | `requirements-dev.txt` |

All modes need `DATABASE_URL` pointing to Postgres. See [REQUIREMENTS.md](REQUIREMENTS.md) for venv setup.

---

## Docker

| Service | Image target | Default command |
|---------|--------------|-----------------|
| `backend` | `INSTALL_TARGET=api` | `uvicorn app.main:app` |
| `pipeline` | `INSTALL_TARGET=pipeline` | `weekly_continuous` (profile `pipeline`) |

```bash
docker compose up -d backend
docker compose --profile pipeline run --rm pipeline
```

---

## Directory map

```
backend/
├── app/                    # Application package — see app/README.md
│   ├── main.py             # FastAPI entry (routers + health/metrics)
│   ├── core/               # Config, DB, tables, spatial utils
│   ├── repositories/       # All SQL queries
│   └── features/           # Domain modules (scores, pois, pipeline, …)
├── tests/
│   ├── unit/               # No DB required
│   └── integration/        # Needs Postgres + schema
├── requirements.txt        # API runtime
├── requirements-dev.txt    # API + pytest + ruff
├── requirements-pipeline.txt
├── requirements-ingest.txt
└── Dockerfile
```

---

## Scripts from repo root

Schema and ingest scripts live in [`../scripts/`](../scripts/) but import `app.*`. Run them from the repo root:

```bash
python scripts/schema/apply_feature_pipeline.py
python scripts/ingest/load_properties_from_parquet.py --parquet input/file.parquet
```

See [scripts/README.md](../scripts/README.md).

---

## Further reading

| Doc | Topic |
|-----|-------|
| [app/README.md](app/README.md) | Layer architecture |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Python deps and venv |
| [app/features/feature_pipeline/README.md](app/features/feature_pipeline/README.md) | Pipeline flows |
| [docs/RUNBOOK.md](../docs/RUNBOOK.md) | Operations |
| [docs/DATA_MODEL.md](../docs/DATA_MODEL.md) | Database tables |
