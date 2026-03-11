"""Pydantic schemas for POI list API."""

from pydantic import BaseModel, Field


class PoiItemOut(BaseModel):
    """One POI with distance for list/map display."""

    id: int
    name: str
    fclass: str
    super_category: str
    latitude: float
    longitude: float
    distance_km: float = Field(..., description="Distance from query point in km")


class PoisListResponse(BaseModel):
    """List of POIs within radius."""

    pois: list[PoiItemOut]
