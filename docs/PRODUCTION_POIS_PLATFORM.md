# Production POIs Platform — What It Takes

> Full breakdown of the workflow, pipeline, feature computation, and integration
> into the transactions database. Scoped to our actual environment: single
> PostgreSQL instance, colleague-managed OSM extraction, ~800k transactions,
> internal use, AWS deployment.

---

## 0. Context & constraints (answered)

| Question | Answer |
|---|---|
| Transactions DB engine | PostgreSQL (same instance as POIs) |
| DB topology | **Single Postgres** — transactions, POIs, features all live in one instance, different schemas |
| Transaction volume | ~800,000 rows |
| Pipeline refresh cadence | Explore both **weekly** and **monthly** options |
| OSM data ownership | Colleague manages extraction. Provides `osm_history` schema with two tables: **raw** + **active**. Updated monthly. We just connect and query. |
| Where do features land | `production.property_features` only — enrichment column store |
| OSM current POIs | Also managed by colleague, same pattern — a table in the DB we link to |
| Consumers | **ML models** (feature input) + **internal dashboard** (employee-facing) |
| Auth scope | Internal only — no public API |
| Deployment | **AWS** (ECS/EC2 + RDS or similar) |

---

## 1. What the prototype already does

The current codebase is a working prototype:

- **Queries POI data** from `production.pois_current` (~44 fclass types, 9 super-categories, Morocco).
- **Queries historical POIs** from `osm_history.poi_history_active` for temporal scoring at transaction dates.
- **Loads transaction/property data** from Parquet into `production.properties` (Casablanca transactions with price, surface, admin hierarchy).
- **Computes spatial features** per property: density, diversity, accessibility, nearest-POI distances, coastal corrections.
- **Stores features** in `production.property_features` via a batch pipeline.
- **Serves results** via FastAPI (single/batch scoring + properties map API).
- **React frontend** with map, metrics panel, properties drilldown.

### What's fragile or missing

| Area | Issue | Impact |
|---|---|---|
| **Transactions sync** | Loaded from Parquet, not from the real DB | Manual step, data gets stale |
| **Schema management** | DDL scripts, no Alembic | Risky schema changes |
| **Pipeline orchestration** | Single Python script, no scheduler | Must be triggered manually |
| **Pipeline performance** | Sequential, 200-row chunks for 800k rows | ~4,000 chunks, slow |
| **Coastline/land data** | Loader scripts missing from repo | Must be set up fresh |
| **Monitoring** | Prometheus stub, no dashboards | Blind in production |
| **Testing** | Unit tests for mapper only | No confidence in deployments |
| **Auth** | None | Anyone with network access can hit the API |
| **CI/CD** | `.gitlab-ci.yml` exists but minimal | No automated deploy |

---

## 2. Production architecture

