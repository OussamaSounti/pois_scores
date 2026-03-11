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

## Quick start (Phase 0)

1. **Copy environment file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` if you change the DB user, password, or database name (they must match `docker-compose.yml` and the restore step).

2. **Start Postgres**
   ```bash
   docker compose up -d db
   ```
   Wait until the DB is healthy (`docker compose ps`).

3. **Restore the POI dump**
   The application uses a PostgreSQL dump (`.dump` or `.sql`) as the source of schema and data. Restore it **after** the first start. See [docs/RUNBOOK.md](docs/RUNBOOK.md) for exact commands (`pg_restore` or `psql`).

4. **Document the schema**
   After restore, inspect tables in `psql` and record the actual table and column names in [docs/DATA_MODEL.md](docs/DATA_MODEL.md). The backend will use this to query POIs (no schema creation in code).

## Run the API (Phase 1)

With Postgres running and the dump restored:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **API docs:** http://localhost:8000/docs  
- **Single-location score:** GET or POST `/api/v1/scores` (query params or body `{"lat": 33.5, "lon": -7.6}`)  
- **Health:** GET `/health`, GET `/ready`

Set `DATABASE_URL` in `.env` at the project root (or export it) so the backend can connect to Postgres; the app loads `.env` from the current working directory when run from `backend/`.

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
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md) — Actual POI table(s) and columns (fill after restore)
- [PROJECT_SPEC.md](PROJECT_SPEC.md) — Full project specification and phased plan

## Next steps

- **Phase 3:** Backend in Docker, GitLab CI
- **Phase 4:** Dashboard (single, batch, map)
- **Phase 5:** Docs and polish
