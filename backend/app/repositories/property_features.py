"""Property features write queries and pending-property selection."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.constants import POI_SOURCE_HISTORY, PROPERTY_FEATURE_COLUMNS
from app.core.tables import T_PROPERTIES, T_PROPERTY_FEATURES


class PropertyFeaturesRepository:
    """Reads and writes production.property_features."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def max_poi_refreshed_at(self) -> datetime | None:
        return self._session.execute(
            text(f"SELECT max(poi_refreshed_at) FROM {T_PROPERTY_FEATURES}")
        ).scalar()

    def count_pending_for_refresh(self, refresh_ts: datetime) -> int:
        sql = text(f"""
            SELECT count(*)
            FROM {T_PROPERTIES} p
            WHERE NOT EXISTS (
                SELECT 1
                FROM {T_PROPERTY_FEATURES} f
                WHERE f.transaction_id = p.transaction_id
                  AND f.poi_refreshed_at = :refresh_ts
            )
        """)
        return int(
            self._session.execute(sql, {"refresh_ts": refresh_ts}).scalar() or 0
        )

    def count_pending_weekly(self, current_poi: datetime) -> int:
        sql = text(f"""
            SELECT count(*)
            FROM {T_PROPERTIES} p
            WHERE NOT EXISTS (
                SELECT 1 FROM {T_PROPERTY_FEATURES} f
                WHERE f.transaction_id = p.transaction_id
                  AND f.poi_refreshed_at = :current_poi
                  AND f.dist_coast_km IS NOT NULL
                  AND f.land_buffer_fraction_1km IS NOT NULL
            )
        """)
        return int(
            self._session.execute(sql, {"current_poi": current_poi}).scalar() or 0
        )

    def fetch_pending_weekly(
        self,
        current_poi: datetime,
        limit: int,
        after_transaction_id: int = 0,
    ) -> list[tuple[int, float, float]]:
        sql = text(f"""
            SELECT p.transaction_id, p.latitude, p.longitude
            FROM {T_PROPERTIES} p
            WHERE p.transaction_id > :after_transaction_id
              AND NOT EXISTS (
                SELECT 1 FROM {T_PROPERTY_FEATURES} f
                WHERE f.transaction_id = p.transaction_id
                  AND f.poi_refreshed_at = :current_poi
                  AND f.dist_coast_km IS NOT NULL
                  AND f.land_buffer_fraction_1km IS NOT NULL
            )
            ORDER BY p.transaction_id
            LIMIT :limit
        """)
        rows = self._session.execute(
            sql,
            {
                "current_poi": current_poi,
                "limit": limit,
                "after_transaction_id": after_transaction_id,
            },
        ).fetchall()
        return [(r.transaction_id, float(r.latitude), float(r.longitude)) for r in rows]

    def count_pending_historical(self) -> int:
        sql = text(f"""
            SELECT count(*)
            FROM {T_PROPERTIES} p
            WHERE p.transaction_date IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM {T_PROPERTY_FEATURES} f
                  WHERE f.transaction_id = p.transaction_id
                    AND f.poi_refreshed_at = p.transaction_date::timestamptz
                    AND f.poi_source = :poi_source
                    AND f.dist_coast_km IS NOT NULL
                    AND f.land_buffer_fraction_1km IS NOT NULL
              )
        """)
        return int(
            self._session.execute(sql, {"poi_source": POI_SOURCE_HISTORY}).scalar() or 0
        )

    def fetch_pending_historical(
        self,
        limit: int,
        after_transaction_id: int = 0,
    ) -> list[tuple[int, float, float, date]]:
        sql = text(f"""
            SELECT p.transaction_id, p.latitude, p.longitude, p.transaction_date
            FROM {T_PROPERTIES} p
            WHERE p.transaction_id > :after_transaction_id
              AND p.transaction_date IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM {T_PROPERTY_FEATURES} f
                  WHERE f.transaction_id = p.transaction_id
                    AND f.poi_refreshed_at = p.transaction_date::timestamptz
                    AND f.poi_source = :poi_source
                    AND f.dist_coast_km IS NOT NULL
                    AND f.land_buffer_fraction_1km IS NOT NULL
              )
            ORDER BY p.transaction_id
            LIMIT :limit
        """)
        rows = self._session.execute(
            sql,
            {
                "limit": limit,
                "after_transaction_id": after_transaction_id,
                "poi_source": POI_SOURCE_HISTORY,
            },
        ).fetchall()
        return [
            (r.transaction_id, float(r.latitude), float(r.longitude), r.transaction_date)
            for r in rows
        ]

    def upsert_rows(self, rows: list[dict[str, Any]]) -> None:
        """Insert or update a batch of property_features rows. Commits on completion."""
        if not rows:
            return
        cols = list(PROPERTY_FEATURE_COLUMNS)
        placeholders = ", ".join(f":{c}" for c in cols)
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "transaction_id")
        sql = text(
            f"""
            INSERT INTO {T_PROPERTY_FEATURES} ({", ".join(cols)})
            VALUES ({placeholders})
            ON CONFLICT (transaction_id) DO UPDATE SET {updates}
            """
        )
        payloads = []
        for row in rows:
            payload = {c: row.get(c) for c in cols}
            payload["by_category"] = json.dumps(row["by_category"])
            payload["nearest_km"] = json.dumps(row["nearest_km"])
            payloads.append(payload)
        self._session.execute(sql, payloads)
        self._session.commit()