Since everything lives in **one PostgreSQL instance**, the architecture is simpler than the prototype assumed:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     SINGLE POSTGRESQL + PostGIS (AWS RDS)                │
│                                                                          │
│  ┌─────────────────────┐   ┌──────────────────────────────────────────┐ │
│  │ transactions schema  │   │ osm_history schema (colleague-managed)   │ │
│  │                      │   │                                          │ │
│  │  transactions table  │   │  poi_history_raw     (monthly refresh)  │ │
│  │  (~800k rows)        │   │  poi_history_active  (monthly refresh)  │ │
│  └──────────┬───────────┘   └──────────────────────┬─────────────────┘ │
│             │                                       │                    │
│             │  sync (view or                        │  read-only         │
│             │  INSERT..SELECT)                      │  queries           │
│             ▼                                       ▼                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ production schema (we own this)                                   │   │
│  │                                                                   │   │
│  │  properties            (synced from transactions, ~800k)         │   │
│  │  pois_current          (colleague-managed, we read)              │   │
│  │  property_features     (our output, ML + dashboard consume)      │   │
│  └──────────────────────────────────────┬───────────────────────────┘   │
│                                          │                               │
│  ┌────────────────────┐                 │                               │
│  │ geo schema          │                 │                               │
│  │  coastline          │─────────────────┤                               │
│  │  land               │                 │                               │
│  └────────────────────┘                 │                               │
│                                          │                               │
│  ┌────────────────────┐                 │                               │
│  │ audit schema        │                 │                               │
│  │  pipeline_runs      │─────────────────┘                               │
│  └────────────────────┘                                                  │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              │  DATABASE_URL
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER (AWS ECS)                       │
│                                                                          │
│  ┌────────────────────┐     ┌──────────────────────────────────────┐    │
│  │ Feature Pipeline    │     │ FastAPI Backend                      │    │
│  │ (scheduled task)    │     │                                      │    │
│  │                     │     │  /api/v1/scores       (live compute) │    │
│  │ properties ──────►  │     │  /api/v1/properties   (pre-computed) │    │
│  │ POIs (query) ────►  │     │  /api/v1/pois         (POI list)    │    │
│  │ geo (query) ─────►  │     │  /api/v1/properties/stats            │    │
│  │       │             │     │                                      │    │
│  │       ▼             │     └───────────────┬──────────────────────┘    │
│  │ property_features   │                     │                           │
│  └────────────────────┘                     │                           │
│                                              ▼                           │
│                               ┌──────────────────────────┐              │
│                               │  React Dashboard          │              │
│                               │  (internal employees)     │              │
│                               └──────────────────────────┘              │
│                                                                          │
│                               ┌──────────────────────────┐              │
│                               │  ML Models                │              │
│                               │  (read property_features  │              │
│                               │   directly from DB)       │              │
│                               └──────────────────────────┘              │
└──────────────────────────────────────────────────────────────────────────┘
```

### Key simplifications vs. original doc

- **No separate POI database** — everything is in one Postgres.
- **No Overpass pipeline to build** — colleague handles OSM extraction and provides tables.
- **No FDW needed** — same instance, just cross-schema queries.
- **Integration = direct JOINs** — `property_features` is already in the same DB as transactions.

---

## 3. The pipeline — step by step

### 3.1 POI data (colleague-managed, we consume)

Our colleague provides and maintains two schemas we **read from**:

| What we query | Table | Refresh |
|---|---|---|
| Current POI snapshot | `production.pois_current` | Monthly |
| Historical POIs | `osm_history.poi_history_active` | Monthly |
| Raw history | `osm_history.poi_history_raw` | Monthly |

**Our responsibility:** ensure our queries and indexes are compatible with his schema. The current code already queries these tables correctly via PostGIS `ST_DWithin` on `geom::geography`.

**What we need to agree on with the colleague:**
- Column names and types (currently aligned)
- The `fclass` and `super_category` taxonomy (44 types, 9 categories)
- The `valid_range` tstzrange column on history for temporal containment queries
- A signal for "new data is available" (e.g. `audit.pipeline_runs.run_timestamp` updated)
- Spatial indexes on `geom` (GiST) — who creates them?

### 3.2 Transaction/property sync

**Current:** Parquet file → `production.properties` via script.

**Production:** Since transactions are in the **same Postgres instance**, the sync becomes trivial:

**Option A — View (zero-copy, real-time):**
```sql
CREATE OR REPLACE VIEW production.properties AS
SELECT
    transaction_id AS id,
    asset_latitude AS latitude,
    asset_longitude AS longitude,
    transaction_date,
    asset_price,
    asset_surface,
    asset_psqm,
    asset_type,
    district_uid, district_name,
    neighbourhood_uid, neighbour_name,
    iris_uid, iris_code,
    ilot_uid, ilot_objectid
FROM transactions_schema.transactions
WHERE asset_latitude IS NOT NULL
  AND asset_longitude IS NOT NULL;
```

**Option B — Materialized view (snapshot, faster queries):**
```sql
CREATE MATERIALIZED VIEW production.properties AS
SELECT ... (same as above) ...
WITH DATA;

