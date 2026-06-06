"""POI table queries — every read against the external POI contract lives here.

Two source tables, both produced by an upstream pipeline:

- ``active.production_pois_current``: flat snapshot. Allowed columns:
  ``osm_id, name, fclass, super_category, lat, lon, geom``. There is no
  ``is_active`` filter and no integer ``id``.

- ``history.production_poi_history``: SCD2. Allowed columns add
  ``valid_from, valid_to, is_canonical``. Every query MUST filter on
  ``is_canonical = true`` (deduplicates point/polygon doubles) and use the
  half-open temporal range ``[valid_from, valid_to)``.

The taxonomy ``super_category`` is pre-resolved upstream; this module never
re-derives it from raw tags.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.spatial import _as_of_ts

# ---------------------------------------------------------------------------
# Shared taxonomy / accessibility constants (used by scoring + tests)
# ---------------------------------------------------------------------------

# Total number of distinct super_category values present in the dataset
# (verified by SELECT COUNT(DISTINCT super_category) across both source tables).
N_SUPER_CATEGORIES = 11

# Total number of distinct fclass values across both source tables.
N_FCLASS_TYPES = 91

# Key fclass values for accessibility scoring (presence within 400 m).
ACCESSIBILITY_KEY_TYPES = frozenset(
    {
        "bus_stop",
        "pharmacy",
        "school",
        "hospital",
        "supermarket",
        "bank",
        "atm",
        "clinic",
        "fuel",
        "police",
        "park",
        "doctors",
        "taxi",
    }
)


@dataclass
class PoiRow:
    """One POI row from either source table, in-memory.

    Field names mirror the external contract exactly.
    """

    osm_id: str
    name: str
    fclass: str
    super_category: str
    lat: float
    lon: float


# ---------------------------------------------------------------------------
# active.production_pois_current — current snapshot
# ---------------------------------------------------------------------------


def query_pois_radius(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float,
) -> list[PoiRow]:
    """POIs in ``active.production_pois_current`` within ``radius_m`` of (lat, lon)."""
    radius_m = max(0, min(radius_m, 100_000))
    sql = text("""
        SELECT osm_id, name, fclass, super_category, lat, lon
        FROM active.production_pois_current
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :radius_m
        )
    """)
    rows = session.execute(sql, {"lat": lat, "lon": lon, "radius_m": radius_m}).fetchall()
    return [
        PoiRow(
            osm_id=r.osm_id,
            name=r.name or "Unnamed",
            fclass=r.fclass,
            super_category=r.super_category,
            lat=float(r.lat),
            lon=float(r.lon),
        )
        for r in rows
    ]


def get_pois_with_distance(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float = 1000.0,
) -> list[dict[str, Any]]:
    """POIs within ``radius_m`` with ``distance_km`` for list/map display."""
    radius_m = max(0, min(radius_m, 25_000))
    sql = text("""
        SELECT osm_id, name, fclass, super_category, lat, lon,
               ST_Distance(
                   geom::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               ) / 1000.0 AS dist_km
        FROM active.production_pois_current
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :radius_m
        )
        ORDER BY dist_km
    """)
    rows = session.execute(sql, {"lat": lat, "lon": lon, "radius_m": radius_m}).fetchall()
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


def _nearest_km_by_category(
    session: Session,
    lat: float,
    lon: float,
    max_radius_m: float = 25_000,
) -> dict[str, float]:
    """Min distance in km to nearest POI per ``super_category`` (current snapshot)."""
    sql = text("""
        SELECT super_category,
               MIN(ST_Distance(
                   geom::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               )) / 1000.0 AS dist_km
        FROM active.production_pois_current
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :max_radius_m
        )
        GROUP BY super_category
    """)
    rows = session.execute(
        sql,
        {"lat": lat, "lon": lon, "max_radius_m": max_radius_m},
    ).fetchall()
    return {r.super_category: round(float(r.dist_km), 4) for r in rows}


# ---------------------------------------------------------------------------
# history.production_poi_history — SCD2, requires is_canonical filter
# ---------------------------------------------------------------------------


def query_pois_radius_at_date(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float,
    as_of: date | datetime,
) -> list[PoiRow]:
    """POIs from ``history.production_poi_history`` active at *as_of* within ``radius_m``."""
    radius_m = max(0, min(radius_m, 100_000))
    ts = _as_of_ts(as_of)
    sql = text("""
        SELECT osm_id, name, fclass, super_category, lat, lon
        FROM history.production_poi_history
        WHERE is_canonical = true
          AND :as_of >= valid_from AND :as_of < valid_to
          AND ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :radius_m
          )
    """)
    params = {"as_of": ts, "lat": lat, "lon": lon, "radius_m": radius_m}
    rows = session.execute(sql, params).fetchall()
    return [
        PoiRow(
            osm_id=r.osm_id,
            name=r.name or "Unnamed",
            fclass=r.fclass,
            super_category=r.super_category,
            lat=float(r.lat),
            lon=float(r.lon),
        )
        for r in rows
    ]


def get_pois_with_distance_at_date(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float = 1000.0,
    as_of: date | datetime | None = None,
) -> list[dict[str, Any]]:
    """POIs from history active at *as_of*, with ``distance_km`` for display."""
    radius_m = max(0, min(radius_m, 25_000))
    ts = _as_of_ts(as_of) if as_of is not None else None
    sql = text("""
        SELECT osm_id, name, fclass, super_category, lat, lon,
               ST_Distance(
                   geom::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               ) / 1000.0 AS dist_km
        FROM history.production_poi_history
        WHERE is_canonical = true
          AND :as_of >= valid_from AND :as_of < valid_to
          AND ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :radius_m
          )
        ORDER BY dist_km
    """)
    params = {"as_of": ts, "lat": lat, "lon": lon, "radius_m": radius_m}
    rows = session.execute(sql, params).fetchall()
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


def _nearest_km_by_category_at_date(
    session: Session,
    lat: float,
    lon: float,
    as_of: date | datetime,
    max_radius_m: float = 25_000,
) -> dict[str, float]:
    """Min distance in km to nearest POI per ``super_category`` at *as_of* (history)."""
    ts = _as_of_ts(as_of)
    sql = text("""
        SELECT super_category,
               MIN(ST_Distance(
                   geom::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               )) / 1000.0 AS dist_km
        FROM history.production_poi_history
        WHERE is_canonical = true
          AND :as_of >= valid_from AND :as_of < valid_to
          AND ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :max_radius_m
          )
        GROUP BY super_category
    """)
    rows = session.execute(
        sql,
        {"as_of": ts, "lat": lat, "lon": lon, "max_radius_m": max_radius_m},
    ).fetchall()
    return {r.super_category: round(float(r.dist_km), 4) for r in rows}
