# Contributing to Morocco Spatial Dashboard

## Standards

All code and docs must follow the project’s [Engineering standards](docs/ENGINEERING_STANDARDS.md): tech stack and versions, naming, typing, testing, and CI/CD gates. Read that doc before contributing.

## Branching

Work on feature branches from `main`. Do not commit directly to `main`. Create a branch for your change (e.g. `feature/your-feature` or `fix/your-fix`).

## Merge requests

Open a Merge Request (MR) to `main`. Describe the change clearly and ensure CI passes (lint, test, build). Request review if your team uses it.

## Code quality

Before pushing, ensure [Engineering standards](docs/ENGINEERING_STANDARDS.md) are met:

1. **Tests:** From the project root or `backend/`:
   ```bash
   cd backend && pytest tests/ -v
   ```
   Integration tests require Postgres with the schema (see [README](README.md) and [docs/RUNBOOK.md](docs/RUNBOOK.md)). For frontend: `cd frontend && npm run test`.

2. **Lint and format:** CI runs Ruff (backend) and ESLint/Prettier (frontend). Run locally to avoid failures:
   ```bash
   ruff check backend/
   ruff format backend/
   cd frontend && npm run lint && npm run format:check
   ```
   See [.gitlab-ci.yml](.gitlab-ci.yml) for the exact commands.

## Pre-commit

Install [pre-commit](https://pre-commit.com/) and run hooks before each commit:

```bash
pip install pre-commit
pre-commit install
```

To run on all files once: `pre-commit run --all-files`. Pre-commit runs the same checks as CI (backend Ruff, frontend lint/format, hygiene). Node must be installed for frontend hooks.

## Documentation

- **[docs/README.md](docs/README.md)** — Documentation hub (start here)
- [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) — First-run tutorial
- [README.md](README.md) — Project overview
- [PROJECT_SPEC.md](PROJECT_SPEC.md) — Product specification (as implemented)
- [docs/RUNBOOK.md](docs/RUNBOOK.md) — Operations
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md) — Schema reference
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System design

## GitLab and operations

- **Wiki:** Use the project Wiki (GitLab: Project → Wiki) for extra runbooks or living docs if you prefer not to keep everything in `docs/`.
- **Integrations:** Configure in GitLab **Settings → Integrations** (e.g. Slack on pipeline failure, Jira link).
- **Kubernetes:** If you deploy to Kubernetes, add a cluster in **Settings → Kubernetes**. Deployment manifests can live in this repo or a separate one when you adopt K8s.
