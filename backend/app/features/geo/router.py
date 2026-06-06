"""Geo data endpoints — exposes reference geometries as GeoJSON for the frontend."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.features.geo.service import (
    get_coastline_feature_collection,
    get_land_feature_collection,
)

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/land")
def get_land(db: Session = Depends(get_db)) -> JSONResponse:
    """Return ``geo.land`` as a GeoJSON FeatureCollection."""
    return JSONResponse(get_land_feature_collection(db))


@router.get("/coastline")
def get_coastline(db: Session = Depends(get_db)) -> JSONResponse:
    """Return ``geo.coastline`` as a GeoJSON FeatureCollection."""
    return JSONResponse(get_coastline_feature_collection(db))
