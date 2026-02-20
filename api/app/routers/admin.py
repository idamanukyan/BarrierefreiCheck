"""
Admin Router

API endpoints for admin-only operations and system metrics.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from ..database import get_db
from ..models import Scan, ScanStatus, User
from ..models.user import PlanType
from ..routers.auth import get_current_user
from ..services.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# Rate limit for admin operations
ADMIN_RATE_LIMIT = "60/minute"


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that ensures the current user is an admin.

    Returns the user if they are an admin, otherwise raises 403.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


class SystemMetrics(BaseModel):
    """System-wide metrics for admin dashboard."""

    # User metrics
    total_users: int
    active_users_24h: int
    active_users_7d: int
    users_by_plan: dict
    new_users_today: int
    new_users_week: int

    # Scan metrics
    total_scans: int
    scans_today: int
    scans_week: int
    scans_by_status: dict
    average_scan_duration_ms: Optional[float]
    average_pages_per_scan: Optional[float]

    # Issue metrics
    total_issues_found: int
    issues_by_impact: dict
    average_score: Optional[float]

    # System info
    timestamp: datetime
    database_size_mb: Optional[float]


class UserStats(BaseModel):
    """Individual user statistics."""

    id: str
    email: str
    plan: str
    is_active: bool
    is_verified: bool
    total_scans: int
    last_scan_at: Optional[datetime]
    created_at: datetime
    last_login_at: Optional[datetime]


class RecentActivity(BaseModel):
    """Recent system activity."""

    scan_id: str
    user_email: str
    url: str
    status: str
    score: Optional[float]
    created_at: datetime


@router.get("/metrics", response_model=SystemMetrics)
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_admin_metrics(
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
):
    """
    Get system-wide metrics for admin dashboard.

    Requires admin privileges.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    day_ago = now - timedelta(days=1)

    # User metrics
    total_users = db.query(func.count(User.id)).scalar() or 0

    active_users_24h = db.query(func.count(User.id)).filter(
        User.last_login_at >= day_ago
    ).scalar() or 0

    active_users_7d = db.query(func.count(User.id)).filter(
        User.last_login_at >= week_ago
    ).scalar() or 0

    # Users by plan
    plan_counts = db.query(
        User.plan, func.count(User.id)
    ).group_by(User.plan).all()
    users_by_plan = {plan.value: count for plan, count in plan_counts}

    new_users_today = db.query(func.count(User.id)).filter(
        User.created_at >= today_start
    ).scalar() or 0

    new_users_week = db.query(func.count(User.id)).filter(
        User.created_at >= week_ago
    ).scalar() or 0

    # Scan metrics
    total_scans = db.query(func.count(Scan.id)).scalar() or 0

    scans_today = db.query(func.count(Scan.id)).filter(
        Scan.created_at >= today_start
    ).scalar() or 0

    scans_week = db.query(func.count(Scan.id)).filter(
        Scan.created_at >= week_ago
    ).scalar() or 0

    # Scans by status
    status_counts = db.query(
        Scan.status, func.count(Scan.id)
    ).group_by(Scan.status).all()
    scans_by_status = {s.value: count for s, count in status_counts}

    # Average scan duration (for completed scans)
    avg_duration = db.query(
        func.avg(
            func.extract('epoch', Scan.completed_at) -
            func.extract('epoch', Scan.started_at)
        ) * 1000  # Convert to milliseconds
    ).filter(
        Scan.status == ScanStatus.COMPLETED,
        Scan.started_at.isnot(None),
        Scan.completed_at.isnot(None),
    ).scalar()

    # Average pages per scan
    avg_pages = db.query(
        func.avg(Scan.pages_scanned)
    ).filter(
        Scan.status == ScanStatus.COMPLETED
    ).scalar()

    # Issue metrics
    total_issues = db.query(func.sum(Scan.issues_count)).scalar() or 0

    # Issues by impact (aggregate)
    impact_sums = db.query(
        func.coalesce(func.sum(Scan.issues_critical), 0).label('critical'),
        func.coalesce(func.sum(Scan.issues_serious), 0).label('serious'),
        func.coalesce(func.sum(Scan.issues_moderate), 0).label('moderate'),
        func.coalesce(func.sum(Scan.issues_minor), 0).label('minor'),
    ).filter(
        Scan.status == ScanStatus.COMPLETED,
    ).first()

    issues_by_impact = {
        "critical": int(impact_sums.critical) if impact_sums else 0,
        "serious": int(impact_sums.serious) if impact_sums else 0,
        "moderate": int(impact_sums.moderate) if impact_sums else 0,
        "minor": int(impact_sums.minor) if impact_sums else 0,
    }

    # Average compliance score
    avg_score = db.query(
        func.avg(Scan.score)
    ).filter(
        Scan.status == ScanStatus.COMPLETED,
        Scan.score.isnot(None),
    ).scalar()

    # Database size (PostgreSQL specific)
    database_size_mb = None
    try:
        result = db.execute(text(
            "SELECT pg_database_size(current_database()) / 1024.0 / 1024.0"
        ))
        database_size_mb = result.scalar()
    except Exception as e:
        logger.debug(f"Could not get database size: {e}")

    return SystemMetrics(
        total_users=total_users,
        active_users_24h=active_users_24h,
        active_users_7d=active_users_7d,
        users_by_plan=users_by_plan,
        new_users_today=new_users_today,
        new_users_week=new_users_week,
        total_scans=total_scans,
        scans_today=scans_today,
        scans_week=scans_week,
        scans_by_status=scans_by_status,
        average_scan_duration_ms=float(avg_duration) if avg_duration else None,
        average_pages_per_scan=float(avg_pages) if avg_pages else None,
        total_issues_found=total_issues,
        issues_by_impact=issues_by_impact,
        average_score=round(float(avg_score), 1) if avg_score else None,
        timestamp=now,
        database_size_mb=round(database_size_mb, 2) if database_size_mb else None,
    )


