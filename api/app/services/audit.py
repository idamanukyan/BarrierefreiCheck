"""
Audit Logging Service

Provides audit trail functionality for security-sensitive operations.
Important for GDPR compliance and security monitoring.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from functools import wraps

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Use a dedicated logger for audit events
audit_logger = logging.getLogger("audit")


class AuditAction(str, Enum):
    """Audit action types for categorization."""
    # Authentication
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    LOGOUT = "auth.logout"
    PASSWORD_RESET_REQUEST = "auth.password_reset.request"
    PASSWORD_RESET_COMPLETE = "auth.password_reset.complete"
    PASSWORD_CHANGE = "auth.password.change"
    EMAIL_VERIFICATION = "auth.email.verify"

    # User Management
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_EXPORT_DATA = "user.export_data"
    USER_DELETE_DATA = "user.delete_data"

    # API Keys
    API_KEY_CREATE = "api_key.create"
    API_KEY_DELETE = "api_key.delete"
    API_KEY_USED = "api_key.used"

    # Scans
    SCAN_CREATE = "scan.create"
    SCAN_DELETE = "scan.delete"

    # Billing
    SUBSCRIPTION_CREATE = "billing.subscription.create"
    SUBSCRIPTION_CANCEL = "billing.subscription.cancel"
    SUBSCRIPTION_UPDATE = "billing.subscription.update"
    PAYMENT_SUCCESS = "billing.payment.success"
    PAYMENT_FAILED = "billing.payment.failed"

    # Admin Actions
    ADMIN_USER_VIEW = "admin.user.view"
    ADMIN_USER_MODIFY = "admin.user.modify"
    ADMIN_SETTINGS_CHANGE = "admin.settings.change"

    # Security Events
    RATE_LIMIT_EXCEEDED = "security.rate_limit"
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    SSRF_ATTEMPT = "security.ssrf_attempt"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def log_audit_event(
    action: AuditAction,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    severity: AuditSeverity = AuditSeverity.INFO,
    correlation_id: Optional[str] = None,
):
    """
    Log an audit event.

    This function logs audit events in a structured format suitable for:
    - Security Information and Event Management (SIEM) systems
    - Compliance reporting (GDPR Article 30)
    - Forensic analysis

    Args:
        action: The type of action being audited
        user_id: ID of the user performing the action
        email: Email of the user (for failed login attempts)
        ip_address: IP address of the request
        user_agent: User agent string from the request
        resource_type: Type of resource being acted upon (e.g., "scan", "user")
        resource_id: ID of the specific resource
        details: Additional context for the event
        severity: Severity level of the event
        correlation_id: Request correlation ID for tracing
    """
    # Build audit record
    audit_record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "action": action.value,
        "severity": severity.value,
        "actor": {
            "user_id": user_id,
            "email": _mask_email(email) if email else None,
            "ip_address": ip_address,
            "user_agent": _truncate_user_agent(user_agent),
        },
        "resource": {
            "type": resource_type,
            "id": resource_id,
        } if resource_type else None,
        "details": _sanitize_details(details),
        "correlation_id": correlation_id,
    }

    # Remove None values for cleaner logs
    audit_record = {k: v for k, v in audit_record.items() if v is not None}
    if audit_record.get("actor"):
        audit_record["actor"] = {k: v for k, v in audit_record["actor"].items() if v is not None}
    if audit_record.get("resource"):
        audit_record["resource"] = {k: v for k, v in audit_record["resource"].items() if v is not None}

    # Log the event
    log_message = f"AUDIT: {action.value}"
    if resource_type and resource_id:
        log_message += f" | {resource_type}:{resource_id}"
    if user_id:
        log_message += f" | user:{user_id}"

    # Use appropriate log level based on severity
    log_level = {
        AuditSeverity.INFO: logging.INFO,
        AuditSeverity.WARNING: logging.WARNING,
        AuditSeverity.ERROR: logging.ERROR,
        AuditSeverity.CRITICAL: logging.CRITICAL,
    }.get(severity, logging.INFO)

    audit_logger.log(log_level, log_message, extra={"audit_data": audit_record})

    # Also log to main logger in debug mode
    logger.debug(f"Audit event: {json.dumps(audit_record)}")


def _mask_email(email: str) -> str:
    """Mask email address for privacy (keep first char and domain)."""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked_local}@{domain}"


def _truncate_user_agent(user_agent: Optional[str], max_length: int = 200) -> Optional[str]:
    """Truncate user agent to reasonable length."""
    if not user_agent:
        return None
    return user_agent[:max_length] if len(user_agent) > max_length else user_agent


def _sanitize_details(details: Optional[dict]) -> Optional[dict]:
    """Sanitize details dict to remove sensitive information."""
    if not details:
        return None

    # Keys that should never be logged
    sensitive_keys = {
        "password", "secret", "token", "key", "authorization",
        "credit_card", "cvv", "ssn", "api_key", "access_token",
        "refresh_token", "jwt", "bearer",
    }

    sanitized = {}
    for key, value in details.items():
        lower_key = key.lower()
        if any(sensitive in lower_key for sensitive in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_details(value)
        else:
            sanitized[key] = value

    return sanitized


def audit_decorator(
    action: AuditAction,
    resource_type: Optional[str] = None,
    get_resource_id: Optional[callable] = None,
    severity: AuditSeverity = AuditSeverity.INFO,
):
    """
    Decorator to automatically log audit events for functions.

    Usage:
        @audit_decorator(AuditAction.USER_CREATE, resource_type="user")
        async def create_user(user_data, current_user):
            ...

        @audit_decorator(
            AuditAction.SCAN_DELETE,
            resource_type="scan",
            get_resource_id=lambda args, kwargs: kwargs.get("scan_id")
        )
        async def delete_scan(scan_id, current_user):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to extract user from common patterns
            user_id = None
            request = kwargs.get("request")

            # Try to get user from dependency injection patterns
            current_user = kwargs.get("current_user")
            if current_user and hasattr(current_user, "id"):
                user_id = str(current_user.id)

            # Try to get resource ID
            resource_id = None
            if get_resource_id:
                try:
                    resource_id = get_resource_id(args, kwargs)
                except Exception:
                    pass

            # Get IP and correlation ID from request if available
            ip_address = None
            correlation_id = None
            user_agent = None
            if request:
                ip_address = getattr(request, "client", {})
                if hasattr(ip_address, "host"):
                    ip_address = ip_address.host
                else:
                    ip_address = None
                correlation_id = getattr(request.state, "correlation_id", None)
                user_agent = request.headers.get("user-agent")

            try:
                result = await func(*args, **kwargs)

                # Log success
                log_audit_event(
                    action=action,
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    resource_type=resource_type,
                    resource_id=str(resource_id) if resource_id else None,
                    severity=severity,
                    correlation_id=correlation_id,
                )

                return result

            except Exception as e:
                # Log failure
                log_audit_event(
                    action=action,
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    resource_type=resource_type,
                    resource_id=str(resource_id) if resource_id else None,
                    details={"error": str(e), "status": "failed"},
                    severity=AuditSeverity.ERROR,
                    correlation_id=correlation_id,
                )
                raise

        return wrapper
    return decorator


