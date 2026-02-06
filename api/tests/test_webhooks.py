"""
Tests for webhook service.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.webhooks import (
    WebhookService,
    WebhookEvent,
    WebhookPayload,
    verify_webhook_signature,
    notify_scan_completed,
)


class TestWebhookPayload:
    """Tests for webhook payload creation."""

    def test_payload_creation(self):
        """Test creating a webhook payload."""
        payload = WebhookPayload(
            WebhookEvent.SCAN_COMPLETED,
            {"scan_id": "123", "score": 85.5}
        )

        assert payload.event == WebhookEvent.SCAN_COMPLETED
        assert payload.data["scan_id"] == "123"
        assert payload.id is not None
        assert payload.timestamp is not None

    def test_payload_to_dict(self):
        """Test converting payload to dictionary."""
        payload = WebhookPayload(
            WebhookEvent.SCAN_STARTED,
            {"url": "https://example.com"}
        )

        data = payload.to_dict()
        assert data["event"] == "scan.started"
        assert data["data"]["url"] == "https://example.com"
        assert "id" in data
        assert "timestamp" in data

    def test_payload_to_json(self):
        """Test converting payload to JSON string."""
        payload = WebhookPayload(
            WebhookEvent.SCAN_FAILED,
            {"error": "Timeout"}
        )

        json_str = payload.to_json()
        assert "scan.failed" in json_str
        assert "Timeout" in json_str


class TestWebhookSignature:
    """Tests for webhook signature verification."""

    def test_sign_and_verify(self):
        """Test signing and verifying webhook payload."""
        service = WebhookService(secret_key="test-secret")
        payload = '{"event": "test"}'

        signature = service.sign_payload(payload)
        assert signature.startswith("sha256=")

        # Verify with same secret
        assert verify_webhook_signature(payload, signature, "test-secret")

    def test_verify_invalid_signature(self):
        """Test that invalid signature is rejected."""
        assert not verify_webhook_signature(
            '{"event": "test"}',
            "sha256=invalid",
            "test-secret"
        )

    def test_verify_wrong_prefix(self):
        """Test that wrong signature prefix is rejected."""
        assert not verify_webhook_signature(
            '{"event": "test"}',
            "md5=abc123",
            "test-secret"
        )


class TestWebhookService:
    """Tests for webhook service."""

    @pytest.mark.asyncio
    async def test_send_webhook_success(self):
        """Test successful webhook delivery."""
        service = WebhookService(secret_key="test-secret")

        with patch.object(service, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await service.send(
                "https://webhook.example.com/endpoint",
                WebhookEvent.SCAN_COMPLETED,
                {"scan_id": "123", "score": 85.5}
            )

            assert result is True
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_webhook_failure(self):
        """Test webhook delivery failure handling."""
        service = WebhookService(secret_key="test-secret")

        with patch.object(service, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Connection failed")
            mock_get_client.return_value = mock_client

            result = await service.send(
                "https://webhook.example.com/endpoint",
                WebhookEvent.SCAN_COMPLETED,
                {"scan_id": "123"}
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_to_multiple_urls(self):
        """Test sending to multiple URLs."""
        service = WebhookService(secret_key="test-secret")

        with patch.object(service, 'send') as mock_send:
            mock_send.return_value = True

            results = await service.send_to_multiple(
                ["https://url1.com", "https://url2.com"],
                WebhookEvent.SCAN_COMPLETED,
                {"scan_id": "123"}
            )

            assert len(results) == 2
            assert mock_send.call_count == 2


class TestWebhookEvents:
    """Tests for webhook event types."""

    def test_event_values(self):
        """Test webhook event string values."""
        assert WebhookEvent.SCAN_STARTED.value == "scan.started"
        assert WebhookEvent.SCAN_PROGRESS.value == "scan.progress"
        assert WebhookEvent.SCAN_COMPLETED.value == "scan.completed"
        assert WebhookEvent.SCAN_FAILED.value == "scan.failed"
        assert WebhookEvent.REPORT_GENERATED.value == "report.generated"
