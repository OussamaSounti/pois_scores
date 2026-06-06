# CLEANUP.md

## Baseline — 2026-06-06
- Backend tests: 32 passed / 0 failed
- Backend coverage: 71%
- Frontend tests: 3 passed / 0 failed
- Frontend coverage: 1.38%
- desloppify score before: ___
- Schema dump: `baseline-schema.sql` (poi_user/poi_db via docker compose)
- Migrations: no Alembic — see `baseline-migrations.txt`
- Score fingerprint (SHA256): `ace051fffc2e77a8acc2b8fbb3820055a7308dfd3d42c1aad496f687388cc392`
  - Entry point: `compute_scores(session, lat, lon)` on 5 fixed Morocco coords
  - Locations: (33.5,-7.6), (34.0,-6.8), (33.0,-7.0), (33.1,-7.1), (33.2,-7.2)
  - Raw output: `baseline-score-fingerprint.txt`
- DB geometry fingerprint: `baseline-db-fingerprint.txt` (72,600 POIs in `active.production_pois_current`; avg/stddev area = 0 — point geometries)

## Triage findings
(filled in Phase 2)

## Agent blueprint
(filled in Phase 3)

## Completed slices
(filled in Phase 4)

## Final state
- Backend tests: ___ passed / ___ failed
- Backend coverage: ___%
- Frontend tests: ___ passed / ___ failed
- desloppify score after: ___