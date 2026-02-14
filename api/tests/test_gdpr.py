"""
Tests for GDPR compliance endpoints.

Tests cover:
- Data summary (Art. 15 GDPR - Right of Access)
- Data export (Art. 20 GDPR - Right to Data Portability)
- Data deletion (Art. 17 GDPR - Right to be Forgotten)
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    User,
    Scan,
    Page,
    Issue,
    APIKey,
    ScanStatus,
    ImpactLevel,
    WcagLevel,
)
from app.models.api_key import hash_api_key
from app.routers.auth import get_password_hash, create_access_token


@pytest.fixture
def test_user_with_data(db: Session) -> User:
    """Create a test user with associated data (scans, pages, issues, API keys)."""
    user = User(
        email="gdprtest@example.com",
        password_hash=get_password_hash("TestPassword123"),
        full_name="GDPR Test User",
        company="Test GmbH",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Add a scan with pages and issues
    scan = Scan(
        user_id=user.id,
        url="https://example.com",
        crawl=True,
        max_pages=10,
        status=ScanStatus.COMPLETED,
        score=75.5,
        pages_scanned=2,
        issues_count=3,
        issues_critical=1,
        issues_serious=1,
        issues_moderate=1,
        issues_minor=0,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Add pages
    page1 = Page(
        scan_id=scan.id,
        url="https://example.com/",
        title="Home Page",
        depth=0,
        score=80.0,
        issues_count=2,
        passed_rules=50,
        failed_rules=2,
        load_time_ms=500,
        scan_time_ms=1000,
    )
    page2 = Page(
        scan_id=scan.id,
        url="https://example.com/about",
        title="About Page",
        depth=1,
        score=70.0,
        issues_count=1,
        passed_rules=48,
        failed_rules=1,
        load_time_ms=400,
        scan_time_ms=800,
    )
    db.add_all([page1, page2])
    db.commit()
    db.refresh(page1)
    db.refresh(page2)

    # Add issues
    issue1 = Issue(
        page_id=page1.id,
        rule_id="image-alt",
        impact=ImpactLevel.CRITICAL,
        wcag_criteria=["1.1.1"],
        wcag_level=WcagLevel.A,
        bfsg_reference="BFSG §3 Abs. 1",
        title_de="Bild ohne Alternativtext",
        description_de="Dieses Bild hat keinen Alternativtext.",
        fix_suggestion_de="Fügen Sie einen beschreibenden alt-Attribut hinzu.",
        element_selector="img.hero-image",
        element_html='<img src="hero.jpg" class="hero-image">',
        help_url="https://dequeuniversity.com/rules/axe/image-alt",
    )
    issue2 = Issue(
        page_id=page1.id,
        rule_id="color-contrast",
        impact=ImpactLevel.SERIOUS,
        wcag_criteria=["1.4.3"],
        wcag_level=WcagLevel.AA,
        bfsg_reference="BFSG §3 Abs. 2",
        title_de="Unzureichender Farbkontrast",
        description_de="Der Text hat nicht genügend Kontrast zum Hintergrund.",
        fix_suggestion_de="Erhöhen Sie den Kontrastwert auf mindestens 4.5:1.",
        element_selector="p.subtitle",
    )
    issue3 = Issue(
        page_id=page2.id,
        rule_id="label",
        impact=ImpactLevel.MODERATE,
        wcag_criteria=["1.3.1", "4.1.2"],
        wcag_level=WcagLevel.A,
        title_de="Formularfeld ohne Label",
        description_de="Das Eingabefeld hat kein zugeordnetes Label.",
        fix_suggestion_de="Verwenden Sie ein <label>-Element.",
        element_selector="input#email",
    )
    db.add_all([issue1, issue2, issue3])
    db.commit()

    # Add an API key
    api_key = APIKey(
        user_id=user.id,
        key_prefix="ac_test",
        key_hash=hash_api_key("ac_test_key_12345678901234567890"),
        name="Test API Key",
        description="API key for testing",
        scopes=["scans:read", "scans:write"],
        is_active=True,
    )
    db.add(api_key)
    db.commit()

    return user


@pytest.fixture
def gdpr_auth_headers(test_user_with_data: User) -> dict:
    """Create authorization headers for GDPR test user."""
    token = create_access_token(data={"sub": test_user_with_data.email})
    return {"Authorization": f"Bearer {token}"}


class TestDataSummary:
    """Tests for data summary endpoint (Art. 15 GDPR)."""

    def test_get_data_summary_success(
        self, client: TestClient, gdpr_auth_headers: dict, test_user_with_data: User
    ):
        """Test successful data summary retrieval."""
        response = client.get("/api/v1/users/me/summary", headers=gdpr_auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "user" in data
        assert "data_counts" in data

        assert data["user"]["email"] == test_user_with_data.email
        assert data["data_counts"]["scans"] == 1
        assert data["data_counts"]["pages"] == 2
        assert data["data_counts"]["issues"] == 3
        assert data["data_counts"]["api_keys"] == 1

    def test_get_data_summary_no_auth(self, client: TestClient):
        """Test data summary without authentication."""
        response = client.get("/api/v1/users/me/summary")
        assert response.status_code == 401

    def test_get_data_summary_empty_user(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Test data summary for user with no data."""
        response = client.get("/api/v1/users/me/summary", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["data_counts"]["scans"] == 0
        assert data["data_counts"]["pages"] == 0
        assert data["data_counts"]["issues"] == 0


class TestDataExport:
    """Tests for data export endpoint (Art. 20 GDPR)."""

    def test_export_user_data_success(
        self, client: TestClient, gdpr_auth_headers: dict, test_user_with_data: User
    ):
        """Test successful data export."""
        response = client.get("/api/v1/users/me/export", headers=gdpr_auth_headers)
        assert response.status_code == 200

        data = response.json()

        # Check export metadata
        assert "export_metadata" in data
        assert data["export_metadata"]["format_version"] == "1.0"
        assert "Art. 20 GDPR" in data["export_metadata"]["gdpr_article"]

        # Check user data
        assert "user" in data
        assert data["user"]["email"] == test_user_with_data.email
        assert data["user"]["full_name"] == "GDPR Test User"
        assert data["user"]["company"] == "Test GmbH"

        # Check scans
        assert "scans" in data
        assert len(data["scans"]) == 1
        scan = data["scans"][0]
        assert scan["url"] == "https://example.com"
        assert scan["score"] == 75.5

        # Check pages within scan
        assert len(scan["pages"]) == 2
        assert any(p["url"] == "https://example.com/" for p in scan["pages"])

        # Check issues within pages
        total_issues = sum(len(p["issues"]) for p in scan["pages"])
        assert total_issues == 3

        # Check API keys (no secrets exposed)
        assert "api_keys" in data
        assert len(data["api_keys"]) == 1
        assert data["api_keys"][0]["name"] == "Test API Key"
        assert "key_hash" not in data["api_keys"][0]  # Hash should not be exported

    def test_export_user_data_no_auth(self, client: TestClient):
        """Test data export without authentication."""
        response = client.get("/api/v1/users/me/export")
        assert response.status_code == 401

    def test_download_user_data(
        self, client: TestClient, gdpr_auth_headers: dict, test_user_with_data: User
    ):
        """Test data download as JSON file."""
        response = client.get(
            "/api/v1/users/me/export/download", headers=gdpr_auth_headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers.get("content-disposition", "")
        assert "barrierefrei_check_export" in response.headers.get(
            "content-disposition", ""
        )

        # Verify content is valid JSON
        import json

        data = json.loads(response.content)
        assert "export_metadata" in data
        assert "user" in data


class TestDataDeletion:
    """Tests for data deletion endpoint (Art. 17 GDPR)."""

    def test_delete_user_data_success(
        self,
        client: TestClient,
        db: Session,
        gdpr_auth_headers: dict,
        test_user_with_data: User,
    ):
        """Test successful data deletion."""
        user_id = test_user_with_data.id

        # Verify user exists before deletion
        user = db.query(User).filter(User.id == user_id).first()
        assert user is not None

        response = client.delete(
            "/api/v1/users/me/data",
            headers=gdpr_auth_headers,
            json={
                "password": "TestPassword123",
                "confirm_deletion": True,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["deleted"] is True
        assert "deleted_at" in data
        assert data["counts"]["scans"] == 1
        assert data["counts"]["api_keys"] == 1

        # Verify user no longer exists
        db.expire_all()
        user = db.query(User).filter(User.id == user_id).first()
        assert user is None

        # Verify associated data was deleted
        from app.models import Scan, APIKey

        scans = db.query(Scan).filter(Scan.user_id == user_id).all()
        assert len(scans) == 0

        api_keys = db.query(APIKey).filter(APIKey.user_id == user_id).all()
        assert len(api_keys) == 0

    def test_delete_user_data_wrong_password(
        self, client: TestClient, gdpr_auth_headers: dict, test_user_with_data: User
    ):
        """Test deletion with wrong password."""
        response = client.delete(
            "/api/v1/users/me/data",
            headers=gdpr_auth_headers,
            json={
                "password": "WrongPassword123",
                "confirm_deletion": True,
            },
        )
        assert response.status_code == 401
        assert "password" in response.json()["detail"].lower()

    def test_delete_user_data_not_confirmed(
        self, client: TestClient, gdpr_auth_headers: dict, test_user_with_data: User
    ):
        """Test deletion without confirmation."""
        response = client.delete(
            "/api/v1/users/me/data",
            headers=gdpr_auth_headers,
            json={
                "password": "TestPassword123",
                "confirm_deletion": False,
            },
        )
        assert response.status_code == 400
        assert "not confirmed" in response.json()["detail"].lower()

    def test_delete_user_data_no_auth(self, client: TestClient):
        """Test deletion without authentication."""
        response = client.delete(
            "/api/v1/users/me/data",
            json={
                "password": "anypassword",
                "confirm_deletion": True,
            },
        )
        assert response.status_code == 401

    def test_delete_user_data_missing_password(
        self, client: TestClient, gdpr_auth_headers: dict
    ):
        """Test deletion without password."""
        response = client.delete(
            "/api/v1/users/me/data",
            headers=gdpr_auth_headers,
            json={
                "confirm_deletion": True,
            },
        )
        assert response.status_code == 422


class TestGDPRService:
    """Tests for GDPR service functions."""

    def test_get_user_export_data(
        self, db: Session, test_user_with_data: User
    ):
        """Test export data generation."""
        from app.services.gdpr import get_gdpr_service

        gdpr_service = get_gdpr_service()
        export_data = gdpr_service.get_user_export_data(test_user_with_data.id, db)

        assert export_data is not None
        assert "user" in export_data
        assert export_data["user"]["email"] == test_user_with_data.email

    def test_export_to_json(self, db: Session, test_user_with_data: User):
        """Test JSON export generation."""
        import json
        from app.services.gdpr import get_gdpr_service

        gdpr_service = get_gdpr_service()
        json_str = gdpr_service.export_to_json(test_user_with_data.id, db)

        # Verify valid JSON
        data = json.loads(json_str)
        assert "user" in data
        assert "scans" in data

    def test_get_user_data_summary(
        self, db: Session, test_user_with_data: User
    ):
        """Test data summary generation."""
        from app.services.gdpr import get_gdpr_service

        gdpr_service = get_gdpr_service()
        summary = gdpr_service.get_user_data_summary(test_user_with_data.id, db)

        assert "user" in summary
        assert "data_counts" in summary
        assert summary["data_counts"]["scans"] == 1
        assert summary["data_counts"]["issues"] == 3

    def test_delete_nonexistent_user(self, db: Session):
        """Test deletion of non-existent user."""
        import uuid
        from app.services.gdpr import get_gdpr_service

        gdpr_service = get_gdpr_service()
        result = gdpr_service.delete_user_data(uuid.uuid4(), db)

        assert result["deleted"] is False
        assert "error" in result


class TestDataRetentionPolicy:
    """Tests for data retention policy."""

    def test_apply_retention_policy(self, db: Session, test_user_with_data: User):
        """Test retention policy application."""
        from app.services.gdpr import get_gdpr_service

        gdpr_service = get_gdpr_service()

        # Create an old scan (older than retention period)
        old_scan = Scan(
            user_id=test_user_with_data.id,
            url="https://old-example.com",
            status=ScanStatus.COMPLETED,
            created_at=datetime.now(timezone.utc) - timedelta(days=800),
        )
        db.add(old_scan)
        db.commit()

        # Apply retention policy with 730 days
        result = gdpr_service.apply_retention_policy(db, retention_days=730)

        assert "deleted_counts" in result
        assert result["deleted_counts"]["scans"] == 1

        # Verify old scan is deleted
        db.expire_all()
        remaining = db.query(Scan).filter(Scan.id == old_scan.id).first()
        assert remaining is None

        # Verify recent scan still exists
        recent_scans = db.query(Scan).filter(
            Scan.user_id == test_user_with_data.id
        ).all()
        assert len(recent_scans) == 1

    def test_retention_policy_preserves_recent_data(
        self, db: Session, test_user_with_data: User
    ):
        """Test that retention policy preserves recent data."""
        from app.services.gdpr import get_gdpr_service

        gdpr_service = get_gdpr_service()

        # Count scans before
        scans_before = db.query(Scan).filter(
            Scan.user_id == test_user_with_data.id
        ).count()

        # Apply retention policy
        result = gdpr_service.apply_retention_policy(db, retention_days=730)

        # Recent scans should not be affected
        scans_after = db.query(Scan).filter(
            Scan.user_id == test_user_with_data.id
        ).count()

        assert scans_before == scans_after
