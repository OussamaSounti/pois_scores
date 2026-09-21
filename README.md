# POI Scores — spatial location scoring for Morocco

**Score any coordinate in Morocco on a 0–100 "location quality" scale from the amenities around it — live through a REST API and interactive map, or in bulk through a versioned, temporally-aware feature pipeline that feeds ML models.**

`Python` · `FastAPI` · `PostgreSQL/PostGIS` · `Prefect` · `React + Leaflet` · `Docker` · `pytest` · `GitLab CI`

🔗 **Live demo:** [pois-scores.vercel.app](https://pois-scores.vercel.app) — click anywhere on the map
📘 **API docs (OpenAPI):** [pois-scores.onrender.com/docs](https://pois-scores.onrender.com/docs)

> Runs on free tiers (Vercel + Render + Supabase). The first request after idle can take ~30 s while the API wakes up.

```bash
curl "https://pois-scores.onrender.com/api/v1/scores?lat=33.5731&lon=-7.5898"
```

---

## The problem

Real-estate valuation models need to know *where* a property is, not just *what* it is — how walkable it is, how dense and diverse the surrounding amenities are, how far it is from the coast. Raw OpenStreetMap points of interest (POIs) don't answer that directly, and the answer changes over time as the POI landscape evolves.

This project turns a stream of ~monthly POI snapshots into **stable, explainable, reproducible location features** that can be queried on demand or precomputed for hundreds of thousands of transactions at the date each one actually happened.

## Data

POIs come from OpenStreetMap, stored in PostGIS as a current snapshot (`active.production_pois_current`, ~72k rows) plus an SCD2 history table (`history.production_poi_history`, ~190k versioned rows) and a two-level taxonomy (11 super-categories, 91 functional classes). A trimmed dump is provided for local development ([docs/POI_EXPORT.md](docs/POI_EXPORT.md)).

> **Upcoming:** the full **POI cleaning & preprocessing pipeline** — OSM extraction, cleaning, deduplication (`dedup_group` / `is_canonical`), taxonomy mapping and SCD2 loading — is being added to this repo. The scoring stack below already consumes its output tables.

## What it does

| Mode | Entry point | Use case |
|------|-------------|----------|
| **Live scoring** | `GET/POST /api/v1/scores` | Score one location, optionally `as_of` a past date |
| **Batch scoring** | `POST /api/v1/scores/batch` | Up to 500 locations per request |
| **Feature pipeline** | CLI / Docker / Prefect | Precompute features into `production.property_features` for ML training |
| **Dashboard** | React + Leaflet | Click the map → scores, nearby POIs, land/coast overlays; upload a CSV → batch results |

Both modes call **the same scoring code** (`backend/app/features/scores/service.py`), so the API and the training features can never drift apart.

## Method

Every score is built from POIs within a 1 km buffer and a 400 m walking radius:

- **Density (30 %)** — POI count within 1 km, corrected by the land fraction of the buffer so coastal locations aren't penalised for having half their circle in the sea.
- **Diversity (30 %)** — number of distinct super-categories and functional classes, plus Shannon entropy of the mix.
- **Accessibility (40 %)** — share of 13 essential amenity types (pharmacy, school, bus stop, supermarket, …) reachable within 400 m.

Plus nearest-distance per category (up to 25 km) and distance to coastline. Full formulas: [docs/POI_SCORES.md](docs/POI_SCORES.md).

**Temporal correctness.** POI tables are versioned (SCD2). The historical pipeline scores each transaction against the POI landscape *as it was on the transaction date*, not today's snapshot — no leakage from the future into training features.

## Engineering highlights

- **Feature-based backend** with a strict dependency rule (`core → repositories → services → routers`); all SQL lives in the repository layer.
- **Idempotent pipeline runs** tracked in `production.feature_pipeline_runs` with status, POI version and pipeline version, so any feature row is traceable to the exact inputs that produced it.
- **Two orchestration paths**: plain CLI for cron/Docker, or Prefect flows for scheduled, observable runs.
- **Observability**: `/health`, `/ready`, Prometheus `/metrics`.
- **Tests**: unit (spatial math, pipeline mapper, run bookkeeping) and integration (API against a real PostGIS); CI runs lint → tests with coverage gate → image build.

## Quick start

```bash
cp .env.example .env
docker compose up -d                         # PostGIS + API + pgAdmin
cd frontend && npm install && npm run dev    # dashboard on :3000
```

| Service | URL |
|---------|-----|
| API + OpenAPI | http://localhost:8000/docs |
| Dashboard | http://localhost:3000 |
| pgAdmin | http://localhost:5050 |

```bash
# score a point in Casablanca
curl "http://localhost:8000/api/v1/scores?lat=33.5731&lon=-7.5898"
```

Full walkthrough (POI dump, geo overlays, pipeline schema, Prefect): **[docs/GUIDE.md](docs/GUIDE.md)**

## Repository layout

```
backend/app/            FastAPI app, scoring logic, feature pipeline
  core/                 config, DB, spatial math, constants
  repositories/         all SQL
  features/             scores · pois · geo · feature_pipeline
backend/tests/          unit + integration
frontend/               React + Vite + Leaflet dashboard
scripts/                schema apply, OSM geo loaders, parquet ingest
docs/                   architecture, data model, guide, score definitions
```

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/POI_SCORES.md](docs/POI_SCORES.md) | Exact score formulas |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | Tables and columns |
| [docs/GUIDE.md](docs/GUIDE.md) | Setup, operations, deployment |
| [docs/PLATFORM_REFERENCE.md](docs/PLATFORM_REFERENCE.md) | Detailed reference — pipeline, DB, API |
| [docs/POI_EXPORT.md](docs/POI_EXPORT.md) | POI dump format and taxonomy |

Also: [CONTRIBUTING.md](CONTRIBUTING.md) · [CHANGELOG.md](CHANGELOG.md)

## Limitations and next steps

- **POI cleaning & preprocessing pipeline** (OSM extract → clean → dedup → taxonomy → SCD2 load) is upcoming; until it lands, the POI tables are loaded from the dump.
- Score weights (30/30/40) are hand-set from domain judgement, not learned; a natural next step is to validate them against transaction prices.
- POI coverage depends on OpenStreetMap completeness, which varies across Moroccan cities.
- Property sync from the source transactions table and Alembic migrations are still manual.

## Environment variables

| Variable | Example |
|----------|---------|
| `DATABASE_URL` | `postgresql://poi_user:poi_password@localhost:5432/poi_db` |
| `LOG_LEVEL` | `info` |
| `CORS_ORIGINS` | `http://localhost:3000` |
| `PIPELINE_VERSION` | `1.0` |
| `VITE_API_URL` | `http://localhost:8000` |

See `.env.example`.
