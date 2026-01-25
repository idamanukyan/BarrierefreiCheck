"""
Scan Models

Defines the Scan, Page, and Issue tables for accessibility testing.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ScanStatus(enum.Enum):
    """Scan status types."""
    QUEUED = "queued"
    CRAWLING = "crawling"
    SCANNING = "scanning"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImpactLevel(enum.Enum):
    """Accessibility issue impact levels."""
    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


class WcagLevel(enum.Enum):
    """WCAG conformance levels."""
    A = "A"
    AA = "AA"
    AAA = "AAA"


class Scan(Base):
    """Scan model for accessibility scan jobs."""

    __tablename__ = "scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Scan configuration
    url = Column(String(2048), nullable=False)
    crawl = Column(Boolean, default=False)
    max_pages = Column(Integer, default=1)

    # Status and progress
    status = Column(SQLEnum(ScanStatus), default=ScanStatus.QUEUED, nullable=False, index=True)
    progress_stage = Column(String(50), nullable=True)
    progress_current = Column(Integer, default=0)
    progress_total = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Results summary
    score = Column(Float, nullable=True)
    pages_scanned = Column(Integer, default=0)
    issues_count = Column(Integer, default=0)
    issues_critical = Column(Integer, default=0)
    issues_serious = Column(Integer, default=0)
    issues_moderate = Column(Integer, default=0)
    issues_minor = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="scans")
    pages = relationship("Page", back_populates="scan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Scan {self.id} - {self.url}>"

    @property
    def duration_seconds(self) -> int | None:
        """Calculate scan duration in seconds."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "url": self.url,
            "crawl": self.crawl,
            "max_pages": self.max_pages,
            "status": self.status.value,
            "progress": {
                "stage": self.progress_stage,
                "current": self.progress_current,
                "total": self.progress_total,
            },
            "score": self.score,
            "pages_scanned": self.pages_scanned,
            "issues_count": self.issues_count,
            "issues_by_impact": {
                "critical": self.issues_critical,
                "serious": self.issues_serious,
                "moderate": self.issues_moderate,
                "minor": self.issues_minor,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }


class Page(Base):
    """Page model for scanned pages within a scan."""

    __tablename__ = "pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False, index=True)

    # Page info
    url = Column(String(2048), nullable=False)
    title = Column(String(512), nullable=True)
    depth = Column(Integer, default=0)

    # Results
    score = Column(Float, nullable=True)
    issues_count = Column(Integer, default=0)
    passed_rules = Column(Integer, default=0)
    failed_rules = Column(Integer, default=0)
    incomplete_rules = Column(Integer, default=0)

    # Timing
    load_time_ms = Column(Integer, nullable=True)
    scan_time_ms = Column(Integer, nullable=True)

    # Status
    error = Column(Text, nullable=True)
    scanned_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    scan = relationship("Scan", back_populates="pages")
    issues = relationship("Issue", back_populates="page", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Page {self.url}>"


class Issue(Base):
    """Issue model for accessibility issues found during scanning."""

    __tablename__ = "issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(UUID(as_uuid=True), ForeignKey("pages.id"), nullable=False, index=True)

    # Rule identification
    rule_id = Column(String(100), nullable=False, index=True)
    impact = Column(SQLEnum(ImpactLevel), nullable=False, index=True)

    # WCAG and BFSG mapping
    wcag_criteria = Column(ARRAY(String), nullable=True)
    wcag_level = Column(SQLEnum(WcagLevel), default=WcagLevel.A)
    bfsg_reference = Column(String(255), nullable=True)

    # German translations
    title_de = Column(String(500), nullable=False)
    description_de = Column(Text, nullable=True)
    fix_suggestion_de = Column(Text, nullable=True)

    # Element information
    element_selector = Column(Text, nullable=True)
    element_html = Column(Text, nullable=True)
    element_xpath = Column(Text, nullable=True)

    # Resources
    help_url = Column(String(2048), nullable=True)
    screenshot_path = Column(String(512), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    page = relationship("Page", back_populates="issues")

    def __repr__(self):
        return f"<Issue {self.rule_id} - {self.impact.value}>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "rule_id": self.rule_id,
            "impact": self.impact.value,
            "wcag_criteria": self.wcag_criteria,
            "wcag_level": self.wcag_level.value if self.wcag_level else None,
            "bfsg_reference": self.bfsg_reference,
            "title_de": self.title_de,
            "description_de": self.description_de,
            "fix_suggestion_de": self.fix_suggestion_de,
            "element": {
                "selector": self.element_selector,
                "html": self.element_html,
            },
            "help_url": self.help_url,
            "screenshot_url": self.screenshot_path,
        }
