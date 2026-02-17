"""
Scans Router

API endpoints for accessibility scan management.
"""

import math
import logging
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func

from app.database import get_db
from app.services.cache import cache_get, cache_set, cache_delete
from app.services.metrics import record_scan_created
from app.services.queue import add_scan_job, cancel_job
from app.services.rate_limiter import (
    limiter,
    plan_limit_scan_create,
    plan_limit_scan_read,
    plan_limit_scan_list,
)
from app.utils.validators import validate_scan_url, URLValidationError

logger = logging.getLogger(__name__)
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
    PageListResponse,
)

# Cache TTL for completed scans (5 minutes)
SCAN_CACHE_TTL = 300

router = APIRouter()


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


def get_current_month_scan_count(db: Session, user_id: UUID) -> int:
    """Get the number of scans the user has created in the current month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    count = db.query(func.count(Scan.id)).filter(
        Scan.user_id == user_id,
        Scan.created_at >= month_start,
    ).scalar()

    return count or 0


@router.post("", response_model=ScanResponse, status_code=201)
@limiter.limit(plan_limit_scan_create)
async def create_scan(
    request: Request,
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
    plan_limits = current_user.plan_limits

    # Validate URL for SSRF protection
    try:
        _, validated_url, _ = validate_scan_url(scan_data.url)
    except URLValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    # Check monthly scan limit
    scans_per_month = plan_limits.get("scans_per_month", 3)
    if scans_per_month != -1:  # -1 means unlimited
        current_month_scans = get_current_month_scan_count(db, user_id)
        if current_month_scans >= scans_per_month:
            raise HTTPException(
                status_code=403,
                detail=f"Monthly scan limit reached ({scans_per_month} scans). "
                       f"Please upgrade your plan for more scans."
            )

    # Check pages per scan limit
    pages_per_scan_limit = plan_limits.get("pages_per_scan", 5)
    requested_pages = scan_data.max_pages if scan_data.crawl else 1
    if requested_pages > pages_per_scan_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Your plan allows up to {pages_per_scan_limit} pages per scan. "
                   f"Please upgrade your plan or reduce the number of pages."
        )

    # Enforce the limit on max_pages
    effective_max_pages = min(scan_data.max_pages, pages_per_scan_limit)

    # Create scan record with validated URL
    scan = Scan(
        user_id=user_id,
        url=validated_url,
        crawl=scan_data.crawl,
        max_pages=effective_max_pages,
        status=ScanStatus.QUEUED,
        progress_total=effective_max_pages if scan_data.crawl else 1,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Record metrics
    record_scan_created()

    # Add job to Redis queue using proper BullMQ format
    success = add_scan_job(
        scan_id=scan.id,
        url=validated_url,
        crawl=scan_data.crawl,
        max_pages=effective_max_pages,
        user_id=user_id,
        options={
            "captureScreenshots": True,
            "respectRobotsTxt": True,
        },
    )

    if not success:
        # Mark scan as failed since job couldn't be queued
        logger.error(f"Failed to queue scan job {scan.id}")
        scan.status = ScanStatus.FAILED
        scan.error_message = "Failed to queue scan job. Please try again later."
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan)

        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Failed to queue scan job. Please try again later."
        )

    return scan_to_response(scan)


@router.get("", response_model=ScanListResponse)
@limiter.limit(plan_limit_scan_list)
async def list_scans(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all scans for the current user.

    Supports pagination and filtering by status.
    """
    # Filter by authenticated user
    query = db.query(Scan).filter(Scan.user_id == current_user.id)

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
@limiter.limit(plan_limit_scan_read)
async def get_scan(
    request: Request,
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get details of a specific scan.
    """
    cache_key = f"scan:{scan_id}:{current_user.id}"

    # Try cache for completed scans
    cached = cache_get(cache_key)
    if cached:
        logger.debug(f"Cache hit for scan {scan_id}")
        return ScanResponse(**cached)

    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id,
    ).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    response = scan_to_response(scan)

    # Cache completed/failed scans (they won't change)
    if scan.status in [ScanStatus.COMPLETED, ScanStatus.FAILED, ScanStatus.CANCELLED]:
        cache_set(cache_key, response.model_dump(), SCAN_CACHE_TTL)

    return response


@router.delete("/{scan_id}", status_code=204)
@limiter.limit(plan_limit_scan_read)
async def delete_scan(
    request: Request,
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a scan and all associated data.
    """
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id,
    ).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    db.delete(scan)
    db.commit()

    # Invalidate cache
    cache_key = f"scan:{scan_id}:{current_user.id}"
    cache_delete(cache_key)

    return None


@router.get("/{scan_id}/issues", response_model=IssueListResponse)
@limiter.limit(plan_limit_scan_read)
async def get_scan_issues(
    request: Request,
    scan_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    impact: Optional[str] = Query(None, description="Filter by impact (critical,serious,moderate,minor)"),
    rule_id: Optional[str] = Query(None, description="Filter by rule ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all issues found in a scan.

    Supports pagination and filtering by impact level or rule ID.
    """
    # Verify scan exists and belongs to current user (eager load pages to avoid N+1)
    scan = db.query(Scan).options(
        joinedload(Scan.pages)
    ).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id,
    ).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Build page URL map once (pages already loaded via joinedload)
    page_url_map = {p.id: p.url for p in scan.pages}
    page_ids = list(page_url_map.keys())

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
    query = query.order_by(Issue.impact, Issue.created_at)

    # Get total count
    total = query.count()

    # Paginate
    issues = query.offset((page - 1) * per_page).limit(per_page).all()

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


@router.get("/{scan_id}/pages", response_model=PageListResponse)
@limiter.limit(plan_limit_scan_read)
async def get_scan_pages(
    request: Request,
    scan_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all pages scanned in a scan.

    Supports pagination for scans with many pages.
    """
    # Verify scan exists and belongs to current user
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id,
    ).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Query pages with pagination
    query = db.query(Page).filter(Page.scan_id == scan_id).order_by(Page.scanned_at)

    # Get total count
    total = query.count()

    # Paginate
    pages = query.offset((page - 1) * per_page).limit(per_page).all()

    return PageListResponse(
        pages=[
            PageResponse(
                id=p.id,
                url=p.url,
                title=p.title,
                score=p.score,
                issues_count=p.issues_count,
                passed_rules=p.passed_rules,
                failed_rules=p.failed_rules,
                load_time_ms=p.load_time_ms,
                scan_time_ms=p.scan_time_ms,
                error=p.error,
                scanned_at=p.scanned_at,
            )
            for p in pages
        ],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 1,
    )


@router.post("/{scan_id}/cancel", response_model=ScanResponse)
@limiter.limit(plan_limit_scan_create)
async def cancel_scan(
    request: Request,
    scan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a running or queued scan.
    """
    scan = db.query(Scan).filter(
        Scan.id == scan_id,
        Scan.user_id == current_user.id,
    ).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status not in [ScanStatus.QUEUED, ScanStatus.CRAWLING, ScanStatus.SCANNING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel scan with status: {scan.status.value}",
        )

    scan.status = ScanStatus.CANCELLED
    scan.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(scan)

    # Remove job from queue if still pending
    cancel_job(scan_id)

    return scan_to_response(scan)
