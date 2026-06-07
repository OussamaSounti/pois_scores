"""POI business logic — delegates data access to :class:`PoiRepository`.

Two source tables, both produced by an upstream pipeline:

- ``active.production_pois_current``: flat snapshot.
- ``history.production_poi_history``: SCD2 with ``is_canonical`` filter.

The taxonomy ``super_category`` is pre-resolved upstream; this module never
re-derives it from raw tags.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.poi import PoiRepository, PoiRow

__all__ = [
    "PoiRow",
    "get_pois_with_distance",
    "get_pois_with_distance_at_date",
    "query_pois_combined",
    "query_pois_combined_at_date",
    "query_pois_radius",
    "query_pois_radius_at_date",
    "_nearest_km_by_category",
    "_nearest_km_by_category_at_date",
]


def query_pois_radius(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float,
) -> list[PoiRow]:
    return PoiRepository(session).query_radius(lat, lon, radius_m)


def get_pois_with_distance(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float = 1000.0,
) -> list[dict[str, Any]]:
    return PoiRepository(session).query_with_distance(lat, lon, radius_m)


def _nearest_km_by_category(
    session: Session,
    lat: float,
    lon: float,
    max_radius_m: float = 25_000,
) -> dict[str, float]:
    return PoiRepository(session).nearest_km_by_category(lat, lon, max_radius_m)


def query_pois_radius_at_date(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float,
    as_of: date | datetime,
) -> list[PoiRow]:
    return PoiRepository(session).query_radius_at_date(lat, lon, radius_m, as_of)


def get_pois_with_distance_at_date(
    session: Session,
    lat: float,
    lon: float,
    radius_m: float = 1000.0,
    as_of: date | datetime | None = None,
) -> list[dict[str, Any]]:
    return PoiRepository(session).query_with_distance_at_date(lat, lon, radius_m, as_of)


def _nearest_km_by_category_at_date(
    session: Session,
    lat: float,
    lon: float,
    as_of: date | datetime,
    max_radius_m: float = 25_000,
) -> dict[str, float]:
    return PoiRepository(session).nearest_km_by_category_at_date(
        lat, lon, as_of, max_radius_m
    )


def query_pois_combined(
    session: Session,
    lat: float,
    lon: float,
) -> tuple[list[PoiRow], list[PoiRow], dict[str, float]]:
    """1km POIs, 400m POIs, and nearest-by-category in one DB round-trip."""
    return PoiRepository(session).query_pois_and_nearest_current(lat, lon)


def query_pois_combined_at_date(
    session: Session,
    lat: float,
    lon: float,
    as_of: date | datetime,
) -> tuple[list[PoiRow], list[PoiRow], dict[str, float]]:
    """1km POIs, 400m POIs, and nearest-by-category at *as_of* in one round-trip."""
    return PoiRepository(session).query_pois_and_nearest_at_date(lat, lon, as_of)