# Convenience functions for common audit events

def audit_login_success(
    user_id: str,
    email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    correlation_id: Optional[str] = None,
):
    """Log successful login."""
    log_audit_event(
        action=AuditAction.LOGIN_SUCCESS,
        user_id=user_id,
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
    )


def audit_login_failed(
    email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    reason: Optional[str] = None,
    correlation_id: Optional[str] = None,
):
    """Log failed login attempt."""
    log_audit_event(
        action=AuditAction.LOGIN_FAILED,
        email=email,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"reason": reason} if reason else None,
        severity=AuditSeverity.WARNING,
        correlation_id=correlation_id,
    )


def audit_data_export(
    user_id: str,
    ip_address: Optional[str] = None,
    correlation_id: Optional[str] = None,
):
    """Log GDPR data export request."""
    log_audit_event(
        action=AuditAction.USER_EXPORT_DATA,
        user_id=user_id,
        ip_address=ip_address,
        resource_type="user",
        resource_id=user_id,
        details={"gdpr_request": True},
        correlation_id=correlation_id,
    )


def audit_data_deletion(
    user_id: str,
    ip_address: Optional[str] = None,
    correlation_id: Optional[str] = None,
):
    """Log GDPR data deletion request."""
    log_audit_event(
        action=AuditAction.USER_DELETE_DATA,
        user_id=user_id,
        ip_address=ip_address,
        resource_type="user",
        resource_id=user_id,
        details={"gdpr_request": True},
        severity=AuditSeverity.WARNING,
        correlation_id=correlation_id,
    )


def audit_security_event(
    event_type: AuditAction,
    ip_address: Optional[str] = None,
    user_id: Optional[str] = None,
    details: Optional[dict] = None,
    correlation_id: Optional[str] = None,
):
    """Log security-related events."""
    log_audit_event(
        action=event_type,
        user_id=user_id,
        ip_address=ip_address,
        details=details,
        severity=AuditSeverity.WARNING,
        correlation_id=correlation_id,
    )
