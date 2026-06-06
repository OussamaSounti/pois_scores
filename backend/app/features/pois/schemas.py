"""Pydantic schemas for the POI list API."""

from pydantic import BaseModel, ConfigDict, Field


class PoiItemOut(BaseModel):
    """One POI with distance for list/map display.

    Field names follow the external POI contract (``osm_id``, ``lat``, ``lon``)
    so the wire format mirrors the underlying tables.
    """

    model_config = ConfigDict(extra="ignore")

    osm_id: str
    name: str
    fclass: str
    super_category: str
    lat: float
    lon: float
    distance_km: float = Field(..., description="Distance from query point in km")


class PoisListResponse(BaseModel):
    """List of POIs within radius."""

    model_config = ConfigDict(extra="ignore")

    pois: list[PoiItemOut]