-- Refresh before pipeline runs:
REFRESH MATERIALIZED VIEW CONCURRENTLY production.properties;
```

**Option C — Physical table with sync script (current approach, more control):**
```sql
INSERT INTO production.properties (id, latitude, longitude, ...)
SELECT transaction_id, asset_latitude, asset_longitude, ...
FROM transactions_schema.transactions t
WHERE NOT EXISTS (
    SELECT 1 FROM production.properties p WHERE p.id = t.transaction_id
)
AND t.asset_latitude IS NOT NULL;
```

**Recommendation:** Option B (materialized view) for the initial build — simple, gives the pipeline a stable snapshot to work against, and `REFRESH CONCURRENTLY` doesn't lock reads. Move to Option C only if you need custom transformations.

### 3.3 Reference geographic data

Two static datasets needed for the coastal correction:

| Table | Purpose | Source | Frequency |
|---|---|---|---|
| `geo.coastline` | Distance to coast, buffer splitting | OSM coastline (already used) | Once, rarely updated |
| `geo.land` | Point-in-polygon (on land?), accurate land fraction | Natural Earth 10m polygons | Once, rarely updated |

Scripts to load these exist in the prototype (referenced in README). They need to be recovered/rewritten and run once on the production DB.

### 3.4 Feature computation (the core)

For each property without up-to-date features, the pipeline computes:

**Density:**
| Feature | Query | Radius |
|---|---|---|
| `poi_count_1km` | Count POIs | 1 km |
| `poi_count_400m` | Count POIs | 400 m |
| `by_category` | Count per super_category | 1 km |

**Diversity:**
| Feature | Formula |
|---|---|
| `n_categories` | Count distinct super_categories in 1 km (out of 9) |
| `n_poi_types` | Count distinct fclass in 1 km (out of 44) |
| `entropy` | Shannon entropy H of super_category distribution |
| `entropy_fclass` | Shannon entropy H of fclass distribution |
| `entropy_norm` | H / log2(9) — Pielou's J evenness |
| `entropy_fclass_norm` | H_fclass / log2(44) |

**Accessibility (400 m walking distance):**
Boolean presence of 13 essential POI types:
`bus_stop`, `pharmacy`, `school`, `hospital`, `supermarket`, `bank`, `atm`, `clinic`, `fuel`, `police`, `park`, `doctors`, `taxi`

**Nearest distance:**
Min km to nearest POI per super_category within 25 km search radius → `nearest_km` JSONB

**Coastal correction:**
- `dist_coast_km` — geodesic distance to nearest coastline
- `land_buffer_fraction_1km` — what fraction of the 1 km buffer is on land
  - Near coast (< 1 km): PostGIS `ST_Split` buffer by coastline, measure areas
  - Far from coast (≥ 1 km): binary 1.0 (land) or 0.0 (ocean) via `geo.land` check
- Density normalization: `effective_count = poi_count_1km / land_fraction`

**Aggregate score (0–100):**
```
effective_count = poi_count_1km / land_buffer_fraction
density   = min(effective_count / 50, 1.0)
diversity = min((n_categories/10 + n_poi_types/20) / 2, 1.0)
access    = sum(accessibility_400m) / 13

