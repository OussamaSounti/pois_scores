"""POI list endpoint for map and right panel."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import DEFAULT_RADIUS_KM, KM_TO_M, MAX_POI_RADIUS_KM
from app.core.db import get_db
from app.features.pois.schemas import PoiItemOut, PoisListResponse
from app.features.pois.service import (
    get_pois_with_distance,
    get_pois_with_distance_at_date,
)

router = APIRouter(prefix="/pois", tags=["pois"])


@router.get("", response_model=PoisListResponse)
def list_pois(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(DEFAULT_RADIUS_KM, ge=0.1, le=MAX_POI_RADIUS_KM),
    as_of: date | None = Query(
        default=None,
        description=(
            "Optional date (YYYY-MM-DD). When provided, POIs active at that date are "
            "returned from the history table instead of the current snapshot."
        ),
    ),
    db: Session = Depends(get_db),
) -> PoisListResponse:
    """Get POIs within radius_km of (lat, lon) for map and list display."""
    radius_m = radius_km * KM_TO_M
    if as_of is not None:
        rows = get_pois_with_distance_at_date(db, lat, lon, radius_m, as_of)
    else:
        rows = get_pois_with_distance(db, lat, lon, radius_m)
    return PoisListResponse(pois=[PoiItemOut(**r) for r in rows])
