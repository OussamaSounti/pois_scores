Morocco Spatial Dashboard — Project Specification & Implementation Plan
Version: 1.0
Purpose: Full project brief for a from-scratch, production-grade rebuild. Use this document to brief Cursor (or developers) for planning and implementation.

1. Project overview
1.1 Name and purpose
Name: Morocco Spatial Dashboard (internal/product name: e.g. “YakeeyVal” or “POI Score API”).
Purpose: Provide POI-based spatial scores for any location in Morocco. Users (analysts, internal tools, or a dashboard) can:
Get a single-location score (one lat/lon).
Get batch scores for many locations (e.g. list of addresses/sites).
Value: Quantify “what’s around” a point (density, diversity, accessibility) for site selection, impact analysis, or reporting. Must be reliable, testable, and easy to integrate (“easy to apply and linked to the real database”).
1.2 Users
Primary: Internal analysts / operators using the dashboard or API.
Secondary: Other systems (e.g. internal apps, scripts) consuming the API (single and batch).
Future: Possibly external partners via API (not in scope for v1).
1.3 Out of scope for v1
User authentication / authorization (can be added later).
Real-time streaming; batch is request/response only.
Mobile app; web dashboard + API only.
2. Functional requirements
2.1 API (backend)
ID	Requirement	Details
FR-API-1	Single-location POI score	One endpoint: input = one (lat, lon); output = structured POI scores for that point. Must be the same structure used everywhere so clients can reuse one schema.
FR-API-2	Batch POI scores	One endpoint: input = list of (lat, lon); output = list of same score objects (same order as input). Limit per request (e.g. 100–1000) to avoid timeouts.
FR-API-3	Health and readiness	Endpoint(s) for liveness and DB connectivity (e.g. /health, /ready) for Docker/K8s and monitoring.
FR-API-4	API documentation	OpenAPI (Swagger) generated from code; accurate request/response schemas and examples.
FR-API-5	Stable contract	All score fields named and typed consistently; no breaking changes without versioning or clear communication.
2.2 POI score content (what “score” means)
For each location, the API must return at least:

Identifiers: lat, lon (and optionally an id if provided in the request).
Density (1 km): e.g. poi_count_1km, counts per category (e.g. Transport, Healthcare, Education, …).
Diversity: e.g. n_categories, n_poi_types, entropy (Shannon) so clients can compare locations.
Accessibility (e.g. 400 m walk): Boolean flags for presence of key types (bus_stop, pharmacy, school, hospital, supermarket, etc.) within 400 m.
Nearest: For each category (or a subset), distance in km to nearest POI.
Optional: One aggregate “score” (e.g. 0–100) for quick ranking; formula to be defined but implemented consistently.
Exact field names and formulas should be documented in the API spec and in docs/.

