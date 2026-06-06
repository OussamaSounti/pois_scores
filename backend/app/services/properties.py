"""Queries for property map data and hierarchical statistics."""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.constants import (
    ACC_KEYS,
    HIERARCHY_UID_FIELDS,
    N_FCLASS_TYPES,
    N_SUPER_CATEGORIES,
    PROPERTIES_MAP_MAX_LIMIT,
)

LEVEL_COLUMNS: dict[str, tuple[str, str]] = {
    "district": ("district_uid", "district_name"),
    "neighbourhood": ("neighbourhood_uid", "neighbour_name"),
    "iris": ("iris_uid", "iris_code"),
    "ilot": ("ilot_uid", "ilot_objectid"),
}


def _build_filter_sql(filters: dict[str, str | None]) -> tuple[str, dict[str, Any]]:
    clauses: list[str] = []
    params: dict[str, Any] = {}
    for key in HIERARCHY_UID_FIELDS:
        value = filters.get(key)
        if value:
            clauses.append(f"p.{key} = :{key}")
            params[key] = value
    if not clauses:
        return "", params
    return " AND " + " AND ".join(clauses), params


def _fixed_k_norm(h: float | None, k_total: int) -> float:
    """H / log2(k_total), clamped to [0, 1]. Penalises low richness and unevenness."""
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
        "dist_coast_km": (
            float(row.dist_coast_km) if row.dist_coast_km is not None else None
        ),
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
    """Return property markers with latest feature payload inside a bounding box."""
    filter_sql, filter_params = _build_filter_sql(
        {
            "district_uid": district_uid,
            "neighbourhood_uid": neighbourhood_uid,
            "iris_uid": iris_uid,
            "ilot_uid": ilot_uid,
        }
    )

    sql = text(
        f"""
        WITH latest_features AS (
            SELECT DISTINCT ON (property_id)
                property_id,
                poi_refreshed_at,
                pipeline_version,
                poi_count_1km,
                poi_count_400m,
                n_categories,
                n_poi_types,
                entropy,
                entropy_fclass,
                aggregate_score,
                acc_bus_stop,
                acc_pharmacy,
                acc_school,
                acc_hospital,
                acc_supermarket,
                acc_bank,
                acc_atm,
                acc_clinic,
                acc_fuel,
                acc_police,
                acc_park,
                acc_doctors,
                acc_taxi,
                by_category,
                nearest_km,
                dist_coast_km,
                land_buffer_fraction_1km,
                transaction_date,
                poi_source
            FROM production.property_features
            ORDER BY property_id, poi_refreshed_at DESC
        )
        SELECT
            p.id,
            p.latitude,
            p.longitude,
            p.transaction_date,
            p.asset_price,
            p.asset_surface,
            p.asset_psqm,
            p.asset_type,
            p.district_uid,
            p.district_name,
            p.neighbourhood_uid,
            p.neighbour_name,
            p.iris_uid,
            p.iris_code,
            p.ilot_uid,
            p.ilot_objectid,
            f.poi_refreshed_at,
            f.pipeline_version,
            f.poi_count_1km,
            f.poi_count_400m,
            f.n_categories,
            f.n_poi_types,
            f.entropy,
            f.entropy_fclass,
            f.aggregate_score,
            f.acc_bus_stop,
            f.acc_pharmacy,
            f.acc_school,
            f.acc_hospital,
            f.acc_supermarket,
            f.acc_bank,
            f.acc_atm,
            f.acc_clinic,
            f.acc_fuel,
            f.acc_police,
            f.acc_park,
            f.acc_doctors,
            f.acc_taxi,
            f.by_category,
            f.nearest_km,
            f.dist_coast_km,
            f.land_buffer_fraction_1km,
            f.transaction_date AS f_transaction_date,
            f.poi_source
        FROM production.properties p
        LEFT JOIN latest_features f ON f.property_id = p.id
        WHERE p.longitude BETWEEN :west AND :east
          AND p.latitude BETWEEN :south AND :north
          {filter_sql}
        ORDER BY p.id
        LIMIT :limit
        """
    )

    params = {
        "west": west,
        "south": south,
        "east": east,
        "north": north,
        "limit": max(1, min(limit, PROPERTIES_MAP_MAX_LIMIT)),
        **filter_params,
    }
    rows = session.execute(sql, params).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "id": row.id,
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "transaction_date": (
                    row.transaction_date.isoformat() if row.transaction_date else None
                ),
                "asset_price": float(row.asset_price) if row.asset_price is not None else None,
                "asset_surface": (
                    float(row.asset_surface) if row.asset_surface is not None else None
                ),
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
        )
    return out


