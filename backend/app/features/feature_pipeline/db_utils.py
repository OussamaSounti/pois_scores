"""Row mapping and pipeline DB helpers — delegates writes to repositories."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.constants import ACC_KEYS
from app.repositories.audit import AuditRepository
from app.repositories.property_features import PropertyFeaturesRepository

logger = logging.getLogger(__name__)


def score_dict_to_feature_row(
    transaction_id: int,
    scores: dict[str, Any],
    current_poi: datetime,
    pipeline_version: str,
    computed_at: datetime | None = None,
    transaction_date: date | None = None,
    poi_source: str = "current",
) -> dict[str, Any]:
    """Convert ``compute_scores(_at_date)`` output to one flat row."""
    if computed_at is None:
        computed_at = datetime.now(timezone.utc)
    row: dict[str, Any] = {
        "transaction_id": transaction_id,
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


def get_current_poi_ts(session: Session) -> datetime:
    return AuditRepository(session).current_poi_ts()


def upsert_feature_rows(session: Session, rows: list[dict[str, Any]]) -> None:
    PropertyFeaturesRepository(session).upsert_rows(rows)
