"""Property map data and hierarchical statistics — business logic only."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import (
    ACC_KEYS,
    N_FCLASS_TYPES,
    N_SUPER_CATEGORIES,
    PROPERTIES_MAP_MAX_LIMIT,
)
from app.repositories.property import PropertyRepository

LEVEL_COLUMNS: dict[str, tuple[str, str]] = {
    "district": ("district_uid", "district_name"),
    "neighbourhood": ("neighbourhood_uid", "neighbour_name"),
    "iris": ("iris_uid", "iris_code"),
    "ilot": ("ilot_uid", "ilot_objectid"),
}


def _fixed_k_norm(h: float | None, k_total: int) -> float:
    if h is None:
        return 0.0
    return min(1.0, round(h / math.log2(k_total), 4))


def _score_payload_from_row(row: Any) -> dict[str, Any]:
    h = float(row.entropy) if row.entropy is not None else None
    hf = float(row.entropy_fclass) if row.entropy_fclass is not None else None
    n_cat: int | None = row.n_categories
    n_type: int | None = row.n_poi_types
    return {
        "poi_refreshed_at": row.poi_refreshed_at.isoformat() if row.poi_refreshed_at else None,
        "pipeline_version": row.pipeline_version,
        "poi_count_1km": row.poi_count_1km,
        "poi_count_400m": row.poi_count_400m,
        "n_categories": n_cat,
        "n_poi_types": n_type,
        "entropy": h,
        "entropy_fclass": hf,
        "entropy_norm": _fixed_k_norm(h, N_SUPER_CATEGORIES),
        "entropy_fclass_norm": _fixed_k_norm(hf, N_FCLASS_TYPES),
        "aggregate_score": (
            float(row.aggregate_score) if row.aggregate_score is not None else None
        ),
        "accessibility_400m": {
            k: bool(getattr(row, f"acc_{k}")) if getattr(row, f"acc_{k}") is not None else False
            for k in ACC_KEYS
        },
        "by_category": dict(row.by_category or {}),
        "nearest_km": dict(row.nearest_km or {}),
        "dist_coast_km": (float(row.dist_coast_km) if row.dist_coast_km is not None else None),
        "land_buffer_fraction_1km": (
            float(row.land_buffer_fraction_1km)
            if row.land_buffer_fraction_1km is not None
            else None
        ),
        "transaction_date": (
            row.f_transaction_date.isoformat() if row.f_transaction_date else None
        ),
        "poi_source": row.poi_source,
    }


def _row_to_item(row: Any) -> dict[str, Any]:
    return {
        "id": row.transaction_id,
        "transaction_id": row.transaction_id,
        "latitude": float(row.latitude),
        "longitude": float(row.longitude),
        "transaction_date": (row.transaction_date.isoformat() if row.transaction_date else None),
        "asset_price": float(row.asset_price) if row.asset_price is not None else None,
        "asset_surface": (float(row.asset_surface) if row.asset_surface is not None else None),
        "asset_psqm": float(row.asset_psqm) if row.asset_psqm is not None else None,
        "asset_type": row.asset_type,
        "district_uid": row.district_uid,
        "district_name": row.district_name,
        "neighbourhood_uid": row.neighbourhood_uid,
        "neighbour_name": row.neighbour_name,
        "iris_uid": row.iris_uid,
        "iris_code": row.iris_code,
        "ilot_uid": row.ilot_uid,
        "ilot_objectid": row.ilot_objectid,
        "scores": _score_payload_from_row(row),
    }


def list_properties_for_map(
    session: Session,
    *,
    west: float,
    south: float,
    east: float,
    north: float,
    limit: int,
    district_uid: str | None,
    neighbourhood_uid: str | None,
    iris_uid: str | None,
    ilot_uid: str | None,
) -> list[dict[str, Any]]:
    repo = PropertyRepository(session)
    rows = repo.list_for_map(
        west=west,
        south=south,
        east=east,
        north=north,
        limit=max(1, min(limit, PROPERTIES_MAP_MAX_LIMIT)),
        filters={
            "district_uid": district_uid,
            "neighbourhood_uid": neighbourhood_uid,
            "iris_uid": iris_uid,
            "ilot_uid": ilot_uid,
        },
    )
    return [_row_to_item(row) for row in rows]


def get_property_detail(session: Session, property_id: int) -> dict[str, Any] | None:
    row = PropertyRepository(session).get_by_id(property_id)
    if row is None:
        return None
    return _row_to_item(row)


def get_properties_stats(
    session: Session,
    *,
    level: str,
    district_uid: str | None,
    neighbourhood_uid: str | None,
    iris_uid: str | None,
    ilot_uid: str | None,
) -> list[dict[str, Any]]:
    if level not in LEVEL_COLUMNS:
        raise ValueError("Unsupported level")

    key_col, label_col = LEVEL_COLUMNS[level]
    rows = PropertyRepository(session).stats_by_level(
        key_col=key_col,
        label_col=label_col,
        filters={
            "district_uid": district_uid,
            "neighbourhood_uid": neighbourhood_uid,
            "iris_uid": iris_uid,
            "ilot_uid": ilot_uid,
        },
    )
    return [
        {
            "key": r.group_key,
            "label": r.group_label,
            "properties_count": int(r.properties_count),
            "avg_poi_count_1km": (
                round(float(r.avg_poi_count_1km), 3) if r.avg_poi_count_1km is not None else None
            ),
            "avg_entropy": round(float(r.avg_entropy), 4) if r.avg_entropy is not None else None,
            "avg_entropy_fclass": (
                round(float(r.avg_entropy_fclass), 4) if r.avg_entropy_fclass is not None else None
            ),
            "avg_aggregate_score": (
                round(float(r.avg_aggregate_score), 2)
                if r.avg_aggregate_score is not None
                else None
            ),
        }
        for r in rows
    ]
