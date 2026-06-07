"""Historical batch flow — manual one-shot backfill.

Supports parallel workers via ``concurrent.futures.ThreadPoolExecutor``.
Each worker gets its own DB session and processes chunks from a shared
keyset-paginated cursor (thread-safe via a lock).
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.core.constants import (
    PIPELINE_FLOW_HISTORICAL,
    POI_SOURCE_HISTORY,
    TRIGGERED_BY_CLI,
)
from app.core.db import get_session_factory
from app.features.feature_pipeline.db_utils import score_dict_to_feature_row, upsert_feature_rows
from app.features.feature_pipeline.progress import ProgressTracker
from app.features.feature_pipeline.run_context import PipelineRunTracker, run_config
from app.features.scores.service import compute_scores_at_date
from app.repositories.property_features import PropertyFeaturesRepository

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 1000


def _process_chunk_historical(
    chunk: list[tuple[int, float, float, date]],
    pipeline_version: str,
    computed_at: datetime,
    skip_errors: bool,
) -> tuple[list[dict[str, Any]], int, list[tuple[int, str]]]:
    """Score one chunk using a dedicated session."""
    session = get_session_factory()()
    try:
        rows: list[dict[str, Any]] = []
        skipped = 0
        failures: list[tuple[int, str]] = []
        for transaction_id, lat, lon, transaction_date in chunk:
            try:
                scores = compute_scores_at_date(session, lat, lon, transaction_date)
                poi_ref = datetime(
                    transaction_date.year,
                    transaction_date.month,
                    transaction_date.day,
                    tzinfo=timezone.utc,
                )
                rows.append(
                    score_dict_to_feature_row(
                        transaction_id,
                        scores,
                        poi_ref,
                        pipeline_version,
                        computed_at,
                        transaction_date=transaction_date,
                        poi_source=POI_SOURCE_HISTORY,
                    )
                )
            except Exception as exc:
                logger.exception(
                    "Historical scoring failed for transaction %s at %s",
                    transaction_id,
                    transaction_date,
                )
                if skip_errors:
                    skipped += 1
                    failures.append((transaction_id, str(exc)))
                    continue
                raise
        upsert_feature_rows(session, rows)
        return rows, skipped, failures
    finally:
        session.close()


def run_historical_batch(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    skip_errors: bool = False,
    workers: int | None = None,
    run: PipelineRunTracker | None = None,
) -> int:
    """Backfill historical scores for every property with a transaction_date.

    When *skip_errors* is True, individual property failures are logged and
    skipped instead of aborting the entire run. *workers* controls parallel
    threads (defaults to ``settings.pipeline_workers``).
    """
    if workers is None:
        workers = get_settings().pipeline_workers

    session_factory = get_session_factory()
    session = session_factory()
    try:
        features_repo = PropertyFeaturesRepository(session)
        total_pending = features_repo.count_pending_historical()
        logger.info(
            "Historical batch starting: pending=%d, chunk_size=%d, workers=%d",
            total_pending,
            chunk_size,
            workers,
        )
        if total_pending == 0:
            logger.info("No pending historical properties; exiting.")
            return 0

        computed_at = datetime.now(timezone.utc)
        pipeline_version = get_settings().pipeline_version
        tracker = ProgressTracker(total_pending, "historical")

        last_transaction_id = 0
        last_id_lock = threading.Lock()
        processed = 0
        total_skipped = 0
        chunk_index = 0

        def next_chunk() -> list[tuple[int, float, float, date]] | None:
            nonlocal last_transaction_id
            with last_id_lock:
                chunk = features_repo.fetch_pending_historical(
                    limit=chunk_size, after_transaction_id=last_transaction_id
                )
                if chunk:
                    last_transaction_id = chunk[-1][0]
                return chunk or None

        if workers <= 1:
            while True:
                chunk = next_chunk()
                if not chunk:
                    break
                start = datetime.now(timezone.utc)
                rows, skipped, failures = _process_chunk_historical(
                    chunk, pipeline_version, computed_at, skip_errors
                )
                processed += len(rows)
                total_skipped += skipped
                chunk_index += 1
                elapsed = (datetime.now(timezone.utc) - start).total_seconds()
                tracker.log_chunk(chunk_index, len(rows), elapsed)
                if run is not None:
                    run.record_chunk(len(rows), skipped, failures)
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {}
                for _ in range(workers):
                    chunk = next_chunk()
                    if chunk:
                        fut = pool.submit(
                            _process_chunk_historical,
                            chunk,
                            pipeline_version,
                            computed_at,
                            skip_errors,
                        )
                        futures[fut] = datetime.now(timezone.utc)

                while futures:
                    done = next(as_completed(futures))
                    start_time = futures.pop(done)
                    rows, skipped, failures = done.result()
                    processed += len(rows)
                    total_skipped += skipped
                    chunk_index += 1
                    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                    tracker.log_chunk(chunk_index, len(rows), elapsed)
                    if run is not None:
                        run.record_chunk(len(rows), skipped, failures)

                    chunk = next_chunk()
                    if chunk:
                        fut = pool.submit(
                            _process_chunk_historical,
                            chunk,
                            pipeline_version,
                            computed_at,
                            skip_errors,
                        )
                        futures[fut] = datetime.now(timezone.utc)

        tracker.log_done(processed, total_skipped)
        return processed
    finally:
        session.close()


def main(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    skip_errors: bool = False,
    workers: int | None = None,
) -> None:
    logging.basicConfig(
        level=get_settings().log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    settings = get_settings()
    worker_count = workers if workers is not None else settings.pipeline_workers
    config = run_config(
        chunk_size=chunk_size,
        workers=worker_count,
        skip_errors=skip_errors,
    )

    session = get_session_factory()()
    try:
        pending_before = PropertyFeaturesRepository(session).count_pending_historical()
    finally:
        session.close()

    try:
        with PipelineRunTracker(
            PIPELINE_FLOW_HISTORICAL,
            triggered_by=TRIGGERED_BY_CLI,
            config=config,
            poi_source=POI_SOURCE_HISTORY,
        ) as run:
            run.start(pending_before=pending_before)
            if pending_before == 0:
                run.skip("no_pending")
                logger.info("No pending historical properties; exiting.")
                return
            n = run_historical_batch(
                chunk_size=chunk_size,
                skip_errors=skip_errors,
                workers=workers,
                run=run,
            )
            session = get_session_factory()()
            try:
                pending_after = PropertyFeaturesRepository(session).count_pending_historical()
            finally:
                session.close()
            run.complete(pending_after=pending_after)
            logger.info("Processed %d historical properties.", n)
    except Exception:
        logger.exception("Historical batch failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
