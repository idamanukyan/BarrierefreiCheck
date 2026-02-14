"""
GDPR Compliance Router

Endpoints for GDPR compliance:
- Data export (Art. 20 - Right to Data Portability)
- Data deletion (Art. 17 - Right to be Forgotten)
- Data summary (Art. 15 - Right of Access)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user, verify_password
from app.services.gdpr import get_gdpr_service
from app.services.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limits for GDPR endpoints (strict to prevent abuse)
GDPR_EXPORT_RATE_LIMIT = "5/hour"
GDPR_DELETE_RATE_LIMIT = "3/hour"
GDPR_SUMMARY_RATE_LIMIT = "20/hour"


# Request/Response schemas
class DataSummaryResponse(BaseModel):
    """Summary of user data stored in the system."""

    user: dict = Field(..., description="Basic user info")
    data_counts: dict = Field(..., description="Counts of data by type")


class DataExportResponse(BaseModel):
    """Response containing exported user data."""

    export_metadata: dict = Field(..., description="Export metadata")
    user: dict = Field(..., description="User profile data")
    scans: list = Field(..., description="All scan data with pages and issues")
    api_keys: list = Field(..., description="API key metadata (no secrets)")
    subscription: Optional[dict] = Field(None, description="Subscription and payments")
    usage_records: list = Field(..., description="Usage history")
    reports: list = Field(..., description="Generated report metadata")


class DeleteConfirmRequest(BaseModel):
    """Request to confirm data deletion."""

    password: str = Field(..., description="Current password for confirmation")
    confirm_deletion: bool = Field(
        ..., description="Must be true to confirm deletion"
    )


class DeleteResponse(BaseModel):
    """Response after data deletion."""

    deleted: bool = Field(..., description="Whether deletion was successful")
    deleted_at: str = Field(..., description="ISO timestamp of deletion")
    counts: dict = Field(..., description="Counts of deleted data by type")
    message: str = Field(..., description="Human-readable message")


# Endpoints


@router.get(
    "/summary",
    response_model=DataSummaryResponse,
    summary="Get data summary",
    description="Get a summary of all data stored for the current user (Art. 15 GDPR - Right of Access).",
)
@limiter.limit(GDPR_SUMMARY_RATE_LIMIT)
async def get_data_summary(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DataSummaryResponse:
    """
    Get a summary of all user data stored in the system.

    This endpoint helps users understand what data is stored about them
    before requesting a full export or deletion.
    """
    gdpr_service = get_gdpr_service()
    summary = gdpr_service.get_user_data_summary(current_user.id, db)

    if "error" in summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=summary["error"],
        )

    logger.info(
        f"GDPR: Data summary requested",
        extra={"user_id": str(current_user.id), "gdpr_article": "Art. 15"},
    )

    return DataSummaryResponse(**summary)


@router.get(
    "/export",
    response_model=DataExportResponse,
    summary="Export all user data",
    description="Export all user data in JSON format (Art. 20 GDPR - Right to Data Portability).",
)
@limiter.limit(GDPR_EXPORT_RATE_LIMIT)
async def export_user_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DataExportResponse:
    """
    Export all user data in a portable JSON format.

    This implements Art. 20 GDPR - Right to Data Portability.
    The export includes:
    - User profile information
    - All scans with pages and accessibility issues
    - API key metadata (not the actual keys)
    - Subscription and payment history
    - Usage records
    - Generated report metadata

    Note: Large exports may take a few seconds to generate.
    """
    gdpr_service = get_gdpr_service()
    export_data = gdpr_service.get_user_export_data(current_user.id, db)

    if not export_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    logger.info(
        f"GDPR: Data export requested",
        extra={
            "user_id": str(current_user.id),
            "gdpr_article": "Art. 20",
            "scans_count": len(export_data.get("scans", [])),
        },
    )

    return DataExportResponse(**export_data)


@router.get(
    "/export/download",
    summary="Download user data as JSON file",
    description="Download all user data as a JSON file (Art. 20 GDPR).",
    responses={
        200: {
            "content": {"application/json": {}},
            "description": "JSON file download",
        }
    },
)
@limiter.limit(GDPR_EXPORT_RATE_LIMIT)
async def download_user_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Download all user data as a JSON file.

    Returns a downloadable JSON file containing all user data.
    """
    gdpr_service = get_gdpr_service()
    json_content = gdpr_service.export_to_json(current_user.id, db)

    if not json_content or json_content == "{}":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generate filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"barrierefrei_check_export_{timestamp}.json"

    logger.info(
        f"GDPR: Data export downloaded",
        extra={
            "user_id": str(current_user.id),
            "gdpr_article": "Art. 20",
            "filename": filename,
        },
    )

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.delete(
    "/data",
    response_model=DeleteResponse,
    summary="Delete all user data",
    description="Permanently delete all user data (Art. 17 GDPR - Right to be Forgotten).",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(GDPR_DELETE_RATE_LIMIT)
async def delete_user_data(
    request: Request,
    delete_request: DeleteConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeleteResponse:
    """
    Permanently delete all user data.

    This implements Art. 17 GDPR - Right to be Forgotten.

    **WARNING: This action is irreversible!**

    All data will be permanently deleted:
    - User account and profile
    - All scans, pages, and accessibility issues
    - All API keys
    - Subscription and payment records
    - Usage history
    - Generated reports

    Requirements:
    - Must provide current password for verification
    - Must explicitly confirm deletion (confirm_deletion=true)

    After deletion, the user will be logged out and the account will cease to exist.
    """
    # Verify password
    if not verify_password(delete_request.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    # Verify confirmation
    if not delete_request.confirm_deletion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion not confirmed. Set confirm_deletion to true to proceed.",
        )

    # Log before deletion (audit trail)
    logger.warning(
        f"GDPR: User data deletion initiated",
        extra={
            "user_id": str(current_user.id),
            "user_email": current_user.email,
            "gdpr_article": "Art. 17",
        },
    )

    # Perform deletion
    gdpr_service = get_gdpr_service()
    result = gdpr_service.delete_user_data(current_user.id, db)

    if not result.get("deleted"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user data. Please contact support.",
        )

    return DeleteResponse(
        deleted=True,
        deleted_at=result["deleted_at"],
        counts=result["counts"],
        message="All your data has been permanently deleted. Your account no longer exists.",
    )
