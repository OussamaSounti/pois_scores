# Documentation

**Start here.** This hub maps docs by what you want to do.

---

## I want to…

| Goal | Read |
|------|------|
| Run the project locally for the first time | [GETTING_STARTED.md](GETTING_STARTED.md) |
| Operate in production (restore, pipeline, Prefect) | [RUNBOOK.md](RUNBOOK.md), [DEPLOYMENT.md](DEPLOYMENT.md) |
| Understand how the system works | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Look up a table or column | [DATA_MODEL.md](DATA_MODEL.md), [data/README.md](../data/README.md) |
| Run a CLI command | [scripts/README.md](../scripts/README.md) |
| Work on backend code | [backend/app/README.md](../backend/app/README.md) + feature READMEs |
| Work on frontend | [frontend/README.md](../frontend/README.md) |
| Contribute (branch, lint, tests) | [CONTRIBUTING.md](../CONTRIBUTING.md), [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) |
| Release and deploy | [RELEASE_AND_DEPLOY.md](RELEASE_AND_DEPLOY.md) |
| Monitor health and metrics | [OBSERVABILITY.md](OBSERVABILITY.md) |

---

## By doc type (Diátaxis)

### Tutorial — learn by doing

| Doc | Purpose |
|-----|---------|
| [GETTING_STARTED.md](GETTING_STARTED.md) | First run: Docker → geo → schema → properties → pipeline → dashboard |
| [README.md](../README.md) | Project overview and quick links |

### How-to — solve a specific task

| Doc | Purpose |
|-----|---------|
| [RUNBOOK.md](RUNBOOK.md) | Database, ingest, pipeline, Prefect, verification |
| [scripts/README.md](../scripts/README.md) | Copy-paste CLI commands |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Dev vs prod-like Docker setup |
| [RELEASE_AND_DEPLOY.md](RELEASE_AND_DEPLOY.md) | GitLab MR flow, tagging, rollback |
| [backend/REQUIREMENTS.md](../backend/REQUIREMENTS.md) | Python venv and requirement files |

### Reference — look up facts

| Doc | Purpose |
|-----|---------|
| [DATA_MODEL.md](DATA_MODEL.md) | All schemas and tables |
| [data/README.md](../data/README.md) | POI export format and taxonomy |
| [backend/app/core/tables.py](../backend/app/core/tables.py) | Canonical table name constants |
| Module READMEs under `backend/app/` | Per-feature endpoints, files, algorithms |
| OpenAPI | http://localhost:8000/docs (when API is running) |

### Explanation — understand why

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System context, data flows, scoring modes |
| [PROJECT_SPEC.md](../PROJECT_SPEC.md) | Product requirements as implemented |
| [PRODUCTION_POIS_PLATFORM.md](PRODUCTION_POIS_PLATFORM.md) | Production platform and data ownership |
| [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md) | Stack, conventions, CI gates |
| [OBSERVABILITY.md](OBSERVABILITY.md) | Logging, health, metrics |

---

## Module README index

| Path | Topic |
|------|-------|
| [backend/README.md](../backend/README.md) | Run API, pipeline, or tests |
| [backend/app/README.md](../backend/app/README.md) | App layers: core → repositories → features |
| [backend/app/features/README.md](../backend/app/features/README.md) | Feature modules map |
| [backend/app/features/scores/README.md](../backend/app/features/scores/README.md) | Scoring engine |
| [backend/app/features/pois/README.md](../backend/app/features/pois/README.md) | POI queries |
| [backend/app/features/properties/README.md](../backend/app/features/properties/README.md) | Properties map API |
| [backend/app/features/geo/README.md](../backend/app/features/geo/README.md) | GeoJSON overlays |
| [backend/app/features/feature_pipeline/README.md](../backend/app/features/feature_pipeline/README.md) | Batch pipeline |
| [backend/app/repositories/README.md](../backend/app/repositories/README.md) | SQL repository layer |
| [backend/app/core/README.md](../backend/app/core/README.md) | Config, DB, spatial utils |
| [frontend/README.md](../frontend/README.md) | Dashboard tabs and API client |
| [samples/README.md](../samples/README.md) | Batch test CSV/JSON files |

---

## Keeping docs in sync

When you change schema names (`tables.py`), script paths, or Docker profiles, update in the same MR:

`tables.py` → `DATA_MODEL.md` → `RUNBOOK.md` → `scripts/README.md` → root `README.md` if affected.

See [ENGINEERING_STANDARDS.md](ENGINEERING_STANDARDS.md#documentation).
