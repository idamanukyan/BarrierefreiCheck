"""
Tests for metrics endpoint and service.
"""

import pytest
from fastapi.testclient import TestClient

from app.services.metrics import (
    record_scan_created,
    record_scan_completed,
    record_scan_failed,
    record_auth_attempt,
    record_cache_access,
)


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_metrics_endpoint_exists(self, client: TestClient):
        """Test that metrics endpoint returns data."""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Prometheus format uses text/plain with specific content type
        assert "text/plain" in response.headers["content-type"] or \
               "text/plain" in response.headers.get("content-type", "")

    def test_metrics_contains_app_info(self, client: TestClient):
        """Test that metrics include app info."""
        response = client.get("/metrics")
        content = response.text
        assert "app_info" in content

    def test_metrics_contains_http_metrics(self, client: TestClient):
        """Test that HTTP metrics are tracked."""
        # Make a request first
        client.get("/api/v1/health")

        response = client.get("/metrics")
        content = response.text
        assert "http_requests_total" in content
        assert "http_request_duration_seconds" in content


class TestMetricsRecording:
    """Tests for metric recording functions."""

    def test_record_scan_created(self):
        """Test scan created metric recording."""
        # Should not raise
        record_scan_created()

    def test_record_scan_completed(self):
        """Test scan completed metric recording."""
        record_scan_completed(
            duration_seconds=30.5,
            issues_by_impact={
                "critical": 2,
                "serious": 5,
                "moderate": 3,
                "minor": 1,
            },
            pages_count=10,
        )

    def test_record_scan_failed(self):
        """Test scan failed metric recording."""
        record_scan_failed()

    def test_record_auth_attempt_success(self):
        """Test auth success metric recording."""
        record_auth_attempt("login", success=True)

    def test_record_auth_attempt_failure(self):
        """Test auth failure metric recording."""
        record_auth_attempt("login", success=False)

    def test_record_cache_access(self):
        """Test cache access metric recording."""
        record_cache_access("dashboard", hit=True)
        record_cache_access("dashboard", hit=False)
