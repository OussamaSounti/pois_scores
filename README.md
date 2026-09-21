# POI Scores — spatial location scoring for Morocco

[![CI](https://github.com/OussamaSounti/pois_scores/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/OussamaSounti/pois_scores/actions/workflows/ci.yml)
[![Live demo](https://img.shields.io/badge/demo-live-2ea44f)](https://pois-scores.vercel.app)
[![API docs](https://img.shields.io/badge/API-OpenAPI-blue)](https://pois-scores.onrender.com/docs)
[![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

**Score any coordinate in Morocco on a 0–100 "location quality" scale from the amenities around it — live through a REST API and interactive map, or in bulk through a versioned, temporally-aware feature pipeline that feeds ML models.**

`Python` · `FastAPI` · `PostgreSQL/PostGIS` · `Prefect` · `React + Leaflet` · `Docker` · `pytest` · `GitHub Actions`

🔗 **Live demo:** [pois-scores.vercel.app](https://pois-scores.vercel.app) — click anywhere on the map
📘 **API docs (OpenAPI):** [pois-scores.onrender.com/docs](https://pois-scores.onrender.com/docs)

> Runs on free tiers (Vercel + Render + Supabase). The first request after idle can take ~30 s while the API wakes up.

```bash
curl "https://pois-scores.onrender.com/api/v1/scores?lat=33.5731&lon=-7.5898"
```

[![POI Scores dashboard — Casablanca scored as of 2016-07-22: 249 POIs within 1 km, category density, 400 m accessibility grid](docs/images/dashboard-single.jpg)](https://pois-scores.vercel.app)

<sub>Central Casablanca scored **as of 22 July 2016** — the SCD2 history table reconstructs the POI landscape at that date (249 POIs within 1 km). Left: category density and 400 m walk accessibility. Right: nearest POIs with distances.</sub>

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

The amenity features follow the specification used by **Deng & Zhang (2025)** for property valuation in Hong Kong, re-implemented on OpenStreetMap data for Morocco:

| Feature family (Deng & Zhang 2025) | Definition | This implementation |
|---|---|---|
| **POI density** | number of POIs within 1 km | `poi_count_1km`, corrected by the **land fraction** of the buffer so coastal locations aren't penalised for having half their circle in the sea (an addition — Hong Kong's study area didn't need it) |
| **POI diversity** | number of POI types + Shannon entropy within 1 km | `n_categories`, `n_poi_types`, `entropy`, `entropy_fclass` (normalised variants included) |
| **POI accessibility** | binary: is each of 13 key POI types within 400 m (5-min walk)? | `accessibility_400m` over 13 types adapted to Moroccan cities (pharmacy, school, bus stop, supermarket, bank, hospital, …) |

These three families are combined into a single 0–100 **aggregate score** (30 % density · 30 % diversity · 40 % accessibility) for the dashboard; the individual features are what the ML pipeline stores. Also computed: nearest-distance per category (up to 25 km) and distance to coastline. Full formulas: [docs/POI_SCORES.md](docs/POI_SCORES.md).

> Deng & Zhang list *"discrepancies of data temporal consistency … such as the update of POI places during the study period"* as a limitation of their study. The SCD2 history table below is this project's answer to it.

<details>
<summary>Screenshot — nearest POI per category, coastal proximity and the land-fraction buffer</summary>

![Dashboard showing nearest distance per category (Healthcare 0.09 km … Religion 0.68 km), 1.10 km to the coastline, and a 100 % land buffer](docs/images/dashboard-nearest-coast.jpg)

</details>

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
- Score weights (30/30/40) are hand-set from domain judgement, not learned; the natural next step is the one Deng & Zhang take — feed the individual features to an ensemble valuation model and let feature importance / SHAP tell us what matters in Morocco.
- POI coverage depends on OpenStreetMap completeness, which varies across Moroccan cities (Deng & Zhang used a curated government POI database; OSM is noisier, hence the upcoming cleaning pipeline).
- Property sync from the source transactions table and Alembic migrations are still manual.

## Reference

Deng, L., & Zhang, X. (2025). *Boosting the accuracy of property valuation with ensemble learning and explainable artificial intelligence: The case of Hong Kong.* The Annals of Regional Science, 74, 32. https://doi.org/10.1007/s00168-025-01365-7 (open access)

## Environment variables

| Variable | Example |
|----------|---------|
| `DATABASE_URL` | `postgresql://poi_user:poi_password@localhost:5432/poi_db` |
| `LOG_LEVEL` | `info` |
| `CORS_ORIGINS` | `http://localhost:3000` |
| `PIPELINE_VERSION` | `1.0` |
| `VITE_API_URL` | `http://localhost:8000` |

See `.env.example`.
