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


def _land_buffer_fraction(dist_coast_km: float, radius_km: float = 1.0) -> float:
    """
    Fraction of a circle (radius=radius_km) that lies on land when the centre
    is at distance dist_coast_km from a **straight** coastline.

    Uses the circular-segment formula:
        ocean_cap_area = r² · arccos(d/r) − d · √(r²−d²)
        land_fraction  = 1 − ocean_cap_area / (π·r²)

    NOTE: This is a fallback approximation only.  For capes, peninsulas, bays
    or any non-linear coastline use _land_buffer_fraction_db() which computes
    the true intersection via PostGIS land polygons.

    Special cases:
      - dist_coast_km >= radius_km  → 1.0  (buffer fully on land)
      - dist_coast_km == 0          → 0.5  (buffer half on land, half in ocean)
    """
    if dist_coast_km >= radius_km:
        return 1.0
    d = max(dist_coast_km, 0.0)
    ratio = d / radius_km  # in [0, 1)
    ocean_fraction = (math.acos(ratio) - ratio * math.sqrt(1.0 - ratio**2)) / math.pi
    return max(0.0, min(1.0, 1.0 - ocean_fraction))


def _land_buffer_fraction_db(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float = 1000.0,
) -> float | None:
    """
    Compute the fraction of a circular buffer that lies on land.

    Algorithm:
      1. Union all nearby OSM coastline rows into one blade geometry.
      2. ST_Split(buffer_circle, blade) → 1 or 2 polygon pieces.
      3. Find the "center piece" — the piece that contains the query point.
      4. Ask geo.land (NE 10m) whether the query point itself is on land.
         - Yes → land area = area of center piece.
         - No  → land area = buffer area − area of center piece.
      5. land_fraction = land_area / buffer_area.

    This avoids ray-casting (which breaks on open polylines like OSM coastline
    segments) and avoids topology issues with ST_Node/ST_Polygonize.
    Returns None only when geo.coastline or the query fails.
    """
    sql = text("""
        WITH
        pt  AS (SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS geom),
        buf AS (SELECT ST_Buffer(pt.geom::geography, :radius_m)::geometry AS geom FROM pt),

        -- Union all OSM coastline rows within 1.5 × radius into one blade.
        coast AS (
            SELECT ST_Union(c.geom) AS geom
            FROM   geo.coastline c, pt
            WHERE  ST_DWithin(c.geom::geography, pt.geom::geography, :radius_m * 1.5)
        ),

        -- Split the buffer by the coastline blade.
        -- If no coast is within range, keep the full buffer as one piece.
        split_polys AS (
            SELECT (ST_Dump(ST_Split(buf.geom, coast.geom))).geom AS geom
            FROM   buf, coast
            WHERE  coast.geom IS NOT NULL
            UNION ALL
            SELECT buf.geom
            FROM   buf
            WHERE  (SELECT coast.geom FROM coast) IS NULL
        ),

        -- Is the query point on land?  geo.land is the NE 10m Morocco polygon,
        -- accurate to ~500 m — reliable enough for the center-point check since
        -- _land_buffer_fraction_db is only called when dist_coast < 1 km and the
        -- user will restrict to on-land locations.
        center_on_land AS (
            SELECT EXISTS (
                SELECT 1 FROM geo.land l
                WHERE  ST_Contains(l.geom, (SELECT pt.geom FROM pt))
            ) AS val
        ),

        -- The piece that contains the query point (the "same side" piece).
        -- LIMIT 1 guards against floating-point edge cases where the point
        -- lands exactly on the split boundary.
        center_piece AS (
            SELECT ST_Area(geom::geography) AS area_m2
            FROM   split_polys
            WHERE  ST_Contains(geom, (SELECT pt.geom FROM pt))
            LIMIT  1
        ),

        -- Land area calculation:
        --   center on land  → land = center_piece                            
        --   center in ocean → land = buffer − center_piece (the other slices)
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
        row = session.execute(
            sql, {"lat": lat, "lon": lon, "radius_m": radius_m}
        ).fetchone()
    except Exception:  # noqa: BLE001 – table absent or schema missing
        return None
    if row is None or row.land_fraction is None:
        return None
    return round(max(0.0, min(1.0, float(row.land_fraction))), 4)


def _is_on_land(session: Session, lat: float, lon: float) -> bool:
    """Return True if the point is inside geo.land (i.e. on land, not in ocean).

    Used as a fast path for points more than 1 km from the coastline where
    the answer is binary.  geo.land is the Natural Earth 10 m Morocco polygon
    which is accurate to ~500 m — reliable at the 1 km threshold.
    Defaults to True (land) when the table is absent.
    """
    sql = text("""
        SELECT EXISTS (
            SELECT 1 FROM geo.land l
            WHERE ST_Contains(
                l.geom,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            )
        ) AS on_land
    """)
    try:
        row = session.execute(sql, {"lat": lat, "lon": lon}).fetchone()
    except Exception:  # noqa: BLE001
        return True
    return bool(row.on_land) if row is not None else True


def _dist_coast_km(
    session: Session,
    lat: float,
    lon: float,
) -> float | None:
    """
    Geodesic distance (km) from the given point to the nearest feature in
    geo.coastline.  Returns None when the table does not exist or is empty.
    """
    sql = text("""
        SELECT
            ST_Distance(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            ) / 1000.0 AS dist_km
        FROM geo.coastline
        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
        LIMIT 1
    """)
    try:
        row = session.execute(sql, {"lat": lat, "lon": lon}).fetchone()
    except Exception:  # noqa: BLE001 – table absent or schema missing
        return None
    if row is None:
        return None
    return round(float(row.dist_km), 4)


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

    # --- Coastal correction -----------------------------------------------
    # Properties on the seafront have part of their buffer in the ocean, which
    # artificially lowers raw POI counts.  We measure the distance to the
    # nearest coastline and derive the fraction of the 1 km buffer that is on
    # land.  That fraction is used to normalise the density component so that
    # a beachfront property is not penalised relative to an equivalent inland
    # property.  dist_coast_km is also returned as a standalone feature
    # (beach proximity is a market-value premium).
    dist_coast = _dist_coast_km(session, lat, lon)

    # Only run the PostGIS polygonize when the 1 km buffer actually straddles
    # the coastline (i.e. dist_coast < 1 km).  This avoids the per-query
    # ST_Node / ST_Polygonize overhead for the vast majority of inland
    # properties where the land fraction is simply 1.0.
    if dist_coast is not None and dist_coast < 1.0:
        # Buffer overlaps the coast — use OSM-geometry-accurate polygonize.
        land_frac_1km = _land_buffer_fraction_db(session, lat, lon, radius_m=1000.0)
        if land_frac_1km is None:
            # geo.coastline / geo.land missing — fall back to straight formula
            land_frac_1km = _land_buffer_fraction(dist_coast, radius_km=1.0)
    elif dist_coast is not None:
        # Buffer is entirely on one side of the coast (> 1 km away).
        # Could be deep inland OR fully in the ocean — check which.
        land_frac_1km = 1.0 if _is_on_land(session, lat, lon) else 0.0
    else:
        # No coastline data loaded at all — assume land.
        land_frac_1km = 1.0

    # Optional aggregate: simple weighted mix (placeholder formula)
    agg = None
    if by_category:
        n_cat = len(by_category)
        n_type = len(fclasses_1km)
        # Normalise density by the land fraction so ocean-side buffers are not
        # penalised.  land_frac_1km == 1.0 when no coastline table is loaded.
        effective_count_1km = total_1km / land_frac_1km if land_frac_1km > 0 else total_1km
        dens = min(effective_count_1km / 50.0, 1.0)
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
        "dist_coast_km": dist_coast,
        "land_buffer_fraction_1km": round(land_frac_1km, 4),
    }
