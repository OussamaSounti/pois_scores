# Morocco Spatial Dashboard

POI-based spatial scores for any location in Morocco. Single-location and batch API endpoints; React dashboard for analysts and internal tools.

**Production:** the database is set up and refreshed by an external POI pipeline — this app connects via `DATABASE_URL`.  
**Local/dev:** optional dump or minimal schema for testing.

---

## Quick start

1. Copy env: `cp .env.example .env`
2. Start stack: `docker compose up -d`
3. Follow the full walkthrough: **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)**

| Service | URL |
|---------|-----|
| Backend API + OpenAPI | http://localhost:8000/docs |
| Dashboard (after `npm run dev`) | http://localhost:3000 |
| pgAdmin | http://localhost:5050 |

---

## What this project does

- **Scores any point in Morocco** using nearby POIs — density, diversity, accessibility, nearest distances, coastal signals.
- **Serves a REST API** (`/api/v1/scores`, `/pois`, `/properties`, `/geo/*`) and a **React dashboard** (Single, Batch, Properties tabs).
- **Runs an offline pipeline** that precomputes features into `production.property_features` for ML and the Properties map.

Two scoring modes:

| Mode | When | Where results live |
|------|------|-------------------|
| **Live API** | On-demand per request | Response JSON |
| **Batch pipeline** | Scheduled or manual | `production.property_features` table |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full data flow.

---

## Repository layout

| Path | Purpose |
|------|---------|
| `backend/` | FastAPI app, feature pipeline, tests |
| `frontend/` | React + Vite dashboard |
| `scripts/` | Schema apply, geo ingest, parquet load — [scripts/README.md](scripts/README.md) |
| `docs/` | Central documentation hub — **[docs/README.md](docs/README.md)** |
| `data/` | POI database export — [data/README.md](data/README.md) |

---

## Common commands

```bash
# Geo reference (once per fresh DB)
python scripts/ingest/load_osm_coastline.py
python scripts/ingest/load_osm_land.py

# Apply app schema
python scripts/schema/apply_feature_pipeline.py

# Load properties
python scripts/ingest/load_properties_from_parquet.py --parquet input/your_file.parquet

# Run feature pipeline
docker compose --profile pipeline run --rm pipeline

# Backend tests
cd backend && pytest tests/unit -v

# Frontend dev server
cd frontend && npm install && npm run dev
```

Full command reference: [scripts/README.md](scripts/README.md) and [docs/RUNBOOK.md](docs/RUNBOOK.md).

---

## Environment variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://poi_user:poi_password@localhost:5432/poi_db` |
| `LOG_LEVEL` | Log level | `info` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `http://localhost:3000` |
| `PIPELINE_VERSION` | Label written to property_features | `1.0` |
| `VITE_API_URL` | Frontend API base (frontend only) | `http://localhost:8000` |

See `.env.example`. Do not commit `.env`.

---

## Documentation

**Start here:** [docs/README.md](docs/README.md)

| Doc | Purpose |
|-----|---------|
| [GETTING_STARTED.md](docs/GETTING_STARTED.md) | First-run tutorial |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flows |
| [DATA_MODEL.md](docs/DATA_MODEL.md) | Schemas and tables |
| [RUNBOOK.md](docs/RUNBOOK.md) | Operations and pipeline |
| [ENGINEERING_STANDARDS.md](docs/ENGINEERING_STANDARDS.md) | Coding conventions and CI |
| [PROJECT_SPEC.md](PROJECT_SPEC.md) | Product specification |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute |

Module-level docs live next to code — see the index in [docs/README.md](docs/README.md).

---

## CI/CD (GitLab)

Pipeline (`.gitlab-ci.yml`) on push:

- **lint:** Ruff on `backend/`
- **test:** PostGIS service → `apply_init.py` → pytest (70% coverage floor)
- **build:** Docker backend image (default branch)
- **frontend:** lint, format, test, build

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/RELEASE_AND_DEPLOY.md](docs/RELEASE_AND_DEPLOY.md).

---

## Contributing

Work on feature branches from `main`. Open Merge Requests; ensure CI passes. See [CONTRIBUTING.md](CONTRIBUTING.md).

Prerequisites: [backend/REQUIREMENTS.md](backend/REQUIREMENTS.md) for Python setup.
