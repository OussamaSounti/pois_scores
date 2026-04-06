"""Pydantic schemas for properties map/statistics APIs."""

from pydantic import BaseModel, ConfigDict, Field


class PropertyScoresOut(BaseModel):
    """Detailed, non-aggregated POI feature payload for a property."""

    model_config = ConfigDict(extra="ignore")

    poi_refreshed_at: str | None = None
    pipeline_version: str | None = None
    poi_count_1km: int | None = None
    poi_count_400m: int | None = None
    n_categories: int | None = None
    n_poi_types: int | None = None
    entropy: float | None = None
    entropy_fclass: float | None = None
    aggregate_score: float | None = Field(default=None, ge=0, le=100)
    accessibility_400m: dict[str, bool] = Field(default_factory=dict)
    by_category: dict[str, float] = Field(default_factory=dict)
    nearest_km: dict[str, float] = Field(default_factory=dict)


class PropertyMapItemOut(BaseModel):
    """One property marker item for map rendering."""

    model_config = ConfigDict(extra="ignore")

    id: int
    latitude: float
    longitude: float
    transaction_date: str | None = None
    asset_price: float | None = None
    asset_surface: float | None = None
    asset_psqm: float | None = None
    asset_type: str | None = None
    district_uid: str | None = None
    district_name: str | None = None
    neighbourhood_uid: str | None = None
    neighbour_name: str | None = None
    iris_uid: str | None = None
    iris_code: str | None = None
    ilot_uid: str | None = None
    ilot_objectid: str | None = None
    scores: PropertyScoresOut = Field(default_factory=PropertyScoresOut)


class PropertiesMapResponse(BaseModel):
    """Map payload for properties layer."""

    model_config = ConfigDict(extra="ignore")

    items: list[PropertyMapItemOut]
    count: int


class PropertyDetailResponse(BaseModel):
    """Single property detail response."""

    model_config = ConfigDict(extra="ignore")

    item: PropertyMapItemOut


class PropertyStatsGroupOut(BaseModel):
    """Aggregated stats for one admin group (district/neighbourhood/iris/ilot)."""

    model_config = ConfigDict(extra="ignore")

    key: str
    label: str
    properties_count: int
    avg_poi_count_1km: float | None = None
    avg_entropy: float | None = None
    avg_entropy_fclass: float | None = None
    avg_aggregate_score: float | None = None


class PropertyStatsResponse(BaseModel):
    """Grouped statistics response for hierarchy drilldown."""

    model_config = ConfigDict(extra="ignore")

    level: str
    groups: list[PropertyStatsGroupOut]
