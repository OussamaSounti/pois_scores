"""POI feature: HTTP listing endpoint and POI-table queries.

Owns every read against the POI pipeline output tables
``active.production_pois_current`` (flat current snapshot) and
``history.production_poi_history`` (SCD2, ``is_canonical`` + ``dedup_group`` dedup).
"""

from app.features.pois.router import router
from app.features.pois.service import (
    PoiRow,
    get_pois_with_distance,
    get_pois_with_distance_at_date,
    query_pois_combined,
    query_pois_combined_at_date,
    query_pois_radius,
    query_pois_radius_at_date,
)

__all__ = [
    "PoiRow",
    "get_pois_with_distance",
    "get_pois_with_distance_at_date",
    "query_pois_combined",
    "query_pois_combined_at_date",
    "query_pois_radius",
    "query_pois_radius_at_date",
    "router",
]
