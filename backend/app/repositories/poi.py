"""POI table queries against the external POI contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.spatial import _as_of_ts
from app.core.tables import POI_HISTORY_SCD2_WHERE, T_POIS_CURRENT, T_POI_HISTORY


@dataclass
class PoiRow:
    """One POI row from either source table, in-memory."""

    osm_id: str
    name: str
    fclass: str
    super_category: str
    lat: float
    lon: float


def _row_to_poi(row: Any) -> PoiRow:
    return PoiRow(
        osm_id=row.osm_id,
        name=row.name or "Unnamed",
        fclass=row.fclass,
        super_category=row.super_category,
        lat=float(row.lat),
        lon=float(row.lon),
    )


class PoiRepository:
    """Reads from active.production_pois_current and history.production_poi_history."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def query_radius(self, lat: float, lon: float, radius_m: float) -> list[PoiRow]:
        """POIs in the current snapshot within radius_m of (lat, lon)."""
        radius_m = max(0, min(radius_m, 100_000))
        sql = text(f"""
            SELECT osm_id, name, fclass, super_category, lat, lon
            FROM {T_POIS_CURRENT}
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius_m
            )
        """)
        rows = self._session.execute(
            sql, {"lat": lat, "lon": lon, "radius_m": radius_m}
        ).fetchall()
        return [_row_to_poi(r) for r in rows]

    def query_with_distance(
        self,
        lat: float,
        lon: float,
        radius_m: float = 1000.0,
    ) -> list[dict[str, Any]]:
        """POIs within radius_m with distance_km for list/map display."""
        radius_m = max(0, min(radius_m, 25_000))
        sql = text(f"""
            SELECT osm_id, name, fclass, super_category, lat, lon,
                   ST_Distance(
                       geom::geography,
                       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                   ) / 1000.0 AS dist_km
            FROM {T_POIS_CURRENT}
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius_m
            )
            ORDER BY dist_km
        """)
        rows = self._session.execute(
            sql, {"lat": lat, "lon": lon, "radius_m": radius_m}
        ).fetchall()
        return [
            {
                "osm_id": r.osm_id,
                "name": r.name or "Unnamed",
                "fclass": r.fclass,
                "super_category": r.super_category,
                "lat": float(r.lat),
                "lon": float(r.lon),
                "distance_km": round(float(r.dist_km), 4),
            }
            for r in rows
        ]

    def nearest_km_by_category(
        self,
        lat: float,
        lon: float,
        max_radius_m: float = 25_000,
    ) -> dict[str, float]:
        """Min distance in km to nearest POI per super_category (current snapshot)."""
        sql = text(f"""
            SELECT super_category,
                   MIN(ST_Distance(
                       geom::geography,
                       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                   )) / 1000.0 AS dist_km
            FROM {T_POIS_CURRENT}
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :max_radius_m
            )
            GROUP BY super_category
        """)
        rows = self._session.execute(
            sql,
            {"lat": lat, "lon": lon, "max_radius_m": max_radius_m},
        ).fetchall()
        return {r.super_category: round(float(r.dist_km), 4) for r in rows}

    def query_radius_at_date(
        self,
        lat: float,
        lon: float,
        radius_m: float,
        as_of: date | datetime,
    ) -> list[PoiRow]:
        """POIs from history active at as_of within radius_m."""
        radius_m = max(0, min(radius_m, 100_000))
        ts = _as_of_ts(as_of)
        sql = text(f"""
            SELECT osm_id, name, fclass, super_category, lat, lon
            FROM {T_POI_HISTORY}
            WHERE {POI_HISTORY_SCD2_WHERE}
              AND ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius_m
              )
        """)
        params = {"as_of": ts, "lat": lat, "lon": lon, "radius_m": radius_m}
        rows = self._session.execute(sql, params).fetchall()
        return [_row_to_poi(r) for r in rows]

    def query_with_distance_at_date(
        self,
        lat: float,
        lon: float,
        radius_m: float = 1000.0,
        as_of: date | datetime | None = None,
    ) -> list[dict[str, Any]]:
        """POIs from history active at as_of, with distance_km for display."""
        radius_m = max(0, min(radius_m, 25_000))
        ts = _as_of_ts(as_of) if as_of is not None else None
        sql = text(f"""
            SELECT osm_id, name, fclass, super_category, lat, lon,
                   ST_Distance(
                       geom::geography,
                       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                   ) / 1000.0 AS dist_km
            FROM {T_POI_HISTORY}
            WHERE {POI_HISTORY_SCD2_WHERE}
              AND ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius_m
              )
            ORDER BY dist_km
        """)
        params = {"as_of": ts, "lat": lat, "lon": lon, "radius_m": radius_m}
        rows = self._session.execute(sql, params).fetchall()
        return [
            {
                "osm_id": r.osm_id,
                "name": r.name or "Unnamed",
                "fclass": r.fclass,
                "super_category": r.super_category,
                "lat": float(r.lat),
                "lon": float(r.lon),
                "distance_km": round(float(r.dist_km), 4),
            }
            for r in rows
        ]

    def nearest_km_by_category_at_date(
        self,
        lat: float,
        lon: float,
        as_of: date | datetime,
        max_radius_m: float = 25_000,
    ) -> dict[str, float]:
        """Min distance in km to nearest POI per super_category at as_of (history)."""
        ts = _as_of_ts(as_of)
        sql = text(f"""
            SELECT super_category,
                   MIN(ST_Distance(
                       geom::geography,
                       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                   )) / 1000.0 AS dist_km
            FROM {T_POI_HISTORY}
            WHERE {POI_HISTORY_SCD2_WHERE}
              AND ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :max_radius_m
              )
            GROUP BY super_category
        """)
        rows = self._session.execute(
            sql,
            {"as_of": ts, "lat": lat, "lon": lon, "max_radius_m": max_radius_m},
        ).fetchall()
        return {r.super_category: round(float(r.dist_km), 4) for r in rows}

    # ------------------------------------------------------------------
    # Combined queries for pipeline throughput (fewer round-trips)
    # ------------------------------------------------------------------

    def query_pois_and_nearest_current(
        self,
        lat: float,
        lon: float,
    ) -> tuple[list[PoiRow], list[PoiRow], dict[str, float]]:
        """Fetch 1km POIs, 400m POIs, and nearest-by-category in one round-trip.

        Returns (pois_1km, pois_400m, nearest_km).
        """
        sql = text(f"""
            WITH
              pt AS (
                SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography AS geog
              ),
              pois AS (
                SELECT osm_id, name, fclass, super_category, lat, lon,
                       ST_Distance(geom::geography, (SELECT geog FROM pt)) AS dist_m
                FROM {T_POIS_CURRENT}
                WHERE ST_DWithin(
                    geom::geography, (SELECT geog FROM pt), 25000
                )
              )
            SELECT osm_id, name, fclass, super_category, lat, lon, dist_m
            FROM pois
            ORDER BY dist_m
        """)
        rows = self._session.execute(sql, {"lat": lat, "lon": lon}).fetchall()

        pois_1km: list[PoiRow] = []
        pois_400m: list[PoiRow] = []
        nearest: dict[str, float] = {}
        for r in rows:
            poi = _row_to_poi(r)
            dist_m = float(r.dist_m)
            cat = r.super_category
            dist_km = dist_m / 1000.0
            if cat not in nearest or dist_km < nearest[cat]:
                nearest[cat] = round(dist_km, 4)
            if dist_m <= 1000:
                pois_1km.append(poi)
            if dist_m <= 400:
                pois_400m.append(poi)
        return pois_1km, pois_400m, nearest

    def query_pois_and_nearest_at_date(
        self,
        lat: float,
        lon: float,
        as_of: date | datetime,
    ) -> tuple[list[PoiRow], list[PoiRow], dict[str, float]]:
        """Fetch 1km POIs, 400m POIs, and nearest-by-category at *as_of* in one round-trip.

        Returns (pois_1km, pois_400m, nearest_km).
        """
        ts = _as_of_ts(as_of)
        sql = text(f"""
            WITH
              pt AS (
                SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography AS geog
              ),
              pois AS (
                SELECT osm_id, name, fclass, super_category, lat, lon,
                       ST_Distance(geom::geography, (SELECT geog FROM pt)) AS dist_m
                FROM {T_POI_HISTORY}
                WHERE {POI_HISTORY_SCD2_WHERE}
                  AND ST_DWithin(
                      geom::geography, (SELECT geog FROM pt), 25000
                  )
              )
            SELECT osm_id, name, fclass, super_category, lat, lon, dist_m
            FROM pois
            ORDER BY dist_m
        """)
        rows = self._session.execute(
            sql, {"lat": lat, "lon": lon, "as_of": ts}
        ).fetchall()

        pois_1km: list[PoiRow] = []
        pois_400m: list[PoiRow] = []
        nearest: dict[str, float] = {}
        for r in rows:
            poi = _row_to_poi(r)
            dist_m = float(r.dist_m)
            cat = r.super_category
            dist_km = dist_m / 1000.0
            if cat not in nearest or dist_km < nearest[cat]:
                nearest[cat] = round(dist_km, 4)
            if dist_m <= 1000:
                pois_1km.append(poi)
            if dist_m <= 400:
                pois_400m.append(poi)
        return pois_1km, pois_400m, nearest
