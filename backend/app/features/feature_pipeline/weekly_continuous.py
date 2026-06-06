"""Weekly continuous flow — Prefect-scheduled delta against the current snapshot.

Triggered weekly when new property transactions land. Selects properties that
have no ``production.property_features`` row aligned to the current POI
refresh timestamp and scores them against ``active.production_pois_current``
via :func:`app.features.scores.service.compute_scores`.

Optimised for fast turnaround: small chunks, picks up only newly-arrived or
stale rows. Idempotent — if no new properties arrived since the last run the
flow exits immediately.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import CHUNK_SIZE, POI_SOURCE_CURRENT
from app.core.db import get_session_factory
from app.features.feature_pipeline.db_utils import (
    get_current_poi_ts,
    score_dict_to_feature_row,
    upsert_feature_rows,
)
from app.features.scores.service import compute_scores

logger = logging.getLogger(__name__)


def _count_pending(session: Session, current_poi: datetime) -> int:
    sql = text(
        """
        SELECT count(*)
        FROM production.properties p
        WHERE NOT EXISTS (
            SELECT 1 FROM production.property_features f
            WHERE f.property_id = p.id
              AND f.poi_refreshed_at = :current_poi
              AND f.dist_coast_km IS NOT NULL
              AND f.land_buffer_fraction_1km IS NOT NULL
        )
        """
    )
    return session.execute(sql, {"current_poi": current_poi}).scalar() or 0


def _fetch_pending(
    session: Session, current_poi: datetime, limit: int, offset: int
) -> list[tuple[int, float, float]]:
    sql = text(
        """
        SELECT p.id, p.latitude, p.longitude
        FROM production.properties p
        WHERE NOT EXISTS (
            SELECT 1 FROM production.property_features f
            WHERE f.property_id = p.id
              AND f.poi_refreshed_at = :current_poi
              AND f.dist_coast_km IS NOT NULL
              AND f.land_buffer_fraction_1km IS NOT NULL
        )
        ORDER BY p.id
        LIMIT :limit OFFSET :offset
        """
    )
    rows = session.execute(
        sql, {"current_poi": current_poi, "limit": limit, "offset": offset}
    ).fetchall()
    return [(r.id, float(r.latitude), float(r.longitude)) for r in rows]


def run_weekly_continuous(chunk_size: int = CHUNK_SIZE) -> int:
    """Score every property without a feature row at the current POI snapshot.

    Returns total number of properties processed.
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        current_poi = get_current_poi_ts(session)
        total_pending = _count_pending(session, current_poi)
        logger.info(
            "Weekly continuous starting: current_poi=%s, pending=%d, chunk_size=%d",
            current_poi.isoformat(),
            total_pending,
            chunk_size,
        )
        if total_pending == 0:
            logger.info("No pending properties; exiting.")
            return 0

        processed = 0
        offset = 0
        chunk_index = 0
        computed_at = datetime.now(timezone.utc)
        pipeline_version = get_settings().pipeline_version

        while True:
            chunk = _fetch_pending(session, current_poi, limit=chunk_size, offset=offset)
            if not chunk:
                break
            start = datetime.now(timezone.utc)
            rows: list[dict[str, Any]] = []
            for prop_id, lat, lon in chunk:
                try:
                    scores = compute_scores(session, lat, lon)
                    rows.append(
                        score_dict_to_feature_row(
                            prop_id,
                            scores,
                            current_poi,
                            pipeline_version,
                            computed_at,
                            transaction_date=None,
                            poi_source=POI_SOURCE_CURRENT,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Weekly scoring failed for property %s",
                        prop_id,
                    )
                    raise
            upsert_feature_rows(session, rows)
            processed += len(rows)
            chunk_index += 1
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            logger.info(
                "Weekly chunk %d: processed %d properties in %.2fs",
                chunk_index,
                len(rows),
                elapsed,
            )
            offset += chunk_size

        logger.info("Weekly continuous finished: total_processed=%d", processed)
        return processed
    finally:
        session.close()


def main(chunk_size: int = CHUNK_SIZE) -> None:
    """CLI entrypoint."""
    logging.basicConfig(
        level=get_settings().log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    try:
        n = run_weekly_continuous(chunk_size=chunk_size)
        logger.info("Processed %d properties.", n)
    except Exception:
        logger.exception("Weekly continuous failed")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
