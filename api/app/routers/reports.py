"""
Reports Router

API endpoints for generating and managing accessibility reports.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse
import html
import io

from ..database import get_db
from ..models import User, Scan, Report, ReportFormat as ReportFormatEnum
from ..services.report_generator import ReportGenerator, ReportFormat
from ..services.email_service import EmailService
from ..services.rate_limiter import limiter
from ..services.metrics import record_report_generated
from .auth import get_current_user
import time as time_module

router = APIRouter(prefix="/reports", tags=["reports"])

# Rate limits for report operations
REPORT_CREATE_LIMIT = "10/minute"  # Report generation is resource-intensive
REPORT_DOWNLOAD_LIMIT = "30/minute"  # Downloads are less intensive


# Pydantic schemas
class BrandingConfig(BaseModel):
    logo: Optional[str] = Field(None, description="URL to company logo image")
    company_name: Optional[str] = Field(None, max_length=200, description="Company name for branding")

    @field_validator("logo")
    @classmethod
    def validate_logo_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate logo URL to prevent XSS and other attacks."""
        if v is None:
            return None
        try:
            parsed = urlparse(v)
            # Must be a valid URL with scheme
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid logo URL format")
            # Only allow HTTPS URLs for logos (or data: for base64 images)
            if parsed.scheme not in ("https", "data"):
                raise ValueError("Logo URL must use HTTPS or be a data URI")
            # Block dangerous patterns
            if any(pattern in v.lower() for pattern in ["javascript:", "<script", "onerror", "onload"]):
                raise ValueError("Logo URL contains potentially unsafe content")
            return v
        except Exception as e:
            raise ValueError(f"Invalid logo URL: {e}")

    @field_validator("company_name")
    @classmethod
    def sanitize_company_name(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize company name to prevent XSS."""
        if v is None:
            return None
        # HTML escape the company name
        return html.escape(v.strip())


class ReportCreate(BaseModel):
    scan_id: str = Field(..., description="ID of the scan to generate report for")
    format: str = Field("pdf", description="Report format: pdf, html, json, csv")
    language: str = Field("de", description="Report language: de or en")
    include_screenshots: bool = Field(True, description="Include screenshots in report")
    branding: Optional[BrandingConfig] = None


class ReportResponse(BaseModel):
    id: str
    scan_id: str
    format: str
    language: str
    status: str
    file_size: Optional[int] = None
    download_url: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    items: List[ReportResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Initialize services
report_generator = ReportGenerator()
email_service = EmailService()


async def generate_report_task(
    report_id: str,
    scan_data: dict,
    format: ReportFormat,
    language: str,
    include_screenshots: bool,
    branding: Optional[dict],
    db: Session,
):
    """Background task to generate report."""
    start_time = time_module.time()
    format_str = format.value if hasattr(format, 'value') else str(format)

    try:
        # Generate report
        content = report_generator.generate(
            scan_data=scan_data,
            format=format,
            language=language,
            include_screenshots=include_screenshots,
            branding=branding,
        )

        # Update report in database
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = "completed"
            report.file_content = content
            report.file_size = len(content)
            db.commit()

        # Record success metrics
        duration = time_module.time() - start_time
        record_report_generated(format_str, language, duration, success=True)

    except Exception as e:
        # Mark report as failed
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = "failed"
            report.error = str(e)
            db.commit()

        # Record failure metrics
        duration = time_module.time() - start_time
        record_report_generated(format_str, language, duration, success=False)


@router.post("", response_model=ReportResponse, status_code=201)
@limiter.limit(REPORT_CREATE_LIMIT)
async def create_report(
    request: Request,
    report_data: ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a new report for a scan.

    The report is generated asynchronously. Use GET /reports/{id} to check status.
    """
    user_id = str(current_user.id)

    # Validate format
    try:
        format = ReportFormat(report_data.format.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Supported formats: pdf, html, json, csv",
        )

    # Validate language
    if report_data.language not in ["de", "en"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid language. Supported languages: de, en",
        )

    # Get scan
    scan = db.query(Scan).filter(
        Scan.id == report_data.scan_id,
        Scan.user_id == user_id,
    ).first()

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Cannot generate report for incomplete scan",
        )

    # Create report record
    report_id = str(uuid.uuid4())
    report = Report(
        id=report_id,
        scan_id=scan.id,
        user_id=user_id,
        format=ReportFormatEnum(report_data.format.lower()),
        language=report_data.language,
        include_screenshots=report_data.include_screenshots,
        status="generating",
    )
    db.add(report)
    db.commit()

    # Prepare scan data for report
    scan_data = {
        "id": str(scan.id),
        "url": scan.url,
        "score": scan.score,
        "duration": scan.duration,
        "created_at": scan.created_at.isoformat(),
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "pages": [],
    }

    # Add pages and issues
    for page in scan.pages:
        page_data = {
            "url": page.url,
            "title": page.title,
            "score": page.score,
            "issues": [],
        }
        for issue in page.issues:
            page_data["issues"].append({
                "rule_id": issue.rule_id,
                "title": issue.title,
                "description": issue.description,
                "fix": issue.fix,
                "impact": issue.impact.value,
                "wcag_level": issue.wcag_level.value,
                "wcag_criteria": issue.wcag_criteria or [],
                "bfsg_reference": issue.bfsg_reference,
                "element": {
                    "selector": issue.element_selector,
                    "html": issue.element_html,
                },
                "screenshot_path": issue.screenshot_path,
            })
        scan_data["pages"].append(page_data)

    # Start background generation
    branding = report_data.branding.dict() if report_data.branding else None
    background_tasks.add_task(
        generate_report_task,
        report_id,
        scan_data,
        format,
        report_data.language,
        report_data.include_screenshots,
        branding,
        db,
    )

    return ReportResponse(
        id=report_id,
        scan_id=str(scan.id),
        format=report_data.format,
        language=report_data.language,
        status="generating",
        created_at=datetime.now(timezone.utc),
    )


