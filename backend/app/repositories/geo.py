"""Geo reference-data queries against geo.coastline and geo.land."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.tables import T_GEO_COASTLINE, T_GEO_LAND


class GeoReferenceRepository:
    """Reads from static geo.coastline and geo.land reference datasets."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def dist_coast_km(self, lat: float, lon: float) -> float | None:
        """Geodesic distance (km) from (lat, lon) to nearest coastline feature."""
        sql = text(f"""
            SELECT
                ST_Distance(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) / 1000.0 AS dist_km
            FROM {T_GEO_COASTLINE}
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            LIMIT 1
        """)
        try:
            row = self._session.execute(sql, {"lat": lat, "lon": lon}).fetchone()
        except Exception:  # noqa: BLE001
            self._session.rollback()
            return None
        if row is None:
            return None
        return round(float(row.dist_km), 4)

    def is_on_land(self, lat: float, lon: float) -> bool:
        """True if (lat, lon) is inside geo.land."""
        sql = text(f"""
            SELECT EXISTS (
                SELECT 1 FROM {T_GEO_LAND} l
                WHERE ST_Contains(
                    l.geom,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                )
            ) AS on_land
        """)
        try:
            row = self._session.execute(sql, {"lat": lat, "lon": lon}).fetchone()
        except Exception:  # noqa: BLE001
            self._session.rollback()
            return True
        return bool(row.on_land) if row is not None else True

    def land_buffer_fraction(
        self,
        lat: float,
        lon: float,
        radius_m: float = 1000.0,
    ) -> float | None:
        """Fraction of a circular buffer that lies on land, computed via PostGIS."""
        sql = text(f"""
            WITH
            pt  AS (SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS geom),
            buf AS (SELECT ST_Buffer(pt.geom::geography, :radius_m)::geometry AS geom FROM pt),
            coast AS (
                SELECT ST_Union(c.geom) AS geom
                FROM   {T_GEO_COASTLINE} c, pt
                WHERE  ST_DWithin(c.geom::geography, pt.geom::geography, :radius_m * 1.5)
            ),
            split_polys AS (
                SELECT (ST_Dump(ST_Split(buf.geom, coast.geom))).geom AS geom
                FROM   buf, coast
                WHERE  coast.geom IS NOT NULL
                UNION ALL
                SELECT buf.geom
                FROM   buf
                WHERE  (SELECT coast.geom FROM coast) IS NULL
            ),
            center_on_land AS (
                SELECT EXISTS (
                    SELECT 1 FROM {T_GEO_LAND} l
                    WHERE  ST_Contains(l.geom, (SELECT pt.geom FROM pt))
                ) AS val
            ),
            center_piece AS (
                SELECT ST_Area(geom::geography) AS area_m2
                FROM   split_polys
                WHERE  ST_Contains(geom, (SELECT pt.geom FROM pt))
                LIMIT  1
            ),
            land_area AS (
                SELECT
                    CASE WHEN col.val
                        THEN COALESCE(cp.area_m2,  ST_Area(buf.geom::geography))
                        ELSE ST_Area(buf.geom::geography) - COALESCE(cp.area_m2, 0.0)
                    END AS val
                FROM  center_on_land col, buf
                LEFT JOIN center_piece cp ON TRUE
            )
            SELECT GREATEST(0.0, LEAST(1.0,
                la.val / NULLIF(ST_Area(buf.geom::geography), 0.0)
            )) AS land_fraction
            FROM land_area la, buf
        """)
        try:
            row = self._session.execute(
                sql, {"lat": lat, "lon": lon, "radius_m": radius_m}
            ).fetchone()
        except Exception:  # noqa: BLE001
            self._session.rollback()
            return None
        if row is None or row.land_fraction is None:
            return None
        return round(max(0.0, min(1.0, float(row.land_fraction))), 4)

    def table_to_feature_collection(self, table: str) -> dict[str, Any]:
        """Return all rows from a geo table as a GeoJSON FeatureCollection."""
        rows = self._session.execute(
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

    def get_land_feature_collection(self) -> dict[str, Any]:
        return self.table_to_feature_collection(T_GEO_LAND)

    def get_coastline_feature_collection(self) -> dict[str, Any]:
        return self.table_to_feature_collection(T_GEO_COASTLINE)
