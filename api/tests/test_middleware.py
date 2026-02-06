"""
Tests for middleware components.
"""

import pytest
from fastapi.testclient import TestClient


class TestCorrelationId:
    """Tests for correlation ID middleware."""

    def test_generates_correlation_id(self, client: TestClient):
        """Test that correlation ID is generated for requests."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) > 0

    def test_preserves_incoming_correlation_id(self, client: TestClient):
        """Test that incoming correlation ID is preserved."""
        custom_id = "my-custom-correlation-id-12345"
        response = client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": custom_id},
        )
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == custom_id

    def test_returns_correlation_id_in_body(self, client: TestClient):
        """Test that health endpoint includes correlation ID."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "correlation_id" in data
        assert data["correlation_id"] == response.headers["X-Correlation-ID"]


class TestSecurityHeaders:
    """Tests for security headers middleware."""

    def test_content_type_options(self, client: TestClient):
        """Test X-Content-Type-Options header."""
        response = client.get("/api/v1/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_frame_options(self, client: TestClient):
        """Test X-Frame-Options header."""
        response = client.get("/api/v1/health")
        assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"

    def test_xss_protection(self, client: TestClient):
        """Test X-XSS-Protection header."""
        response = client.get("/api/v1/health")
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    def test_referrer_policy(self, client: TestClient):
        """Test Referrer-Policy header."""
        response = client.get("/api/v1/health")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client: TestClient):
        """Test Permissions-Policy header."""
        response = client.get("/api/v1/health")
        permissions = response.headers.get("Permissions-Policy")
        assert permissions is not None
        assert "camera=()" in permissions
        assert "microphone=()" in permissions

    def test_cache_control_for_api(self, client: TestClient):
        """Test Cache-Control header for API endpoints."""
        response = client.get("/api/v1/health")
        cache_control = response.headers.get("Cache-Control")
        assert "no-store" in cache_control
        assert "private" in cache_control


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check returns healthy status."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data
