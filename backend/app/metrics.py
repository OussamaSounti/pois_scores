"""Prometheus metrics for the API."""

from prometheus_client import Counter, generate_latest

# Request counter (optional: label by method/path for more detail)
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path"],
)


def get_metrics() -> bytes:
    """Return Prometheus text exposition format."""
    return generate_latest()
