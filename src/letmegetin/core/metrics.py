"""Prometheus instruments for the API (scraped on the internal network)."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "letmegetin_http_requests_total",
    "HTTP requests by method, route and status.",
    ["method", "path", "status"],
)
HTTP_DURATION = Histogram(
    "letmegetin_http_request_duration_seconds",
    "HTTP request duration by method and route.",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
RATE_LIMITED = Counter(
    "letmegetin_rate_limited_total",
    "Requests rejected by the rate limiter.",
)
REDIS_UP = Gauge(
    "letmegetin_redis_up",
    "1 when Redis answers a PING, 0 otherwise.",
)


def record_request(method: str, path: str, status: int, seconds: float) -> None:
    HTTP_REQUESTS.labels(method=method, path=path, status=str(status)).inc()
    HTTP_DURATION.labels(method=method, path=path).observe(seconds)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
