"""
Scans Router

API endpoints for accessibility scan management.
"""

import math
from uuid import UUID
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc
import redis

from app.database import get_db
from app.config import settings
from app.models.scan import Scan, Page, Issue, ScanStatus, ImpactLevel, WcagLevel
from app.models import User
from app.routers.auth import get_current_user
from app.schemas.scan import (
    ScanCreate,
    ScanResponse,
    ScanListResponse,
    ScanProgress,
    IssuesByImpact,
    IssueResponse,
    IssueListResponse,
    ElementInfo,
    PageResponse,
)

router = APIRouter()

# Redis connection for job queue
def get_redis():
    return redis.from_url(settings.redis_url)


def scan_to_response(scan: Scan) -> ScanResponse:
    """Convert Scan model to response schema."""
    return ScanResponse(
        id=scan.id,
        url=scan.url,
        crawl=scan.crawl,
        max_pages=scan.max_pages,
        status=scan.status.value,
        progress=ScanProgress(
            stage=scan.progress_stage,
            current=scan.progress_current,
            total=scan.progress_total,
        ),
        score=scan.score,
        pages_scanned=scan.pages_scanned,
        issues_count=scan.issues_count,
        issues_by_impact=IssuesByImpact(
            critical=scan.issues_critical or 0,
            serious=scan.issues_serious or 0,
            moderate=scan.issues_moderate or 0,
            minor=scan.issues_minor or 0,
        ),
        created_at=scan.created_at,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        duration_seconds=scan.duration_seconds,
        error_message=scan.error_message,
    )


@router.post("", response_model=ScanResponse, status_code=201)
async def create_scan(
    scan_data: ScanCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start a new accessibility scan.

    - **url**: The URL to scan
    - **crawl**: Whether to crawl and scan multiple pages
    - **max_pages**: Maximum number of pages to scan (if crawl=True)
    """
    user_id = current_user.id

    # Create scan record
    scan = Scan(
        user_id=user_id,
        url=scan_data.url,
        crawl=scan_data.crawl,
        max_pages=scan_data.max_pages,
        status=ScanStatus.QUEUED,
        progress_total=scan_data.max_pages if scan_data.crawl else 1,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Add job to Redis queue
    try:
        r = get_redis()
        job_data = {
            "scanId": str(scan.id),
            "url": scan_data.url,
            "crawl": scan_data.crawl,
            "maxPages": scan_data.max_pages,
            "userId": str(user_id),
            "options": {
                "captureScreenshots": True,
                "respectRobotsTxt": True,
            },
        }

        # Push to BullMQ-compatible queue
        # BullMQ uses a specific Redis key structure
        import json
        job_id = str(scan.id)
        job = {
            "name": f"scan-{job_id}",
            "data": job_data,
            "opts": {
                "jobId": job_id,
                "attempts": 3,
            },
        }
        r.rpush("bull:accessibility-scans:wait", json.dumps(job))

    except Exception as e:
        # Log error but don't fail - scan record is created
        print(f"Error adding job to queue: {e}")

    return scan_to_response(scan)


@router.get("", response_model=ScanListResponse)
async def list_scans(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
):
    """
    List all scans for the current user.

    Supports pagination and filtering by status.
    """
    # TODO: Filter by authenticated user
    query = db.query(Scan)

    # Filter by status
    if status:
        try:
            status_enum = ScanStatus(status)
            query = query.filter(Scan.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Order by created_at desc
    query = query.order_by(desc(Scan.created_at))

    # Get total count
    total = query.count()

    # Paginate
    scans = query.offset((page - 1) * per_page).limit(per_page).all()

    return ScanListResponse(
        scans=[scan_to_response(scan) for scan in scans],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 1,
    )


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: UUID, db: Session = Depends(get_db)):
    """
    Get details of a specific scan.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return scan_to_response(scan)


@router.delete("/{scan_id}", status_code=204)
async def delete_scan(scan_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a scan and all associated data.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    db.delete(scan)
    db.commit()

    return None


@router.get("/{scan_id}/issues", response_model=IssueListResponse)
async def get_scan_issues(
    scan_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    impact: Optional[str] = Query(None, description="Filter by impact (critical,serious,moderate,minor)"),
    rule_id: Optional[str] = Query(None, description="Filter by rule ID"),
    db: Session = Depends(get_db),
):
    """
    Get all issues found in a scan.

    Supports pagination and filtering by impact level or rule ID.
    """
    # Verify scan exists
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Get page IDs for this scan
    page_ids = [p.id for p in scan.pages]

    if not page_ids:
        return IssueListResponse(
            issues=[],
            total=0,
            page=page,
            per_page=per_page,
            pages=1,
        )

    # Query issues
    query = db.query(Issue).filter(Issue.page_id.in_(page_ids))

    # Filter by impact
    if impact:
        impact_values = [i.strip() for i in impact.split(",")]
        impact_enums = []
        for iv in impact_values:
            try:
                impact_enums.append(ImpactLevel(iv))
            except ValueError:
                pass
        if impact_enums:
            query = query.filter(Issue.impact.in_(impact_enums))

    # Filter by rule_id
    if rule_id:
        query = query.filter(Issue.rule_id == rule_id)

    # Order by impact severity
    impact_order = {
        ImpactLevel.CRITICAL: 0,
        ImpactLevel.SERIOUS: 1,
        ImpactLevel.MODERATE: 2,
        ImpactLevel.MINOR: 3,
    }
    query = query.order_by(Issue.impact, Issue.created_at)

    # Get total count
    total = query.count()

    # Paginate
    issues = query.offset((page - 1) * per_page).limit(per_page).all()

    # Get page URLs for issues
    page_url_map = {p.id: p.url for p in scan.pages}

    issue_responses = []
    for issue in issues:
        issue_responses.append(
            IssueResponse(
                id=issue.id,
                rule_id=issue.rule_id,
                impact=issue.impact.value,
                wcag_criteria=issue.wcag_criteria,
                wcag_level=issue.wcag_level.value if issue.wcag_level else None,
                bfsg_reference=issue.bfsg_reference,
                title_de=issue.title_de,
                description_de=issue.description_de,
                fix_suggestion_de=issue.fix_suggestion_de,
                element=ElementInfo(
                    selector=issue.element_selector,
                    html=issue.element_html,
                ),
                help_url=issue.help_url,
                screenshot_url=issue.screenshot_path,
                page_url=page_url_map.get(issue.page_id),
            )
        )

    return IssueListResponse(
        issues=issue_responses,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 1,
    )


@router.get("/{scan_id}/pages", response_model=list[PageResponse])
async def get_scan_pages(
    scan_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get all pages scanned in a scan.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return [
        PageResponse(
            id=page.id,
            url=page.url,
            title=page.title,
            score=page.score,
            issues_count=page.issues_count,
            passed_rules=page.passed_rules,
            failed_rules=page.failed_rules,
            load_time_ms=page.load_time_ms,
            scan_time_ms=page.scan_time_ms,
            error=page.error,
            scanned_at=page.scanned_at,
        )
        for page in scan.pages
    ]


@router.post("/{scan_id}/cancel", response_model=ScanResponse)
async def cancel_scan(scan_id: UUID, db: Session = Depends(get_db)):
    """
    Cancel a running or queued scan.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status not in [ScanStatus.QUEUED, ScanStatus.CRAWLING, ScanStatus.SCANNING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel scan with status: {scan.status.value}",
        )

    scan.status = ScanStatus.CANCELLED
    scan.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(scan)

    # TODO: Remove job from queue if still pending

    return scan_to_response(scan)