2.3 Dashboard (frontend)
ID	Requirement	Details
FR-UI-1	Clear structure	Obvious sections: “Single location” (input + result), “Batch” (input + results table or list), “Map” (optional but recommended for single location).
FR-UI-2	Single location flow	User enters or clicks a point → request to single-location endpoint → display scores in a clear layout (cards/sections, no clutter).
FR-UI-3	Batch flow	User uploads CSV (or pastes/pastes list of lat,lon) → request to batch endpoint → table/list of results with location + main scores; optional export (CSV/JSON).
FR-UI-4	Readable and professional	Typography, spacing, and hierarchy that look production-ready; accessible (contrast, focus states).
FR-UI-5	Error and loading states	Loading indicators, validation errors (e.g. invalid coordinates), and API error messages shown clearly.
2.4 Data and database
ID	Requirement	Details
FR-DB-1	PostgreSQL	All POI and app data in PostgreSQL (no SQLite in production).
FR-DB-2	Real data link	Schema and connection design must allow switching to the real production DB (e.g. via DATABASE_URL) without code changes.
FR-DB-3	Local development	Developers run Postgres in Docker; same schema as production (migrations).
FR-DB-4	POI schema	At least: unique id, name, type/fclass, category/super_category, latitude, longitude. Spatial index (PostGIS or btree on lat/lon with bounding box) for fast “within radius” queries.
3. Non-functional requirements
3.1 Performance
Single-location: response time target e.g. < 2 s under normal load.
Batch: support at least 100 locations per request; design so 500–1000 is feasible (with timeouts and limits documented).
Use connection pooling and efficient queries (indexed, minimal round-trips).
3.2 Reliability and operations
App starts and stops cleanly in Docker.
Health/readiness endpoints for orchestrators.
No secrets in code; config via environment variables.
Logging: structured (JSON) with request id and level (info/error).
3.3 Maintainability and quality
Tested: unit tests for core logic (distance, score computation); integration tests for API and DB.
Linting and formatting automated (e.g. Ruff, Black).
Clear git history: one logical change per commit; meaningful messages.
Documentation: README, API docs, architecture, and runbooks where useful.
3.4 Security (baseline)
No secrets in repo; .env in .gitignore; .env.example with dummy values.
CORS configurable (not necessarily * in production).
Input validation and limits on batch size and coordinate ranges to avoid abuse.
4. Technology stack
4.1 Backend
Runtime: Python 3.11+.
Framework: FastAPI.
DB access: SQLAlchemy 2.x (async optional) or asyncpg + raw SQL; prefer one consistent approach.
Spatial: PostGIS extension for “within radius” and indexing, or bounding-box + Haversine in app (document choice).
Validation: Pydantic v2 for request/response models.
Config: Pydantic Settings (or similar) from env (e.g. DATABASE_URL, LOG_LEVEL).
4.2 Frontend
Approach: Single-page app; tech choice open (vanilla JS + Leaflet, or Vue/React/Svelte) but must be structured and maintainable.
Map: Leaflet (or Mapbox/Leaflet) for Morocco; Carto or OSM tiles.
UI: Clear layout (sections for single, batch, map); responsive where relevant.
4.3 Database
Engine: PostgreSQL 15+.
Extensions: PostGIS if used for spatial queries.
Migrations: Alembic (or similar) for versioned schema changes.
4.4 DevOps and tooling
Containers: Docker; Dockerfile for backend (and optionally frontend if served by backend or nginx).
Orchestration: docker-compose.yml with services: backend, db (Postgres). Optional: frontend or static served by backend.
VCS: Git; host on GitLab.
CI/CD: GitLab CI (.gitlab-ci.yml): lint → test (with Postgres service) → build Docker image; optional deploy stage.
Testing: pytest; pytest-cov for coverage; optional integration tests using testcontainers or a dedicated test DB in CI.
Code quality: Ruff (lint + format or Black), mypy optional; all run in CI.
4.5 Documentation
In repo: README (overview, quick start, env, how to run tests), .env.example, OpenAPI at /docs.
Optional: docs/ARCHITECTURE.md, docs/API.md, docs/DEPLOYMENT.md, docs/RUNBOOK.md.
5. Architecture (high-level)
5.1 System context
[User / Browser]  <-->  [Dashboard (Frontend)]
                              |
                              v
[External System] <-->  [Backend API (FastAPI)]  <-->  [PostgreSQL + POI data]
Dashboard and external systems call the same API (single + batch).
Backend is the only component that talks to the database.
“Real database” = same schema, different DATABASE_URL (e.g. RDS or managed Postgres).
5.2 Backend layout (suggested)
backend/
  app/
    main.py           # FastAPI app, routers, middleware
    config.py         # Settings from env
    db.py             # Session/engine, dependency
    models/           # SQLAlchemy models (if ORM)
    schemas/          # Pydantic request/response
    routers/
      scores.py       # GET/POST /api/scores, POST /api/scores/batch
      health.py       # /health, /ready
    services/
      spatial.py      # query_pois_radius, compute_scores (single), compute_scores_batch
    core/             # Optional: security, logging
  tests/
    unit/
    integration/
  alembic/
  Dockerfile
5.3 Data flow
Single score: Request (lat, lon) → validate → service loads POIs in radius (1 km / 400 m) from DB → compute metrics → return score DTO.
Batch: Request (list of lat, lon) → validate (size limit, coordinate ranges) → for each location call same “compute score” logic (or a shared function) → collect results → return list of score DTOs.
DB: All reads; no write endpoints in v1 (POI data loaded via migrations or ETL).
6. API specification (detailed)
6.1 Base URL and versioning
Base: e.g. http://localhost:8000 (dev) or https://api.example.com (prod).
Prefix: /api/v1 (or /api) for all endpoints so future versions can coexist.
Document in OpenAPI and README.
6.2 Endpoints
Health

GET /health — Liveness: 200 + {"status": "ok"}.
GET /ready — Readiness: check DB; 200 if OK, 503 if DB unreachable.
Single location score

GET /api/v1/scores?lat={lat}&lon={lon}
Response: 200 + JSON: { "location": { "lat", "lon" }, "scores": { ... } }
scores = same structure as below (density, diversity, accessibility, nearest, optional aggregate).
Or POST /api/v1/scores with body { "lat": number, "lon": number } → same response shape.
Errors: 400 invalid params, 422 validation, 500 server error.
Batch scores

POST /api/v1/scores/batch
Body: { "locations": [ { "lat": number, "lon": number }, ... ] }
Optional: "id" per location for correlation in results.
Limit: e.g. max 500 locations per request (document and enforce).
Response: 200 + { "results": [ { "location": { "lat", "lon" }, "scores": { ... } }, ... ] }
Order of results = order of locations.
Errors: 400 if over limit or invalid coordinates, 422 validation.
Score object (schema to document in OpenAPI)

