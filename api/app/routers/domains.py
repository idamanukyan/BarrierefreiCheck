"""
Domains Router

Endpoints for managing user domains with bulk operations support.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, Domain, DomainStatus, extract_domain
from app.routers.auth import get_current_user
from app.services.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limits
DOMAIN_RATE_LIMIT = "30/minute"
BULK_RATE_LIMIT = "10/minute"


# Pydantic Schemas
class DomainCreate(BaseModel):
    """Schema for creating a single domain."""
    domain: str = Field(..., min_length=1, max_length=255, description="Domain or URL to add")
    display_name: Optional[str] = Field(None, max_length=255, description="Friendly name for the domain")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")

    @field_validator('domain')
    @classmethod
    def normalize_domain(cls, v: str) -> str:
        return extract_domain(v.strip())


class DomainBulkCreate(BaseModel):
    """Schema for bulk domain creation."""
    domains: List[DomainCreate] = Field(..., min_length=1, max_length=50, description="List of domains to add (max 50)")


class DomainUpdate(BaseModel):
    """Schema for updating a domain."""
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class DomainResponse(BaseModel):
    """Response schema for a single domain."""
    id: str
    domain: str
    display_name: Optional[str]
    description: Optional[str]
    status: str
    total_scans: int
    last_scan_at: Optional[datetime]
    last_score: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DomainListResponse(BaseModel):
    """Response schema for listing domains."""
    items: List[DomainResponse]
    total: int
    limit: int  # Plan limit (-1 for unlimited)
    remaining: int  # Slots remaining (-1 for unlimited)


class BulkCreateResult(BaseModel):
    """Result of a single domain in bulk create."""
    domain: str
    success: bool
    id: Optional[str] = None
    error: Optional[str] = None


class BulkCreateResponse(BaseModel):
    """Response schema for bulk domain creation."""
    created: List[DomainResponse]
    errors: List[BulkCreateResult]
    total_created: int
    total_errors: int


class BulkDeleteResponse(BaseModel):
    """Response schema for bulk domain deletion."""
    deleted_count: int
    deleted_ids: List[str]


# Helper functions
def check_domain_limit(db: Session, user: User, new_count: int = 1) -> None:
    """
    Check if user can add more domains based on plan limits.

    Raises:
        HTTPException: If domain limit would be exceeded
    """
    limit = user.plan_limits.get("domains", 1)
    if limit == -1:  # Unlimited
        return

    current_count = db.query(func.count(Domain.id)).filter(
        Domain.user_id == user.id,
        Domain.is_active == True,
    ).scalar() or 0

    if current_count + new_count > limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Domain limit reached. Your plan allows {limit} domains. "
                   f"Current: {current_count}. Upgrade your plan for more domains."
        )


def domain_to_response(domain: Domain) -> DomainResponse:
    """Convert a Domain model to a response schema."""
    return DomainResponse(
        id=str(domain.id),
        domain=domain.domain,
        display_name=domain.display_name,
        description=domain.description,
        status=domain.status.value if domain.status else "pending",
        total_scans=domain.total_scans or 0,
        last_scan_at=domain.last_scan_at,
        last_score=domain.last_score,
        is_active=domain.is_active,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


# Endpoints
@router.post("", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(DOMAIN_RATE_LIMIT)
async def create_domain(
    request: Request,
    domain_data: DomainCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a new domain to monitor.

    The domain will be normalized (www. removed, lowercase).
    """
    # Check plan limit
    check_domain_limit(db, current_user, 1)

    # Check for duplicate
    existing = db.query(Domain).filter(
        Domain.user_id == current_user.id,
        Domain.domain == domain_data.domain,
    ).first()

    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Domain '{domain_data.domain}' already exists"
            )
        else:
            # Reactivate deleted domain
            existing.is_active = True
            existing.display_name = domain_data.display_name
            existing.description = domain_data.description
            existing.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            logger.info(f"Domain reactivated for user {current_user.id}: {existing.domain}")
            return domain_to_response(existing)

    # Create new domain
    domain = Domain.create_domain(
        user_id=current_user.id,
        domain=domain_data.domain,
        display_name=domain_data.display_name,
        description=domain_data.description,
    )

    db.add(domain)
    db.commit()
    db.refresh(domain)

    logger.info(f"Domain created for user {current_user.id}: {domain.domain}")
    return domain_to_response(domain)


