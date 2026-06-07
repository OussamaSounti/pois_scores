"""Run ledger context for production.feature_pipeline_runs."""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.core.constants import (
    RUN_STATUS_FAILED,
    RUN_STATUS_PARTIAL,
    RUN_STATUS_SKIPPED,
    RUN_STATUS_SUCCESS,
)
from app.core.db import get_session_factory
from app.repositories.feature_pipeline_runs import FeaturePipelineRunRepository

logger = logging.getLogger(__name__)

_PROGRESS_FLUSH_EVERY = 5


class PipelineRunTracker:
    """Insert and update one row in production.feature_pipeline_runs."""

    def __init__(
        self,
        flow_name: str,
        *,
        triggered_by: str,
        config: dict[str, Any],
        poi_refreshed_at: datetime | None = None,
        poi_source: str | None = None,
        prefect_run_id: str | None = None,
    ) -> None:
        self.flow_name = flow_name
        self.triggered_by = triggered_by
        self.config = config
        self.poi_refreshed_at = poi_refreshed_at
        self.poi_source = poi_source
        self.prefect_run_id = prefect_run_id

        self.run_id = uuid.uuid4()
        self._session = get_session_factory()()
        self._repo = FeaturePipelineRunRepository(self._session)
        self._enabled = False
        self._started_at = datetime.now(timezone.utc)
        self._started = False
        self._finished = False
        self._lock = threading.Lock()
        self._processed = 0
        self._skipped = 0
        self._chunks_since_flush = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    def __enter__(self) -> PipelineRunTracker:
        existed = self._repo.table_exists()
        if not existed:
            try:
                FeaturePipelineRunRepository.ensure_tables()
            except Exception:
                logger.exception("Failed to create pipeline run tracking tables")
        self._enabled = self._repo.table_exists()
        if self._enabled and not existed:
            logger.info(
                "Created pipeline run tracking tables in production schema"
            )
        elif not self._enabled:
            logger.warning(
                "production.feature_pipeline_runs is unavailable; run tracking disabled"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        try:
            if exc_type is not None and self._enabled and self._started and not self._finished:
                self._finalize(
                    RUN_STATUS_FAILED,
                    error_summary=str(exc_val) if exc_val else exc_type.__name__,
                )
        finally:
            self._session.close()
        return False

    def start(self, pending_before: int | None = None) -> None:
        if not self._enabled or self._started:
            return
        settings = get_settings()
        try:
            self._repo.start_run(
                run_id=self.run_id,
                flow_name=self.flow_name,
                pipeline_version=settings.pipeline_version,
                triggered_by=self.triggered_by,
                config=self.config,
                poi_refreshed_at=self.poi_refreshed_at,
                poi_source=self.poi_source,
                prefect_run_id=self.prefect_run_id,
                pending_before=pending_before,
            )
            self._started = True
        except Exception:
            logger.exception("Failed to start pipeline run ledger row")
            self._enabled = False

    def skip(self, reason: str, *, pending_after: int | None = None) -> None:
        if not self._enabled or self._finished:
            return
        if not self._started:
            self.start()
        self._finalize(
            RUN_STATUS_SKIPPED,
            skip_reason=reason,
            pending_after=pending_after,
        )

    def complete(self, *, pending_after: int | None = None) -> None:
        if not self._enabled or self._finished:
            return
        if not self._started:
            self.start()
        if pending_after and pending_after > 0:
            status = RUN_STATUS_FAILED
            error_summary = f"{pending_after} properties still pending"
        elif self._skipped > 0:
            status = RUN_STATUS_PARTIAL
            error_summary = None
        else:
            status = RUN_STATUS_SUCCESS
            error_summary = None
        self._finalize(status, pending_after=pending_after, error_summary=error_summary)

    def record_chunk(
        self,
        processed: int,
        skipped: int,
        failures: list[tuple[int, str]] | None = None,
    ) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._processed += processed
            self._skipped += skipped
            self._chunks_since_flush += 1
            should_flush = self._chunks_since_flush >= _PROGRESS_FLUSH_EVERY
            if should_flush:
                self._chunks_since_flush = 0
            run_id = self.run_id
            flow_name = self.flow_name
            repo = self._repo
            total_processed = self._processed
            total_skipped = self._skipped
            chunk_failures = list(failures or [])

        if chunk_failures:
            try:
                repo.record_failures(run_id, flow_name, chunk_failures)
            except Exception:
                logger.exception("Failed to record pipeline property failures")
        if should_flush:
            try:
                repo.update_progress(
                    run_id,
                    processed=total_processed,
                    skipped=total_skipped,
                    failed=total_skipped,
                )
            except Exception:
                logger.exception("Failed to update pipeline run progress")

    def _finalize(
        self,
        status: str,
        *,
        skip_reason: str | None = None,
        pending_after: int | None = None,
        error_summary: str | None = None,
    ) -> None:
        if not self._enabled or self._finished:
            return
        self._finished = True
        try:
            self._repo.finish_run(
                self.run_id,
                status=status,
                processed=self._processed,
                skipped=self._skipped,
                failed=self._skipped,
                pending_after=pending_after,
                skip_reason=skip_reason,
                error_summary=error_summary,
                started_at=self._started_at,
            )
        except Exception:
            logger.exception("Failed to finalize pipeline run ledger row")


def prefect_run_id() -> str | None:
    """Return the current Prefect flow run id when running inside a flow."""
    try:
        from prefect.context import get_run_context

        ctx = get_run_context()
        if ctx.flow_run is not None:
            return str(ctx.flow_run.id)
    except Exception:
        pass
    return None


def run_config(
    *,
    chunk_size: int,
    workers: int,
    skip_errors: bool,
) -> dict[str, Any]:
    return {
        "chunk_size": chunk_size,
        "workers": workers,
        "skip_errors": skip_errors,
    }
