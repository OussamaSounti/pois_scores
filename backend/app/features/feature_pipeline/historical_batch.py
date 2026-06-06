"""Historical batch flow — manual one-shot backfill.

Selects every property with a ``transaction_date`` whose
``production.property_features`` row is not aligned to that exact date, and
scores it against ``history.production_poi_history`` via
:func:`app.features.scores.service.compute_scores_at_date`.

Run manually:

    python -m app.features.feature_pipeline historical_batch [--chunk-size N]

Default chunk size is large because this flow is built for bulk throughput
on millions of historical transactions.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import POI_SOURCE_HISTORY
from app.core.db import get_session_factory
from app.features.feature_pipeline.db_utils import score_dict_to_feature_row, upsert_feature_rows
from app.features.scores.service import compute_scores_at_date

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 1000


def _count_pending(session: Session) -> int:
    sql = text(
        """
        SELECT count(*)
        FROM production.properties p
        WHERE p.transaction_date IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM production.property_features f
              WHERE f.property_id = p.id
                AND f.poi_refreshed_at = p.transaction_date::timestamptz
                AND f.poi_source = 'history'
                AND f.dist_coast_km IS NOT NULL
                AND f.land_buffer_fraction_1km IS NOT NULL
          )
        """
    )
    return session.execute(sql).scalar() or 0


def _fetch_pending(
    session: Session, limit: int, offset: int
) -> list[tuple[int, float, float, date]]:
    sql = text(
        """
        SELECT p.id, p.latitude, p.longitude, p.transaction_date
        FROM production.properties p
        WHERE p.transaction_date IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM production.property_features f
              WHERE f.property_id = p.id
                AND f.poi_refreshed_at = p.transaction_date::timestamptz
                AND f.poi_source = 'history'
                AND f.dist_coast_km IS NOT NULL
                AND f.land_buffer_fraction_1km IS NOT NULL
          )
        ORDER BY p.id
        LIMIT :limit OFFSET :offset
        """
    )
    rows = session.execute(sql, {"limit": limit, "offset": offset}).fetchall()
    return [(r.id, float(r.latitude), float(r.longitude), r.transaction_date) for r in rows]


def run_historical_batch(chunk_size: int = DEFAULT_CHUNK_SIZE) -> int:
    """Backfill historical scores for every property with a ``transaction_date``.

    Returns total number of properties processed.
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        total_pending = _count_pending(session)
        logger.info(
            "Historical batch starting: pending=%d, chunk_size=%d", total_pending, chunk_size
        )
        if total_pending == 0:
            logger.info("No pending historical properties; exiting.")
            return 0

        processed = 0
        offset = 0
        chunk_index = 0
        computed_at = datetime.now(timezone.utc)
        pipeline_version = get_settings().pipeline_version

        while True:
            chunk = _fetch_pending(session, limit=chunk_size, offset=offset)
            if not chunk:
                break
            start = datetime.now(timezone.utc)
            rows: list[dict[str, Any]] = []
            for prop_id, lat, lon, transaction_date in chunk:
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
                            prop_id,
                            scores,
                            poi_ref,
                            pipeline_version,
                            computed_at,
                            transaction_date=transaction_date,
                            poi_source=POI_SOURCE_HISTORY,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Historical scoring failed for property %s at %s",
                        prop_id,
                        transaction_date,
                    )
                    raise
            upsert_feature_rows(session, rows)
            processed += len(rows)
            chunk_index += 1
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            logger.info(
                "Historical chunk %d: processed %d properties in %.2fs",
                chunk_index,
                len(rows),
                elapsed,
            )
            offset += chunk_size

        logger.info("Historical batch finished: total_processed=%d", processed)
        return processed
    finally:
        session.close()


def main(chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
    """CLI entrypoint."""
    logging.basicConfig(
        level=get_settings().log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    try:
        n = run_historical_batch(chunk_size=chunk_size)
        logger.info("Processed %d historical properties.", n)
    except Exception:
        logger.exception("Historical batch failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
