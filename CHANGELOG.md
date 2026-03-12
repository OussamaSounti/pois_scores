# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

No changes yet.

## [0.1.0] - 2025-03-10

### Added

- API: single-location and batch POI scores (GET/POST `/api/v1/scores`, POST `/api/v1/scores/batch`), POI list (`GET /api/v1/pois`), health and readiness (`/health`, `/ready`).
- Dashboard: React app with Single tab (map, metrics, POI list, section filters) and Batch tab (paste/upload CSV or JSON, auto-detect lat/lon, export CSV, row click to Single tab).
- Feature engineering pipeline: reads from `production.properties`, computes spatial indicators via shared logic, writes to `production.property_features`; POI versioning via `production.poi_imports`; run on demand or on schedule.
- Docker Compose: `db`, `backend`, and `pipeline` (profile); RUNBOOK for dump restore and pipeline schema/run.
- GitLab CI: lint (Ruff), test (Postgres + pytest with coverage threshold), build (backend image on default branch).
- Documentation: RUNBOOK, DATA_MODEL, ARCHITECTURE, DEPLOYMENT, OBSERVABILITY; LICENSE, CHANGELOG, CONTRIBUTING.
