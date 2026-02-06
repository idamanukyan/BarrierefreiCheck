"""
Tests for dashboard endpoints.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Scan, ScanStatus


class TestDashboardStats:
    """Tests for dashboard statistics."""

    def test_get_stats_empty(self, client: TestClient, auth_headers: dict, mock_redis):
        """Test getting stats with no data."""
        response = client.get("/api/v1/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["totalScans"] == 0
        assert data["pagesScanned"] == 0
        assert data["issuesFound"] == 0
        assert data["averageScore"] == 0.0

    def test_get_stats_with_data(
        self, client: TestClient, auth_headers: dict, test_scan: Scan, mock_redis
    ):
        """Test getting stats with scan data."""
        response = client.get("/api/v1/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["totalScans"] == 1
        assert data["pagesScanned"] == test_scan.pages_scanned
        assert data["issuesFound"] == test_scan.issues_count
        assert data["averageScore"] == test_scan.score

    def test_get_stats_multiple_scans(
        self, client: TestClient, auth_headers: dict, db: Session, test_user: User, mock_redis
    ):
        """Test stats calculation with multiple scans."""
        # Create multiple scans
        scan1 = Scan(
            user_id=test_user.id,
            url="https://example1.com",
            status=ScanStatus.COMPLETED,
            score=80.0,
            pages_scanned=5,
            issues_count=10,
            issues_critical=2,
            issues_serious=3,
            issues_moderate=3,
            issues_minor=2,
        )
        scan2 = Scan(
            user_id=test_user.id,
            url="https://example2.com",
            status=ScanStatus.COMPLETED,
            score=90.0,
            pages_scanned=3,
            issues_count=5,
            issues_critical=0,
            issues_serious=1,
            issues_moderate=2,
            issues_minor=2,
        )
        db.add_all([scan1, scan2])
        db.commit()

        response = client.get("/api/v1/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["totalScans"] == 2
        assert data["pagesScanned"] == 8  # 5 + 3
        assert data["issuesFound"] == 15  # 10 + 5
        assert data["averageScore"] == 85.0  # (80 + 90) / 2

    def test_get_stats_excludes_other_users(
        self, client: TestClient, auth_headers: dict, db: Session, test_user: User, mock_redis
    ):
        """Test that stats only include current user's data."""
        # Create scan for test user
        user_scan = Scan(
            user_id=test_user.id,
            url="https://my-site.com",
            status=ScanStatus.COMPLETED,
            score=75.0,
            pages_scanned=2,
            issues_count=8,
        )
        db.add(user_scan)

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
            url="https://other-site.com",
            status=ScanStatus.COMPLETED,
            score=100.0,
            pages_scanned=10,
            issues_count=0,
        )
        db.add(other_scan)
        db.commit()

        response = client.get("/api/v1/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should only include test user's scan
        assert data["totalScans"] == 1
        assert data["pagesScanned"] == 2
        assert data["averageScore"] == 75.0

    def test_get_stats_no_auth(self, client: TestClient):
        """Test getting stats without authentication."""
        response = client.get("/api/v1/dashboard/stats")
        assert response.status_code == 401

    def test_get_stats_issues_by_impact(
        self, client: TestClient, auth_headers: dict, db: Session, test_user: User, mock_redis
    ):
        """Test issues by impact aggregation."""
        scan = Scan(
            user_id=test_user.id,
            url="https://example.com",
            status=ScanStatus.COMPLETED,
            score=70.0,
            issues_critical=5,
            issues_serious=10,
            issues_moderate=15,
            issues_minor=20,
        )
        db.add(scan)
        db.commit()

        response = client.get("/api/v1/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["issuesByImpact"]["critical"] == 5
        assert data["issuesByImpact"]["serious"] == 10
        assert data["issuesByImpact"]["moderate"] == 15
        assert data["issuesByImpact"]["minor"] == 20

    def test_get_stats_recent_scans(
        self, client: TestClient, auth_headers: dict, db: Session, test_user: User, mock_redis
    ):
        """Test recent scans in response."""
        # Create 7 scans
        for i in range(7):
            scan = Scan(
                user_id=test_user.id,
                url=f"https://example{i}.com",
                status=ScanStatus.COMPLETED,
                score=80.0 + i,
            )
            db.add(scan)
        db.commit()

        response = client.get("/api/v1/dashboard/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should only return 5 most recent
        assert len(data["recentScans"]) == 5
