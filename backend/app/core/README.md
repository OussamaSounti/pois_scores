# core/

Foundation layer — shared infrastructure that every feature module depends on.

> **NEVER import from `app.features.*` in this package.**
>
> `app.core` is the bottom of the dependency graph. Feature modules import
> from core, never the reverse. If you need a constant or utility that a
> feature currently owns, move it here first.

## Files

| File           | Role                                                        |
|----------------|-------------------------------------------------------------|
| `config.py`    | Pydantic `Settings` — environment-driven configuration      |
| `constants.py` | Static business-rule literals (taxonomy, radii, column defs) |
| `db.py`        | SQLAlchemy engine with connection pool, session factory, `get_db` dependency |
| `spatial.py`   | Pure spatial math (haversine, entropy, land fraction) and reference-data queries (coastline, land) |
| `tables.py`    | Centralized schema-qualified table name constants           |
| `metrics.py`   | Observability / metrics helpers                             |

## Key Settings (config.py)

| Env Variable        | Default | Purpose                              |
|---------------------|---------|--------------------------------------|
| `DATABASE_URL`      | local   | PostgreSQL connection string         |
| `PIPELINE_WORKERS`  | 4       | Parallel threads for batch pipeline  |
| `DB_POOL_SIZE`      | 5       | SQLAlchemy connection pool size      |
| `DB_MAX_OVERFLOW`   | 10      | Extra connections beyond pool_size   |
| `PIPELINE_VERSION`  | "1.0"   | Version label in property_features   |

## Dependency Rule

```
app.core  <──  app.features.*  <──  app.main
   │                                     │
   └─────── never imports from ──────────┘
            app.features
```

When adding new shared logic, place it here if it has **no feature-specific
knowledge**. If it depends on a specific domain concept (e.g., POI tables),
it belongs in the relevant feature module instead.
