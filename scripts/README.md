# scripts/

Single execution layer for every CLI entrypoint. All scripts read settings via
`app.core.config.get_settings()` and use the same DB DSN as the API.

Documentation hub: [docs/README.md](../docs/README.md) · Operations: [docs/RUNBOOK.md](../docs/RUNBOOK.md)

## Layout

```
scripts/
├── schema/
│   ├── apply_init.py                   # apply init_schema_ci.sql (used in CI)
│   ├── apply_feature_pipeline.py       # apply feature_pipeline.sql
│   ├── init_schema_ci.sql
│   └── feature_pipeline.sql
└── ingest/
    ├── load_osm_land.py                # geo.land from OSM Overpass
    ├── load_osm_coastline.py           # geo.coastline from OSM Overpass
    └── load_properties_from_parquet.py # staging.transactions + slim production.properties
```

## Python dependencies

Ingest and schema scripts need the backend package plus extra libraries. From `backend/`
with your venv activated:

```bash
pip install -r requirements-ingest.txt
```

See [backend/REQUIREMENTS.md](../backend/REQUIREMENTS.md) for venv setup and other requirement files.

## Common operations

| Task                                         | Command                                                              |
|----------------------------------------------|----------------------------------------------------------------------|
| Apply CI schema (active.* + history.*)       | `python scripts/schema/apply_init.py`                                |
| Apply feature pipeline schema (production.*) | `python scripts/schema/apply_feature_pipeline.py`                    |
| Load Morocco land polygon                    | `python scripts/ingest/load_osm_land.py`                             |
| Load Morocco coastline                       | `python scripts/ingest/load_osm_coastline.py`                        |
| Load properties from parquet                 | `python scripts/ingest/load_properties_from_parquet.py --parquet …`  |
| Run weekly continuous flow                   | `python -m app.features.feature_pipeline weekly_continuous`          |
| Run historical batch flow                    | `python -m app.features.feature_pipeline historical_batch`           |
