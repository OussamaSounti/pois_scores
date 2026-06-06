"""Database helpers for both pipeline flows.

Combines row mapping and upsert logic for ``production.property_features``
so the two flow modules only deal with their selection criteria.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.constants import ACC_KEYS, PROPERTY_FEATURE_COLUMNS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Row mapping: score dict -> flat DB row
# ---------------------------------------------------------------------------


def score_dict_to_feature_row(
    property_id: int,
    scores: dict[str, Any],
    current_poi: datetime,
    pipeline_version: str,
    computed_at: datetime | None = None,
    transaction_date: date | None = None,
    poi_source: str = "current",
) -> dict[str, Any]:
    """Convert ``compute_scores(_at_date)`` output to one flat row.

    Parameters
    ----------
    transaction_date:
        The transaction date used for temporal POI lookup. NULL for
        properties scored against ``active.production_pois_current``.
    poi_source:
        ``'history'`` when ``history.production_poi_history`` was queried;
        ``'current'`` when ``active.production_pois_current`` was queried.
    """
    if computed_at is None:
        computed_at = datetime.now(timezone.utc)
    row: dict[str, Any] = {
        "property_id": property_id,
        "poi_refreshed_at": current_poi,
        "pipeline_version": pipeline_version,
        "computed_at": computed_at,
        "poi_count_1km": scores["poi_count_1km"],
        "poi_count_400m": scores["poi_count_400m"],
        "n_categories": scores["n_categories"],
        "n_poi_types": scores["n_poi_types"],
        "entropy": scores["entropy"],
        "entropy_fclass": scores["entropy_fclass"],
        "aggregate_score": scores.get("aggregate_score"),
        "by_category": scores["by_category"],
        "nearest_km": scores["nearest_km"],
        "dist_coast_km": scores.get("dist_coast_km"),
        "land_buffer_fraction_1km": scores.get("land_buffer_fraction_1km"),
        "transaction_date": transaction_date,
        "poi_source": poi_source,
    }
    acc = scores.get("accessibility_400m", {})
    for k in ACC_KEYS:
        row[f"acc_{k}"] = acc.get(k, False)
    return row


# ---------------------------------------------------------------------------
# Upsert + POI timestamp helpers
# ---------------------------------------------------------------------------


def get_current_poi_ts(session: Session) -> datetime:
    """Return the latest external POI refresh timestamp.

    Source: ``active.audit_pipeline_runs.max(run_timestamp)``. Falls back to
    ``now()`` (UTC) when the audit table has no rows.
    """
    row = session.execute(
        text("SELECT max(run_timestamp) FROM active.audit_pipeline_runs")
    ).scalar()
    if row is not None:
        return row if row.tzinfo else row.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def upsert_feature_rows(session: Session, rows: list[dict[str, Any]]) -> None:
    """Insert or update a batch of ``production.property_features`` rows.

    ``by_category`` and ``nearest_km`` are JSON-encoded on the way in.
    Commits on completion.
    """
    if not rows:
        return
    cols = list(PROPERTY_FEATURE_COLUMNS)
    placeholders = ", ".join(f":{c}" for c in cols)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "property_id")
    sql = text(
        f"""
        INSERT INTO production.property_features ({", ".join(cols)})
        VALUES ({placeholders})
        ON CONFLICT (property_id) DO UPDATE SET {updates}
        """
    )
    for row in rows:
        payload = {c: row.get(c) for c in cols}
        payload["by_category"] = json.dumps(row["by_category"])
        payload["nearest_km"] = json.dumps(row["nearest_km"])
        session.execute(sql, payload)
    session.commit()
