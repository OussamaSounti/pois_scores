"""Pure spatial primitives shared by features.

Three categories of helpers live here:

1. Stateless math: ``_haversine_km``, ``_entropy``, ``_land_buffer_fraction``.
2. Reference-data lookups via :class:`GeoReferenceRepository` (static datasets).
3. Date/time normalisation for SCD2 history queries: ``_as_of_ts``.

POI table queries belong in :class:`app.repositories.poi.PoiRepository`.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.repositories.geo import GeoReferenceRepository

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

    Fallback approximation only; ``_land_buffer_fraction_db`` computes the
    true intersection via PostGIS land polygons for non-linear coastlines.
    """
    if dist_coast_km >= radius_km:
        return 1.0
    d = max(dist_coast_km, 0.0)
    ratio = d / radius_km
    ocean_fraction = (math.acos(ratio) - ratio * math.sqrt(1.0 - ratio**2)) / math.pi
    return max(0.0, min(1.0, 1.0 - ocean_fraction))


# ---------------------------------------------------------------------------
# Reference-data lookups (geo.coastline / geo.land — static datasets)
# ---------------------------------------------------------------------------


def _dist_coast_km(session: Session, lat: float, lon: float) -> float | None:
    return GeoReferenceRepository(session).dist_coast_km(lat, lon)


def _is_on_land(session: Session, lat: float, lon: float) -> bool:
    return GeoReferenceRepository(session).is_on_land(lat, lon)


def _land_buffer_fraction_db(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float = 1000.0,
) -> float | None:
    return GeoReferenceRepository(session).land_buffer_fraction(lat, lon, radius_m)


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
    """Compose the coastal correction policy used by both score flows."""
    if dist_coast_km is None:
        return 1.0
    if dist_coast_km < 1.0:
        frac = _land_buffer_fraction_db(session, lat, lon, radius_m=1000.0)
        if frac is None:
            frac = _land_buffer_fraction(dist_coast_km, radius_km=1.0)
        return frac
    return 1.0 if _is_on_land(session, lat, lon) else 0.0
