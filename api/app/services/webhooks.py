"""
Webhook Service

Send notifications to external URLs when events occur.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx

from app.config import settings
from app.services.resilience import retry_with_backoff

logger = logging.getLogger(__name__)


class WebhookEvent(str, Enum):
    """Webhook event types."""
    SCAN_STARTED = "scan.started"
    SCAN_PROGRESS = "scan.progress"
    SCAN_COMPLETED = "scan.completed"
    SCAN_FAILED = "scan.failed"
    REPORT_GENERATED = "report.generated"


class WebhookPayload:
    """Webhook payload builder."""

    def __init__(self, event: WebhookEvent, data: Dict[str, Any]):
        self.event = event
        self.data = data
        self.timestamp = datetime.utcnow().isoformat()
        self.id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique webhook delivery ID."""
        import uuid
        return str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "event": self.event.value,
            "timestamp": self.timestamp,
            "data": self.data,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class WebhookService:
    """Service for managing and sending webhooks."""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or settings.jwt_secret
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                follow_redirects=True,
            )
        return self._client

    def sign_payload(self, payload: str) -> str:
        """Generate HMAC signature for webhook payload."""
        signature = hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(httpx.HTTPError, httpx.TimeoutException)
    )
    async def _send_webhook(
        self,
        url: str,
        payload: WebhookPayload,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """Send webhook to URL with retry logic."""
        client = await self._get_client()

        json_payload = payload.to_json()
        signature = self.sign_payload(json_payload)

        request_headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": payload.event.value,
            "X-Webhook-Delivery": payload.id,
            "X-Webhook-Timestamp": payload.timestamp,
            "User-Agent": "AccessibilityChecker-Webhook/1.0",
        }
        if headers:
            request_headers.update(headers)

        response = await client.post(
            url,
            content=json_payload,
            headers=request_headers,
        )

        if response.status_code >= 400:
            logger.warning(
                f"Webhook delivery failed: {url} returned {response.status_code}"
            )
            response.raise_for_status()

        logger.info(f"Webhook delivered successfully: {payload.event.value} to {url}")
        return True

    async def send(
        self,
        url: str,
        event: WebhookEvent,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send a webhook notification.

        Args:
            url: Destination URL
            event: Event type
            data: Event data
            headers: Optional additional headers

        Returns:
            True if successful, False otherwise
        """
        payload = WebhookPayload(event, data)

        try:
            return await self._send_webhook(url, payload, headers)
        except Exception as e:
            logger.error(f"Failed to send webhook to {url}: {e}")
            return False

    async def send_to_multiple(
        self,
        urls: List[str],
        event: WebhookEvent,
        data: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Send webhook to multiple URLs concurrently.

        Returns:
            Dict mapping URL to success status
        """
        tasks = [self.send(url, event, data) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            url: result is True
            for url, result in zip(urls, results)
        }

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Global webhook service instance
_webhook_service: Optional[WebhookService] = None


def get_webhook_service() -> WebhookService:
    """Get or create the global webhook service."""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service


# Convenience functions for common webhook events
async def notify_scan_started(
    webhook_url: str,
    scan_id: str,
    url: str,
    user_id: str
) -> bool:
    """Send scan started notification."""
    service = get_webhook_service()
    return await service.send(
        webhook_url,
        WebhookEvent.SCAN_STARTED,
        {
            "scan_id": scan_id,
            "url": url,
            "user_id": user_id,
            "started_at": datetime.utcnow().isoformat(),
        }
    )


async def notify_scan_completed(
    webhook_url: str,
    scan_id: str,
    url: str,
    score: float,
    issues_count: int,
    pages_scanned: int,
    duration_seconds: int
) -> bool:
    """Send scan completed notification."""
    service = get_webhook_service()
    return await service.send(
        webhook_url,
        WebhookEvent.SCAN_COMPLETED,
        {
            "scan_id": scan_id,
            "url": url,
            "score": score,
            "issues_count": issues_count,
            "pages_scanned": pages_scanned,
            "duration_seconds": duration_seconds,
            "completed_at": datetime.utcnow().isoformat(),
        }
    )


async def notify_scan_failed(
    webhook_url: str,
    scan_id: str,
    url: str,
    error: str
) -> bool:
    """Send scan failed notification."""
    service = get_webhook_service()
    return await service.send(
        webhook_url,
        WebhookEvent.SCAN_FAILED,
        {
            "scan_id": scan_id,
            "url": url,
            "error": error,
            "failed_at": datetime.utcnow().isoformat(),
        }
    )


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verify incoming webhook signature.

    Use this to verify webhooks from external services.
    """
    if not signature.startswith("sha256="):
        return False

    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    provided = signature[7:]  # Remove "sha256=" prefix

    return hmac.compare_digest(expected, provided)
