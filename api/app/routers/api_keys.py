"""
API Keys Router

Endpoints for managing API keys for programmatic access.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, APIKey
from app.routers.auth import get_current_user
from app.services.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limits for API key operations
API_KEY_RATE_LIMIT = "10/minute"


# Pydantic schemas
class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name for the API key")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Days until expiration (null = never)")


class APIKeyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    key_prefix: str
    is_active: bool
    last_used_at: Optional[datetime]
    usage_count: str
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    """Response when creating a new API key - includes the plain key (shown only once)."""
    api_key: APIKeyResponse
    key: str = Field(..., description="The API key. Store this securely - it won't be shown again!")


class APIKeyListResponse(BaseModel):
    items: List[APIKeyResponse]
    total: int


@router.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(API_KEY_RATE_LIMIT)
async def create_api_key(
    request: Request,
    key_data: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new API key for programmatic access.

    The API key will be shown only once in the response. Store it securely!

    API keys can be used instead of JWT tokens for authentication by passing
    them in the `X-API-Key` header.
    """
    # Check plan limits for API access
    plan_limits = current_user.plan_limits
    if current_user.plan.value == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key access requires a paid plan. Please upgrade to use API keys."
        )

    # Limit number of API keys per user
    existing_count = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True,
    ).count()

    max_keys = 5 if current_user.plan.value in ("starter", "professional") else 20
    if existing_count >= max_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum number of API keys reached ({max_keys}). Delete an existing key first."
        )

    # Calculate expiration
    expires_at = None
    if key_data.expires_in_days:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=key_data.expires_in_days)

    # Create the API key
    api_key, plain_key = APIKey.create_key(
        user_id=current_user.id,
        name=key_data.name,
        description=key_data.description,
        expires_at=expires_at,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.info(f"API key created for user {current_user.id}: {api_key.key_prefix}...")

    return APIKeyCreateResponse(
        api_key=APIKeyResponse(
            id=str(api_key.id),
            name=api_key.name,
            description=api_key.description,
            key_prefix=api_key.key_prefix,
            is_active=api_key.is_active,
            last_used_at=api_key.last_used_at,
            usage_count=api_key.usage_count,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
        ),
        key=plain_key,
    )


@router.get("", response_model=APIKeyListResponse)
@limiter.limit(API_KEY_RATE_LIMIT)
async def list_api_keys(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all API keys for the current user."""
    keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
    ).order_by(APIKey.created_at.desc()).all()

    return APIKeyListResponse(
        items=[
            APIKeyResponse(
                id=str(key.id),
                name=key.name,
                description=key.description,
                key_prefix=key.key_prefix,
                is_active=key.is_active,
                last_used_at=key.last_used_at,
                usage_count=key.usage_count,
                expires_at=key.expires_at,
                created_at=key.created_at,
            )
            for key in keys
        ],
        total=len(keys),
    )


@router.get("/{key_id}", response_model=APIKeyResponse)
@limiter.limit(API_KEY_RATE_LIMIT)
async def get_api_key(
    request: Request,
    key_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific API key."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    return APIKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        usage_count=api_key.usage_count,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(API_KEY_RATE_LIMIT)
async def delete_api_key(
    request: Request,
    key_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete (revoke) an API key."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    db.delete(api_key)
    db.commit()

    logger.info(f"API key deleted for user {current_user.id}: {api_key.key_prefix}...")

    return None


@router.post("/{key_id}/regenerate", response_model=APIKeyCreateResponse)
@limiter.limit(API_KEY_RATE_LIMIT)
async def regenerate_api_key(
    request: Request,
    key_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Regenerate an API key (creates new key, invalidates old one).

    The old key will immediately stop working.
    """
    old_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
    ).first()

    if not old_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Create new key with same metadata
    new_key, plain_key = APIKey.create_key(
        user_id=current_user.id,
        name=old_key.name,
        description=old_key.description,
        expires_at=old_key.expires_at,
    )

    # Delete old key and add new one
    db.delete(old_key)
    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    logger.info(f"API key regenerated for user {current_user.id}: {old_key.key_prefix}... -> {new_key.key_prefix}...")

    return APIKeyCreateResponse(
        api_key=APIKeyResponse(
            id=str(new_key.id),
            name=new_key.name,
            description=new_key.description,
            key_prefix=new_key.key_prefix,
            is_active=new_key.is_active,
            last_used_at=new_key.last_used_at,
            usage_count=new_key.usage_count,
            expires_at=new_key.expires_at,
            created_at=new_key.created_at,
        ),
        key=plain_key,
    )
