# CLAUDE.md — pois_scores_v2

## Project
Geospatial POI scoring platform and pipline. FastAPI backend with PostGIS spatial queries,
React/TypeScript/Vite frontend, PostgreSQL database, Docker Compose orchestration.

## Cleanup rules (MANDATORY — never override these)
1. NEVER modify any file without being explicitly told to in the current session.
2. NEVER refactor PostGIS queries, raw SQL, or GeoAlchemy2 expressions without
   a human reviewing every line first. Flag these and stop.
3. NEVER change function signatures, endpoint paths, HTTP methods, or response
   schemas without explicit approval. These are API contracts.
4. NEVER use placeholders like `# ... rest of code here`. Output complete files only.
5. NEVER mix analysis and execution in the same pass. Analyse first, wait for approval,
   then fix.
6. After every file change, list all other files that need import updates as a result.
7. If tests go red at any point: stop, revert the last change, report what happened.

## Stack details
- Backend: Python 3.x, FastAPI, SQLAlchemy + PostGIS/GeoAlchemy2, Pydantic v2,
  Prefect (orchestration), Pytest
- Frontend: React 18, TypeScript, Vite, Vitest
- DB: PostgreSQL 16 + PostGIS 3.5
- Infra: Docker Compose, pgAdmin

## Test commands (Windows PowerShell)
# Backend (from backend/ with venv active)
pytest --tb=short

# Frontend (from frontend/)
npx vitest run

