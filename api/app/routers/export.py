"""
Export Router

API endpoints for exporting scan data.
"""

from enum import Enum
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import User, Scan, Page, Issue
from app.routers.auth import get_current_user
from app.services.export import get_export_service
from app.services.rate_limiter import limiter
from app.services.metrics import record_export_created

router = APIRouter(prefix="/export", tags=["Export"])

# Rate limits for export operations
EXPORT_RATE_LIMIT = "20/minute"  # Exports can be resource-intensive


class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"


@router.get("/scans/{scan_id}/issues")
@limiter.limit(EXPORT_RATE_LIMIT)
async def export_scan_issues(
    request: Request,
    scan_id: UUID,
    format: ExportFormat = Query(ExportFormat.CSV, description="Export format"),
    include_html: bool = Query(False, description="Include element HTML in export"),
    impact: Optional[str] = Query(None, description="Filter by impact level"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export all issues from a scan.

    Available formats:
    - CSV: Spreadsheet-compatible format
    - JSON: Structured data format

    Filters:
    - impact: critical, serious, moderate, minor
    """
    # Get scan with user verification
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id
    ).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Build query with eager loading
    query = db.query(Issue).join(Page).filter(
        Page.scan_id == scan_id
    ).options(
        joinedload(Issue.page)
    )

    # Apply impact filter
    if impact:
        from app.models import ImpactLevel
        try:
            impact_level = ImpactLevel(impact)
            query = query.filter(Issue.impact == impact_level)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid impact level. Must be one of: critical, serious, moderate, minor"
            )

    issues = query.all()

    export_service = get_export_service()

    if format == ExportFormat.CSV:
        content = export_service.issues_to_csv(issues, include_html=include_html)
        filename = f"scan-{scan_id}-issues.csv"
        media_type = "text/csv"
    else:
        content = export_service.issues_to_json(issues, include_html=include_html)
        filename = f"scan-{scan_id}-issues.json"
        media_type = "application/json"

    # Record export metrics
    record_export_created(format.value, "issues", len(content.encode('utf-8') if isinstance(content, str) else content))

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/scans/{scan_id}/summary")
@limiter.limit(EXPORT_RATE_LIMIT)
async def export_scan_summary(
    request: Request,
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export full scan summary as JSON.

    Includes:
    - Scan metadata and score
    - Summary statistics
    - List of all scanned pages
    - Issue counts by impact and WCAG criteria
    """
    # Get scan with eager loading
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id
    ).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Get pages with eager loading
    pages = db.query(Page).filter(
        Page.scan_id == scan_id
    ).order_by(Page.depth, Page.url).all()

    # Get all issues with eager loading
    issues = db.query(Issue).join(Page).filter(
        Page.scan_id == scan_id
    ).options(
        joinedload(Issue.page)
    ).all()

    export_service = get_export_service()
    content = export_service.scan_summary_to_json(scan, pages, issues)

    filename = f"scan-{scan_id}-summary.json"

    # Record export metrics
    record_export_created("json", "summary", len(content.encode('utf-8') if isinstance(content, str) else content))

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/scans/{scan_id}/pages")
@limiter.limit(EXPORT_RATE_LIMIT)
async def export_scan_pages(
    request: Request,
    scan_id: UUID,
    format: ExportFormat = Query(ExportFormat.CSV, description="Export format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export all scanned pages from a scan.

    Available formats:
    - CSV: Spreadsheet-compatible format
    - JSON: Structured data format
    """
    # Get scan with user verification
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id
    ).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Get pages
    pages = db.query(Page).filter(
        Page.scan_id == scan_id
    ).order_by(Page.depth, Page.url).all()

    export_service = get_export_service()

    if format == ExportFormat.CSV:
        content = export_service.pages_to_csv(pages)
        filename = f"scan-{scan_id}-pages.csv"
        media_type = "text/csv"
    else:
        # Convert to JSON
        import json
        data = {
            "exported_at": None,
            "scan_id": str(scan_id),
            "total_pages": len(pages),
            "pages": [
                {
                    "id": str(page.id),
                    "url": page.url,
                    "title": page.title,
                    "depth": page.depth,
                    "score": page.score,
                    "issues_count": page.issues_count,
                    "passed_rules": page.passed_rules,
                    "failed_rules": page.failed_rules,
                    "load_time_ms": page.load_time_ms,
                    "scan_time_ms": page.scan_time_ms,
                    "error": page.error,
                }
                for page in pages
            ]
        }
        from datetime import datetime, timezone
        data["exported_at"] = datetime.now(timezone.utc).isoformat()
        content = json.dumps(data, indent=2, ensure_ascii=False)
        filename = f"scan-{scan_id}-pages.json"
        media_type = "application/json"

    # Record export metrics
    record_export_created(format.value, "pages", len(content.encode('utf-8') if isinstance(content, str) else content))

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
