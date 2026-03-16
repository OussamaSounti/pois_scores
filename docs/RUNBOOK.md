# Runbook — Morocco Spatial Dashboard

Operations: starting the database, running the pipeline, and debugging.

- **Production:** The database is already set up and refreshed monthly by another pipeline. This app connects via `DATABASE_URL` and uses that data directly; no restore step.
- **Local / dev:** You may restore a POI dump for test data, or use the minimal schema from CI (`init_schema_ci.sql`). See below.

## Start the database (local)

```bash
docker compose up -d db
docker compose ps   # ensure db is healthy
```

Connection (from host): `postgresql://poi_user:poi_password@localhost:5432/poi_db`  
Use the same user, password, and database name when restoring a dump (local only).

## Restore the POI dump (local / dev only)

For **local development or CI**, you may load schema and data from a PostgreSQL dump (`.dump` or `.sql`). The project does not create the POI schema via migrations. Restore once after the first `docker compose up` if you need real POI data locally.

### If the file is custom format (`.dump`)

1. Copy the dump into the container or mount its directory. Example with copy:
   ```bash
   docker compose cp path/to/file.dump db:/tmp/file.dump
   ```
   Or mount a volume in `docker-compose.yml` (e.g. `./dumps:/dumps:ro`) and use `/dumps/file.dump` inside the container.

2. Run restore **inside** the Postgres container:
   ```bash
   docker compose exec db pg_restore -d poi_db -U poi_user -v /tmp/file.dump
   ```
   Use the same `-d` (database), `-U` (user), and ensure the user has rights on `poi_db`. If the dump was created with a different user, you may need `--no-owner` or similar (see `pg_restore --help`).

### If the file is plain SQL (`.sql`)

1. Get the file into the container (copy or volume), e.g.:
   ```bash
   docker compose cp path/to/file.sql db:/tmp/file.sql
   ```

2. Run:
   ```bash
   docker compose exec db psql -d poi_db -U poi_user -f /tmp/file.sql
   ```

### One-off container (alternative)

If you prefer not to exec into the running `db` service, use a one-off container that connects to the same network and database:

```bash
# Custom .dump
docker run --rm -v "C:\path\to\dumps:/dumps" --network pois_scores_default postgis/postgis:15-3.5-alpine pg_restore -h db -d poi_db -U poi_user -v /dumps/file.dump

# Plain .sql
docker run --rm -v "C:\path\to\dumps:/dumps" --network pois_scores_default postgis/postgis:15-3.5-alpine psql -h db -d poi_db -U poi_user -f /dumps/file.sql
```

Replace `pois_scores_default` with your Compose project network name (`docker network ls`).

## Inspect the schema (after restore)

Connect to the database:

```bash
docker compose exec db psql -d poi_db -U poi_user
```

Then:

- List tables: `\dt`
- Describe a table (e.g. POIs): `\d pois` (or the actual table name)
- List extensions: `\dx` (e.g. PostGIS)

Record the **actual** table and column names in [DATA_MODEL.md](DATA_MODEL.md) so the backend can query the existing schema.

## Debug DB connection

- From host: `psql "postgresql://poi_user:poi_password@localhost:5432/poi_db"` (if `psql` is installed).
- From another container on the same Compose network: use hostname `db`, port `5432`, and the same user/password/database.
- Ensure `DATABASE_URL` in `.env` matches (user, password, host, port, database name).

---

## Feature engineering pipeline

The pipeline computes spatial indicators for every property in `production.properties` and writes them to `production.property_features` (ML input). It reuses the same spatial logic as the API.

### Apply pipeline schema (once)

Create the pipeline tables (`production.properties`, `production.property_features`) when adding the pipeline. In production the schema may already exist (managed by the external pipeline); in local/dev run the script once.

**From host:** The script uses the app config and loads `DATABASE_URL` from `.env` (in `backend/` or project root). If you don't use a `.env` file, set it in the shell first (e.g. `export DATABASE_URL="postgresql://poi_user:poi_password@localhost:5432/poi_db"` or PowerShell: `$env:DATABASE_URL="postgresql://..."`).
```bash
cd backend
python scripts/run_schema_feature_pipeline.py
```

**Via Docker:** Rebuild the backend image first if you changed the Dockerfile (e.g. `docker compose build backend`), then:
```bash
docker compose run --rm backend python scripts/run_schema_feature_pipeline.py
```

You can also run the SQL by hand: `psql $DATABASE_URL -f backend/scripts/schema_feature_pipeline.sql`.

### Run the pipeline

The pipeline service is not started by default with `docker compose up -d`; run it on demand as below.

**Manual (one-off):**
```bash
docker compose run --rm pipeline
```

**Scheduled (e.g. nightly at 2am):** Use host cron or your scheduler to run the same command, e.g.:
```bash
0 2 * * * cd /path/to/repo && docker compose run --rm pipeline
```

The pipeline processes only **pending** properties: those that do not yet have a row in `property_features` for the current POI version. It uses **`audit.pipeline_runs.run_timestamp`** (max) as the current POI version—that table is maintained by the external POI refresh pipeline. After a POI refresh, the next run will recompute the entire portfolio. It processes in chunks and commits after each chunk, so it can be restarted after an interruption and will continue from the remaining pending set.

