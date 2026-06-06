"""Property map and hierarchy statistics endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.constants import (
    HIERARCHY_LEVEL_PATTERN,
    PROPERTIES_MAP_DEFAULT_LIMIT,
    PROPERTIES_MAP_MAX_LIMIT,
)
from app.core.db import get_db
from app.features.properties.schemas import (
    PropertiesMapResponse,
    PropertyDetailResponse,
    PropertyStatsResponse,
)
from app.features.properties.service import (
    get_properties_stats,
    get_property_detail,
    list_properties_for_map,
)

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=PropertiesMapResponse)
def list_properties(
    west: float = Query(..., ge=-180, le=180),
    south: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    north: float = Query(..., ge=-90, le=90),
    limit: int = Query(PROPERTIES_MAP_DEFAULT_LIMIT, ge=1, le=PROPERTIES_MAP_MAX_LIMIT),
    district_uid: str | None = Query(default=None),
    neighbourhood_uid: str | None = Query(default=None),
    iris_uid: str | None = Query(default=None),
    ilot_uid: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PropertiesMapResponse:
    """Get properties in bbox for map rendering, including non-aggregated score fields."""
    if west > east or south > north:
        raise HTTPException(
            status_code=400,
            detail="Invalid bbox: expected west<=east and south<=north",
        )

    items = list_properties_for_map(
        db,
        west=west,
        south=south,
        east=east,
        north=north,
        limit=limit,
        district_uid=district_uid,
        neighbourhood_uid=neighbourhood_uid,
        iris_uid=iris_uid,
        ilot_uid=ilot_uid,
    )
    return PropertiesMapResponse(items=items, count=len(items))


@router.get("/stats", response_model=PropertyStatsResponse)
def properties_stats(
    level: str = Query(..., pattern=HIERARCHY_LEVEL_PATTERN),
    district_uid: str | None = Query(default=None),
    neighbourhood_uid: str | None = Query(default=None),
    iris_uid: str | None = Query(default=None),
    ilot_uid: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PropertyStatsResponse:
    """Get grouped stats by one admin hierarchy level."""
    groups = get_properties_stats(
        db,
        level=level,
        district_uid=district_uid,
        neighbourhood_uid=neighbourhood_uid,
        iris_uid=iris_uid,
        ilot_uid=ilot_uid,
    )
    return PropertyStatsResponse(level=level, groups=groups)


@router.get("/{property_id}", response_model=PropertyDetailResponse)
def property_detail(property_id: int, db: Session = Depends(get_db)) -> PropertyDetailResponse:
    """Get one property with its latest feature payload."""
    item = get_property_detail(db, property_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return PropertyDetailResponse(item=item)
