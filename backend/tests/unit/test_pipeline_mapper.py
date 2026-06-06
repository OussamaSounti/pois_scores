"""Unit tests for pipeline mapper (score_dict_to_feature_row)."""

from datetime import date, datetime, timezone

from app.features.feature_pipeline.db_utils import score_dict_to_feature_row
from app.core.constants import ACCESSIBILITY_KEY_TYPES


def test_score_dict_to_feature_row_keys_and_types() -> None:
    """Returned row has all expected keys and correct types."""
    scores = {
        "poi_count_1km": 10,
        "poi_count_400m": 3,
        "n_categories": 2,
        "n_poi_types": 4,
        "entropy": 1.5,
        "entropy_fclass": 1.2,
        "aggregate_score": 45.0,
        "by_category": {"Transport": 5, "Healthcare": 5},
        "accessibility_400m": {"bus_stop": True, "pharmacy": False},
        "nearest_km": {"Transport": 0.2, "Healthcare": 0.5},
        "dist_coast_km": 0.35,
        "land_buffer_fraction_1km": 0.78,
    }
    for k in ACCESSIBILITY_KEY_TYPES:
        if k not in scores["accessibility_400m"]:
            scores["accessibility_400m"][k] = False
    current_poi = datetime(2025, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    computed_at = datetime(2025, 3, 1, 12, 5, 0, tzinfo=timezone.utc)

    row = score_dict_to_feature_row(
        property_id=1,
        scores=scores,
        current_poi=current_poi,
        pipeline_version="1.0",
        computed_at=computed_at,
    )

    assert row["property_id"] == 1
    assert row["poi_refreshed_at"] == current_poi
    assert row["pipeline_version"] == "1.0"
    assert row["computed_at"] == computed_at
    assert row["poi_count_1km"] == 10
    assert row["poi_count_400m"] == 3
    assert row["n_categories"] == 2
    assert row["n_poi_types"] == 4
    assert row["entropy"] == 1.5
    assert row["entropy_fclass"] == 1.2
    assert row["aggregate_score"] == 45.0
    assert row["by_category"] == {"Transport": 5, "Healthcare": 5}
    assert row["nearest_km"] == {"Transport": 0.2, "Healthcare": 0.5}

    for k in ACCESSIBILITY_KEY_TYPES:
        key = f"acc_{k}"
        assert key in row
        assert isinstance(row[key], bool)
    assert row["acc_bus_stop"] is True
    assert row["acc_pharmacy"] is False
    assert row["dist_coast_km"] == 0.35
    assert row["land_buffer_fraction_1km"] == 0.78


def test_score_dict_to_feature_row_default_computed_at() -> None:
    """When computed_at is None, it is set to utcnow."""
    scores = {
        "poi_count_1km": 0,
        "poi_count_400m": 0,
        "n_categories": 0,
        "n_poi_types": 0,
        "entropy": 0.0,
        "entropy_fclass": 0.0,
        "aggregate_score": None,
        "by_category": {},
        "accessibility_400m": {k: False for k in ACCESSIBILITY_KEY_TYPES},
        "nearest_km": {},
    }
    current_poi = datetime.now(timezone.utc)

    row = score_dict_to_feature_row(
        property_id=42,
        scores=scores,
        current_poi=current_poi,
        pipeline_version="test",
        computed_at=None,
    )

    assert row["property_id"] == 42
    assert row["computed_at"] is not None
    assert row["aggregate_score"] is None
    assert row["by_category"] == {}
    assert row["nearest_km"] == {}
    assert row["dist_coast_km"] is None
    assert row["land_buffer_fraction_1km"] is None
    # Default temporal fields
    assert row["transaction_date"] is None
    assert row["poi_source"] == "current"


def test_score_dict_to_feature_row_temporal_mode() -> None:
    """Temporal fields are written correctly when a transaction_date is supplied."""
    scores = {
        "poi_count_1km": 5,
        "poi_count_400m": 1,
        "n_categories": 1,
        "n_poi_types": 2,
        "entropy": 0.9,
        "entropy_fclass": 0.7,
        "aggregate_score": 30.0,
        "by_category": {"Transport": 5},
        "accessibility_400m": {k: False for k in ACCESSIBILITY_KEY_TYPES},
        "nearest_km": {"Transport": 0.4},
        "poi_source": "history",
    }
    tx_date = date(2018, 3, 23)
    poi_ref = datetime(2018, 3, 23, tzinfo=timezone.utc)
    row = score_dict_to_feature_row(
        property_id=99,
        scores=scores,
        current_poi=poi_ref,
        pipeline_version="1.0",
        transaction_date=tx_date,
        poi_source="history",
    )
    assert row["transaction_date"] == tx_date
    assert row["poi_source"] == "history"
    assert row["poi_refreshed_at"] == poi_ref
