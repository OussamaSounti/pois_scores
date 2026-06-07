"""Tests for pipeline run ledger helpers."""

from app.features.feature_pipeline.run_context import run_config
from app.repositories.feature_pipeline_runs import _truncate


def test_truncate_short_string_unchanged() -> None:
    assert _truncate("hello") == "hello"


def test_truncate_long_string() -> None:
    value = "x" * 2005
    result = _truncate(value)
    assert result is not None
    assert len(result) == 2000
    assert result.endswith("...")


def test_run_config_snapshot() -> None:
    assert run_config(chunk_size=500, workers=8, skip_errors=True) == {
        "chunk_size": 500,
        "workers": 8,
        "skip_errors": True,
    }