@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all reports for the current user."""
    user_id = str(current_user.id)

    # Get total count
    total = db.query(Report).filter(Report.user_id == user_id).count()

    # Get paginated reports
    reports = (
        db.query(Report)
        .filter(Report.user_id == user_id)
        .order_by(Report.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ReportListResponse(
        items=[
            ReportResponse(
                id=str(r.id),
                scan_id=str(r.scan_id),
                format=r.format.value,
                language=r.language,
                status=r.status,
                file_size=r.file_size,
                download_url=f"/api/v1/reports/{r.id}/download" if r.status == "completed" else None,
                created_at=r.created_at,
                expires_at=r.expires_at,
            )
            for r in reports
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get report details by ID."""
    user_id = str(current_user.id)

    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user_id,
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse(
        id=str(report.id),
        scan_id=str(report.scan_id),
        format=report.format.value,
        language=report.language,
        status=report.status,
        file_size=report.file_size,
        download_url=f"/api/v1/reports/{report.id}/download" if report.status == "completed" else None,
        created_at=report.created_at,
        expires_at=report.expires_at,
    )


@router.get("/{report_id}/download")
@limiter.limit(REPORT_DOWNLOAD_LIMIT)
async def download_report(
    request: Request,
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a generated report."""
    user_id = str(current_user.id)

    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user_id,
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Report is not ready. Status: {report.status}",
        )

    if not report.file_content:
        raise HTTPException(status_code=404, detail="Report file not found")

    # Determine content type and filename
    content_types = {
        ReportFormatEnum.PDF: "application/pdf",
        ReportFormatEnum.HTML: "text/html",
        ReportFormatEnum.JSON: "application/json",
        ReportFormatEnum.CSV: "text/csv",
    }
    extensions = {
        ReportFormatEnum.PDF: "pdf",
        ReportFormatEnum.HTML: "html",
        ReportFormatEnum.JSON: "json",
        ReportFormatEnum.CSV: "csv",
    }

    content_type = content_types.get(report.format, "application/octet-stream")
    extension = extensions.get(report.format, "bin")

    # Get scan URL for filename
    scan = db.query(Scan).filter(Scan.id == report.scan_id).first()
    domain = "report"
    if scan:
        try:
            from urllib.parse import urlparse
            domain = urlparse(scan.url).netloc.replace(".", "_")
        except:
            pass

    filename = f"accessibility_report_{domain}_{report.created_at.strftime('%Y%m%d')}.{extension}"

    return StreamingResponse(
        io.BytesIO(report.file_content),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(report.file_content)),
        },
    )


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a report."""
    user_id = str(current_user.id)

    report = db.query(Report).filter(
        Report.id == report_id,
        Report.user_id == user_id,
    ).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    db.delete(report)
    db.commit()
