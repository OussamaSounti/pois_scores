"""Feature pipeline: select pending properties, compute scores, upsert property_features."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_session_factory
from app.pipeline.mapper import score_dict_to_feature_row
from app.services.spatial import compute_scores

logger = logging.getLogger(__name__)

CHUNK_SIZE = 200
PIPELINE_VERSION = os.environ.get("PIPELINE_VERSION", "1.0")


def _get_current_poi(session: Session) -> datetime:
    """Current POI version from audit.pipeline_runs (max run_timestamp). If no row, use now()."""
    row = session.execute(text("SELECT max(run_timestamp) FROM audit.pipeline_runs")).scalar()
    if row is not None:
        return row if row.tzinfo else row.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _get_pending(
    session: Session, current_poi: datetime, limit: int, offset: int
) -> list[tuple[int, float, float]]:
    """Properties that need (re-)computation for the current POI version.
    Includes properties with no feature row yet AND properties whose
    dist_coast_km / land_buffer_fraction_1km are still NULL.
    """
    sql = text("""
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
    """)
    rows = session.execute(
        sql,
        {"current_poi": current_poi, "limit": limit, "offset": offset},
    ).fetchall()
    return [(r.id, float(r.latitude), float(r.longitude)) for r in rows]


def _count_pending(session: Session, current_poi: datetime) -> int:
    """Total number of properties pending for this POI version."""
    sql = text("""
        SELECT count(*)
        FROM production.properties p
        WHERE NOT EXISTS (
            SELECT 1 FROM production.property_features f
            WHERE f.property_id = p.id
              AND f.poi_refreshed_at = :current_poi
              AND f.dist_coast_km IS NOT NULL
              AND f.land_buffer_fraction_1km IS NOT NULL
        )
    """)
    return session.execute(sql, {"current_poi": current_poi}).scalar() or 0


def _upsert_rows(session: Session, rows: list[dict[str, Any]]) -> None:
    """Insert or update property_features for the given rows."""
    if not rows:
        return
    # Build one upsert per row (could be batched with executemany + ON CONFLICT)
    # PostgreSQL: INSERT ... ON CONFLICT (property_id) DO UPDATE
    cols = [
        "property_id",
        "poi_refreshed_at",
        "pipeline_version",
        "computed_at",
        "poi_count_1km",
        "poi_count_400m",
        "n_categories",
        "n_poi_types",
        "entropy",
        "entropy_fclass",
        "aggregate_score",
        "acc_bus_stop",
        "acc_pharmacy",
        "acc_school",
        "acc_hospital",
        "acc_supermarket",
        "acc_bank",
        "acc_atm",
        "acc_clinic",
        "acc_fuel",
        "acc_police",
        "acc_park",
        "acc_doctors",
        "acc_taxi",
        "by_category",
        "nearest_km",
        "dist_coast_km",
        "land_buffer_fraction_1km",
    ]
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
            for prop_id, lat, lon in chunk:
                try:
                    scores = compute_scores(session, lat, lon)
                    row = score_dict_to_feature_row(
                        prop_id, scores, current_poi, PIPELINE_VERSION, computed_at
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
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
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
