"""Prometheus metrics for the API."""

from prometheus_client import generate_latest


def get_metrics() -> bytes:
    """Return Prometheus text exposition format for the /metrics endpoint."""
    return generate_latest()
