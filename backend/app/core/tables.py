"""Centralized database table references.

All schema-qualified table names live here. Repository classes import from
this module; service and router layers must not embed raw table strings.
"""

from __future__ import annotations

SCHEMA_PRODUCTION = "production"
SCHEMA_STAGING = "staging"
SCHEMA_ACTIVE = "active"
SCHEMA_HISTORY = "history"
SCHEMA_GEO = "geo"

T_PROPERTIES = f"{SCHEMA_PRODUCTION}.properties"
T_PROPERTY_FEATURES = f"{SCHEMA_PRODUCTION}.property_features"
T_FEATURE_PIPELINE_RUNS = f"{SCHEMA_PRODUCTION}.feature_pipeline_runs"
T_FEATURE_PIPELINE_FAILURES = f"{SCHEMA_PRODUCTION}.feature_pipeline_failures"
T_POIS_CURRENT = f"{SCHEMA_ACTIVE}.production_pois_current"
T_POI_HISTORY = f"{SCHEMA_HISTORY}.production_poi_history"
T_AUDIT_PIPELINE_RUNS = f"{SCHEMA_ACTIVE}.audit_pipeline_runs"
T_GEO_COASTLINE = f"{SCHEMA_GEO}.coastline"
T_GEO_LAND = f"{SCHEMA_GEO}.land"

# Dev default for parquet ingest; production sets TRANSACTIONS_TABLE env to the
# real 1M-row source table (e.g. analytics.transactions).
T_TRANSACTIONS_DEV = f"{SCHEMA_STAGING}.transactions"

# SCD2 temporal filter for history.production_poi_history queries.
POI_HISTORY_SCD2_WHERE = """
    is_canonical = true
    AND :as_of >= valid_from AND :as_of < valid_to
"""

__all__ = [
    "POI_HISTORY_SCD2_WHERE",
    "SCHEMA_STAGING",
    "T_TRANSACTIONS_DEV",
    "SCHEMA_GEO",
    "SCHEMA_HISTORY",
    "SCHEMA_PRODUCTION",
    "T_AUDIT_PIPELINE_RUNS",
    "T_FEATURE_PIPELINE_FAILURES",
    "T_FEATURE_PIPELINE_RUNS",
    "T_GEO_COASTLINE",
    "T_GEO_LAND",
    "T_POIS_CURRENT",
    "T_POI_HISTORY",
    "T_PROPERTIES",
    "T_PROPERTY_FEATURES",
]