location: { "lat", "lon" }
scores:
poi_count_1km, poi_count_400m
n_categories, n_poi_types, entropy
by_category: { "Transport": count, ... }
accessibility_400m: { "bus_stop": true, "pharmacy": false, ... }
nearest_km: { "Transport": 0.2, "Healthcare": 0.5, ... }
Optional: aggregate_score (0–100)
Exact keys and types must be defined in Pydantic and reflected in /docs.

7. Data model (PostgreSQL)
7.1 POI table (minimal)
id (PK, e.g. bigint or uuid)
name (nullable text)
fclass (text, e.g. bus_stop, pharmacy)
super_category (text, e.g. Transport, Healthcare)
latitude (numeric), longitude (numeric)
Optional: created_at, source
7.2 Spatial index
Option A: PostGIS geometry column + spatial index (recommended for production).
Option B: B-tree on (latitude, longitude) + bounding-box filter in query + Haversine in app.
Document choice and provide migration.
7.3 Migrations
Use Alembic (or similar); all schema changes via migrations.
Initial migration: create pois (and optional PostGIS); no application logic in DB beyond schema.
---

## 7b. Existing database: using a provided .dump

### 7b.1 Source of schema and data

- The project uses a **PostgreSQL dump** (`.dump` or `.sql`) provided by a colleague as the source of the real POI data and schema.
- The application **must not** redefine this schema from scratch with migrations; instead it **restores** the dump and **adapts** to the existing tables and column names.

### 7b.2 Dump format and restore

- **If the file is `.dump` (custom format):**  
  - Restore with: `pg_restore -d <database_name> -U <user> path/to/file.dump`  
  - Use the same database name, user, and password in `DATABASE_URL` as used for restore.
- **If the file is `.sql` (plain SQL):**  
  - Restore with: `psql -d <database_name> -U <user> -f path/to/file.sql`
- **Where to run:**  
  - **Local:** Run restore **inside** the Postgres container (e.g. copy dump into container or mount a volume, then run `pg_restore` or `psql` from inside the container), or use a one-off container that connects to the same DB and runs restore.
  - Document the exact command in README and in `docs/DEPLOYMENT.md` or `docs/RUNBOOK.md`.

### 7b.3 Project setup with the dump

- **Phase 0** should include:
  1. Start Postgres via Docker Compose (as in the main spec).
  2. Restore the colleague’s dump into the Compose Postgres database (see 7b.2).
  3. Inspect the restored schema (e.g. `\dt` and `\d pois` in `psql`) and document the actual table and column names (e.g. in `docs/DATA_MODEL.md` or in README).
  4. Configure the backend to use this database via `DATABASE_URL` and to query the **existing** tables (no schema creation in code; only reads).
- **Migrations (Alembic):**  
  - Use only for **future** changes (e.g. adding an index, or a new table for caching).  
  - The initial “schema” is the restored dump, not the first migration.

### 7b.4 Linking to the “real” database

