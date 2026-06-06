"""Geo feature: GeoJSON endpoints for reference geometries (land, coastline)."""

from app.features.geo.router import router
from app.features.geo.service import get_coastline_feature_collection, get_land_feature_collection

__all__ = ["get_coastline_feature_collection", "get_land_feature_collection", "router"]
