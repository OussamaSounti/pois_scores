# Runbook — Morocco Spatial Dashboard

Operations: starting the database, restoring the POI dump, and debugging. POI data is loaded by restoring the provided PostgreSQL dump (see below); there is no separate CSV-import or migration for initial data.

## Start the database (local)

```bash
docker compose up -d db
docker compose ps   # ensure db is healthy
```

Connection (from host): `postgresql://poi_user:poi_password@localhost:5432/poi_db`  
Use the same user, password, and database name when restoring the dump.

## Restore the POI dump

The project **does not** create the POI schema via migrations. Schema and data come from a provided PostgreSQL dump (`.dump` or `.sql`). Restore it once after the first `docker compose up`.

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

After the POI dump is restored, create the pipeline tables (`production.properties`, `production.poi_imports`, `production.property_features`):

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

The pipeline processes only **pending** properties: those that do not yet have a row in `property_features` for the current POI version. After a POI refresh (see below), the next run will recompute the entire portfolio. It processes in chunks and commits after each chunk, so it can be restarted after an interruption and will continue from the remaining pending set.

### POI refresh (monthly)

When the data team imports new POI data (e.g. monthly), they must **insert one row** into `production.poi_imports` so the pipeline knows to recompute all property features:

```sql
INSERT INTO production.poi_imports (imported_at, label) VALUES (now(), '2025-03');
```

The pipeline uses `max(imported_at)` as the current POI version. Every row in `property_features` stores `poi_refreshed_at` so the ML team can trace which POI dataset produced each set of features.

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

The current approach is **dump-first**: schema and data come from a restored PostgreSQL dump (and, in CI, from `init_schema_ci.sql`). There is no migration runner in the repo today.

- **When Alembic (or similar) is adopted:** run a baseline revision that matches the current schema; then apply incremental migrations for future DDL changes. Initial load (dump restore) remains as documented above.
- **Until then:** any schema change (new table, column, or index) requires either a **new dump** or **manual SQL**; update [DATA_MODEL.md](DATA_MODEL.md) and this runbook accordingly.
