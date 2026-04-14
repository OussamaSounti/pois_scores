"""Map compute_scores output to a flat row for property_features table."""

from datetime import datetime, timezone
from typing import Any

from app.services.spatial import ACCESSIBILITY_KEY_TYPES

# Fixed order for acc_* columns (matches schema)
ACC_KEYS = sorted(ACCESSIBILITY_KEY_TYPES)


def score_dict_to_feature_row(
    property_id: int,
    scores: dict[str, Any],
    current_poi: datetime,
    pipeline_version: str,
    computed_at: datetime | None = None,
) -> dict[str, Any]:
    """
    Convert compute_scores() output to one flat row for property_features.
    Scalars and acc_* are flat; by_category and nearest_km become JSONB-ready dicts.
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
    }
    acc = scores.get("accessibility_400m", {})
    for k in ACC_KEYS:
        row[f"acc_{k}"] = acc.get(k, False)
    return row
