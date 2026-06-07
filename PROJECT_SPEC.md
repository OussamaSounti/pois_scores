# Morocco Spatial Dashboard — Project Specification

**Version:** 2.0 (as implemented)  
**Purpose:** Product and technical specification reflecting the current codebase.

---

## 1. Overview

### 1.1 Name and purpose

**Morocco Spatial Dashboard** (internal: YakeeyVal) provides POI-based spatial scores for any location in Morocco.

Users can:

- Score a **single point** (lat/lon) via API or dashboard.
- Score **many locations** in one batch request.
- Browse **precomputed property features** on an interactive map.
- Consume scores from **ML pipelines** via `production.property_features` (no API required).

### 1.2 Users

| User | How they interact |
|------|-----------------|
| Internal analysts | React dashboard (Single, Batch, Properties tabs) |
| Other internal systems | REST API (`/api/v1/*`) |
| ML team | Direct SQL on `production.property_features` |

### 1.3 Out of scope

- User authentication / authorization
- Real-time streaming
- Mobile native app
- POI ingestion (owned by external pipeline)

---

## 2. Functional requirements (implemented)

### 2.1 API

| ID | Requirement | Status |
|----|-------------|--------|
| FR-API-1 | Single-location POI score (`GET/POST /api/v1/scores`) | Done |
| FR-API-2 | Batch scores (`POST /api/v1/scores/batch`, max 500) | Done |
| FR-API-3 | Health and readiness (`/health`, `/ready`) | Done |
| FR-API-4 | OpenAPI at `/docs` | Done |
| FR-API-5 | Stable score schema (Pydantic models) | Done |
| FR-API-6 | POI list within radius (`GET /api/v1/pois`) | Done |
| FR-API-7 | Properties map API (`/api/v1/properties/*`) | Done |
| FR-API-8 | Geo overlays (`/api/v1/geo/land`, `/geo/coastline`) | Done |
| FR-API-9 | Temporal scoring via `as_of` (history SCD2) | Done |
| FR-API-10 | Prometheus metrics (`/metrics`) | Done |

### 2.2 Score content

For each location, scores include:

| Category | Fields |
|----------|--------|
| Density | `poi_count_1km`, `poi_count_400m`, `by_category` |
| Diversity | `n_categories`, `n_poi_types`, `entropy`, `entropy_fclass`, normalized variants |
| Accessibility (400 m) | Boolean flags per key type (bus_stop, pharmacy, school, …) |
| Nearest | `nearest_km` per super_category |
| Coastal | `dist_coast_km`, `land_buffer_fraction_1km` |
| Aggregate | `aggregate_score` (0–100, nullable) |
| Temporal | `poi_source` (`current` or `history`) when applicable |

Exact formulas: [backend/app/features/scores/README.md](backend/app/features/scores/README.md).

### 2.3 Dashboard

| ID | Requirement | Status |
|----|-------------|--------|
| FR-UI-1 | Three tabs: Single, Batch, Properties | Done |
| FR-UI-2 | Single: input + map click + metrics + POI list + filters | Done |
| FR-UI-3 | Batch: CSV/JSON upload, results table, export, row → Single | Done |
| FR-UI-4 | Properties: map of precomputed features, hierarchy drill-down | Done |
| FR-UI-5 | Loading and error states | Done |

Details: [frontend/README.md](frontend/README.md).

### 2.4 Feature pipeline

| ID | Requirement | Status |
|----|-------------|--------|
| FR-PIPE-1 | Weekly continuous flow (current POI snapshot) | Done |
| FR-PIPE-2 | Historical batch flow (transaction_date + SCD2) | Done |
| FR-PIPE-3 | Write to `production.property_features` | Done |
| FR-PIPE-4 | Run ledger (`production.feature_pipeline_runs`) | Done |
| FR-PIPE-5 | Prefect orchestration wrappers | Done |
| FR-PIPE-6 | Docker pipeline profile | Done |
| FR-PIPE-7 | Pending detection via `active.audit_pipeline_runs` | Done |

Details: [backend/app/features/feature_pipeline/README.md](backend/app/features/feature_pipeline/README.md).

### 2.5 Data and database

| ID | Requirement | Status |
|----|-------------|--------|
| FR-DB-1 | PostgreSQL + PostGIS | Done |
| FR-DB-2 | Production via `DATABASE_URL` only | Done |
| FR-DB-3 | Local Docker Postgres + optional dump | Done |
| FR-DB-4 | POI from `active.production_pois_current` | Done |
| FR-DB-5 | History from `history.production_poi_history` (SCD2) | Done |
| FR-DB-6 | Repository layer for all SQL | Done |

Schema reference: [docs/DATA_MODEL.md](docs/DATA_MODEL.md).