aggregate_score = 100 × (0.3 × density + 0.3 × diversity + 0.4 × access)
```

**Temporal mode:**
- Property has `transaction_date` → score against `osm_history.poi_history_active` at that date → `poi_source = 'history'`
- No `transaction_date` → score against `production.pois_current` → `poi_source = 'current'`

### 3.5 Pipeline performance (800k properties)

Current pipeline does **sequential processing** in chunks of 200. Each property requires **3–5 PostGIS queries** (1 km radius, 400 m radius, nearest by category, coast distance, land fraction).

**Rough estimate at current speed:**
- ~50ms per property (optimistic, indexed PostGIS) → 800k × 50ms = **~11 hours**
- ~200ms per property (realistic with coastal) → 800k × 200ms = **~44 hours**

**Required optimizations for production:**
1. **Parallel workers** — split property IDs across N processes (e.g. 8 workers = 8× speedup)
2. **Batch spatial queries** — instead of N individual `ST_DWithin` calls, use a single query with `LATERAL JOIN` across multiple points
3. **Skip coastal for inland properties** — only compute `_land_buffer_fraction_db` when `dist_coast_km < 1.0` (already implemented, but the coast distance query itself can be cached)
4. **Incremental processing** — only compute new/changed properties (already implemented via pending check)
5. **Consider `UNLOGGED` staging table** for bulk writes, then swap

**Weekly vs. monthly refresh:**

| Cadence | When to recompute | Properties affected | Runtime target |
|---|---|---|---|
| **Monthly** (after colleague refreshes OSM) | All 800k (full recompute against new POI version) | 800k | < 8 hours (overnight batch) |
| **Weekly** (new transactions only) | Only new transactions since last run | ~few thousand | < 30 minutes |

**Recommendation:** Run **weekly** for new transactions (incremental). Run **monthly** full recompute after colleague updates OSM data. Both can be the same pipeline — the pending-property check handles it.

### 3.6 Output: `production.property_features`

```sql
production.property_features (
    property_id              bigint PK → production.properties(id),
    poi_refreshed_at         timestamptz,     -- POI version computed against
    pipeline_version         text,            -- '1.0', '2.0', etc.
    computed_at              timestamptz,
    -- Density
    poi_count_1km            integer,
    poi_count_400m           integer,
    -- Diversity
    n_categories             integer,
    n_poi_types              integer,
    entropy                  double precision,
    entropy_fclass           double precision,
    aggregate_score          double precision,
    -- Accessibility (13 boolean columns)
    acc_bus_stop, acc_pharmacy, acc_school, acc_hospital,
    acc_supermarket, acc_bank, acc_atm, acc_clinic,
    acc_fuel, acc_police, acc_park, acc_doctors, acc_taxi,
    -- Dynamic JSONB
    by_category              jsonb,           -- {"Transport": 12, ...}
    nearest_km               jsonb,           -- {"Transport": 0.23, ...}
    -- Coastal
    dist_coast_km            double precision,
    land_buffer_fraction_1km double precision,
    -- Temporal tracking
    transaction_date         date,
    poi_source               text             -- 'history' | 'current'
)
```

---

## 4. Integration into the transactions DB

Since everything is in the **same Postgres instance**, integration is a direct JOIN — no sync, no replication, no API middleman.

### The join

```sql
SELECT
    t.transaction_id,
    t.transaction_date,
    t.asset_price,
    t.asset_surface,
    t.asset_psqm,
    -- POI features for ML
    f.poi_count_1km,
    f.poi_count_400m,
    f.n_categories,
    f.n_poi_types,
    f.entropy,
    f.entropy_fclass,
    f.aggregate_score,
    f.dist_coast_km,
    f.land_buffer_fraction_1km,
    -- Accessibility booleans
    f.acc_bus_stop,
    f.acc_pharmacy,
    f.acc_school,
    f.acc_hospital,
    f.acc_supermarket,
    -- JSONB fields (ML can parse or extract specific keys)
    f.by_category,
    f.nearest_km,
    f.nearest_km->>'Healthcare' AS nearest_healthcare_km,
    f.nearest_km->>'Education' AS nearest_education_km,
    -- Metadata
    f.poi_source,
    f.pipeline_version,
    f.computed_at
FROM transactions_schema.transactions t
JOIN production.property_features f
    ON f.property_id = t.transaction_id
WHERE f.computed_at IS NOT NULL;  -- only properties with computed features
```

### For ML consumption

ML models can read directly from `property_features` or from a view that flattens everything:

```sql
CREATE VIEW ml.transaction_features AS
SELECT
    t.transaction_id,
    t.asset_price,
    t.asset_surface,
    t.asset_psqm,
    f.poi_count_1km,
    f.poi_count_400m,
    f.entropy,
    f.entropy_fclass,
    f.aggregate_score,
    f.acc_bus_stop::int, f.acc_pharmacy::int, f.acc_school::int,
    f.acc_hospital::int, f.acc_supermarket::int, f.acc_bank::int,
    f.acc_atm::int, f.acc_clinic::int, f.acc_fuel::int,
    f.acc_police::int, f.acc_park::int, f.acc_doctors::int, f.acc_taxi::int,
    f.dist_coast_km,
    f.land_buffer_fraction_1km,
    (f.nearest_km->>'Transport')::float AS nearest_transport_km,
    (f.nearest_km->>'Healthcare')::float AS nearest_healthcare_km,
    (f.nearest_km->>'Education')::float AS nearest_education_km,
    (f.nearest_km->>'Shopping')::float AS nearest_shopping_km,
    (f.nearest_km->>'Leisure')::float AS nearest_leisure_km
