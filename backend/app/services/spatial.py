"""Spatial queries and score computation for production.pois_current."""

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

# Key fclass values for accessibility (within 400 m)
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
    """One POI row from production.pois_current (for in-memory use)."""

    id: int
    name: str
    fclass: str
    super_category: str
    latitude: float
    longitude: float


def query_pois_radius(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float,
) -> list[PoiRow]:
    """Return active POIs in production.pois_current within radius_m. Uses PostGIS geom."""
    radius_m = max(0, min(radius_m, 100_000))
    sql = text("""
        SELECT id, name, fclass, super_category, latitude, longitude
        FROM production.pois_current
        WHERE is_active = true
          AND ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :radius_m
        )
    """)
    rows = session.execute(sql, {"lat": lat, "lon": lon, "radius_m": radius_m}).fetchall()
    return [
        PoiRow(
            id=r.id,
            name=r.name or "Unnamed",
            fclass=r.fclass,
            super_category=r.super_category,
            latitude=float(r.latitude),
            longitude=float(r.longitude),
        )
        for r in rows
    ]


def get_pois_with_distance(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float = 1000.0,
) -> list[dict[str, Any]]:
    """Return POIs within radius_m with distance_km for list/map display. Only active POIs."""
    radius_m = max(0, min(radius_m, 25_000))
    sql = text("""
        SELECT id, name, fclass, super_category, latitude, longitude,
               ST_Distance(
                   geom::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               ) / 1000.0 AS dist_km
        FROM production.pois_current
        WHERE is_active = true
          AND ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :radius_m
        )
        ORDER BY dist_km
    """)
    rows = session.execute(sql, {"lat": lat, "lon": lon, "radius_m": radius_m}).fetchall()
    return [
        {
            "id": r.id,
            "name": r.name or "Unnamed",
            "fclass": r.fclass,
            "super_category": r.super_category,
            "latitude": float(r.latitude),
            "longitude": float(r.longitude),
            "distance_km": round(float(r.dist_km), 4),
        }
        for r in rows
    ]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two WGS84 points."""
    r = 6371.0  # Earth radius km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def _entropy(counts: dict[str, int], total: int) -> float:
    """Shannon entropy (bits) of category distribution. 0 if total is 0."""
    if total <= 0:
        return 0.0
    h = 0.0
    for n in counts.values():
        if n > 0:
            p = n / total
            h -= p * math.log2(p)
    return h


def _nearest_km_by_category(
    session: Session,
    lat: float,
    lon: float,
    max_radius_m: float = 25_000,
) -> dict[str, float]:
    """Min distance in km to nearest POI per super_category (PostGIS). Only active POIs."""
    sql = text("""
        SELECT super_category,
               MIN(ST_Distance(
                   geom::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               )) / 1000.0 AS dist_km
        FROM production.pois_current
        WHERE is_active = true
          AND ST_DWithin(
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


def compute_scores(session: Session, lat: float, lon: float) -> dict[str, Any]:
    """
    Compute POI scores for one location from production.pois_current (active POIs only).
    Returns a dict suitable for ScoresPayload (by_category, accessibility_400m, nearest_km, etc.).
    """
    pois_1km = query_pois_radius(session, lat, lon, 1000.0)
    pois_400m = query_pois_radius(session, lat, lon, 400.0)

    by_category: dict[str, int] = defaultdict(int)
    by_fclass: dict[str, int] = defaultdict(int)
    fclasses_1km: set[str] = set()
    for p in pois_1km:
        by_category[p.super_category] += 1
        by_fclass[p.fclass] += 1
        fclasses_1km.add(p.fclass)

    total_1km = len(pois_1km)
    entropy = _entropy(dict(by_category), total_1km)
    entropy_fclass = _entropy(dict(by_fclass), total_1km)

    accessibility_400m: dict[str, bool] = {}
    fclass_in_400m = {p.fclass for p in pois_400m}
    for k in ACCESSIBILITY_KEY_TYPES:
        accessibility_400m[k] = k in fclass_in_400m

    nearest_km = _nearest_km_by_category(session, lat, lon)

    # Optional aggregate: simple weighted mix (placeholder formula)
    agg = None
    if by_category:
        n_cat = len(by_category)
        n_type = len(fclasses_1km)
        dens = min(total_1km / 50.0, 1.0)  # cap density component
        div = min((n_cat / 10.0 + n_type / 20.0) / 2, 1.0)
        acc = sum(accessibility_400m.values()) / max(len(ACCESSIBILITY_KEY_TYPES), 1)
        agg = round(100.0 * (0.3 * dens + 0.3 * div + 0.4 * acc), 1)

    return {
        "poi_count_1km": total_1km,
        "poi_count_400m": len(pois_400m),
        "n_categories": len(by_category),
        "n_poi_types": len(fclasses_1km),
        "entropy": round(entropy, 4),
        "entropy_fclass": round(entropy_fclass, 4),
        "by_category": dict(by_category),
        "accessibility_400m": accessibility_400m,
        "nearest_km": nearest_km,
        "aggregate_score": agg,
    }