---

## 3. Non-functional requirements

### 3.1 Performance

- Single-location target: under 2 s under normal load.
- Batch: up to 500 locations per request.
- Connection pooling via SQLAlchemy; spatial indexes on POI geometry.

### 3.2 Reliability

- Docker health/readiness endpoints.
- Pipeline commits per chunk (restart-safe).
- Config via environment variables; no secrets in code.

### 3.3 Quality

- Unit tests (entropy, spatial math) — no DB.
- Integration tests (API) — Postgres + CI schema.
- CI coverage floor: 70%.
- Ruff lint/format on backend; ESLint/Prettier on frontend.

### 3.4 Security (baseline)

- `.env` in `.gitignore`; `.env.example` with placeholders.
- Configurable CORS.
- Input validation and coordinate range checks.

---

## 4. Technology stack (as built)

| Layer | Choice |
|-------|--------|
| Backend runtime | Python 3.12+ |
| API framework | FastAPI + Pydantic v2 |
| DB access | SQLAlchemy 2.x sessions + repository SQL |
| Spatial | PostGIS (`ST_DWithin`, GiST indexes) |
| Frontend | React 18 + Vite + TypeScript + Leaflet |
| Database | PostgreSQL 16 + PostGIS 3.5 (Docker) |
| Containers | Docker; single Dockerfile with `api` / `pipeline` install targets |
| CI/CD | GitLab CI: lint → test → build |
| Orchestration | Prefect (optional) for scheduled pipeline |

---

## 5. Architecture (as built)

```
backend/app/
  main.py              # Routers + health/metrics
  core/                # Config, DB, tables, spatial, metrics
  repositories/        # All SQL
  features/
    scores/            # Score math (API + pipeline)
    pois/              # POI queries
    properties/        # Property map API
    geo/               # GeoJSON
    feature_pipeline/  # Batch scoring CLI + Prefect flows
frontend/src/          # React dashboard
scripts/               # Schema apply, ingest CLIs
```

Full diagram: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 6. API summary

Base: `http://localhost:8000` (dev). Prefix: `/api/v1`.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Liveness |
| `/ready` | GET | DB readiness |
| `/scores` | GET, POST | Single score |
| `/scores/batch` | POST | Batch scores |
| `/pois` | GET | POI list in radius |
| `/properties` | GET | Map markers |
| `/properties/stats` | GET | Hierarchy stats |
| `/properties/{id}` | GET | Property detail |
| `/geo/land` | GET | Land GeoJSON |
| `/geo/coastline` | GET | Coastline GeoJSON |

OpenAPI is the authoritative request/response reference.

---

## 7. Data model summary

| Schema | Tables | Owner |
|--------|--------|-------|
| `active` | `production_pois_current`, `audit_pipeline_runs`, taxonomy | External POI pipeline |
| `history` | `production_poi_history` | External POI pipeline |
| `production` | `properties`, `property_features`, `feature_pipeline_runs` | This app |
| `geo` | `land`, `coastline` | This app (local bootstrap) |

POI contract columns: `osm_id`, `name`, `fclass`, `super_category`, `lat`, `lon`, `geom`.

---

## 8. DevOps

### Docker Compose services

| Service | Purpose |
|---------|---------|
| `db` | PostGIS 16 |
| `backend` | FastAPI API |
| `pipeline` | Feature pipeline (profile `pipeline`) |
| `pgadmin` | DB admin UI |

### CI (GitLab)

1. **lint** — Ruff on backend
2. **test** — PostGIS service → `apply_init.py` → pytest (70% coverage)
3. **build** — Docker backend image
4. **frontend** — lint, format, test, build

### Local quick start

See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

---

## 9. Documentation map

| Doc | Purpose |
|-----|---------|
| [docs/README.md](docs/README.md) | Documentation hub |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | Schema reference |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Operations |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution workflow |

---

## 10. Success criteria (met)

- Single and batch score API with OpenAPI documentation.
- Dashboard with Single, Batch, and Properties tabs.
- Feature pipeline writing to `production.property_features`.
- PostgreSQL with external POI contract + app-owned tables.
- Docker Compose for local dev; GitLab CI on every push.
- README and docs hub for onboarding in under 15 minutes.
- No secrets in repo; production = `DATABASE_URL` only.

---

## 11. Future work (not in current scope)

- User authentication and role-based access
- Alembic migrations for app schema versioning
- Automated deploy to AWS (ECS/RDS)
- Public partner API
- CI doc-drift check (grep for stale schema names)

See [docs/PRODUCTION_POIS_PLATFORM.md](docs/PRODUCTION_POIS_PLATFORM.md) for production roadmap items.
