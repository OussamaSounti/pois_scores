"""Domain constants — single source of truth for non-environment literals.

Static business rules that are stable across deployments live here. Values
that depend on the deployment (URLs, secrets, log levels) belong in
:class:`app.core.config.Settings` instead.

**NEVER import from ``app.features.*`` in this module.** ``app.core`` is the
foundation layer; feature modules depend on it, never the reverse.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# POI taxonomy constants (used by pois, scores, properties, feature_pipeline)
# ---------------------------------------------------------------------------

N_SUPER_CATEGORIES: int = 11

N_FCLASS_TYPES: int = 91

ACCESSIBILITY_KEY_TYPES: frozenset[str] = frozenset(
    {
        "bus_stop",
        "pharmacy",
        "school",
        "hospital",
        "supermarket",
        "bank",
        "atm",
        "clinic",
        "fuel",
        "police",
        "park",
        "doctors",
        "taxi",
    }
)

__all__ = [
    "ACCESSIBILITY_KEY_TYPES",
    "ACC_KEYS",
    "ACC_COLUMN_NAMES",
    "ACCESSIBILITY_RADIUS_M",
    "BATCH_MAX_LOCATIONS",
    "CHUNK_SIZE",
    "DEFAULT_RADIUS_KM",
    "HIERARCHY_LEVELS",
    "HIERARCHY_LEVEL_PATTERN",
    "HIERARCHY_UID_FIELDS",
    "KM_TO_M",
    "MAX_POI_RADIUS_KM",
    "MAX_POI_RADIUS_M",
    "MAX_POI_QUERY_RADIUS_M",
    "N_FCLASS_TYPES",
    "N_SUPER_CATEGORIES",
    "PIPELINE_FLOW_HISTORICAL",
    "PIPELINE_FLOW_WEEKLY",
    "POI_SOURCE_CURRENT",
    "POI_SOURCE_HISTORY",
    "RUN_STATUS_FAILED",
    "RUN_STATUS_PARTIAL",
    "RUN_STATUS_RUNNING",
    "RUN_STATUS_SKIPPED",
    "RUN_STATUS_SUCCESS",
    "TRIGGERED_BY_CLI",
    "TRIGGERED_BY_PREFECT",
    "PROPERTIES_MAP_DEFAULT_LIMIT",
    "PROPERTIES_MAP_MAX_LIMIT",
    "PROPERTY_FEATURE_COLUMNS",
]

ACC_KEYS: tuple[str, ...] = tuple(sorted(ACCESSIBILITY_KEY_TYPES))
ACC_COLUMN_NAMES: tuple[str, ...] = tuple(f"acc_{k}" for k in ACC_KEYS)

PROPERTY_FEATURE_COLUMNS: tuple[str, ...] = (
    "transaction_id",
    "poi_refreshed_at",
    "pipeline_version",
    "computed_at",
    "poi_count_1km",
    "poi_count_400m",
    "n_categories",
    "n_poi_types",
    "entropy",
    "entropy_fclass",
    "aggregate_score",
    *ACC_COLUMN_NAMES,
    "by_category",
    "nearest_km",
    "dist_coast_km",
    "land_buffer_fraction_1km",
    "transaction_date",
    "poi_source",
)

CHUNK_SIZE: int = 200

DEFAULT_RADIUS_KM: float = 1.0
KM_TO_M: float = 1000.0
MAX_POI_RADIUS_KM: float = 25.0
MAX_POI_RADIUS_M: int = 25_000
MAX_POI_QUERY_RADIUS_M: int = 100_000
ACCESSIBILITY_RADIUS_M: float = 400.0

BATCH_MAX_LOCATIONS: int = 500

PROPERTIES_MAP_DEFAULT_LIMIT: int = 1200
PROPERTIES_MAP_MAX_LIMIT: int = 5000

POI_SOURCE_HISTORY: str = "history"
POI_SOURCE_CURRENT: str = "current"

PIPELINE_FLOW_WEEKLY: str = "weekly_continuous"
PIPELINE_FLOW_HISTORICAL: str = "historical_batch"

RUN_STATUS_RUNNING: str = "running"
RUN_STATUS_SUCCESS: str = "success"
RUN_STATUS_PARTIAL: str = "partial"
RUN_STATUS_FAILED: str = "failed"
RUN_STATUS_SKIPPED: str = "skipped"

TRIGGERED_BY_CLI: str = "cli"
TRIGGERED_BY_PREFECT: str = "prefect"

HIERARCHY_LEVELS: tuple[str, ...] = ("district", "neighbourhood", "iris", "ilot")
HIERARCHY_LEVEL_PATTERN: str = "^(" + "|".join(HIERARCHY_LEVELS) + ")$"
HIERARCHY_UID_FIELDS: tuple[str, ...] = tuple(f"{lvl}_uid" for lvl in HIERARCHY_LEVELS)
