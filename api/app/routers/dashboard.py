"""
Dashboard Router

API endpoints for dashboard statistics.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Scan, ScanStatus, User
from ..routers.auth import get_current_user
from ..services.cache import cache_get, cache_set, cache_delete_pattern

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Cache TTL for dashboard stats (60 seconds fresh, 30 seconds stale)
DASHBOARD_CACHE_TTL = 60
DASHBOARD_STALE_TTL = 30


class RecentScan(BaseModel):
    id: str
    url: str
    status: str
    score: float | None
    issues_count: int
    created_at: datetime


class ScoreHistoryItem(BaseModel):
    date: str
    score: float


class DashboardStats(BaseModel):
    totalScans: int
    pagesScanned: int
    issuesFound: int
    averageScore: float
    recentScans: List[RecentScan]
    issuesByImpact: dict
    issuesByWcag: dict
    scoreHistory: List[ScoreHistoryItem]


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics for the current user."""
    user_id = str(current_user.id)
    cache_key = f"dashboard:stats:{user_id}"

    # Try to get from cache
    cached_stats = cache_get(cache_key)
    if cached_stats:
        logger.debug(f"Dashboard stats cache hit for user {user_id}")
        return DashboardStats(**cached_stats)

    logger.debug(f"Dashboard stats cache miss for user {user_id}")

    # Base query filtered by user
    user_scans = db.query(Scan).filter(Scan.user_id == current_user.id)

    # Get total scans
    total_scans = user_scans.with_entities(func.count(Scan.id)).scalar() or 0

    # Get total pages scanned
    pages_scanned = user_scans.with_entities(func.sum(Scan.pages_scanned)).scalar() or 0

    # Get total issues
    issues_found = user_scans.with_entities(func.sum(Scan.issues_count)).scalar() or 0

    # Get average score (only from completed scans with scores)
    avg_score_result = user_scans.filter(
        Scan.status == ScanStatus.COMPLETED,
        Scan.score.isnot(None)
    ).with_entities(func.avg(Scan.score)).scalar()
    average_score = float(avg_score_result) if avg_score_result else 0.0

    # Get recent scans (last 5)
    recent_scans_query = user_scans.order_by(
        Scan.created_at.desc()
    ).limit(5).all()

    recent_scans = [
        RecentScan(
            id=str(scan.id),
            url=scan.url,
            status=scan.status.value,
            score=scan.score,
            issues_count=scan.issues_count or 0,
            created_at=scan.created_at,
        )
        for scan in recent_scans_query
    ]

    # Get issues by impact (aggregate from user's completed scans)
    issues_by_impact = {
        "critical": user_scans.with_entities(func.sum(Scan.issues_critical)).scalar() or 0,
        "serious": user_scans.with_entities(func.sum(Scan.issues_serious)).scalar() or 0,
        "moderate": user_scans.with_entities(func.sum(Scan.issues_moderate)).scalar() or 0,
        "minor": user_scans.with_entities(func.sum(Scan.issues_minor)).scalar() or 0,
    }

    # Issues by WCAG level (placeholder - would need to aggregate from issues table)
    issues_by_wcag = {
        "A": 0,
        "AA": 0,
        "AAA": 0,
    }

    # Score history (last 30 days, daily average) - optimized to single query
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    score_history_query = db.query(
        func.date(Scan.completed_at).label('date'),
        func.avg(Scan.score).label('avg_score')
    ).filter(
        Scan.user_id == current_user.id,
        Scan.status == ScanStatus.COMPLETED,
        Scan.score.isnot(None),
        Scan.completed_at >= thirty_days_ago
    ).group_by(
        func.date(Scan.completed_at)
    ).order_by(
        func.date(Scan.completed_at)
    ).all()

    # Convert to dict for easy lookup
    score_by_date = {str(row.date): round(float(row.avg_score), 1) for row in score_history_query}

    # Build score history with all dates
    score_history = []
    for i in range(30, -1, -1):
        date = datetime.now(timezone.utc) - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        if date_str in score_by_date:
            score_history.append(ScoreHistoryItem(
                date=date_str,
                score=score_by_date[date_str]
            ))

    # If no history, add placeholder data
    if not score_history:
        today = datetime.now(timezone.utc)
        for i in range(7, -1, -1):
            date = today - timedelta(days=i)
            score_history.append(ScoreHistoryItem(
                date=date.strftime("%Y-%m-%d"),
                score=0.0
            ))

    result = DashboardStats(
        totalScans=total_scans,
        pagesScanned=pages_scanned,
        issuesFound=issues_found,
        averageScore=round(average_score, 1),
        recentScans=recent_scans,
        issuesByImpact=issues_by_impact,
        issuesByWcag=issues_by_wcag,
        scoreHistory=score_history,
    )

    # Cache the result
    cache_set(cache_key, result.model_dump(), DASHBOARD_CACHE_TTL)

    return result


def invalidate_user_dashboard_cache(user_id: str) -> None:
    """Invalidate dashboard cache for a user. Call after scan updates."""
    cache_delete_pattern(f"dashboard:stats:{user_id}")
