# Architecture — Morocco Spatial Dashboard

High-level design and data flow for the dashboard, API, and database.

## System context

```
┌─────────────────┐         ┌──────────────────────────────────┐
│  User / Browser │ ◄─────► │  Dashboard (React, Vite)          │
│  (localhost:3000)         │  Single + Batch tabs, Leaflet map │
└─────────────────┘         └─────────────────┬────────────────┘
                                               │ HTTP (REST)
                                               ▼
┌─────────────────┐         ┌──────────────────────────────────┐
│  External tools │ ◄─────► │  Backend API (FastAPI)            │
│  (scripts, etc.)          │  localhost:8000, /api/v1/*        │
└─────────────────┘         └─────────────────┬────────────────┘
                                               │ SQL (read-only)
                                               ▼
                               ┌──────────────────────────────────┐
                               │  PostgreSQL + PostGIS            │
                               │  production.pois, spatial index  │
                               └──────────────────────────────────┘
```

- **Dashboard** and any external client call the **same API** (single-location and batch scores, POI list).
- **Backend** is the only component that talks to the database. No direct DB access from the frontend.
- **Database** in production is an existing DB (refreshed by another pipeline); the app does not run migrations or restore dumps. For local/dev, use a dump or init script.

## Data flow

### Single-location score

1. User enters coordinates or double-clicks the map (or arrives from a batch row click).
2. Frontend calls `GET /api/v1/scores?lat=…&lon=…` (or `POST /api/v1/scores`).
3. Backend: load POIs within 1 km and 400 m (PostGIS `ST_DWithin`), compute density, diversity (entropy), accessibility flags, nearest-by-category; optionally aggregate score.
4. Response: `{ location: { lat, lon }, scores: { poi_count_1km, by_category, accessibility_400m, nearest_km, … } }`.
5. Frontend optionally calls `GET /api/v1/pois?lat=…&lon=…&radius_km=1` to list POIs for the map and right panel.

### Batch scores

1. User pastes coordinates or uploads CSV/JSON; frontend parses and validates (max 500 locations).
2. Frontend calls `POST /api/v1/scores/batch` with `{ locations: [ { lat, lon }, … ] }`.
3. Backend: for each location, same score logic as single-location; returns `{ results: [ { location, scores }, … ] }` in the same order.
4. Frontend displays the table; user can export CSV (with optional `input_row` from file) or click a row to open that site in the Single tab.

### POI list (map and right panel)

1. After a single-location analysis, frontend calls `GET /api/v1/pois?lat=…&lon=…&radius_km=1`.
2. Backend: query `production.pois` within radius with `ST_DWithin`, order by distance, return `{ pois: [ { id, name, fclass, super_category, latitude, longitude, distance_km }, … ] }`.
3. Frontend draws markers on the map and the list in the right panel; optional filter by metric section (category, accessibility, or nearest).

## Components

| Component   | Role |
|------------|------|
| **Frontend** | React SPA; Single tab (map, metrics, POI list, section filters), Batch tab (input, file drop, results table, export CSV, row → Single). |
| **Backend**  | FastAPI; `/health`, `/ready`, `/api/v1/scores`, `/api/v1/scores/batch`, `/api/v1/pois`; config via env (`DATABASE_URL`, `CORS_ORIGINS`). |
| **Database** | PostgreSQL 15+ with PostGIS; table `production.pois_current` (and audit/staging). Production = existing DB; local/dev = dump or init script. |

## Configuration and “real” database

- **Development:** Local Postgres in Docker (and optional backend in Docker); optionally restore a dump or use minimal schema for tests.
- **Production:** Connect to the existing database via `DATABASE_URL`; no restore. The DB is set up and refreshed monthly by another pipeline. See [RUNBOOK.md](RUNBOOK.md) and [DATA_MODEL.md](DATA_MODEL.md).
