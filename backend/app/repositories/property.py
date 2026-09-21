"""Property hierarchy statistics read queries."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import HIERARCHY_UID_FIELDS
from app.core.tables import T_PROPERTIES, T_PROPERTY_FEATURES


def _transactions_table() -> str | None:
    table = get_settings().transactions_table.strip()
    return table or None


def _transactions_join() -> str:
    table = _transactions_table()
    if not table:
        return ""
    return f"LEFT JOIN {table} t ON t.transaction_id = p.transaction_id"


def _filter_prefix() -> str:
    return "t" if _transactions_table() else "p"


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
    """Aggregated statistics over production.properties joined to property_features."""

    def __init__(self, session: Session) -> None:
        self._session = session

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