- **Development:** Local Postgres in Docker, restored from the same dump (or a subset).
- **Production / real data:** Same dump (or a more up-to-date one) restored on the real server or managed Postgres; application connects via `DATABASE_URL`. No code change—only configuration.
- The spec’s requirement that the system be “easy to apply and linked to the real database” is satisfied by: one restore process, one connection string, and code that only reads the existing POI tables.
8. UI/UX requirements (dashboard)
8.1 Layout
Header: App name, optional nav (e.g. “Single” / “Batch”).
Single location:
Input: lat/lon inputs + “Analyze” (and/or map click).
Output: One clear “score” panel (same sections as API: density, diversity, accessibility, nearest).
Batch:
Input: File upload (CSV with lat, lon columns) or text area (one lat,lon per line).
Output: Table: columns = location, main metrics, optional “View on map” or expand row for full score.
Map (single location): Centered on Morocco; click to set point; optional markers for nearby POIs and 400 m / 1 km circles.
8.2 Quality bar
No broken layouts at 1280px width.
Loading states for every async action.
Error messages from API shown in UI (no silent failures).
Labels and placeholders in English (or as per product decision).
9. DevOps and quality (detailed)
9.1 Docker
Backend Dockerfile: Multi-stage if useful; run as non-root; use env for DATABASE_URL and port.
docker-compose.yml:
Service db: image postgres:15-alpine (or + PostGIS); env: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB; volume for persistence; healthcheck.
Service backend: build from backend Dockerfile; env from .env or compose; depends_on db; port 8000.
.env.example: DATABASE_URL, LOG_LEVEL, optional CORS_ORIGINS; no real secrets.
9.2 Git and GitLab
Repo: One GitLab repo; default branch main (or master).
Branches: Feature branches from main; merge via Merge Request.
Commits: One logical change per commit; message format e.g. type(scope): description (feat(api): add batch scores endpoint).
.gitignore: .env, __pycache__, .pytest_cache, *.db, node_modules, build artifacts, IDE files.
9.3 CI pipeline (GitLab)
Stages: lint → test → build.
Lint: Ruff (or Black + isort); fail on error.
Test:
Postgres service (e.g. postgres:15); env DATABASE_URL.
Run migrations (or schema script).
pytest with coverage; fail if tests fail or coverage below threshold (e.g. 80% for backend).
Build: Build backend Docker image; optional push to registry.
Deploy (optional): Only on main; deploy to staging or production (script or GitLab deploy job).
9.4 Testing strategy
Unit: Pure functions (Haversine, score aggregation, mapping from DB row to score). No DB.
Integration:
API tests: start app (or TestClient); use real Postgres in CI (or testcontainers).
Tests: GET /api/v1/scores, POST /api/v1/scores/batch with fixture data; assert status and shape of scores.
Data: Seed minimal POI set in test DB (migration or fixture) so “within radius” and “nearest” are deterministic.
10. Documentation requirements
10.1 README.md
Project name and one-paragraph description.
Prerequisites (Docker, Git).
Quick start: clone, cp .env.example .env, docker compose up, open dashboard and API docs.
Env vars table (name, description, example).
How to run tests locally (pytest).
Link to API docs (/docs) and optional docs/.
10.2 API documentation
OpenAPI generated by FastAPI; describe every endpoint, request body, response, and errors.
Add short descriptions and examples so “single location” and “batch” are self-explanatory.
10.3 Additional docs (optional but recommended)
ARCHITECTURE.md: Diagram (text or Mermaid) of components and data flow; where scores are computed.
DEPLOYMENT.md: How to deploy (e.g. Docker on a server, or K8s); env and secrets.
RUNBOOK.md: How to load POI data, how to run migrations, how to debug DB connection.
11. Phased implementation plan
Use this as the master plan; each phase should be implementable and testable.

Phase 0: Foundation (repo, tooling, DB)
Create new GitLab repo; clone locally.
Add .gitignore, README.md (stub), .env.example.
Add docker-compose.yml: Postgres only; create DB and run initial migration (create pois + index).
Document in README how to start DB and run migrations.
Deliverable: Empty app repo with Postgres and migrations running via Docker.
Phase 1: Backend core and single-location API
Initialize FastAPI app; config from env; DB connection/session.
Implement POI query “within radius” (PostGIS or bbox + Haversine); implement score computation (density, diversity, accessibility, nearest) in a service.
Expose GET or POST /api/v1/scores with Pydantic models; return consistent score object.
Add GET /health and GET /ready.
OpenAPI at /docs with correct schemas.
Deliverable: Single-location score API working against local Postgres; docs and health checks.
Phase 2: Batch API and validation
Add POST /api/v1/scores/batch with size limit and validation.
Reuse single-location score logic in a loop (or small pool); return ordered list of results.
Add unit tests for score logic; integration tests for both endpoints with test DB.
Deliverable: Batch endpoint working; tests in CI.
Phase 3: Docker and CI
Add backend Dockerfile; add backend service to docker-compose.yml; app uses DATABASE_URL from env.
Add .gitlab-ci.yml: lint, test (with Postgres), build image.
Deliverable: Full stack runs with docker compose up; CI green on push.
Phase 4: Dashboard (clear and structured)
Implement or rebuild frontend: sections for Single location, Batch, Map (for single).
Single: call /api/v1/scores, display score panel and map (click to set point).
Batch: CSV or list input → call /api/v1/scores/batch → results table; loading and error states.
Deliverable: Usable dashboard that matches “clear and well structured” and uses the real API.
Phase 5: Data, docs, and polish
Document how to load POI data (e.g. CSV → script or SQL); add sample dataset for dev.
Complete README, ARCHITECTURE.md, and optional DEPLOYMENT/RUNBOOK.
Final pass: error messages, validation, and CORS; ensure “linked to real database” is just DATABASE_URL.
Deliverable: Production-ready repo with docs and a path to real data.
12. Success criteria (definition of done)
Single-location and batch endpoints implemented and documented in OpenAPI.
Dashboard allows single-location and batch analysis with clear layout and error handling.
All data from PostgreSQL; schema and connection suitable for “real” DB.
Docker Compose runs backend + DB; README explains how.
GitLab CI runs lint and tests (and build) on every push; history has clear commits.
README and .env.example allow a new developer to run and test the project in under 15 minutes.
No secrets in repo; config via env.