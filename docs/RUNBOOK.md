# Runbook — Morocco Spatial Dashboard

Operations: starting the database, restoring the POI dump, and debugging.

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
