"""Prefect flows wrapping the two pipeline modules."""

from __future__ import annotations

from datetime import datetime

from prefect import flow, get_run_logger, task

from app.core.config import get_settings
from app.core.constants import (
    CHUNK_SIZE,
    PIPELINE_FLOW_HISTORICAL,
    PIPELINE_FLOW_WEEKLY,
    POI_SOURCE_CURRENT,
    POI_SOURCE_HISTORY,
    TRIGGERED_BY_PREFECT,
)
from app.core.db import get_session_factory
from app.features.feature_pipeline.historical_batch import (
    DEFAULT_CHUNK_SIZE as HISTORICAL_CHUNK_SIZE,
)
from app.features.feature_pipeline.historical_batch import (
    run_historical_batch,
)
from app.features.feature_pipeline.run_context import (
    PipelineRunTracker,
    prefect_run_id,
    run_config,
)
from app.features.feature_pipeline.weekly_continuous import run_weekly_continuous
from app.repositories.audit import AuditRepository
from app.repositories.property_features import PropertyFeaturesRepository


@task
def get_latest_external_refresh() -> datetime | None:
    session = get_session_factory()()
    try:
        audit_repo = AuditRepository(session)
        if not audit_repo.table_exists():
            return None
        return audit_repo.latest_run_timestamp()
    finally:
        session.close()


@task
def get_latest_processed_refresh() -> datetime | None:
    session = get_session_factory()()
    try:
        return PropertyFeaturesRepository(session).max_poi_refreshed_at()
    finally:
        session.close()


@task
def count_pending_for_refresh(refresh_ts: datetime) -> int:
    session = get_session_factory()()
    try:
        return PropertyFeaturesRepository(session).count_pending_for_refresh(refresh_ts)
    finally:
        session.close()


@flow(name="weekly-poi-feature-recompute")
def weekly_recompute_flow(chunk_size: int = CHUNK_SIZE) -> dict[str, str | int]:
    """Run weekly delta when a new external POI refresh is detected."""
    logger = get_run_logger()
    settings = get_settings()
    config = run_config(
        chunk_size=chunk_size,
        workers=settings.pipeline_workers,
        skip_errors=False,
    )

    external_ts = get_latest_external_refresh()
    if external_ts is None:
        logger.warning(
            "No external refresh timestamp found in active.audit_pipeline_runs. Skipping run."
        )
        with PipelineRunTracker(
            PIPELINE_FLOW_WEEKLY,
            triggered_by=TRIGGERED_BY_PREFECT,
            config=config,
            poi_source=POI_SOURCE_CURRENT,
            prefect_run_id=prefect_run_id(),
        ) as run:
            run.skip("no_external_refresh")
        return {"status": "skipped", "reason": "no_external_refresh"}

    processed_ts = get_latest_processed_refresh()
    pending_before = count_pending_for_refresh(external_ts)

    logger.info(
        "external_ts=%s processed_ts=%s pending_before=%d",
        external_ts,
        processed_ts,
        pending_before,
    )

    with PipelineRunTracker(
        PIPELINE_FLOW_WEEKLY,
        triggered_by=TRIGGERED_BY_PREFECT,
        config=config,
        poi_refreshed_at=external_ts,
        poi_source=POI_SOURCE_CURRENT,
        prefect_run_id=prefect_run_id(),
    ) as run:
        run.start(pending_before=pending_before)

        if processed_ts is not None and processed_ts >= external_ts and pending_before == 0:
            logger.info("Latest refresh is already processed; skipping.")
            run.skip("already_up_to_date", pending_after=0)
            return {"status": "skipped", "reason": "already_up_to_date"}

        processed_rows = run_weekly_continuous(
            chunk_size=chunk_size,
            skip_errors=False,
            run=run,
        )
        pending_after = count_pending_for_refresh(external_ts)
        run.complete(pending_after=pending_after)

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


@flow(name="historical-poi-feature-backfill")
def historical_backfill_flow(
    chunk_size: int = HISTORICAL_CHUNK_SIZE,
) -> dict[str, str | int]:
    """Run the historical backfill against history.production_poi_history."""
    logger = get_run_logger()
    settings = get_settings()
    config = run_config(
        chunk_size=chunk_size,
        workers=settings.pipeline_workers,
        skip_errors=False,
    )

    session = get_session_factory()()
    try:
        pending_before = PropertyFeaturesRepository(session).count_pending_historical()
    finally:
        session.close()

    with PipelineRunTracker(
        PIPELINE_FLOW_HISTORICAL,
        triggered_by=TRIGGERED_BY_PREFECT,
        config=config,
        poi_source=POI_SOURCE_HISTORY,
        prefect_run_id=prefect_run_id(),
    ) as run:
        run.start(pending_before=pending_before)
        if pending_before == 0:
            run.skip("no_pending")
            logger.info("No pending historical properties; skipping.")
            return {"status": "skipped", "reason": "no_pending"}

        processed = run_historical_batch(chunk_size=chunk_size, run=run)
        session = get_session_factory()()
        try:
            pending_after = PropertyFeaturesRepository(session).count_pending_historical()
        finally:
            session.close()
        run.complete(pending_after=pending_after)
        logger.info("Historical backfill finished: processed_rows=%d", processed)
        return {"status": "ok", "processed_rows": processed}


if __name__ == "__main__":
    weekly_recompute_flow()
