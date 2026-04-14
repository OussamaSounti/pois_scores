"""Geo data endpoints — exposes reference geometries as GeoJSON for frontend verification."""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/land")
def get_land(db: Session = Depends(get_db)) -> JSONResponse:
    """Return the geo.land table as a GeoJSON FeatureCollection."""
    rows = db.execute(
        text(
            "SELECT name, ST_AsGeoJSON(geom, 6)::text AS geojson FROM geo.land"
        )
    ).fetchall()

    features = [
        {
            "type": "Feature",
            "properties": {"name": row.name},
            "geometry": json.loads(row.geojson),
        }
        for row in rows
    ]
    return JSONResponse({"type": "FeatureCollection", "features": features})


@router.get("/coastline")
def get_coastline(db: Session = Depends(get_db)) -> JSONResponse:
    """Return the geo.coastline table as a GeoJSON FeatureCollection."""
    rows = db.execute(
        text(
            "SELECT name, ST_AsGeoJSON(geom, 6)::text AS geojson FROM geo.coastline"
        )
    ).fetchall()

    features = [
        {
            "type": "Feature",
            "properties": {"name": row.name},
            "geometry": json.loads(row.geojson),
        }
        for row in rows
    ]
    return JSONResponse({"type": "FeatureCollection", "features": features})