@router.post("/bulk", response_model=BulkCreateResponse)
@limiter.limit(BULK_RATE_LIMIT)
async def bulk_create_domains(
    request: Request,
    bulk_data: DomainBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add multiple domains at once (max 50).

    Returns created domains and any errors encountered.
    """
    # Check plan limit for all domains
    check_domain_limit(db, current_user, len(bulk_data.domains))

    created = []
    errors = []

    for domain_data in bulk_data.domains:
        try:
            # Check for duplicate
            existing = db.query(Domain).filter(
                Domain.user_id == current_user.id,
                Domain.domain == domain_data.domain,
            ).first()

            if existing and existing.is_active:
                errors.append(BulkCreateResult(
                    domain=domain_data.domain,
                    success=False,
                    error="Domain already exists"
                ))
                continue

            if existing and not existing.is_active:
                # Reactivate
                existing.is_active = True
                existing.display_name = domain_data.display_name
                existing.description = domain_data.description
                existing.updated_at = datetime.now(timezone.utc)
                db.flush()
                created.append(domain_to_response(existing))
            else:
                # Create new
                domain = Domain.create_domain(
                    user_id=current_user.id,
                    domain=domain_data.domain,
                    display_name=domain_data.display_name,
                    description=domain_data.description,
                )
                db.add(domain)
                db.flush()  # Get ID without committing
                created.append(domain_to_response(domain))

        except Exception as e:
            errors.append(BulkCreateResult(
                domain=domain_data.domain,
                success=False,
                error=str(e)
            ))

    db.commit()

    logger.info(f"Bulk domain create for user {current_user.id}: "
                f"{len(created)} created, {len(errors)} errors")

    return BulkCreateResponse(
        created=created,
        errors=errors,
        total_created=len(created),
        total_errors=len(errors),
    )


@router.get("", response_model=DomainListResponse)
@limiter.limit(DOMAIN_RATE_LIMIT)
async def list_domains(
    request: Request,
    include_inactive: bool = Query(False, description="Include deactivated domains"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all domains for the current user."""
    query = db.query(Domain).filter(Domain.user_id == current_user.id)

    if not include_inactive:
        query = query.filter(Domain.is_active == True)

    domains = query.order_by(Domain.created_at.desc()).all()

    # Get plan limit info
    limit = current_user.plan_limits.get("domains", 1)
    active_count = sum(1 for d in domains if d.is_active)
    remaining = max(0, limit - active_count) if limit != -1 else -1

    return DomainListResponse(
        items=[domain_to_response(d) for d in domains],
        total=len(domains),
        limit=limit,
        remaining=remaining,
    )


@router.get("/{domain_id}", response_model=DomainResponse)
@limiter.limit(DOMAIN_RATE_LIMIT)
async def get_domain(
    request: Request,
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific domain."""
    domain = db.query(Domain).filter(
        Domain.id == domain_id,
        Domain.user_id == current_user.id,
    ).first()

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found"
        )

    return domain_to_response(domain)


@router.patch("/{domain_id}", response_model=DomainResponse)
@limiter.limit(DOMAIN_RATE_LIMIT)
async def update_domain(
    request: Request,
    domain_id: UUID,
    update_data: DomainUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a domain's metadata."""
    domain = db.query(Domain).filter(
        Domain.id == domain_id,
        Domain.user_id == current_user.id,
    ).first()

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found"
        )

    # Apply updates
    if update_data.display_name is not None:
        domain.display_name = update_data.display_name
    if update_data.description is not None:
        domain.description = update_data.description
    if update_data.is_active is not None:
        domain.is_active = update_data.is_active

    domain.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(domain)

    logger.info(f"Domain updated for user {current_user.id}: {domain.domain}")
    return domain_to_response(domain)


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(DOMAIN_RATE_LIMIT)
async def delete_domain(
    request: Request,
    domain_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete (soft-delete) a domain."""
    domain = db.query(Domain).filter(
        Domain.id == domain_id,
        Domain.user_id == current_user.id,
    ).first()

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found"
        )

    # Soft delete
    domain.is_active = False
    domain.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"Domain deleted for user {current_user.id}: {domain.domain}")
    return None


@router.delete("", response_model=BulkDeleteResponse)
@limiter.limit(BULK_RATE_LIMIT)
async def bulk_delete_domains(
    request: Request,
    domain_ids: List[UUID] = Query(..., description="Domain IDs to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete multiple domains at once (soft delete)."""
    domains = db.query(Domain).filter(
        Domain.id.in_(domain_ids),
        Domain.user_id == current_user.id,
        Domain.is_active == True,
    ).all()

    deleted_ids = []
    for domain in domains:
        domain.is_active = False
        domain.updated_at = datetime.now(timezone.utc)
        deleted_ids.append(str(domain.id))

    db.commit()

    logger.info(f"Bulk domain delete for user {current_user.id}: {len(deleted_ids)} deleted")

    return BulkDeleteResponse(
        deleted_count=len(deleted_ids),
        deleted_ids=deleted_ids,
    )
