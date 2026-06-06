"""Properties feature: map markers, hierarchical stats, property detail.

Reads from ``production.properties`` and ``production.property_features``
(this codebase's own tables, not the external POI contract).
"""

from app.features.properties.router import router
from app.features.properties.service import (
    get_properties_stats,
    get_property_detail,
    list_properties_for_map,
)

__all__ = [
    "get_properties_stats",
    "get_property_detail",
    "list_properties_for_map",
    "router",
]
