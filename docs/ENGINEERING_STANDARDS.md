# Engineering standards

Conventions and quality gates for the Morocco Spatial Dashboard. All contributors and CI must follow these.

## Tech stack and supported versions

| Component      | Version / requirement | Where pinned |
|----------------|----------------------|--------------|
| Python         | 3.12+                | Backend Dockerfile, CI image, requirements.txt |
| Node           | 18+ LTS (e.g. 20)    | CI; recommend `engines` in frontend/package.json |
| TypeScript     | 5.x                  | frontend/package.json |
| PostgreSQL     | 15+ with PostGIS     | docker-compose.yml, CI service |
| Backend API    | FastAPI              | backend/requirements.txt |
| Frontend       | Vite, React 18       | frontend/package.json |

## Architecture boundaries

- **Frontend** (Vite/React) talks only to the **Backend API** (FastAPI). No direct database access from the browser.
- **Backend** is the single source of truth for app data; it reads/writes PostgreSQL (and optional pipeline tables).
- **Data flow:** Frontend → HTTP → API → DB. External systems (e.g. ML pipeline) may read from DB or API as documented.

## Coding guidelines

- **Python:** PEP 8; enforce with Ruff (lint + format). Prefer small functions and clear names.
- **TypeScript:** Strict mode (tsconfig); no `any` for public API surfaces; explicit types for API request/response (see `frontend/src/api.ts`).
- **Both:** Keep functions focused; avoid long files; document public APIs.

## Naming conventions

| Scope              | Convention   | Example |
|--------------------|--------------|---------|
| Python files       | snake_case   | `spatial.py`, `run_init_schema_ci.py` |
| React components   | PascalCase   | `SingleView.tsx`, `MetricsPanel.tsx` |
| TS utils / api     | camelCase    | `fetchScore`, `api.ts` |
| API JSON fields   | snake_case   | `poi_count_1km`, `aggregate_score` |
| API routes        | /api/v1/…   | Plural resources: `/api/v1/scores`, `/api/v1/pois` |
| DB tables/columns | snake_case   | `production.pois_current`, `content_hash` |
| DB indexes         | idx_&lt;schema&gt;_&lt;name&gt; | `idx_prod_geom`, `idx_prod_is_active` |
| Branches           | type/desc    | `feature/poi-filter`, `fix/health-check`, `docs/runbook` |
| Commits            | Conventional | `feat: add batch export`, `fix: score 500 on invalid geom`, `docs: update DATA_MODEL` |

## Docstrings

- **Required** for all public modules, classes, and functions (backend and frontend JSDoc where useful).
- Style: one-line summary or short paragraph; add Args/Returns when non-obvious. Ruff-compatible (Google or NumPy style).
- Private helpers (e.g. `_haversine_km`) may use a single-line comment or docstring.

## Typing

- **Python:** Type hints required on all public function signatures and return types. Use `typing`/generics where needed. Ruff enforces strictness.
- **TypeScript:** `strict: true` in tsconfig; avoid `any`; define explicit types for API payloads (request/response) and pass them through the app.

## Pydantic v2

- Use `Field(...)` for description (and `examples=` where it helps).
- **Request models:** `model_config = ConfigDict(extra="forbid")` so unknown keys are rejected.
- **Response models:** `extra="ignore"` (or document that responses ignore extra). Settings may use `extra="ignore"` for env vars.
- Use validators for custom validation; prefer built-in constraints (ge, le, min_length) when possible.
- Document any exception to strictness (e.g. when relaxing for backward compatibility).

## Testing

- **Backend:** Unit tests for business logic (e.g. entropy, haversine); integration tests for API with real Postgres. Minimum coverage **70%** (enforced in CI).
- **Frontend:** Unit tests for API utilities (mocked fetch); at least one smoke test for the app (e.g. render `App`). Coverage target TBD; focus on critical paths first.
- **CI:** All tests must pass; backend coverage must meet the threshold before merge.

## CI/CD quality gates

- **Lint:** Backend (Ruff check + format); frontend (ESLint, Prettier check). Must pass.
- **Test:** Backend pytest with coverage ≥ 70%; frontend test suite. Must pass.
- **Build:** Backend Docker build; frontend `npm run build`. Must succeed.
- **Deploy:** Not automatic on MR; deploy from tagged release or `main` as documented in [RELEASE_AND_DEPLOY.md](RELEASE_AND_DEPLOY.md).

## Security and secrets

- **No secrets in the repo.** Use `.env` for local and CI variables; `.env` is in `.gitignore`.
- **CORS:** Explicit allowlist only (e.g. `http://localhost:3000`). No `*` in production.
- **Secrets handling:** Document in RUNBOOK and in this doc. Rotate credentials per environment; never commit production credentials.

## Batch API: optional client `id`

The batch score request accepts an optional `id` per location (`LocationBatchItem.id`). This is for **client-side correlation only** (e.g. matching results to input rows). The API returns results in the **same order** as the request; it does not echo `id` in the response. Clients should match by index or store the mapping locally.
