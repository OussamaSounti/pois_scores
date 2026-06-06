"""GeoJSON queries against ``geo.land`` and ``geo.coastline``.

These are static reference datasets loaded by ``scripts/ingest/load_osm_*.py``.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def _table_to_feature_collection(session: Session, table: str) -> dict[str, Any]:
    rows = session.execute(
        text(f"SELECT name, ST_AsGeoJSON(geom, 6)::text AS geojson FROM {table}")
    ).fetchall()
    features = [
        {
            "type": "Feature",
            "properties": {"name": row.name},
            "geometry": json.loads(row.geojson),
        }
        for row in rows
    ]
    return {"type": "FeatureCollection", "features": features}


def get_land_feature_collection(session: Session) -> dict[str, Any]:
    """Return ``geo.land`` rows as a GeoJSON FeatureCollection."""
    return _table_to_feature_collection(session, "geo.land")


def get_coastline_feature_collection(session: Session) -> dict[str, Any]:
    """Return ``geo.coastline`` rows as a GeoJSON FeatureCollection."""
    return _table_to_feature_collection(session, "geo.coastline")
