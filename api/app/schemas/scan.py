"""
Scan Schemas

Pydantic models for scan-related API requests and responses.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, validator
from uuid import UUID


class ScanCreate(BaseModel):
    """Schema for creating a new scan."""

    url: str = Field(..., description="URL to scan", min_length=1, max_length=2048)
    crawl: bool = Field(default=False, description="Whether to crawl multiple pages")
    max_pages: int = Field(
        default=1,
        ge=1,
        le=1000,
        description="Maximum number of pages to scan (if crawl=True)",
    )

    @validator("url")
    def validate_url(cls, v):
        """Validate and normalize URL."""
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        return v


class ScanProgress(BaseModel):
    """Schema for scan progress information."""

    stage: Optional[str] = None
    current: int = 0
    total: int = 0


class IssuesByImpact(BaseModel):
    """Schema for issues grouped by impact level."""

    critical: int = 0
    serious: int = 0
    moderate: int = 0
    minor: int = 0


class ScanResponse(BaseModel):
    """Schema for scan response."""

    id: UUID
    url: str
    crawl: bool
    max_pages: int
    status: str
    progress: ScanProgress
    score: Optional[float] = None
    pages_scanned: int = 0
    issues_count: int = 0
    issues_by_impact: IssuesByImpact
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ScanListResponse(BaseModel):
    """Schema for paginated scan list response."""

    scans: List[ScanResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ElementInfo(BaseModel):
    """Schema for element information in an issue."""

    selector: Optional[str] = None
    html: Optional[str] = None


class IssueResponse(BaseModel):
    """Schema for issue response."""

    id: UUID
    rule_id: str
    impact: str
    wcag_criteria: Optional[List[str]] = None
    wcag_level: Optional[str] = None
    bfsg_reference: Optional[str] = None
    title_de: str
    description_de: Optional[str] = None
    fix_suggestion_de: Optional[str] = None
    element: ElementInfo
    help_url: Optional[str] = None
    screenshot_url: Optional[str] = None
    page_url: Optional[str] = None

    class Config:
        from_attributes = True


class IssueListResponse(BaseModel):
    """Schema for paginated issue list response."""

    issues: List[IssueResponse]
    total: int
    page: int
    per_page: int
    pages: int


class PageResponse(BaseModel):
    """Schema for page response."""

    id: UUID
    url: str
    title: Optional[str] = None
    score: Optional[float] = None
    issues_count: int = 0
    passed_rules: int = 0
    failed_rules: int = 0
    load_time_ms: Optional[int] = None
    scan_time_ms: Optional[int] = None
    error: Optional[str] = None
    scanned_at: datetime

    class Config:
        from_attributes = True


class ScanSummaryResponse(BaseModel):
    """Schema for scan summary in reports."""

    scan_id: UUID
    base_url: str
    total_pages: int
    total_issues: int
    issues_by_impact: IssuesByImpact
    issues_by_wcag_level: dict
    overall_score: float
    scan_duration_seconds: int
    completed_at: datetime
