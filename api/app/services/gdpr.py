"""
GDPR Compliance Service

Handles user data export (Art. 20 GDPR - Data Portability) and
user data deletion (Art. 17 GDPR - Right to be Forgotten).
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models import (
    User,
    Scan,
    Page,
    Issue,
    APIKey,
    Subscription,
    Payment,
    UsageRecord,
    Report,
)

logger = logging.getLogger(__name__)


class GDPRService:
    """Service for GDPR compliance operations."""

    # Data retention period in days (default: 2 years for German commercial records)
    DEFAULT_RETENTION_DAYS = 730

    @staticmethod
    def get_user_export_data(user_id: UUID, db: Session) -> Dict[str, Any]:
        """
        Gather all user data for GDPR export (Art. 20 - Data Portability).

        Args:
            user_id: The user's UUID
            db: Database session

        Returns:
            Dictionary containing all user data in portable format
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        # Get all user data with eager loading to avoid N+1 queries
        scans = (
            db.query(Scan)
            .options(joinedload(Scan.pages).joinedload(Page.issues))
            .filter(Scan.user_id == user_id)
            .all()
        )

        api_keys = db.query(APIKey).filter(APIKey.user_id == user_id).all()

        subscription = (
            db.query(Subscription)
            .options(joinedload(Subscription.payments))
            .filter(Subscription.user_id == user_id)
            .first()
        )

        usage_records = (
            db.query(UsageRecord).filter(UsageRecord.user_id == user_id).all()
        )

        reports = db.query(Report).filter(Report.user_id == user_id).all()

        # Build export data structure
        export_data = {
            "export_metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "format_version": "1.0",
                "gdpr_article": "Art. 20 GDPR - Right to Data Portability",
            },
            "user": GDPRService._serialize_user(user),
            "scans": [GDPRService._serialize_scan(scan) for scan in scans],
            "api_keys": [GDPRService._serialize_api_key(key) for key in api_keys],
            "subscription": (
                GDPRService._serialize_subscription(subscription)
                if subscription
                else None
            ),
            "usage_records": [
                GDPRService._serialize_usage_record(record) for record in usage_records
            ],
            "reports": [GDPRService._serialize_report(report) for report in reports],
        }

        return export_data

    @staticmethod
    def export_to_json(user_id: UUID, db: Session) -> str:
        """
        Export user data to JSON format.

        Args:
            user_id: The user's UUID
            db: Database session

        Returns:
            JSON string of all user data
        """
        data = GDPRService.get_user_export_data(user_id, db)
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def delete_user_data(
        user_id: UUID, db: Session, keep_anonymized_stats: bool = False
    ) -> Dict[str, Any]:
        """
        Delete all user data (Art. 17 GDPR - Right to be Forgotten).

        Args:
            user_id: The user's UUID
            db: Database session
            keep_anonymized_stats: Whether to keep anonymized usage statistics

        Returns:
            Summary of deleted data
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found", "deleted": False}

        deletion_summary = {
            "user_id": str(user_id),
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "counts": {},
        }

        # Count data before deletion
        scans_count = db.query(Scan).filter(Scan.user_id == user_id).count()
        api_keys_count = db.query(APIKey).filter(APIKey.user_id == user_id).count()
        reports_count = db.query(Report).filter(Report.user_id == user_id).count()
        usage_records_count = (
            db.query(UsageRecord).filter(UsageRecord.user_id == user_id).count()
        )

        # Get subscription and payments count
        subscription = (
            db.query(Subscription).filter(Subscription.user_id == user_id).first()
        )
        payments_count = 0
        if subscription:
            payments_count = (
                db.query(Payment)
                .filter(Payment.subscription_id == subscription.id)
                .count()
            )

        deletion_summary["counts"] = {
            "scans": scans_count,
            "api_keys": api_keys_count,
            "reports": reports_count,
            "usage_records": usage_records_count,
            "payments": payments_count,
            "subscription": 1 if subscription else 0,
        }

        # Delete in order (respecting foreign key constraints)
        # Note: Most cascades are handled by SQLAlchemy relationships

        # Delete usage records (no cascade from user)
        db.query(UsageRecord).filter(UsageRecord.user_id == user_id).delete()

        # Delete reports (no cascade from user)
        db.query(Report).filter(Report.user_id == user_id).delete()

        # Delete the user - cascades will handle:
        # - Scans -> Pages -> Issues
        # - Subscription -> Payments
        # - API Keys
        db.delete(user)
        db.commit()

        logger.info(
            f"GDPR: Deleted all data for user {user_id}",
            extra={
                "user_id": str(user_id),
                "deletion_summary": deletion_summary,
                "gdpr_article": "Art. 17 GDPR",
            },
        )

        deletion_summary["deleted"] = True
        return deletion_summary

    @staticmethod
    def apply_retention_policy(
        db: Session, retention_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Apply data retention policy - delete data older than retention period.

        This should be run as a scheduled task (e.g., daily cron job).

        Args:
            db: Database session
            retention_days: Number of days to retain data (default: 730 days / 2 years)

        Returns:
            Summary of deleted data
        """
        if retention_days is None:
            retention_days = GDPRService.DEFAULT_RETENTION_DAYS

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        summary = {
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "deleted_counts": {},
        }

        # Delete old completed scans (and cascade to pages/issues)
        old_scans = (
            db.query(Scan)
            .filter(
                Scan.created_at < cutoff_date,
                Scan.status.in_(["completed", "failed", "cancelled"]),
            )
            .all()
        )

        scan_ids_to_delete = [scan.id for scan in old_scans]
        summary["deleted_counts"]["scans"] = len(scan_ids_to_delete)

        # Delete reports for old scans
        if scan_ids_to_delete:
            reports_deleted = (
                db.query(Report)
                .filter(Report.scan_id.in_(scan_ids_to_delete))
                .delete(synchronize_session=False)
            )
            summary["deleted_counts"]["reports"] = reports_deleted

            # Delete the scans (cascades to pages and issues)
            for scan in old_scans:
                db.delete(scan)

        # Delete old usage records
        old_usage_records = (
            db.query(UsageRecord)
            .filter(UsageRecord.period_end < cutoff_date)
            .delete(synchronize_session=False)
        )
        summary["deleted_counts"]["usage_records"] = old_usage_records

        # Delete expired API keys
        expired_api_keys = (
            db.query(APIKey)
            .filter(
                APIKey.expires_at.isnot(None),
                APIKey.expires_at < datetime.now(timezone.utc),
            )
            .delete(synchronize_session=False)
        )
        summary["deleted_counts"]["expired_api_keys"] = expired_api_keys

        db.commit()

        logger.info(
            "GDPR: Applied data retention policy",
            extra={"retention_summary": summary},
        )

        return summary

    @staticmethod
    def get_user_data_summary(user_id: UUID, db: Session) -> Dict[str, Any]:
        """
        Get a summary of user data (without full export).

        Useful for showing users what data will be exported/deleted.

        Args:
            user_id: The user's UUID
            db: Database session

        Returns:
            Summary of user data counts
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        scans_count = db.query(Scan).filter(Scan.user_id == user_id).count()

        # Count total pages and issues
        pages_count = (
            db.query(Page)
            .join(Scan)
            .filter(Scan.user_id == user_id)
            .count()
        )
        issues_count = (
            db.query(Issue)
            .join(Page)
            .join(Scan)
            .filter(Scan.user_id == user_id)
            .count()
        )

        api_keys_count = db.query(APIKey).filter(APIKey.user_id == user_id).count()
        reports_count = db.query(Report).filter(Report.user_id == user_id).count()

        subscription = (
            db.query(Subscription).filter(Subscription.user_id == user_id).first()
        )
        payments_count = 0
        if subscription:
            payments_count = (
                db.query(Payment)
                .filter(Payment.subscription_id == subscription.id)
                .count()
            )

        return {
            "user": {
                "email": user.email,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "data_counts": {
                "scans": scans_count,
                "pages": pages_count,
                "issues": issues_count,
                "api_keys": api_keys_count,
                "reports": reports_count,
                "payments": payments_count,
                "has_subscription": subscription is not None,
            },
        }

    # Private serialization methods

    @staticmethod
    def _serialize_user(user: User) -> Dict[str, Any]:
        """Serialize user data for export."""
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "company": user.company,
            "plan": user.plan.value if user.plan else None,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login_at": (
                user.last_login_at.isoformat() if user.last_login_at else None
            ),
        }

    @staticmethod
    def _serialize_scan(scan: Scan) -> Dict[str, Any]:
        """Serialize scan data for export."""
        return {
            "id": str(scan.id),
            "url": scan.url,
            "crawl": scan.crawl,
            "max_pages": scan.max_pages,
            "status": scan.status.value if scan.status else None,
            "score": scan.score,
            "pages_scanned": scan.pages_scanned,
            "issues_count": scan.issues_count,
            "issues_by_impact": {
                "critical": scan.issues_critical,
                "serious": scan.issues_serious,
                "moderate": scan.issues_moderate,
                "minor": scan.issues_minor,
            },
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
            "started_at": scan.started_at.isoformat() if scan.started_at else None,
            "completed_at": (
                scan.completed_at.isoformat() if scan.completed_at else None
            ),
            "pages": [GDPRService._serialize_page(page) for page in scan.pages],
        }

    @staticmethod
    def _serialize_page(page: Page) -> Dict[str, Any]:
        """Serialize page data for export."""
        return {
            "id": str(page.id),
            "url": page.url,
            "title": page.title,
            "depth": page.depth,
            "score": page.score,
            "issues_count": page.issues_count,
            "passed_rules": page.passed_rules,
            "failed_rules": page.failed_rules,
            "load_time_ms": page.load_time_ms,
            "scan_time_ms": page.scan_time_ms,
            "scanned_at": page.scanned_at.isoformat() if page.scanned_at else None,
            "issues": [GDPRService._serialize_issue(issue) for issue in page.issues],
        }

    @staticmethod
    def _serialize_issue(issue: Issue) -> Dict[str, Any]:
        """Serialize issue data for export."""
        return {
            "id": str(issue.id),
            "rule_id": issue.rule_id,
            "impact": issue.impact.value if issue.impact else None,
            "wcag_criteria": issue.wcag_criteria,
            "wcag_level": issue.wcag_level.value if issue.wcag_level else None,
            "bfsg_reference": issue.bfsg_reference,
            "title_de": issue.title_de,
            "description_de": issue.description_de,
            "fix_suggestion_de": issue.fix_suggestion_de,
            "element_selector": issue.element_selector,
            "element_html": issue.element_html,
            "help_url": issue.help_url,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
        }

    @staticmethod
    def _serialize_api_key(api_key: APIKey) -> Dict[str, Any]:
        """Serialize API key data for export (excluding the key hash)."""
        return {
            "id": str(api_key.id),
            "name": api_key.name,
            "description": api_key.description,
            "key_prefix": api_key.key_prefix,
            "scopes": api_key.scopes,
            "is_active": api_key.is_active,
            "created_at": (
                api_key.created_at.isoformat() if api_key.created_at else None
            ),
            "last_used_at": (
                api_key.last_used_at.isoformat() if api_key.last_used_at else None
            ),
            "expires_at": (
                api_key.expires_at.isoformat() if api_key.expires_at else None
            ),
            "usage_count": api_key.usage_count,
        }

    @staticmethod
    def _serialize_subscription(subscription: Subscription) -> Dict[str, Any]:
        """Serialize subscription data for export."""
        return {
            "id": str(subscription.id),
            "plan": subscription.plan.value if subscription.plan else None,
            "status": subscription.status.value if subscription.status else None,
            "current_period_start": (
                subscription.current_period_start.isoformat()
                if subscription.current_period_start
                else None
            ),
            "current_period_end": (
                subscription.current_period_end.isoformat()
                if subscription.current_period_end
                else None
            ),
            "trial_end": (
                subscription.trial_end.isoformat() if subscription.trial_end else None
            ),
            "created_at": (
                subscription.created_at.isoformat() if subscription.created_at else None
            ),
            "canceled_at": (
                subscription.canceled_at.isoformat()
                if subscription.canceled_at
                else None
            ),
            "payments": [
                GDPRService._serialize_payment(payment)
                for payment in subscription.payments
            ],
        }

    @staticmethod
    def _serialize_payment(payment: Payment) -> Dict[str, Any]:
        """Serialize payment data for export."""
        return {
            "id": str(payment.id),
            "amount": payment.amount,
            "amount_formatted": payment.amount_formatted,
            "currency": payment.currency,
            "status": payment.status.value if payment.status else None,
            "invoice_number": payment.invoice_number,
            "description": payment.description,
            "created_at": payment.created_at.isoformat() if payment.created_at else None,
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        }

    @staticmethod
    def _serialize_usage_record(record: UsageRecord) -> Dict[str, Any]:
        """Serialize usage record for export."""
        return {
            "id": str(record.id),
            "period_start": (
                record.period_start.isoformat() if record.period_start else None
            ),
            "period_end": (
                record.period_end.isoformat() if record.period_end else None
            ),
            "scans_count": record.scans_count,
            "pages_scanned": record.pages_scanned,
            "reports_generated": record.reports_generated,
            "api_calls": record.api_calls,
        }

    @staticmethod
    def _serialize_report(report: Report) -> Dict[str, Any]:
        """Serialize report metadata for export (not file content)."""
        return {
            "id": str(report.id),
            "scan_id": str(report.scan_id),
            "format": report.format.value if report.format else None,
            "language": report.language,
            "include_screenshots": report.include_screenshots,
            "status": report.status,
            "file_size": report.file_size,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "expires_at": report.expires_at.isoformat() if report.expires_at else None,
        }


# Global service instance
gdpr_service = GDPRService()


def get_gdpr_service() -> GDPRService:
    """Get the GDPR service instance."""
    return gdpr_service
