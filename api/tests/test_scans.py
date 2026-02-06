"""
Tests for scan endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Scan, ScanStatus


class TestCreateScan:
    """Tests for creating scans."""

    def test_create_scan_success(self, client: TestClient, auth_headers: dict, db: Session):
        """Test successful scan creation."""
        with patch("app.routers.scans.redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_redis.from_url.return_value = mock_instance

            response = client.post(
                "/api/v1/scans",
                json={
                    "url": "https://example.com",
                    "crawl": False,
                    "max_pages": 1,
                },
                headers=auth_headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["url"] == "https://example.com"
        assert data["status"] == "queued"

    def test_create_scan_no_auth(self, client: TestClient):
        """Test scan creation without authentication."""
        response = client.post(
            "/api/v1/scans",
            json={
                "url": "https://example.com",
            },
        )
        assert response.status_code == 401

    def test_create_scan_invalid_url(self, client: TestClient, auth_headers: dict):
        """Test scan creation with invalid URL."""
        response = client.post(
            "/api/v1/scans",
            json={
                "url": "not-a-valid-url",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestListScans:
    """Tests for listing scans."""

    def test_list_scans_empty(self, client: TestClient, auth_headers: dict):
        """Test listing scans when none exist."""
        response = client.get("/api/v1/scans", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_scans_with_data(self, client: TestClient, auth_headers: dict, test_scan: Scan):
        """Test listing scans with existing data."""
        response = client.get("/api/v1/scans", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(test_scan.id)
        assert data["total"] == 1

    def test_list_scans_pagination(
        self, client: TestClient, auth_headers: dict, db: Session, test_user: User
    ):
        """Test scan listing pagination."""
        # Create multiple scans
        for i in range(15):
            scan = Scan(
                user_id=test_user.id,
                url=f"https://example{i}.com",
                status=ScanStatus.COMPLETED,
            )
            db.add(scan)
        db.commit()

        # Test first page
        response = client.get(
            "/api/v1/scans?page=1&page_size=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 15

        # Test second page
        response = client.get(
            "/api/v1/scans?page=2&page_size=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5

    def test_list_scans_no_auth(self, client: TestClient):
        """Test listing scans without authentication."""
        response = client.get("/api/v1/scans")
        assert response.status_code == 401

    def test_list_scans_isolation(
        self, client: TestClient, auth_headers: dict, db: Session, test_user: User
    ):
        """Test that users only see their own scans."""
        # Create another user with scans
        other_user = User(
            email="other@example.com",
            password_hash="hash",
            is_active=True,
        )
        db.add(other_user)
        db.commit()

        other_scan = Scan(
            user_id=other_user.id,
            url="https://other-example.com",
            status=ScanStatus.COMPLETED,
        )
        db.add(other_scan)

        user_scan = Scan(
            user_id=test_user.id,
            url="https://my-example.com",
            status=ScanStatus.COMPLETED,
        )
        db.add(user_scan)
        db.commit()

        # Should only see own scan
        response = client.get("/api/v1/scans", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["url"] == "https://my-example.com"


class TestGetScan:
    """Tests for getting a single scan."""

    def test_get_scan_success(self, client: TestClient, auth_headers: dict, test_scan: Scan):
        """Test getting a scan by ID."""
        response = client.get(
            f"/api/v1/scans/{test_scan.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_scan.id)
        assert data["url"] == test_scan.url

    def test_get_scan_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting non-existent scan."""
        import uuid
        response = client.get(
            f"/api/v1/scans/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_get_scan_no_auth(self, client: TestClient, test_scan: Scan):
        """Test getting scan without authentication."""
        response = client.get(f"/api/v1/scans/{test_scan.id}")
        assert response.status_code == 401

    def test_get_scan_other_user(
        self, client: TestClient, auth_headers: dict, db: Session
    ):
        """Test getting another user's scan."""
        other_user = User(
            email="other@example.com",
            password_hash="hash",
            is_active=True,
        )
        db.add(other_user)
        db.commit()

        other_scan = Scan(
            user_id=other_user.id,
            url="https://other-example.com",
            status=ScanStatus.COMPLETED,
        )
        db.add(other_scan)
        db.commit()

        response = client.get(
            f"/api/v1/scans/{other_scan.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeleteScan:
    """Tests for deleting scans."""

    def test_delete_scan_success(
        self, client: TestClient, auth_headers: dict, test_scan: Scan, db: Session
    ):
        """Test successful scan deletion."""
        response = client.delete(
            f"/api/v1/scans/{test_scan.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify deletion
        deleted_scan = db.query(Scan).filter(Scan.id == test_scan.id).first()
        assert deleted_scan is None

    def test_delete_scan_not_found(self, client: TestClient, auth_headers: dict):
        """Test deleting non-existent scan."""
        import uuid
        response = client.delete(
            f"/api/v1/scans/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_delete_scan_no_auth(self, client: TestClient, test_scan: Scan):
        """Test deleting scan without authentication."""
        response = client.delete(f"/api/v1/scans/{test_scan.id}")
        assert response.status_code == 401
