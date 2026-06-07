"""Property and property_features read queries."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import HIERARCHY_UID_FIELDS
from app.core.tables import T_PROPERTIES, T_PROPERTY_FEATURES

# Dashboard attributes read from the external transactions table when configured.
_TRANSACTION_ATTR_COLUMNS: tuple[str, ...] = (
    "asset_price",
    "asset_surface",
    "asset_psqm",
    "asset_type",
    "district_uid",
    "district_name",
    "neighbourhood_uid",
    "neighbour_name",
    "iris_uid",
    "iris_code",
    "ilot_uid",
    "ilot_objectid",
)


def _transactions_table() -> str | None:
    table = get_settings().transactions_table.strip()
    return table or None


def _attr_projection(prefix: str | None) -> str:
    """SQL fragment for optional transaction attributes."""
    if prefix:
        return ",\n        ".join(f"{prefix}.{col}" for col in _TRANSACTION_ATTR_COLUMNS)
    return ",\n        ".join(f"NULL AS {col}" for col in _TRANSACTION_ATTR_COLUMNS)


def _transactions_join() -> str:
    table = _transactions_table()
    if not table:
        return ""
    return f"LEFT JOIN {table} t ON t.transaction_id = p.transaction_id"


def _filter_prefix() -> str:
    return "t" if _transactions_table() else "p"


_LATEST_FEATURES_CTE = f"""
    WITH latest_features AS (
        SELECT DISTINCT ON (transaction_id)
            transaction_id,
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
        FROM {T_PROPERTY_FEATURES}
        ORDER BY transaction_id, poi_refreshed_at DESC
    )
"""


def _property_projection() -> str:
    attr_prefix = "t" if _transactions_table() else None
    return f"""
    SELECT
        p.transaction_id,
        p.latitude,
        p.longitude,
        p.transaction_date,
        {_attr_projection(attr_prefix)},
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
    FROM {T_PROPERTIES} p
    {_transactions_join()}
    LEFT JOIN latest_features f ON f.transaction_id = p.transaction_id
"""


def _build_filter_sql(filters: dict[str, str | None]) -> tuple[str, dict[str, Any]]:
    prefix = _filter_prefix()
    clauses: list[str] = []
    params: dict[str, Any] = {}
    for key in HIERARCHY_UID_FIELDS:
        value = filters.get(key)
        if value:
            clauses.append(f"{prefix}.{key} = :{key}")
            params[key] = value
    if not clauses:
        return "", params
    return " AND " + " AND ".join(clauses), params


class PropertyRepository:
    """Reads production.properties joined to property_features and optional source transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_map(
        self,
        *,
        west: float,
        south: float,
        east: float,
        north: float,
        limit: int,
        filters: dict[str, str | None],
    ) -> list[Any]:
        filter_sql, filter_params = _build_filter_sql(filters)
        sql = text(
            f"""
            {_LATEST_FEATURES_CTE}
            {_property_projection()}
            WHERE p.longitude BETWEEN :west AND :east
              AND p.latitude BETWEEN :south AND :north
              {filter_sql}
            ORDER BY p.transaction_id
            LIMIT :limit
            """
        )
        params = {
            "west": west,
            "south": south,
            "east": east,
            "north": north,
            "limit": limit,
            **filter_params,
        }
        return self._session.execute(sql, params).fetchall()

    def get_by_id(self, transaction_id: int) -> Any | None:
        sql = text(
            f"""
            {_LATEST_FEATURES_CTE}
            {_property_projection()}
            WHERE p.transaction_id = :transaction_id
            """
        )
        return self._session.execute(sql, {"transaction_id": transaction_id}).fetchone()

    def stats_by_level(
        self,
        *,
        key_col: str,
        label_col: str,
        filters: dict[str, str | None],
    ) -> list[Any]:
        filter_sql, filter_params = _build_filter_sql(filters)
        prefix = _filter_prefix()
        sql = text(
            f"""
            WITH latest_features AS (
                SELECT DISTINCT ON (transaction_id)
                    transaction_id,
                    poi_count_1km,
                    entropy,
                    entropy_fclass,
                    aggregate_score
                FROM {T_PROPERTY_FEATURES}
                ORDER BY transaction_id, poi_refreshed_at DESC
            )
            SELECT
                COALESCE({prefix}.{key_col}, 'unknown') AS group_key,
                COALESCE({prefix}.{label_col}, 'Unknown') AS group_label,
                count(*) AS properties_count,
                avg(f.poi_count_1km) AS avg_poi_count_1km,
                avg(f.entropy) AS avg_entropy,
                avg(f.entropy_fclass) AS avg_entropy_fclass,
                avg(f.aggregate_score) AS avg_aggregate_score
            FROM {T_PROPERTIES} p
            {_transactions_join()}
            LEFT JOIN latest_features f ON f.transaction_id = p.transaction_id
            WHERE 1=1
              {filter_sql}
            GROUP BY group_key, group_label
            ORDER BY properties_count DESC, group_label
            """
        )
        return self._session.execute(sql, filter_params).fetchall()
