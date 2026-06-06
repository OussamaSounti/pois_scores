# health/

Liveness and readiness probes for infrastructure monitoring.

## Endpoints

| Method | Path     | Purpose                                      |
|--------|----------|----------------------------------------------|
| GET    | /health  | Liveness — always 200 if the process is up   |
| GET    | /ready   | Readiness — 200 if DB is reachable, 503 otherwise |

## Files

| File        | Role                          |
|-------------|-------------------------------|
| `router.py` | FastAPI router with both endpoints |

## Dependencies

- `app.core.db` (database session)

This module is **standalone** — no other feature imports from it and it
imports nothing from other features.