---

## Prefect automation (local, cloud, production)

This repo provides a Prefect flow at:

- **File:** `backend/app/orchestration/prefect_feature_flow.py`
- **Entrypoint:** `monthly_poi_feature_recompute_flow`

The flow reads `max(audit.pipeline_runs.run_timestamp)` as the current external POI version and recomputes pending properties for that version.

### Mode A - Local only (fastest setup)

Use this to develop/debug quickly on your machine.

1) Install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

2) Set environment for the current shell:

```bash
export DATABASE_URL="postgresql://..."
export LOG_LEVEL="INFO"
```

PowerShell:

```powershell
$env:DATABASE_URL="postgresql://..."
$env:LOG_LEVEL="INFO"
```

3) Run once:

```bash
python -m app.orchestration.prefect_feature_flow
```

4) Optional schedule from local process:

```bash
python -c "from app.orchestration.prefect_feature_flow import monthly_poi_feature_recompute_flow as f; f.serve(name='monthly-local-schedule', cron='0 2 1 * *', parameters={'chunk_size':200})"
```

Notes:

- Keep the terminal alive while using `serve`.
- In some Prefect versions, `Flow.serve()` does not accept `timezone=...`; set timezone in UI schedule settings.

### Mode B - Prefect Cloud (private GitLab)

Use this when you want schedule and run visibility in Prefect UI while keeping flow code in a private GitLab repository.

1) Login:

```bash
prefect cloud login
```

2) Create/update variables (lowercase names required):

```bash
prefect variable set database_url "postgresql://..."
prefect variable set log_level "INFO"
```

3) Create a managed pool:

```bash
prefect work-pool create pois-managed-pool --type prefect:managed
```

4) Configure private GitLab credentials for Prefect code pulls.

Recommended approach:

- Install integration: `pip install "prefect[gitlab]"`
- Register blocks: `prefect block register -m prefect_gitlab`
- Create a `GitLabCredentials` block with a token that has `read_repository` access to the target repo.
- Use that block when deploying from source (for example, with `flow.from_source(...)` and a Git repository storage object).

5) Deploy the flow and schedule it monthly (for example, day 1 at 02:00).

- Source repository URL should be the private GitLab repo (`https://gitlab.com/<group>/<repo>.git`).
- Set deployment environment variables from Prefect variables (for example, `DATABASE_URL` and `LOG_LEVEL`).

6) Trigger and monitor:

```bash
prefect deployment run "monthly-poi-feature-recompute/monthly-poi-refresh"
```

In Prefect UI, verify:

- Deployment is active and schedule is enabled.
- Upcoming runs appear as `Scheduled`.
- Flow run logs show successful pull from private GitLab and successful DB processing.

### Mode C - Production pattern

Use this for stable monthly operation linked to external POI refreshes.

1) Database and network prerequisites:

- `DATABASE_URL` points to production Postgres (not localhost).
- DB contains `audit.pipeline_runs`, `production.properties`, and `production.property_features`.

2) Source control and credentials:

- If code is in a private GitLab repo, use secure Git credentials for Prefect pulls (for example, Prefect GitLab credentials block).
- Avoid embedding plaintext tokens in commands.

3) Deployment schedule:

- Recommended: schedule monthly after expected external refresh window (for example, day 1 at 02:00).
- Optional: trigger on external pipeline completion via CLI/API automation.

4) Operational checks after each run:

- Flow run state is `Completed`.
- Pending count for latest `run_timestamp` is `0`.
- Logs show processed rows and no retry storm.

### External refresh trigger contract

The recompute flow assumes the external POI pipeline writes a new row in `audit.pipeline_runs`. If that table is not updated, the flow may skip because it sees no new POI version.

---

## Verification checklist

Before pushing or releasing, run these locally (see also [CONTRIBUTING.md](../CONTRIBUTING.md) and [.gitlab-ci.yml](../.gitlab-ci.yml)):

| Check | Command |
|-------|--------|
| Backend lint | `ruff check backend/` |
| Backend format | `ruff format --check backend/` |
| Backend tests + coverage | `cd backend && pytest tests/ -v --cov=app --cov-fail-under=70` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend format | `cd frontend && npm run format:check` |
| Frontend tests | `cd frontend && npm run test` |
| Frontend build | `cd frontend && npm run build` |
| Pre-commit (all files) | `pre-commit run --all-files` |

All must pass for CI to succeed. Integration tests need Postgres with the schema (dump or `init_schema_ci.sql`).

---

## Schema change policy

- **Production:** The database is managed elsewhere (existing DB, refreshed by another pipeline). Schema changes there are outside this repo.
- **Local / dev:** Schema and data come from a dump or from `init_schema_ci.sql` (CI). There is no migration runner in the repo today.
- **When Alembic (or similar) is adopted:** run a baseline revision that matches the current schema; then add incremental migrations for future DDL changes.
- **Until then:** any schema change in this app's scope (e.g. pipeline tables) requires manual SQL or script updates; update [DATA_MODEL.md](DATA_MODEL.md) and this runbook accordingly.
