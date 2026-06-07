# features/

**What:** Domain modules — each owns one capability end-to-end.  
**Why:** Keeps scoring, POI reads, properties, geo, and batch pipeline isolated but composable.

---

## Module map

| Module | Purpose | Used by |
|--------|---------|---------|
| [`scores/`](scores/) | Pure score math (density, diversity, accessibility) | API + pipeline |
| [`pois/`](pois/) | POI list queries from `active.*` / `history.*` | API |
| [`properties/`](properties/) | Property map, stats, detail from precomputed features | API |
| [`geo/`](geo/) | GeoJSON for land and coastline overlays | API |
| [`feature_pipeline/`](feature_pipeline/) | Batch scoring → `production.property_features` | CLI, Prefect, Docker |

---

## Dependency rules

```
app.core  ←  app.repositories  ←  features.*.service  ←  router
```

- **`scores`**, **`pois`**, **`feature_pipeline`** form a tightly coupled scoring domain — cross-imports between them are allowed.
- **`properties`** and **`geo`** are standalone (no imports from pipeline).
- **`core`** must never import from **`features`**.

---

## Two scoring paths

| Path | Entry | POI source | Output |
|------|-------|------------|--------|
| **Live API** | `scores/router.py` | `active.production_pois_current` (or history via `as_of`) | JSON response |
| **Batch pipeline** | `feature_pipeline/` CLI | Current or history per property | `production.property_features` rows |

Both call the same functions in `scores/service.py`.

---

## Per-module docs

| README | Covers |
|--------|--------|
| [scores/README.md](scores/README.md) | Endpoints, scoring steps, coastal signals |
| [pois/README.md](pois/README.md) | POI list endpoint, spatial queries |
| [properties/README.md](properties/README.md) | Map markers, hierarchy stats, detail |
| [geo/README.md](geo/README.md) | `/geo/land`, `/geo/coastline` GeoJSON |
| [feature_pipeline/README.md](feature_pipeline/README.md) | Weekly vs historical flows, CLI, Prefect |

---

## Running the pipeline

```bash
# From backend/ with pipeline deps installed
python -m app.features.feature_pipeline weekly_continuous
python -m app.features.feature_pipeline historical_batch

# Prefect flows
# app.features.feature_pipeline.flow — weekly_recompute_flow, historical_backfill_flow
```

Docker: `docker compose --profile pipeline run --rm pipeline`

---

## Further reading

| Doc | Topic |
|-----|-------|
| [../repositories/README.md](../repositories/README.md) | SQL layer |
| [../../../docs/DATA_MODEL.md](../../../docs/DATA_MODEL.md) | Tables |
| [../../../scripts/README.md](../../../scripts/README.md) | CLI commands |
