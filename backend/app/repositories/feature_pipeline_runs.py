"""Feature pipeline run ledger — production.feature_pipeline_runs."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import RUN_STATUS_RUNNING
from app.core.tables import T_FEATURE_PIPELINE_FAILURES, T_FEATURE_PIPELINE_RUNS

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_RUN_LEDGER_SQL = _PROJECT_ROOT / "scripts" / "schema" / "feature_pipeline_runs.sql"


class FeaturePipelineRunRepository:
    """Reads and writes production.feature_pipeline_runs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def ensure_tables() -> None:
        """Create run-ledger tables when missing (idempotent)."""
        if not _RUN_LEDGER_SQL.is_file():
            raise FileNotFoundError(f"Run ledger SQL not found: {_RUN_LEDGER_SQL}")
        ddl = _RUN_LEDGER_SQL.read_text(encoding="utf-8")
        settings = get_settings()
        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(ddl)
        finally:
            conn.close()

    def table_exists(self) -> bool:
        return bool(
            self._session.execute(
                text(f"SELECT to_regclass('{T_FEATURE_PIPELINE_RUNS}') IS NOT NULL")
            ).scalar()
        )

    def start_run(
        self,
        *,
        run_id: uuid.UUID,
        flow_name: str,
        pipeline_version: str,
        triggered_by: str,
        config: dict[str, Any],
        poi_refreshed_at: datetime | None = None,
        poi_source: str | None = None,
        prefect_run_id: str | None = None,
        pending_before: int | None = None,
    ) -> None:
        sql = text(f"""
            INSERT INTO {T_FEATURE_PIPELINE_RUNS} (
                run_id, flow_name, status, pipeline_version,
                poi_refreshed_at, poi_source, config, pending_before,
                prefect_run_id, triggered_by
            ) VALUES (
                :run_id, :flow_name, :status, :pipeline_version,
                :poi_refreshed_at, :poi_source, CAST(:config AS jsonb), :pending_before,
                :prefect_run_id, :triggered_by
            )
        """)
        self._session.execute(
            sql,
            {
                "run_id": str(run_id),
                "flow_name": flow_name,
                "status": RUN_STATUS_RUNNING,
                "pipeline_version": pipeline_version,
                "poi_refreshed_at": poi_refreshed_at,
                "poi_source": poi_source,
                "config": json.dumps(config),
                "pending_before": pending_before,
                "prefect_run_id": prefect_run_id,
                "triggered_by": triggered_by,
            },
        )
        self._session.commit()

    def update_progress(
        self,
        run_id: uuid.UUID,
        *,
        processed: int,
        skipped: int,
        failed: int,
        pending_after: int | None = None,
    ) -> None:
        sql = text(f"""
            UPDATE {T_FEATURE_PIPELINE_RUNS}
            SET processed = :processed,
                skipped = :skipped,
                failed = :failed,
                pending_after = COALESCE(:pending_after, pending_after)
            WHERE run_id = :run_id
        """)
        self._session.execute(
            sql,
            {
                "run_id": str(run_id),
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
                "pending_after": pending_after,
            },
        )
        self._session.commit()

    def finish_run(
        self,
        run_id: uuid.UUID,
        *,
        status: str,
        processed: int,
        skipped: int,
        failed: int,
        pending_after: int | None = None,
        skip_reason: str | None = None,
        error_summary: str | None = None,
        started_at: datetime,
    ) -> None:
        finished_at = datetime.now(timezone.utc)
        duration = (finished_at - started_at).total_seconds()
        sql = text(f"""
            UPDATE {T_FEATURE_PIPELINE_RUNS}
            SET status = :status,
                finished_at = :finished_at,
                duration_seconds = :duration_seconds,
                processed = :processed,
                skipped = :skipped,
                failed = :failed,
                pending_after = :pending_after,
                skip_reason = :skip_reason,
                error_summary = :error_summary
            WHERE run_id = :run_id
        """)
        self._session.execute(
            sql,
            {
                "run_id": str(run_id),
                "status": status,
                "finished_at": finished_at,
                "duration_seconds": duration,
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
                "pending_after": pending_after,
                "skip_reason": skip_reason,
                "error_summary": _truncate(error_summary),
            },
        )
        self._session.commit()

    def record_failures(
        self,
        run_id: uuid.UUID,
        flow_name: str,
        failures: list[tuple[int, str]],
    ) -> None:
        if not failures:
            return
        sql = text(f"""
            INSERT INTO {T_FEATURE_PIPELINE_FAILURES}
                (run_id, transaction_id, flow_name, error_message)
            VALUES
                (:run_id, :transaction_id, :flow_name, :error_message)
        """)
        payloads = [
            {
                "run_id": str(run_id),
                "transaction_id": transaction_id,
                "flow_name": flow_name,
                "error_message": _truncate(message),
            }
            for transaction_id, message in failures
        ]
        self._session.execute(sql, payloads)
        self._session.commit()


def _truncate(value: str | None, limit: int = 2000) -> str | None:
    if value is None:
        return None
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."
