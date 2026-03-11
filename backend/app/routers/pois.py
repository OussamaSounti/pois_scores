"""POI list endpoint for map and right panel."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.pois import PoiItemOut, PoisListResponse
from app.services.spatial import get_pois_with_distance

router = APIRouter(prefix="/pois", tags=["pois"])


@router.get("", response_model=PoisListResponse)
def list_pois(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(1.0, ge=0.1, le=25.0),
    db: Session = Depends(get_db),
) -> PoisListResponse:
    """Get POIs within radius_km of (lat, lon) for map and list display."""
    radius_m = radius_km * 1000.0
    rows = get_pois_with_distance(db, lat, lon, radius_m)
    return PoisListResponse(pois=[PoiItemOut(**r) for r in rows])
