# Contributing

How to contribute code and docs to the Morocco Spatial Dashboard.

---

## Workflow

1. Branch from `main` (e.g. `feature/my-change`, `fix/bug`, `docs/update`).
2. Open a Merge Request — describe the change; CI must pass.
3. Merge after review (if your team uses it).

**Release:** tag from `main` (`v0.1.0`) — see [GUIDE.md](docs/GUIDE.md#part-4--release-and-rollback).

---

## Before pushing

```bash
ruff check backend/ && ruff format --check backend/
cd backend && pytest tests/ -v --cov=app --cov-fail-under=70
cd frontend && npm run lint && npm run format:check && npm run test && npm run build
pre-commit run --all-files   # optional but recommended
```

Integration tests need Postgres + schema — see [GUIDE.md](docs/GUIDE.md).

---

## Tech stack

| Component | Version |
|-----------|---------|
| Python | 3.12+ |
| Node | 18+ (CI uses 20) |
| PostgreSQL | 16+ with PostGIS |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2 |
| Frontend | React 18, Vite, TypeScript |

Deps: [backend/REQUIREMENTS.md](backend/REQUIREMENTS.md).

---

## Coding standards

- **Python:** Ruff lint + format; type hints on public functions; docstrings on public APIs.
- **TypeScript:** `strict: true`; no `any` on API surfaces; types in `frontend/src/api.ts`.
- **Pydantic v2:** `extra="forbid"` on requests; `Field(...)` for descriptions.
- **Architecture:** Frontend → API only. All SQL in `repositories/`. Table names in `core/tables.py`.
- **Naming:** snake_case (Python, DB, API JSON); PascalCase (React components); `/api/v1/…` routes.
- **Commits:** conventional — `feat:`, `fix:`, `docs:`.

**Batch API:** optional `id` per location is client-side correlation only; results match input order.

---

## Testing

- Backend: unit tests (no DB) + integration tests (Postgres). **70% coverage floor** in CI.
- Frontend: Vitest on API utils and app smoke tests.

---

## Documentation

| Doc | When to update |
|-----|----------------|
| [PLATFORM_REFERENCE.md](docs/PLATFORM_REFERENCE.md) | Pipeline logic, API, architecture detail |
| [GUIDE.md](docs/GUIDE.md) | Commands, setup, ops, deploy |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | High-level system design |
| [DATA_MODEL.md](docs/DATA_MODEL.md) | Schema / table changes |
| [POI_EXPORT.md](docs/POI_EXPORT.md) | POI dump format changes |

Also update [scripts/README.md](scripts/README.md) for new CLI scripts.  
Pipeline internals: [feature_pipeline README](backend/app/features/feature_pipeline/README.md).

Avoid stale names: `production.pois_current`, `osm_history.*`, `backend/scripts/` — use `active.production_pois_current`, `scripts/ingest/`.

---

## Security

- No secrets in repo — `.env` is gitignored.
- CORS: explicit allowlist only (no `*` in production).

---

## Pre-commit

```bash
pip install pre-commit && pre-commit install
```

Runs the same checks as CI (Ruff, ESLint, Prettier).
