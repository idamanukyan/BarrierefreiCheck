"""
Tests for resilience patterns (circuit breaker, retry).
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from app.services.resilience import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitState,
    retry_with_backoff,
)


class TestCircuitBreaker:
    """Tests for circuit breaker pattern."""

    @pytest.mark.asyncio
    async def test_closed_state_allows_requests(self):
        """Test that closed circuit allows requests."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        @breaker
        async def successful_call():
            return "success"

        result = await successful_call()
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        """Test that circuit opens after threshold failures."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        @breaker
        async def failing_call():
            raise ValueError("error")

        # Trigger failures
        for _ in range(3):
            with pytest.raises(ValueError):
                await failing_call()

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_requests(self):
        """Test that open circuit rejects requests."""
        breaker = CircuitBreaker("test", failure_threshold=2, recovery_timeout=60)

        @breaker
        async def failing_call():
            raise ValueError("error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await failing_call()

        # Should reject with CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            await failing_call()

    @pytest.mark.asyncio
    async def test_successful_call_resets_failure_count(self):
        """Test that successful call resets failure count."""
        breaker = CircuitBreaker("test", failure_threshold=3)
        call_count = 0

        @breaker
        async def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:
                raise ValueError("error")
            return "success"

        # Fail once
        with pytest.raises(ValueError):
            await sometimes_fails()

        # Succeed
        result = await sometimes_fails()
        assert result == "success"

        # Fail once more - should still be closed
        with pytest.raises(ValueError):
            await sometimes_fails()

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_manual_reset(self):
        """Test manual circuit breaker reset."""
        breaker = CircuitBreaker("test", failure_threshold=2)

        @breaker
        async def failing_call():
            raise ValueError("error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                await failing_call()

        assert breaker.state == CircuitState.OPEN

        # Manual reset
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED


class TestRetryWithBackoff:
    """Tests for retry with backoff."""

    @pytest.mark.asyncio
    async def test_succeeds_without_retry(self):
        """Test that successful call doesn't retry."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        async def successful_call():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_call()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """Test that function retries on failure."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
        async def fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("error")
            return "success"

        result = await fails_twice()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Test that error is raised after max retries."""
        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01, exceptions=(ValueError,))
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")

        with pytest.raises(ValueError, match="persistent error"):
            await always_fails()

        assert call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_only_catches_specified_exceptions(self):
        """Test that only specified exceptions trigger retry."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
        async def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("unexpected error")

        with pytest.raises(TypeError):
            await raises_type_error()

        assert call_count == 1  # No retry for TypeError

    @pytest.mark.asyncio
    async def test_calls_on_retry_callback(self):
        """Test that on_retry callback is called."""
        retry_calls = []

        def on_retry(exc, attempt):
            retry_calls.append((str(exc), attempt))

        @retry_with_backoff(
            max_retries=2,
            base_delay=0.01,
            exceptions=(ValueError,),
            on_retry=on_retry,
        )
        async def always_fails():
            raise ValueError("error")

        with pytest.raises(ValueError):
            await always_fails()

        assert len(retry_calls) == 2
        assert retry_calls[0][1] == 1
        assert retry_calls[1][1] == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test that delay increases exponentially."""
        import time

        timestamps = []

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.05,
            exponential_base=2.0,
            exceptions=(ValueError,),
        )
        async def record_time_and_fail():
            timestamps.append(time.time())
            raise ValueError("error")

        with pytest.raises(ValueError):
            await record_time_and_fail()

        # Check delays: ~0.05s, ~0.1s, ~0.2s
        assert len(timestamps) == 4
        delay1 = timestamps[1] - timestamps[0]
        delay2 = timestamps[2] - timestamps[1]
        delay3 = timestamps[3] - timestamps[2]

        # Allow some tolerance for timing
        assert 0.04 < delay1 < 0.1
        assert 0.08 < delay2 < 0.2
        assert 0.15 < delay3 < 0.4
