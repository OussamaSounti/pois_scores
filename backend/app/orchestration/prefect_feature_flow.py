"""Prefect flow for automated monthly feature recompute."""

from __future__ import annotations

from datetime import datetime

from prefect import flow, get_run_logger, task
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.constants import CHUNK_SIZE
from app.db import get_session_factory
from app.pipeline.run import run_pipeline


def _scalar(session: Session, sql: str, params: dict | None = None):
    return session.execute(text(sql), params or {}).scalar()


@task
def get_latest_external_refresh() -> datetime | None:
    """
    Latest POI refresh timestamp produced by the external pipeline.

    Source: active.audit_pipeline_runs.run_timestamp.
    Returns None if the audit table is unavailable or has no rows.
    """
    session = get_session_factory()()
    try:
        table_exists = _scalar(
            session,
            "SELECT to_regclass('active.audit_pipeline_runs') IS NOT NULL",
        )
        if not table_exists:
            return None
        return _scalar(
            session,
            "SELECT max(run_timestamp) FROM active.audit_pipeline_runs",
        )
    finally:
        session.close()


@task
def get_latest_processed_refresh() -> datetime | None:
    """Latest POI refresh timestamp already processed into property_features."""
    session = get_session_factory()()
    try:
        return _scalar(
            session,
            "SELECT max(poi_refreshed_at) FROM production.property_features",
        )
    finally:
        session.close()


@task
def count_pending_for_refresh(refresh_ts: datetime) -> int:
    """Count properties not yet computed for the provided POI refresh timestamp."""
    session = get_session_factory()()
    try:
        return int(
            _scalar(
                session,
                """
                SELECT count(*)
                FROM production.properties p
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM production.property_features f
                    WHERE f.property_id = p.id
                      AND f.poi_refreshed_at = :refresh_ts
                )
                """,
                {"refresh_ts": refresh_ts},
            )
            or 0
        )
    finally:
        session.close()


@task
def run_feature_pipeline(chunk_size: int = CHUNK_SIZE) -> int:
    """Run the existing feature pipeline implementation."""
    return run_pipeline(chunk_size=chunk_size)


@flow(name="monthly-poi-feature-recompute")
def monthly_poi_feature_recompute_flow(chunk_size: int = CHUNK_SIZE) -> dict[str, str | int]:
    """Run recompute when a new external POI refresh is detected."""
    logger = get_run_logger()

    external_ts = get_latest_external_refresh()
    if external_ts is None:
        logger.warning(
            "No external refresh timestamp found in active.audit_pipeline_runs. Skipping automation run."
        )
        return {"status": "skipped", "reason": "no_external_refresh"}

    processed_ts = get_latest_processed_refresh()
    pending_before = count_pending_for_refresh(external_ts)

    logger.info(
        "external_ts=%s processed_ts=%s pending_before=%d",
        external_ts,
        processed_ts,
        pending_before,
    )

    if processed_ts is not None and processed_ts >= external_ts and pending_before == 0:
        logger.info("Latest refresh is already processed; skipping.")
        return {"status": "skipped", "reason": "already_up_to_date"}

    processed_rows = run_feature_pipeline(chunk_size=chunk_size)
    pending_after = count_pending_for_refresh(external_ts)

    if pending_after != 0:
        raise RuntimeError(
            f"Pipeline finished with {pending_after} pending properties for refresh {external_ts}"
        )

    logger.info("Pipeline success: processed_rows=%d", processed_rows)
    return {
        "status": "ok",
        "external_ts": external_ts.isoformat(),
        "processed_rows": processed_rows,
    }


if __name__ == "__main__":
    monthly_poi_feature_recompute_flow()
