"""
Share Links Router

Endpoints for creating and managing shareable report links,
plus public access to shared reports.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import User, Report, ShareableReportLink, hash_share_token
from app.routers.auth import get_current_user
from app.services.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limits
SHARE_LINK_RATE_LIMIT = "20/minute"
PUBLIC_ACCESS_RATE_LIMIT = "60/minute"


# Pydantic Schemas
class ShareLinkCreate(BaseModel):
    """Schema for creating a share link."""
    name: Optional[str] = Field(None, max_length=100, description="Friendly name for the link")
    expires_in_days: int = Field(7, ge=1, le=90, description="Days until expiration (1-90)")


class ShareLinkResponse(BaseModel):
    """Response schema for a share link (without the token)."""
    id: str
    token_prefix: str
    name: Optional[str]
    expires_at: datetime
    is_active: bool
    access_count: int
    last_accessed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ShareLinkCreateResponse(BaseModel):
    """Response when creating a new share link - includes the plain token (shown only once)."""
    link: ShareLinkResponse
    token: str = Field(..., description="The share token. Store this - it won't be shown again!")
    share_url: str = Field(..., description="Full URL to share")


class ShareLinkListResponse(BaseModel):
    """Response for listing share links."""
    items: List[ShareLinkResponse]
    total: int


class SharedReportResponse(BaseModel):
    """Response for public shared report access."""
    report: dict
    scan: dict
    shared_by: Optional[str]
    expires_at: datetime


# Helper functions
def link_to_response(link: ShareableReportLink) -> ShareLinkResponse:
    """Convert a ShareableReportLink model to a response schema."""
    return ShareLinkResponse(
        id=str(link.id),
        token_prefix=link.token_prefix,
        name=link.name,
        expires_at=link.expires_at,
        is_active=link.is_active,
        access_count=link.access_count or 0,
        last_accessed_at=link.last_accessed_at,
        created_at=link.created_at,
    )


# ============================================================================
# Authenticated Endpoints (for managing share links)
# ============================================================================

@router.post("/reports/{report_id}/share", response_model=ShareLinkCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(SHARE_LINK_RATE_LIMIT)
async def create_share_link(
    request: Request,
    report_id: UUID,
    link_data: ShareLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a shareable link for a report.

    The share token will be shown only once in the response. Store it securely!
    Anyone with the token can view the report until it expires.
    """
    # Verify report exists and belongs to user
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == current_user.id,
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Check if report is completed
    if report.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only share completed reports"
        )

    # Limit number of share links per report
    existing_count = db.query(ShareableReportLink).filter(
        ShareableReportLink.report_id == report_id,
        ShareableReportLink.is_active == True,
    ).count()

    if existing_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 active share links per report. Revoke an existing link first."
        )

    # Calculate expiration
    expires_at = datetime.now(timezone.utc) + timedelta(days=link_data.expires_in_days)

    # Create the share link
    link, plain_token = ShareableReportLink.create_link(
        report_id=report.id,
        user_id=current_user.id,
        expires_at=expires_at,
        name=link_data.name,
    )

    db.add(link)
    db.commit()
    db.refresh(link)

    # Build the share URL
    # In production, this would be the frontend URL
    base_url = request.headers.get("origin", "http://localhost:5173")
    share_url = f"{base_url}/shared/{plain_token}"

    logger.info(f"Share link created for report {report_id} by user {current_user.id}")

    return ShareLinkCreateResponse(
        link=link_to_response(link),
        token=plain_token,
        share_url=share_url,
    )


@router.get("/reports/{report_id}/share", response_model=ShareLinkListResponse)
@limiter.limit(SHARE_LINK_RATE_LIMIT)
async def list_share_links(
    request: Request,
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all share links for a report."""
    # Verify report exists and belongs to user
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == current_user.id,
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    links = db.query(ShareableReportLink).filter(
        ShareableReportLink.report_id == report_id,
    ).order_by(ShareableReportLink.created_at.desc()).all()

    return ShareLinkListResponse(
        items=[link_to_response(link) for link in links],
        total=len(links),
    )


@router.delete("/reports/{report_id}/share/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SHARE_LINK_RATE_LIMIT)
async def revoke_share_link(
    request: Request,
    report_id: UUID,
    link_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke a share link."""
    link = db.query(ShareableReportLink).filter(
        ShareableReportLink.id == link_id,
        ShareableReportLink.report_id == report_id,
        ShareableReportLink.user_id == current_user.id,
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found"
        )

    link.revoke()
    db.commit()

    logger.info(f"Share link {link_id} revoked by user {current_user.id}")

    return None


# ============================================================================
# Public Endpoint (no authentication required)
# ============================================================================

@router.get("/shared/{token}", response_model=SharedReportResponse)
@limiter.limit(PUBLIC_ACCESS_RATE_LIMIT)
async def access_shared_report(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):
    """
    Access a shared report using its token.

    This endpoint is public and does not require authentication.
    """
    # Validate token format
    if not token.startswith("sr_"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid share link"
        )

    # Look up the link by token hash
    token_hash = hash_share_token(token)

    link = db.query(ShareableReportLink).filter(
        ShareableReportLink.token_hash == token_hash,
    ).options(
        joinedload(ShareableReportLink.report),
        joinedload(ShareableReportLink.user),
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or expired"
        )

    # Check if link is valid
    if not link.is_valid:
        if link.is_expired:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This share link has expired"
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or expired"
        )

    # Record access
    link.record_access()
    db.commit()

    # Get the report with scan data
    report = link.report

    # Build report data (similar to report endpoint but limited info)
    report_data = {
        "id": str(report.id),
        "format": report.format.value if hasattr(report.format, 'value') else str(report.format),
        "language": report.language,
        "status": report.status,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }

    # Get scan data
    scan = report.scan if hasattr(report, 'scan') and report.scan else None
    scan_data = {}
    if scan:
        scan_data = {
            "id": str(scan.id),
            "url": scan.url,
            "score": scan.score,
            "pages_scanned": scan.pages_scanned,
            "issues_count": scan.issues_count,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        }

    # Get sharer info (company name only, not personal info)
    shared_by = link.user.company if link.user and link.user.company else None

    return SharedReportResponse(
        report=report_data,
        scan=scan_data,
        shared_by=shared_by,
        expires_at=link.expires_at,
    )
