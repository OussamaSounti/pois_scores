"""Pure spatial primitives shared by features.

Three categories of helpers live here:

1. Stateless math: ``_haversine_km``, ``_entropy``, ``_land_buffer_fraction``.
2. Reference-data SQL against ``geo.coastline`` / ``geo.land`` (static datasets,
   not the external POI contract): ``_dist_coast_km``, ``_is_on_land``,
   ``_land_buffer_fraction_db``.
3. Date/time normalisation for SCD2 history queries: ``_as_of_ts``.

Anything querying ``active.production_pois_current`` or
``history.production_poi_history`` belongs in ``app.features.pois.service``.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Stateless math
# ---------------------------------------------------------------------------


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
        ocean_cap_area = r^2 * arccos(d/r) - d * sqrt(r^2 - d^2)
        land_fraction  = 1 - ocean_cap_area / (pi * r^2)

    Fallback approximation only; ``_land_buffer_fraction_db`` computes the
    true intersection via PostGIS land polygons for non-linear coastlines.

    Special cases:
      - dist_coast_km >= radius_km  -> 1.0  (buffer fully on land)
      - dist_coast_km == 0          -> 0.5  (buffer half on land, half in ocean)
    """
    if dist_coast_km >= radius_km:
        return 1.0
    d = max(dist_coast_km, 0.0)
    ratio = d / radius_km
    ocean_fraction = (math.acos(ratio) - ratio * math.sqrt(1.0 - ratio**2)) / math.pi
    return max(0.0, min(1.0, 1.0 - ocean_fraction))


# ---------------------------------------------------------------------------
# Reference-data SQL (geo.coastline / geo.land — static datasets)
# ---------------------------------------------------------------------------


def _dist_coast_km(session: Session, lat: float, lon: float) -> float | None:
    """Geodesic distance (km) from (lat, lon) to nearest feature in ``geo.coastline``.

    Returns None when the table is missing or empty.
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
    except Exception:  # noqa: BLE001
        session.rollback()
        return None
    if row is None:
        return None
    return round(float(row.dist_km), 4)


def _is_on_land(session: Session, lat: float, lon: float) -> bool:
    """True if (lat, lon) is inside ``geo.land`` (i.e. on land, not in ocean).

    Used as a fast path for points more than 1 km from the coastline where the
    answer is binary. Defaults to True (land) when the table is absent.
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
        session.rollback()
        return True
    return bool(row.on_land) if row is not None else True


def _land_buffer_fraction_db(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float = 1000.0,
) -> float | None:
    """Fraction of a circular buffer that lies on land, computed via PostGIS.

    Algorithm:
      1. Union all nearby OSM coastline rows into one blade geometry.
      2. ``ST_Split(buffer_circle, blade)`` -> 1 or 2 polygon pieces.
      3. Find the "center piece" (the one containing the query point).
      4. Ask ``geo.land`` whether the query point is on land.
         - Yes -> land area = area of center piece.
         - No  -> land area = buffer area - area of center piece.
      5. ``land_fraction = land_area / buffer_area``.

    Returns None when ``geo.coastline`` is missing or the query fails.
    """
    sql = text("""
        WITH
        pt  AS (SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS geom),
        buf AS (SELECT ST_Buffer(pt.geom::geography, :radius_m)::geometry AS geom FROM pt),
        coast AS (
            SELECT ST_Union(c.geom) AS geom
            FROM   geo.coastline c, pt
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
                SELECT 1 FROM geo.land l
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
        row = session.execute(sql, {"lat": lat, "lon": lon, "radius_m": radius_m}).fetchone()
    except Exception:  # noqa: BLE001
        session.rollback()
        return None
    if row is None or row.land_fraction is None:
        return None
    return round(max(0.0, min(1.0, float(row.land_fraction))), 4)


# ---------------------------------------------------------------------------
# Temporal helpers (history.production_poi_history is SCD2)
# ---------------------------------------------------------------------------


def _as_of_ts(as_of: date | datetime) -> datetime:
    """Normalise a date or datetime to a timezone-aware datetime for SQL binding."""
    if isinstance(as_of, datetime):
        return as_of if as_of.tzinfo else as_of.replace(tzinfo=timezone.utc)
    return datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc)


def land_fraction_at_point(
    session: Session,
    lat: float,
    lon: float,
    dist_coast_km: float | None,
) -> float:
    """Compose the coastal correction policy used by both score flows.

    - If ``dist_coast_km`` is None (no coastline data) -> assume 1.0 (land).
    - If ``dist_coast_km < 1.0`` -> use PostGIS polygonize (accurate).
    - Otherwise binary on-land check via ``geo.land``.
    """
    if dist_coast_km is None:
        return 1.0
    if dist_coast_km < 1.0:
        frac = _land_buffer_fraction_db(session, lat, lon, radius_m=1000.0)
        if frac is None:
            frac = _land_buffer_fraction(dist_coast_km, radius_km=1.0)
        return frac
    return 1.0 if _is_on_land(session, lat, lon) else 0.0
