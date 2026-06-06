"""Pure score-math service.

Two entry points:

- :func:`compute_scores` — score against the current POI snapshot
  (``active.production_pois_current``).
- :func:`compute_scores_at_date` — score against the SCD2 history table
  (``history.production_poi_history``) at a specific date.

Both consume :class:`PoiRow` objects whose ``super_category`` field is
already pre-resolved by the upstream pipeline; this module never re-derives
the taxonomy from raw OSM tags.

Used by both the on-demand ``/api/v1/scores`` HTTP endpoint AND the two
``feature_pipeline`` flows.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import ACCESSIBILITY_KEY_TYPES, N_FCLASS_TYPES, N_SUPER_CATEGORIES
from app.core.spatial import _dist_coast_km, _entropy, land_fraction_at_point
from app.features.pois.service import (
    PoiRow,
    _nearest_km_by_category,
    _nearest_km_by_category_at_date,
    query_pois_radius,
    query_pois_radius_at_date,
)


def _aggregate_components(
    pois_1km: list[PoiRow],
    pois_400m: list[PoiRow],
    nearest_km: dict[str, float],
    land_frac_1km: float,
) -> dict[str, Any]:
    """Compute the score payload from already-fetched POI rows.

    Shared by current and historical compute paths so the math is byte-identical.
    """
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
    n_cat = len(by_category)
    n_type = len(fclasses_1km)
    entropy_norm = min(1.0, round(entropy / math.log2(N_SUPER_CATEGORIES), 4))
    entropy_fclass_norm = min(1.0, round(entropy_fclass / math.log2(N_FCLASS_TYPES), 4))

    fclass_in_400m = {p.fclass for p in pois_400m}
    accessibility_400m = {k: k in fclass_in_400m for k in ACCESSIBILITY_KEY_TYPES}

    agg: float | None = None
    if by_category:
        # Normalise density by land fraction so seafront properties are not
        # penalised by ocean overlap. land_frac_1km == 1.0 inland.
        effective_count_1km = total_1km / land_frac_1km if land_frac_1km > 0 else total_1km
        dens = min(effective_count_1km / 50.0, 1.0)
        div = min((n_cat / 10.0 + n_type / 20.0) / 2, 1.0)
        acc = sum(accessibility_400m.values()) / max(len(ACCESSIBILITY_KEY_TYPES), 1)
        agg = round(100.0 * (0.3 * dens + 0.3 * div + 0.4 * acc), 1)

    return {
        "poi_count_1km": total_1km,
        "poi_count_400m": len(pois_400m),
        "n_categories": n_cat,
        "n_poi_types": n_type,
        "entropy": round(entropy, 4),
        "entropy_fclass": round(entropy_fclass, 4),
        "entropy_norm": entropy_norm,
        "entropy_fclass_norm": entropy_fclass_norm,
        "by_category": dict(by_category),
        "accessibility_400m": accessibility_400m,
        "nearest_km": nearest_km,
        "aggregate_score": agg,
        "land_buffer_fraction_1km": round(land_frac_1km, 4),
    }


def compute_scores(session: Session, lat: float, lon: float) -> dict[str, Any]:
    """Score (lat, lon) against ``active.production_pois_current``."""
    pois_1km = query_pois_radius(session, lat, lon, 1000.0)
    pois_400m = query_pois_radius(session, lat, lon, 400.0)
    nearest_km = _nearest_km_by_category(session, lat, lon)
    dist_coast = _dist_coast_km(session, lat, lon)
    land_frac = land_fraction_at_point(session, lat, lon, dist_coast)
    payload = _aggregate_components(pois_1km, pois_400m, nearest_km, land_frac)
    payload["dist_coast_km"] = dist_coast
    return payload


def compute_scores_at_date(
    session: Session,
    lat: float,
    lon: float,
    as_of: date | datetime,
) -> dict[str, Any]:
    """Score (lat, lon) against ``history.production_poi_history`` at *as_of*.

    Coastal features (``dist_coast_km``, ``land_buffer_fraction_1km``) come
    from the static ``geo.coastline`` / ``geo.land`` reference tables and are
    therefore identical to the current-snapshot path.
    """
    pois_1km = query_pois_radius_at_date(session, lat, lon, 1000.0, as_of)
    pois_400m = query_pois_radius_at_date(session, lat, lon, 400.0, as_of)
    nearest_km = _nearest_km_by_category_at_date(session, lat, lon, as_of)
    dist_coast = _dist_coast_km(session, lat, lon)
    land_frac = land_fraction_at_point(session, lat, lon, dist_coast)
    payload = _aggregate_components(pois_1km, pois_400m, nearest_km, land_frac)
    payload["dist_coast_km"] = dist_coast
    payload["poi_source"] = "history"
    return payload
