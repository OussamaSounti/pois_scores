# Contributing to Morocco Spatial Dashboard

## Branching

Work on feature branches from `main`. Do not commit directly to `main`. Create a branch for your change (e.g. `feature/your-feature` or `fix/your-fix`).

## Merge requests

Open a Merge Request (MR) to `main`. Describe the change clearly and ensure CI passes (lint, test, build). Request review if your team uses it.

## Code quality

Before pushing:

1. **Tests:** From the project root or `backend/`:
   ```bash
   cd backend && pytest tests/ -v
   ```
   Integration tests require Postgres with the schema (see [README](README.md) and [docs/RUNBOOK.md](docs/RUNBOOK.md)).

2. **Lint and format:** CI runs Ruff; run locally to avoid failures:
   ```bash
   ruff check backend/
   ruff format backend/
   ```
   See [.gitlab-ci.yml](.gitlab-ci.yml) for the exact commands.

## Documentation

- [README.md](README.md) — Overview, quick start, run tests, env vars.
- [PROJECT_SPEC.md](PROJECT_SPEC.md) — Full specification and phased plan.
- [docs/](docs/) — RUNBOOK, DATA_MODEL, ARCHITECTURE, DEPLOYMENT, OBSERVABILITY.

## GitLab and operations

- **Wiki:** Use the project Wiki (GitLab: Project → Wiki) for extra runbooks or living docs if you prefer not to keep everything in `docs/`.
- **Integrations:** Configure in GitLab **Settings → Integrations** (e.g. Slack on pipeline failure, Jira link).
- **Kubernetes:** If you deploy to Kubernetes, add a cluster in **Settings → Kubernetes**. Deployment manifests can live in this repo or a separate one when you adopt K8s.