FROM transactions_schema.transactions t
JOIN production.property_features f ON f.property_id = t.transaction_id;
```

ML reads this as a flat DataFrame via `pd.read_sql("SELECT * FROM ml.transaction_features", conn)`.

### For the internal dashboard

The FastAPI backend already serves pre-computed features from `property_features`:
- `GET /api/v1/properties?bbox=` — map view with scores
- `GET /api/v1/properties/{id}` — detail view
- `GET /api/v1/properties/stats?level=district` — aggregated by admin hierarchy
- `GET /api/v1/scores?lat=&lon=` — live computation for any arbitrary point

---

## 5. What needs to be built vs. what exists

| Component | Current state | Production-ready? | Work needed |
|---|---|---|---|
| POI data (current + history) | Colleague provides, tables exist | Yes (their responsibility) | Agree on schema contract, verify indexes |
| Transaction → properties sync | Parquet loader script | No | View or materialized view from transactions schema |
| Feature pipeline (core logic) | Working, tested | Yes | Validate formulas with domain/ML team |
| Feature pipeline (ops) | Manual, sequential | No | Scheduling, parallelism, monitoring |
| Coastal reference data | Schema + queries exist | Partially | Recover/write loader scripts, load data |
| API layer | Working | Partially | Auth, caching, error handling |
| Frontend (dashboard) | Working | Partially | Polish for employee use |
| ML integration | Not started | No | Create `ml.transaction_features` view |
| CI/CD | Minimal `.gitlab-ci.yml` | No | Full pipeline: lint → test → build → deploy |
| AWS infra | None | No | RDS, ECS/EC2, networking, IAM |
| Monitoring | Prometheus stub | No | CloudWatch/Grafana dashboards + alerts |
| Schema management | DDL scripts | No | Alembic migrations |

---

## 6. Sprint plan

### Sprint 0 — Foundation & infra (1 week)

- [ ] Set up GitLab repo with branching strategy (main → develop → feature)
- [ ] Set up Alembic; import existing DDL as initial migration
- [ ] AWS infrastructure: RDS (PostGIS), ECS task definitions, networking/security groups
- [ ] Create `.gitlab-ci.yml`: lint → test → build → deploy-to-staging
- [ ] Ruff linting + pre-commit hooks
- [ ] Proper `.env.example` and Docker Compose for local dev

### Sprint 1 — Transactions sync + schema contract (1 week)

- [ ] Map transactions DB schema columns to `production.properties`
- [ ] Create materialized view (or sync query) from transactions → properties
- [ ] Handle the 800k initial load — verify performance
- [ ] Set up `REFRESH MATERIALIZED VIEW CONCURRENTLY` mechanism
- [ ] Agree on schema contract with colleague for OSM tables (column names, indexes, refresh signal)
- [ ] Verify our queries work against his actual `osm_history` tables
- [ ] Define the join key: `transaction_id` = `property_features.property_id`

### Sprint 2 — Pipeline hardening (1.5 weeks)

- [ ] Parallel chunk processing (multiprocessing pool, e.g. 8 workers)
- [ ] Benchmark: target < 8 hours for full 800k recompute
- [ ] Per-property error handling (skip + log, don't kill pipeline)
- [ ] Dead-letter tracking for failed properties
- [ ] Pipeline CLI: `--chunk-size`, `--workers`, `--dry-run`, `--property-id`
- [ ] Proper `audit.pipeline_runs` logging (start, end, counts, errors)
- [ ] Integration test: seed N properties → run → verify all features computed

### Sprint 3 — Scheduling + coastal data (1 week)

- [ ] **Weekly schedule** (AWS EventBridge or cron): process new transactions
- [ ] **Monthly schedule**: full recompute after colleague's OSM refresh
- [ ] Write/recover coastline + land polygon loader scripts
- [ ] Load `geo.coastline` and `geo.land` on RDS
- [ ] Verify coastal corrections for known properties (Casablanca corniche, Tangier, etc.)

### Sprint 4 — ML integration + API hardening (1.5 weeks)

- [ ] Create `ml.transaction_features` view (flat, ML-ready)
- [ ] Validate with ML team: are the features what they need? Any missing?
- [ ] Add internal auth to API (API keys or AWS IAM-based)
- [ ] Add response caching for pre-computed property lookups
- [ ] Optimize batch endpoint (concurrent instead of sequential)
- [ ] Structured error responses
- [ ] Load test: < 200ms single, < 2s batch of 500

### Sprint 5 — Monitoring + testing (1 week)

- [ ] CloudWatch or Grafana dashboards:
  - Pipeline: throughput, duration, error rate
  - API: latency p50/p95/p99, error rate
  - DB: connection pool, query duration
- [ ] Alerts: pipeline failure, API errors, DB issues
- [ ] Unit tests for all pure functions (entropy, haversine, score aggregation)
- [ ] Integration tests with seeded PostGIS (known inputs → known outputs)
- [ ] Pipeline end-to-end test in CI
- [ ] Minimum 80% backend coverage

### Sprint 6 — Frontend polish (1 week)

- [ ] Clean up React app for production (employee-facing)
- [ ] Properties map: marker clustering, zoom behavior
- [ ] Property detail: score breakdown visualization
- [ ] Admin hierarchy drilldown with stats
- [ ] Loading states, error handling, empty states
- [ ] Deploy frontend to S3 + CloudFront (or similar)

### Sprint 7 — Docs, deploy, handoff (1 week)

- [ ] `docs/ARCHITECTURE.md` — system diagram, schema ownership
- [ ] `docs/DEPLOYMENT.md` — AWS deploy steps, RDS config
- [ ] `docs/RUNBOOK.md` — refresh POIs, rerun pipeline, debug
- [ ] `docs/DATA_MODEL.md` — complete schema reference
- [ ] Update `README.md` — quick start, env vars, workflow
- [ ] Production deploy and smoke test
- [ ] Handoff session with team

---

## 7. Estimated effort

| Phase | Sprints | Duration |
|---|---|---|
| Foundation + infra | Sprint 0 | 1 week |
| Data sync + schema | Sprint 1 | 1 week |
| Pipeline hardening | Sprint 2 | 1.5 weeks |
| Scheduling + coastal | Sprint 3 | 1 week |
| ML + API | Sprint 4 | 1.5 weeks |
| Monitoring + testing | Sprint 5 | 1 week |
| Frontend | Sprint 6 | 1 week |
| Docs + deploy | Sprint 7 | 1 week |
| **Total** | | **~9 weeks** (1 engineer) |

With 2 engineers in parallel: **~5–6 weeks**.

**Why it's shorter than the original 15-week estimate:** We don't need to build OSM extraction (colleague owns it), don't need FDW/replication (same DB), and don't need a separate POI database.

---

## 8. Remaining decisions

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | Properties sync mechanism | View / Materialized view / Physical table + sync | Materialized view (simple, stable snapshot) |
| 2 | Pipeline parallelism | Multiprocessing / async / DB-side batch | Multiprocessing (8 workers, proven pattern) |
| 3 | Pipeline scheduler | AWS EventBridge / cron / Airflow / Prefect | EventBridge (native AWS, simple for 2 schedules) |
| 4 | Aggregate score formula | Current 0.3/0.3/0.4 weights | Validate with ML team before production |
| 5 | API auth | API keys / AWS IAM / Cognito | API keys for simplicity (internal only) |
| 6 | Frontend hosting | ECS alongside backend / S3+CloudFront / Nginx sidecar | S3+CloudFront (static, cheap, fast) |
| 7 | Refresh signal from colleague | `audit.pipeline_runs` timestamp / notification / polling | Agree on a mechanism (e.g. he writes a row, we poll) |
