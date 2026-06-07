"""Audit table queries for pipeline orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.tables import T_AUDIT_PIPELINE_RUNS


class AuditRepository:
    """Reads from active.audit_pipeline_runs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def table_exists(self) -> bool:
        return bool(
            self._session.execute(
                text(f"SELECT to_regclass('{T_AUDIT_PIPELINE_RUNS}') IS NOT NULL")
            ).scalar()
        )

    def latest_run_timestamp(self) -> datetime | None:
        row = self._session.execute(
            text(f"SELECT max(run_timestamp) FROM {T_AUDIT_PIPELINE_RUNS}")
        ).scalar()
        if row is None:
            return None
        return row if row.tzinfo else row.replace(tzinfo=timezone.utc)

    def current_poi_ts(self) -> datetime:
        """Latest external POI refresh timestamp, or now() when the table is empty."""
        ts = self.latest_run_timestamp()
        if ts is not None:
            return ts
        return datetime.now(timezone.utc)
