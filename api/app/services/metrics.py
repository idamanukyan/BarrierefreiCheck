"""
Prometheus Metrics Service

Provides application metrics for monitoring and alerting.
"""

import time
from functools import wraps
from typing import Callable

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

# Application info
APP_INFO = Info("app", "Application information")
APP_INFO.info({
    "name": "AccessibilityChecker",
    "version": "0.1.0",
})

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method", "endpoint"]
)

# Business metrics
SCANS_TOTAL = Counter(
    "scans_total",
    "Total number of scans created",
    ["status"]
)

SCANS_IN_PROGRESS = Gauge(
    "scans_in_progress",
    "Number of scans currently in progress"
)

SCAN_DURATION = Histogram(
    "scan_duration_seconds",
    "Scan duration in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1200]
)

ISSUES_FOUND = Counter(
    "accessibility_issues_total",
    "Total accessibility issues found",
    ["impact"]
)

PAGES_SCANNED = Counter(
    "pages_scanned_total",
    "Total pages scanned"
)

# Auth metrics
AUTH_ATTEMPTS = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["type", "status"]  # type: login/register, status: success/failure
)

# External service metrics
EXTERNAL_SERVICE_REQUESTS = Counter(
    "external_service_requests_total",
    "Total requests to external services",
    ["service", "status"]  # service: stripe/minio/redis, status: success/failure
)

EXTERNAL_SERVICE_LATENCY = Histogram(
    "external_service_latency_seconds",
    "External service request latency",
    ["service"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Database metrics
DB_QUERY_COUNT = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation"]  # select/insert/update/delete
)

DB_QUERY_LATENCY = Histogram(
    "db_query_duration_seconds",
    "Database query latency",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Cache metrics
CACHE_HITS = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type"]
)

CACHE_MISSES = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_type"]
)

# Report metrics
REPORTS_GENERATED = Counter(
    "reports_generated_total",
    "Total reports generated",
    ["format", "language", "status"]  # status: success/failure
)

REPORT_GENERATION_DURATION = Histogram(
    "report_generation_duration_seconds",
    "Report generation duration in seconds",
    ["format"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

# Export metrics
EXPORTS_CREATED = Counter(
    "exports_created_total",
    "Total exports created",
    ["format", "type"]  # type: issues/summary/pages
)

EXPORT_SIZE_BYTES = Histogram(
    "export_size_bytes",
    "Export file size in bytes",
    ["format"],
    buckets=[1024, 10240, 102400, 1048576, 10485760]  # 1KB, 10KB, 100KB, 1MB, 10MB
)

# Email metrics
EMAILS_SENT = Counter(
    "emails_sent_total",
    "Total emails sent",
    ["type", "status"]  # type: welcome/report/password_reset, status: success/failure
)

EMAIL_SEND_DURATION = Histogram(
    "email_send_duration_seconds",
    "Email send duration in seconds",
    ["type"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# WebSocket metrics
WEBSOCKET_CONNECTIONS = Gauge(
    "websocket_connections_active",
    "Number of active WebSocket connections",
    ["type"]  # type: scan/notifications
)

WEBSOCKET_MESSAGES = Counter(
    "websocket_messages_total",
    "Total WebSocket messages sent",
    ["type", "message_type"]  # type: scan/notifications, message_type: progress/completed/failed
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics."""

    async def dispatch(self, request: Request, call_next) -> Response:
        method = request.method
        # Normalize endpoint path (remove IDs for grouping)
        path = self._normalize_path(request.url.path)

        # Skip metrics endpoint itself
        if path == "/metrics":
            return await call_next(request)

        REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).inc()
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status_code=status_code
            ).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)
            REQUESTS_IN_PROGRESS.labels(method=method, endpoint=path).dec()

        return response

    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing UUIDs and IDs with placeholders."""
        import re
        # Replace UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
            flags=re.IGNORECASE
        )
        # Replace numeric IDs
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
        return path


def get_metrics() -> Response:
    """Generate Prometheus metrics response."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Helper decorators for tracking metrics
def track_external_service(service_name: str):
    """Decorator to track external service calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                EXTERNAL_SERVICE_REQUESTS.labels(service=service_name, status="success").inc()
                return result
            except Exception as e:
                EXTERNAL_SERVICE_REQUESTS.labels(service=service_name, status="failure").inc()
                raise
            finally:
                duration = time.time() - start_time
                EXTERNAL_SERVICE_LATENCY.labels(service=service_name).observe(duration)
        return wrapper
    return decorator


def record_scan_created():
    """Record a new scan creation."""
    SCANS_TOTAL.labels(status="created").inc()
    SCANS_IN_PROGRESS.inc()


def record_scan_completed(duration_seconds: float, issues_by_impact: dict, pages_count: int):
    """Record scan completion with metrics."""
    SCANS_TOTAL.labels(status="completed").inc()
    SCANS_IN_PROGRESS.dec()
    SCAN_DURATION.observe(duration_seconds)
    PAGES_SCANNED.inc(pages_count)

    for impact, count in issues_by_impact.items():
        if count > 0:
            ISSUES_FOUND.labels(impact=impact).inc(count)


def record_scan_failed():
    """Record a scan failure."""
    SCANS_TOTAL.labels(status="failed").inc()
    SCANS_IN_PROGRESS.dec()


def record_auth_attempt(auth_type: str, success: bool):
    """Record authentication attempt."""
    status = "success" if success else "failure"
    AUTH_ATTEMPTS.labels(type=auth_type, status=status).inc()


def record_cache_access(cache_type: str, hit: bool):
    """Record cache access."""
    if hit:
        CACHE_HITS.labels(cache_type=cache_type).inc()
    else:
        CACHE_MISSES.labels(cache_type=cache_type).inc()


def record_report_generated(format: str, language: str, duration_seconds: float, success: bool = True):
    """Record report generation metrics."""
    status = "success" if success else "failure"
    REPORTS_GENERATED.labels(format=format, language=language, status=status).inc()
    if success:
        REPORT_GENERATION_DURATION.labels(format=format).observe(duration_seconds)


def record_export_created(format: str, export_type: str, size_bytes: int = 0):
    """Record export creation metrics."""
    EXPORTS_CREATED.labels(format=format, type=export_type).inc()
    if size_bytes > 0:
        EXPORT_SIZE_BYTES.labels(format=format).observe(size_bytes)


def record_email_sent(email_type: str, duration_seconds: float, success: bool = True):
    """Record email send metrics."""
    status = "success" if success else "failure"
    EMAILS_SENT.labels(type=email_type, status=status).inc()
    if success:
        EMAIL_SEND_DURATION.labels(type=email_type).observe(duration_seconds)


def record_websocket_connect(ws_type: str):
    """Record WebSocket connection."""
    WEBSOCKET_CONNECTIONS.labels(type=ws_type).inc()


def record_websocket_disconnect(ws_type: str):
    """Record WebSocket disconnection."""
    WEBSOCKET_CONNECTIONS.labels(type=ws_type).dec()


def record_websocket_message(ws_type: str, message_type: str):
    """Record WebSocket message sent."""
    WEBSOCKET_MESSAGES.labels(type=ws_type, message_type=message_type).inc()