def get_property_detail(session: Session, property_id: int) -> dict[str, Any] | None:
    """Return one property with latest feature payload."""
    sql = text(
        """
        WITH latest_features AS (
            SELECT DISTINCT ON (property_id)
                property_id,
                poi_refreshed_at,
                pipeline_version,
                poi_count_1km,
                poi_count_400m,
                n_categories,
                n_poi_types,
                entropy,
                entropy_fclass,
                aggregate_score,
                acc_bus_stop,
                acc_pharmacy,
                acc_school,
                acc_hospital,
                acc_supermarket,
                acc_bank,
                acc_atm,
                acc_clinic,
                acc_fuel,
                acc_police,
                acc_park,
                acc_doctors,
                acc_taxi,
                by_category,
                nearest_km,
                dist_coast_km,
                land_buffer_fraction_1km,
                transaction_date,
                poi_source
            FROM production.property_features
            ORDER BY property_id, poi_refreshed_at DESC
        )
        SELECT
            p.id,
            p.latitude,
            p.longitude,
            p.transaction_date,
            p.asset_price,
            p.asset_surface,
            p.asset_psqm,
            p.asset_type,
            p.district_uid,
            p.district_name,
            p.neighbourhood_uid,
            p.neighbour_name,
            p.iris_uid,
            p.iris_code,
            p.ilot_uid,
            p.ilot_objectid,
            f.poi_refreshed_at,
            f.pipeline_version,
            f.poi_count_1km,
            f.poi_count_400m,
            f.n_categories,
            f.n_poi_types,
            f.entropy,
            f.entropy_fclass,
            f.aggregate_score,
            f.acc_bus_stop,
            f.acc_pharmacy,
            f.acc_school,
            f.acc_hospital,
            f.acc_supermarket,
            f.acc_bank,
            f.acc_atm,
            f.acc_clinic,
            f.acc_fuel,
            f.acc_police,
            f.acc_park,
            f.acc_doctors,
            f.acc_taxi,
            f.by_category,
            f.nearest_km,
            f.dist_coast_km,
            f.land_buffer_fraction_1km,
            f.transaction_date AS f_transaction_date,
            f.poi_source
        FROM production.properties p
        LEFT JOIN latest_features f ON f.property_id = p.id
        WHERE p.id = :property_id
    """
    )
    row = session.execute(sql, {"property_id": property_id}).fetchone()
    if row is None:
        return None
    return {
        "id": row.id,
        "latitude": float(row.latitude),
        "longitude": float(row.longitude),
        "transaction_date": row.transaction_date.isoformat() if row.transaction_date else None,
        "asset_price": float(row.asset_price) if row.asset_price is not None else None,
        "asset_surface": float(row.asset_surface) if row.asset_surface is not None else None,
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


def get_properties_stats(
    session: Session,
    *,
    level: str,
    district_uid: str | None,
    neighbourhood_uid: str | None,
    iris_uid: str | None,
    ilot_uid: str | None,
) -> list[dict[str, Any]]:
    """Return grouped stats for the requested admin hierarchy level."""
    if level not in LEVEL_COLUMNS:
        raise ValueError("Unsupported level")

    key_col, label_col = LEVEL_COLUMNS[level]
    filter_sql, filter_params = _build_filter_sql(
        {
            "district_uid": district_uid,
            "neighbourhood_uid": neighbourhood_uid,
            "iris_uid": iris_uid,
            "ilot_uid": ilot_uid,
        }
    )

    sql = text(
        f"""
        WITH latest_features AS (
            SELECT DISTINCT ON (property_id)
                property_id,
                poi_count_1km,
                entropy,
                entropy_fclass,
                aggregate_score
            FROM production.property_features
            ORDER BY property_id, poi_refreshed_at DESC
        )
        SELECT
            COALESCE(p.{key_col}, 'unknown') AS group_key,
            COALESCE(p.{label_col}, 'Unknown') AS group_label,
            count(*) AS properties_count,
            avg(f.poi_count_1km) AS avg_poi_count_1km,
            avg(f.entropy) AS avg_entropy,
            avg(f.entropy_fclass) AS avg_entropy_fclass,
            avg(f.aggregate_score) AS avg_aggregate_score
        FROM production.properties p
        LEFT JOIN latest_features f ON f.property_id = p.id
        WHERE 1=1
          {filter_sql}
        GROUP BY group_key, group_label
        ORDER BY properties_count DESC, group_label
        """
    )
    rows = session.execute(sql, filter_params).fetchall()
    return [
        {
            "key": r.group_key,
            "label": r.group_label,
            "properties_count": int(r.properties_count),
            "avg_poi_count_1km": (
                round(float(r.avg_poi_count_1km), 3)
                if r.avg_poi_count_1km is not None
                else None
            ),
            "avg_entropy": round(float(r.avg_entropy), 4) if r.avg_entropy is not None else None,
            "avg_entropy_fclass": (
                round(float(r.avg_entropy_fclass), 4)
                if r.avg_entropy_fclass is not None
                else None
            ),
            "avg_aggregate_score": (
                round(float(r.avg_aggregate_score), 2)
                if r.avg_aggregate_score is not None
                else None
            ),
        }
        for r in rows
    ]
