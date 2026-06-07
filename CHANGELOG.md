# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- **Documentation overhaul:** Added [docs/README.md](docs/README.md) hub, [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md), and module READMEs (`backend/`, `frontend/`, `backend/app/`). Rewrote [DATA_MODEL.md](docs/DATA_MODEL.md), [ARCHITECTURE.md](docs/ARCHITECTURE.md), [RUNBOOK.md](docs/RUNBOOK.md), [PROJECT_SPEC.md](PROJECT_SPEC.md), and [PRODUCTION_POIS_PLATFORM.md](docs/PRODUCTION_POIS_PLATFORM.md) to match current code.
- **Schema naming in docs:** POI tables documented as `active.production_pois_current` and `history.production_poi_history`; audit table as `active.audit_pipeline_runs` (replaces stale `production.pois_current`, `osm_history.*`, `audit.pipeline_runs`).
- **Script paths in docs:** All references updated to `scripts/ingest/` and `scripts/schema/` (replaces `backend/scripts/` and root-level loader paths).
- **Docker pipeline:** Documented `docker compose --profile pipeline run --rm pipeline` consistently.

### Removed

- Stale runbook sections referencing non-existent `data/import_data.py` and CSV POI import workflow.

## [0.1.0] - 2025-03-10

### Added

- API: single-location and batch POI scores (GET/POST `/api/v1/scores`, POST `/api/v1/scores/batch`), POI list (`GET /api/v1/pois`), health and readiness (`/health`, `/ready`).
- Dashboard: React app with Single tab (map, metrics, POI list, section filters) and Batch tab (paste/upload CSV or JSON, auto-detect lat/lon, export CSV, row click to Single tab).
- Feature engineering pipeline: reads from `production.properties`, computes spatial indicators via shared logic, writes to `production.property_features`; POI version from `active.audit_pipeline_runs.run_timestamp`; run on demand or on schedule.
- Docker Compose: `db`, `backend`, and `pipeline` (profile); RUNBOOK for dump restore and pipeline schema/run.
- GitLab CI: lint (Ruff), test (Postgres + pytest with coverage threshold), build (backend image on default branch).
- Documentation: RUNBOOK, DATA_MODEL, ARCHITECTURE, DEPLOYMENT, OBSERVABILITY; LICENSE, CHANGELOG, CONTRIBUTING.
