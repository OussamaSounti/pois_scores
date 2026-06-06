"""Map a score-service output dict to a flat ``property_features`` row."""

from datetime import date, datetime, timezone
from typing import Any

from app.core.constants import ACC_KEYS


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
