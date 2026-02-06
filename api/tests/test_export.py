"""
Tests for export endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Scan, Page, Issue, ScanStatus, ImpactLevel, WcagLevel


@pytest.fixture
def scan_with_issues(db: Session, test_user: User) -> Scan:
    """Create a scan with pages and issues for export testing."""
    scan = Scan(
        user_id=test_user.id,
        url="https://example.com",
        status=ScanStatus.COMPLETED,
        score=75.0,
        pages_scanned=2,
        issues_count=3,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Add pages
    page1 = Page(
        scan_id=scan.id,
        url="https://example.com/",
        title="Home Page",
        score=80.0,
        issues_count=2,
    )
    page2 = Page(
        scan_id=scan.id,
        url="https://example.com/about",
        title="About Page",
        score=70.0,
        issues_count=1,
    )
    db.add_all([page1, page2])
    db.commit()
    db.refresh(page1)
    db.refresh(page2)

    # Add issues
    issue1 = Issue(
        page_id=page1.id,
        rule_id="color-contrast",
        impact=ImpactLevel.SERIOUS,
        wcag_criteria=["1.4.3"],
        wcag_level=WcagLevel.AA,
        title_de="Farbkontrast nicht ausreichend",
        description_de="Der Farbkontrast zwischen Text und Hintergrund ist zu gering.",
        element_selector=".header-text",
    )
    issue2 = Issue(
        page_id=page1.id,
        rule_id="image-alt",
        impact=ImpactLevel.CRITICAL,
        wcag_criteria=["1.1.1"],
        wcag_level=WcagLevel.A,
        title_de="Bild ohne Alternativtext",
        description_de="Das Bild hat keinen alt-Text.",
        element_selector="img.logo",
    )
    issue3 = Issue(
        page_id=page2.id,
        rule_id="link-name",
        impact=ImpactLevel.MODERATE,
        wcag_criteria=["2.4.4"],
        wcag_level=WcagLevel.A,
        title_de="Link ohne erkennbaren Text",
        description_de="Der Link hat keinen zugänglichen Namen.",
        element_selector="a.nav-link",
    )
    db.add_all([issue1, issue2, issue3])
    db.commit()

    return scan


class TestExportIssues:
    """Tests for exporting issues."""

    def test_export_issues_csv(
        self, client: TestClient, auth_headers: dict, scan_with_issues: Scan
    ):
        """Test exporting issues as CSV."""
        response = client.get(
            f"/api/v1/export/scans/{scan_with_issues.id}/issues?format=csv",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers.get("content-disposition", "")

        # Check CSV content
        content = response.text
        assert "rule_id" in content
        assert "color-contrast" in content
        assert "image-alt" in content

    def test_export_issues_json(
        self, client: TestClient, auth_headers: dict, scan_with_issues: Scan
    ):
        """Test exporting issues as JSON."""
        response = client.get(
            f"/api/v1/export/scans/{scan_with_issues.id}/issues?format=json",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        data = response.json()
        assert "issues" in data
        assert data["total_issues"] == 3
        assert len(data["issues"]) == 3

    def test_export_issues_filter_by_impact(
        self, client: TestClient, auth_headers: dict, scan_with_issues: Scan
    ):
        """Test filtering exported issues by impact."""
        response = client.get(
            f"/api/v1/export/scans/{scan_with_issues.id}/issues?format=json&impact=critical",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total_issues"] == 1
        assert data["issues"][0]["impact"] == "critical"

    def test_export_issues_not_found(self, client: TestClient, auth_headers: dict):
        """Test exporting issues for non-existent scan."""
        import uuid
        response = client.get(
            f"/api/v1/export/scans/{uuid.uuid4()}/issues",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestExportSummary:
    """Tests for exporting scan summary."""

    def test_export_summary(
        self, client: TestClient, auth_headers: dict, scan_with_issues: Scan
    ):
        """Test exporting scan summary."""
        response = client.get(
            f"/api/v1/export/scans/{scan_with_issues.id}/summary",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "scan" in data
        assert "summary" in data
        assert "pages" in data
        assert data["scan"]["id"] == str(scan_with_issues.id)
        assert data["summary"]["total_issues"] == 3
        assert len(data["pages"]) == 2


class TestExportPages:
    """Tests for exporting pages."""

    def test_export_pages_csv(
        self, client: TestClient, auth_headers: dict, scan_with_issues: Scan
    ):
        """Test exporting pages as CSV."""
        response = client.get(
            f"/api/v1/export/scans/{scan_with_issues.id}/pages?format=csv",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        content = response.text
        assert "url" in content
        assert "example.com" in content

    def test_export_pages_json(
        self, client: TestClient, auth_headers: dict, scan_with_issues: Scan
    ):
        """Test exporting pages as JSON."""
        response = client.get(
            f"/api/v1/export/scans/{scan_with_issues.id}/pages?format=json",
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "pages" in data
        assert data["total_pages"] == 2