@router.get("/users", response_model=List[UserStats])
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_user_list(
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
    limit: int = 50,
    offset: int = 0,
    plan: Optional[str] = None,
):
    """
    Get list of users with their statistics.

    Requires admin privileges.
    """
    query = db.query(User)

    # Filter by plan if specified
    if plan:
        try:
            plan_type = PlanType(plan)
            query = query.filter(User.plan == plan_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid plan type: {plan}",
            )

    # Order by creation date (newest first)
    query = query.order_by(User.created_at.desc())

    # Paginate
    users = query.offset(offset).limit(min(limit, 100)).all()

    result = []
    for user in users:
        # Get user's scan count and last scan
        scan_stats = db.query(
            func.count(Scan.id).label('total'),
            func.max(Scan.created_at).label('last_scan')
        ).filter(Scan.user_id == user.id).first()

        result.append(UserStats(
            id=str(user.id),
            email=user.email,
            plan=user.plan.value,
            is_active=user.is_active,
            is_verified=user.is_verified,
            total_scans=scan_stats.total if scan_stats else 0,
            last_scan_at=scan_stats.last_scan if scan_stats else None,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        ))

    return result


@router.get("/activity", response_model=List[RecentActivity])
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_recent_activity(
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
    limit: int = 20,
):
    """
    Get recent system activity (scans).

    Requires admin privileges.
    """
    recent_scans = db.query(Scan, User.email).join(
        User, Scan.user_id == User.id
    ).order_by(
        Scan.created_at.desc()
    ).limit(min(limit, 100)).all()

    return [
        RecentActivity(
            scan_id=str(scan.id),
            user_email=email,
            url=scan.url,
            status=scan.status.value,
            score=scan.score,
            created_at=scan.created_at,
        )
        for scan, email in recent_scans
    ]


@router.get("/health/summary")
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_health_summary(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
):
    """
    Get aggregated health summary of all system components.

    Requires admin privileges.
    """
    from app.services.health import get_system_health

    health = await get_system_health()

    # Add additional admin-only metrics
    health["admin_info"] = {
        "checked_by": admin_user.email,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    return health
