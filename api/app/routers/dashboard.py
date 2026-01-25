"""
Dashboard Router

API endpoints for dashboard statistics.
"""

from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Scan, ScanStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


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
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""

    # Get total scans
    total_scans = db.query(func.count(Scan.id)).scalar() or 0

    # Get total pages scanned
    pages_scanned = db.query(func.sum(Scan.pages_scanned)).scalar() or 0

    # Get total issues
    issues_found = db.query(func.sum(Scan.issues_count)).scalar() or 0

    # Get average score (only from completed scans with scores)
    avg_score_result = db.query(func.avg(Scan.score)).filter(
        Scan.status == ScanStatus.COMPLETED,
        Scan.score.isnot(None)
    ).scalar()
    average_score = float(avg_score_result) if avg_score_result else 0.0

    # Get recent scans (last 5)
    recent_scans_query = db.query(Scan).order_by(
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

    # Get issues by impact (aggregate from completed scans)
    issues_by_impact = {
        "critical": db.query(func.sum(Scan.issues_critical)).scalar() or 0,
        "serious": db.query(func.sum(Scan.issues_serious)).scalar() or 0,
        "moderate": db.query(func.sum(Scan.issues_moderate)).scalar() or 0,
        "minor": db.query(func.sum(Scan.issues_minor)).scalar() or 0,
    }

    # Issues by WCAG level (placeholder - would need to aggregate from issues table)
    issues_by_wcag = {
        "A": 0,
        "AA": 0,
        "AAA": 0,
    }

    # Score history (last 30 days, daily average)
    score_history = []
    for i in range(30, -1, -1):
        date = datetime.utcnow() - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")

        daily_avg = db.query(func.avg(Scan.score)).filter(
            Scan.status == ScanStatus.COMPLETED,
            Scan.score.isnot(None),
            func.date(Scan.completed_at) == date.date()
        ).scalar()

        if daily_avg is not None:
            score_history.append(ScoreHistoryItem(
                date=date_str,
                score=round(float(daily_avg), 1)
            ))

    # If no history, add some placeholder data
    if not score_history:
        today = datetime.utcnow()
        for i in range(7, -1, -1):
            date = today - timedelta(days=i)
            score_history.append(ScoreHistoryItem(
                date=date.strftime("%Y-%m-%d"),
                score=0.0
            ))

    return DashboardStats(
        totalScans=total_scans,
        pagesScanned=pages_scanned,
        issuesFound=issues_found,
        averageScore=round(average_score, 1),
        recentScans=recent_scans,
        issuesByImpact=issues_by_impact,
        issuesByWcag=issues_by_wcag,
        scoreHistory=score_history,
    )
