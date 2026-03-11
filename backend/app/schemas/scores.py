"""Pydantic schemas for score API request/response."""

from pydantic import BaseModel, Field


class LocationIn(BaseModel):
    """Single location input (lat, lon)."""

    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")


class LocationBatchItem(BaseModel):
    """One location in a batch request; optional id for correlation."""

    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    id: str | int | None = Field(default=None, description="Optional client id for correlation in results")


class LocationOut(BaseModel):
    """Location in response."""

    lat: float
    lon: float


class ScoresPayload(BaseModel):
    """Scores object per location (density, diversity, accessibility, nearest)."""

    poi_count_1km: int = Field(..., description="Number of POIs within 1 km")
    poi_count_400m: int = Field(..., description="Number of POIs within 400 m")
    n_categories: int = Field(..., description="Number of distinct super_categories in 1 km")
    n_poi_types: int = Field(..., description="Number of distinct fclass values in 1 km")
    entropy: float = Field(..., description="Shannon entropy of category distribution in 1 km")
    entropy_fclass: float = Field(
        ...,
        description="Shannon entropy of fclass (POI type) distribution within 1 km",
    )
    by_category: dict[str, int] = Field(
        default_factory=dict,
        description="POI count per super_category within 1 km",
    )
    accessibility_400m: dict[str, bool] = Field(
        default_factory=dict,
        description="Presence of key POI types within 400 m (e.g. bus_stop, pharmacy)",
    )
    nearest_km: dict[str, float] = Field(
        default_factory=dict,
        description="Distance in km to nearest POI per super_category",
    )
    aggregate_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Optional aggregate score 0–100",
    )


class ScoreResponse(BaseModel):
    """Single-location score response."""

    location: LocationOut
    scores: ScoresPayload


BATCH_MAX_LOCATIONS = 500


class BatchScoresRequest(BaseModel):
    """Request body for batch POI scores."""

    locations: list[LocationBatchItem] = Field(
        ...,
        min_length=1,
        max_length=BATCH_MAX_LOCATIONS,
        description=f"List of locations (max {BATCH_MAX_LOCATIONS} per request)",
    )


class BatchScoresResponse(BaseModel):
    """Batch score response; results in same order as request."""

    results: list[ScoreResponse] = Field(..., description="One score result per input location, same order")
