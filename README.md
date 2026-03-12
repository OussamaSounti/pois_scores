# Morocco Spatial Dashboard

POI-based spatial scores for any location in Morocco. Single-location and batch endpoints; dashboard for analysts and internal tools. Data lives in PostgreSQL (schema and data from a provided dump).

## Repository (GitLab)

This project is version-controlled on **GitLab**. Clone and push via GitLab:

```bash
# Clone (replace with your GitLab repo URL)
git clone https://gitlab.com/your-group/morocco-spatial-dashboard.git
cd morocco-spatial-dashboard

# Or if you created a new repo: init and push
git init
git remote add origin https://gitlab.com/your-group/morocco-spatial-dashboard.git
git add .
git commit -m "chore: Phase 0 foundation — Docker Postgres, docs, env example"
git push -u origin main
```

Use the `main` branch as default; use feature branches and Merge Requests for changes.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Git](https://git-scm.com/)
- Python 3.11+ for running the backend

## Quick start

1. **Copy environment file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` if you change the DB user, password, or database name (they must match `docker-compose.yml` and the restore step).

2. **Start the stack (DB + backend)**
   ```bash
   docker compose up -d
   ```
   This starts Postgres and the backend API. Wait until both are up (`docker compose ps`). API: http://localhost:8000/docs

   To start only Postgres (e.g. to restore the dump first):
   ```bash
   docker compose up -d db
   ```

3. **Restore the POI dump**
   The application uses a PostgreSQL dump (`.dump` or `.sql`) as the source of schema and data. Restore it **after** the first start. See [docs/RUNBOOK.md](docs/RUNBOOK.md) for exact commands (`pg_restore` or `psql`).

4. **Document the schema**
   After restore, inspect tables in `psql` and record the actual table and column names in [docs/DATA_MODEL.md](docs/DATA_MODEL.md). The backend will use this to query POIs (no schema creation in code).

## Run the API (local, without Docker)

With Postgres running and the dump restored:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **API docs:** http://localhost:8000/docs  
- **Single-location score:** GET or POST `/api/v1/scores` (query params or body `{"lat": 33.5, "lon": -7.6}`)  
- **Health:** GET `/health`, GET `/ready`

Set `DATABASE_URL` in `.env` at the project root (or export it) so the backend can connect to Postgres; the app loads `.env` from the current working directory when run from `backend/`. When using **Docker Compose**, the backend container uses `DATABASE_URL` with host `db` (set in `docker-compose.yml`).

## Run the dashboard (Phase 4)

The dashboard is a React app: left sidebar (coords + Run + metrics), center map, right panel (POI list). It calls the backend score API and the POI list endpoint.

1. Start the API: `docker compose up -d` or `cd backend && uvicorn app.main:app --reload --port 8000`.
2. From project root: `cd frontend && npm install && npm run dev`. Open http://localhost:3000.

**Single tab**

- Enter coordinates and click Run, or **double‑click** the map to analyze that location.
- Metrics: overview (1 km / 400 m), category density, accessibility 400 m, nearest by category. Use **?** for explanations.
- Map shows the location, 1 km / 400 m circles, and POIs; right panel lists POIs within 1 km. Click a POI in the list to focus it on the map.
- **Filter by metric:** Click a **row** in "Category density", "Accessibility", or "Nearest · by category" to show only related POIs on the map and list. "Nearest" shows only the nearest POI per category. Use **Show all** to clear the filter.

**Batch tab**

- Paste coordinates (one `lat lon` or `lat,lon` per line), or **drag & drop** / choose a CSV or JSON file. Lat/lon columns are auto-detected; row labels (e.g. id, name) link results to your input.
- Run batch → results table. **Click a row** to switch to the Single tab and view that site on the map.
- **Export CSV** to download full scores (including `input_row` when loaded from a file).

Set `VITE_API_URL` in `frontend/.env` to point to another API base (e.g. `http://localhost:8000`).

## Run tests

From the `backend/` directory:

```bash
cd backend
pip install -r requirements.txt
pytest                    # all tests (integration skipped if DB down)
pytest tests/unit -v      # unit only
pytest --cov=app          # with coverage
```
Run integration tests (Postgres must be running and dump restored):
```bash
docker compose up -d db
pytest tests/integration -v
```

- **Unit tests** (entropy, haversine): always run, no DB required.
- **Integration tests** (API single + batch): run only when Postgres is up and the dump is restored; otherwise they are skipped. Use `pytest -v` for verbose output, `pytest --cov=app` for coverage.

## Environment variables

| Variable        | Description                    | Example |
|----------------|--------------------------------|---------|
| `DATABASE_URL` | PostgreSQL connection string   | `postgresql://poi_user:poi_password@localhost:5432/poi_db` |
| `LOG_LEVEL`    | Log level (debug, info, etc.)  | `info`  |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `http://localhost:3000` |

See `.env.example` for a template. Do not commit `.env`.

## Documentation

- [docs/RUNBOOK.md](docs/RUNBOOK.md) — Restore dump, run Postgres, debug connection
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md) — POI table(s) and columns (from restored dump)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System context and data flow
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Development and production-like deployment
- [PROJECT_SPEC.md](PROJECT_SPEC.md) — Full project specification and phased plan

## CI/CD (GitLab)

The pipeline (`.gitlab-ci.yml`) runs on push:

- **lint:** Ruff check and format on `backend/`
- **test:** Postgres (PostGIS) service, init minimal schema, then `pytest` with coverage
- **build:** Docker build of the backend image (on the default branch)

Ensure `.env` is not committed; CI uses its own variables and the Postgres service.

## Project phases (complete)

| Phase | Deliverable |
|-------|-------------|
| 0 | Repo, Docker Postgres (PostGIS), env, runbook for dump restore |
| 1 | Single-location score API, health/ready, OpenAPI |
| 2 | Batch score API, validation, unit and integration tests |
| 3 | Backend Dockerfile, docker-compose backend + db, GitLab CI (lint, test, build) |
| 4 | Dashboard: Single tab (map, metrics, POI list, filters), Batch tab (file drop, CSV/JSON, export, row → Single) |
| 5 | ARCHITECTURE.md, DEPLOYMENT.md, RUNBOOK and DATA_MODEL; real DB = `DATABASE_URL` only |
