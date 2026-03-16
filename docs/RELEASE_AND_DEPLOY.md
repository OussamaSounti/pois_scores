# Release and deployment

Branch flow, versioning, and deployment expectations for the Morocco Spatial Dashboard.

## Branch and merge flow

- Work on **feature branches** (e.g. `feature/xyz`, `fix/abc`, `docs/readme`). Do not push directly to `main`.
- Open a **Merge Request (MR)** to `main`. Describe the change; ensure CI passes (lint, test, build for backend and frontend).
- Merge after review (if your team uses it). CI runs on every push and on MRs.

## Versioning and tagging

- Use **semantic versioning** (e.g. `v0.1.0`, `v1.0.0`). Major.Minor.Patch for releases.
- To create a release tag from `main`:
  ```bash
  git checkout main
  git pull
  git tag v0.1.0
  git push origin v0.1.0
  ```
- Tag only from `main` after the release MR is merged. Document the tag in [CHANGELOG.md](../CHANGELOG.md).

## Deployment expectations

- **Current CI** builds the backend Docker image on the default branch; it does **not** deploy automatically.
- Deploy manually (or via a separate deploy job/stage) from a tagged release or from `main` after merge.
- For production: prefer deploying from a **tag** (e.g. `v0.1.0`) so the running version is clearly identified.
- Frontend: build with `npm run build`; serve the `dist/` output via your web server or static host. CI can store the frontend build as an artifact for deploy jobs if needed.

## Rollback

- **Application:** Redeploy the previous Docker image (by tag or commit). No application code change required.
- **Database:** In production the DB is managed externally (no dump restore by this app). Rollback of app/config does not change DB state. For local/dev, data rollback would be restore a previous dump or manual SQL; document in [RUNBOOK.md](RUNBOOK.md) if needed.
- **Pipeline:** The feature pipeline is idempotent; re-run it to recompute features. No separate rollback step.
