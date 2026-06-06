"""Domain constants — single source of truth for non-environment literals.

Static business rules that are stable across deployments live here. Values
that depend on the deployment (URLs, secrets, log levels) belong in
``app.config.Settings`` instead.

The three POI-counting / accessibility constants are re-exported from
``app.services.spatial`` (which is the historical canonical source and is
locked per project rules) so that callers can depend on this module for
*all* domain literals without duplicating frozensets or magic numbers.
"""

from __future__ import annotations

from app.services.spatial import (
    ACCESSIBILITY_KEY_TYPES,
    N_FCLASS_TYPES,
    N_SUPER_CATEGORIES,
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
    "POI_SOURCE_CURRENT",
    "POI_SOURCE_HISTORY",
    "PROPERTIES_MAP_DEFAULT_LIMIT",
    "PROPERTIES_MAP_MAX_LIMIT",
    "PROPERTY_FEATURE_COLUMNS",
]

# Accessibility fclass list in fixed sorted order. Matches the schema's
# ``acc_*`` columns and is consumed by both the pipeline mapper and the
# property service when assembling response payloads.
ACC_KEYS: tuple[str, ...] = tuple(sorted(ACCESSIBILITY_KEY_TYPES))

# Column names for the accessibility booleans in production.property_features.
ACC_COLUMN_NAMES: tuple[str, ...] = tuple(f"acc_{k}" for k in ACC_KEYS)

# Full ordered column list for production.property_features upserts /
# DISTINCT ON projections. SQL bodies that select these columns are not
# rewritten to consume this tuple (per rule #2) but the Python-side upsert
# in app/pipeline/run.py imports it.
PROPERTY_FEATURE_COLUMNS: tuple[str, ...] = (
    "property_id",
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

# Pipeline batching default; orchestration layer imports from here.
CHUNK_SIZE: int = 200

# Radius defaults / limits used by the POIs router, the spatial layer, and
# the score services. Values match the historical hardcoded literals.
DEFAULT_RADIUS_KM: float = 1.0
KM_TO_M: float = 1000.0
MAX_POI_RADIUS_KM: float = 25.0
MAX_POI_RADIUS_M: int = 25_000
MAX_POI_QUERY_RADIUS_M: int = 100_000
ACCESSIBILITY_RADIUS_M: float = 400.0

# Score batch endpoint cap.
BATCH_MAX_LOCATIONS: int = 500

# Properties map endpoint pagination.
PROPERTIES_MAP_DEFAULT_LIMIT: int = 1200
PROPERTIES_MAP_MAX_LIMIT: int = 5000

# POI source enum values written to property_features.poi_source.
POI_SOURCE_HISTORY: str = "history"
POI_SOURCE_CURRENT: str = "current"

# Admin hierarchy levels exposed by the /properties/stats endpoint.
HIERARCHY_LEVELS: tuple[str, ...] = ("district", "neighbourhood", "iris", "ilot")
HIERARCHY_LEVEL_PATTERN: str = "^(" + "|".join(HIERARCHY_LEVELS) + ")$"
HIERARCHY_UID_FIELDS: tuple[str, ...] = tuple(f"{lvl}_uid" for lvl in HIERARCHY_LEVELS)
