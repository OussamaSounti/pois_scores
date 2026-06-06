# scripts/

Single execution layer for every CLI entrypoint. All scripts read settings via
`app.core.config.get_settings()` and use the same DB DSN as the API.

## Layout

```
scripts/
├── _bootstrap.py                       # puts backend/ on sys.path
├── schema/
│   ├── apply_init.py                   # apply init_schema_ci.sql (used in CI)
│   ├── apply_feature_pipeline.py       # apply feature_pipeline.sql
│   ├── init_schema_ci.sql
│   └── feature_pipeline.sql
└── ingest/
    ├── load_osm_land.py                # geo.land from OSM Overpass
    ├── load_osm_coastline.py           # geo.coastline from OSM Overpass
    └── load_properties_from_parquet.py # production.properties from parquet
```

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
