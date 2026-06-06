"""Feature pipeline: select pending properties, compute scores, upsert property_features."""

import json
import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import CHUNK_SIZE, POI_SOURCE_CURRENT, POI_SOURCE_HISTORY, PROPERTY_FEATURE_COLUMNS
from app.db import get_session_factory
from app.pipeline.mapper import score_dict_to_feature_row
from app.services.spatial import compute_scores, compute_scores_at_date

logger = logging.getLogger(__name__)


def _get_current_poi(session: Session) -> datetime:
    """Current POI version from active.audit_pipeline_runs (max run_timestamp). If no row, use now()."""
    row = session.execute(text("SELECT max(run_timestamp) FROM active.audit_pipeline_runs")).scalar()
    if row is not None:
        return row if row.tzinfo else row.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _get_pending(
    session: Session, current_poi: datetime, limit: int, offset: int
) -> list[tuple[int, float, float, date | None]]:
    """Properties that need (re-)computation.

    For properties WITH a transaction_date the reference POI timestamp is the
    transaction_date itself (cast to timestamptz midnight UTC).
    For properties WITHOUT a transaction_date the reference is the current POI
    refresh timestamp from active.audit_pipeline_runs.

    A property is considered done when property_features already has a row
    whose poi_refreshed_at matches the reference timestamp AND the coastal
    features have been computed (non-NULL).
    """
    sql = text("""
        SELECT p.id, p.latitude, p.longitude, p.transaction_date
        FROM production.properties p
        WHERE NOT EXISTS (
            SELECT 1 FROM production.property_features f
            WHERE f.property_id = p.id
              AND f.poi_refreshed_at = CASE
                  WHEN p.transaction_date IS NOT NULL
                      THEN p.transaction_date::timestamptz
                  ELSE :current_poi
              END
              AND f.dist_coast_km IS NOT NULL
              AND f.land_buffer_fraction_1km IS NOT NULL
        )
        ORDER BY p.id
        LIMIT :limit OFFSET :offset
    """)
    rows = session.execute(
        sql,
        {"current_poi": current_poi, "limit": limit, "offset": offset},
    ).fetchall()
    return [(r.id, float(r.latitude), float(r.longitude), r.transaction_date) for r in rows]


def _count_pending(session: Session, current_poi: datetime) -> int:
    """Total number of properties pending for this POI version."""
    sql = text("""
        SELECT count(*)
        FROM production.properties p
        WHERE NOT EXISTS (
            SELECT 1 FROM production.property_features f
            WHERE f.property_id = p.id
              AND f.poi_refreshed_at = CASE
                  WHEN p.transaction_date IS NOT NULL
                      THEN p.transaction_date::timestamptz
                  ELSE :current_poi
              END
              AND f.dist_coast_km IS NOT NULL
              AND f.land_buffer_fraction_1km IS NOT NULL
        )
    """)
    return session.execute(sql, {"current_poi": current_poi}).scalar() or 0


def _upsert_rows(session: Session, rows: list[dict[str, Any]]) -> None:
    """Insert or update property_features for the given rows."""
    if not rows:
        return
    cols = list(PROPERTY_FEATURE_COLUMNS)
    placeholders = ", ".join(f":{c}" for c in cols)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "property_id")
    sql = text(f"""
        INSERT INTO production.property_features ({", ".join(cols)})
        VALUES ({placeholders})
        ON CONFLICT (property_id) DO UPDATE SET {updates}
    """)
    for row in rows:
        payload = {c: row.get(c) for c in cols}
        payload["by_category"] = json.dumps(row["by_category"])
        payload["nearest_km"] = json.dumps(row["nearest_km"])
        session.execute(sql, payload)
    session.commit()


def run_pipeline(chunk_size: int = CHUNK_SIZE) -> int:
    """
    Process all pending properties: compute scores and upsert into property_features.

    Properties that have a transaction_date are scored against
    history.production_poi_history at that date (temporal mode).
    Properties without a transaction_date are scored against
    active.production_pois_current (current mode).

    Returns total number of properties processed.
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        current_poi = _get_current_poi(session)
        total_pending = _count_pending(session, current_poi)
        logger.info(
            "Pipeline starting: current_poi=%s, pending=%d, chunk_size=%d",
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

        while True:
            chunk = _get_pending(session, current_poi, limit=chunk_size, offset=offset)
            if not chunk:
                break
            start = datetime.now(timezone.utc)
            rows: list[dict[str, Any]] = []
            for prop_id, lat, lon, transaction_date in chunk:
                try:
                    if transaction_date is not None:
                        scores = compute_scores_at_date(session, lat, lon, transaction_date)
                        poi_ref = datetime(
                            transaction_date.year,
                            transaction_date.month,
                            transaction_date.day,
                            tzinfo=timezone.utc,
                        )
                        src = POI_SOURCE_HISTORY
                    else:
                        scores = compute_scores(session, lat, lon)
                        poi_ref = current_poi
                        src = POI_SOURCE_CURRENT

                    row = score_dict_to_feature_row(
                        prop_id,
                        scores,
                        poi_ref,
                        get_settings().pipeline_version,
                        computed_at,
                        transaction_date=transaction_date,
                        poi_source=src,
                    )
                    rows.append(row)
                except Exception as e:
                    logger.exception("Failed to compute scores for property %s: %s", prop_id, e)
                    raise
            _upsert_rows(session, rows)
            processed += len(rows)
            chunk_index += 1
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            logger.info(
                "Chunk %d: processed %d properties in %.2fs",
                chunk_index,
                len(rows),
                elapsed,
            )
            offset += chunk_size

        logger.info("Pipeline finished: total_processed=%d", processed)
        return processed
    finally:
        session.close()


def main() -> None:
    """CLI entrypoint: configure logging and run pipeline."""
    logging.basicConfig(
        level=get_settings().log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    try:
        n = run_pipeline()
        logger.info("Processed %d properties.", n)
    except Exception as e:
        logger.exception("Pipeline failed: %s", e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
