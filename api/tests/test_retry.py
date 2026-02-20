"""
Tests for retry utilities.
"""

import pytest
from unittest.mock import MagicMock, patch
import asyncio

from sqlalchemy.exc import OperationalError, IntegrityError

from app.utils.retry import (
    retry_on_db_error,
    async_retry_on_db_error,
    execute_with_retry,
    is_transient_db_error,
)


class TestIsTransientDbError:
    """Tests for is_transient_db_error function."""

    def test_connection_timeout_is_transient(self):
        """Connection timeout errors should be retryable."""
        error = OperationalError("connection timeout", None, None)
        assert is_transient_db_error(error) is True

    def test_connection_refused_is_transient(self):
        """Connection refused errors should be retryable."""
        error = OperationalError("connection refused", None, None)
        assert is_transient_db_error(error) is True

    def test_pool_exhaustion_is_transient(self):
        """Pool exhaustion errors should be retryable."""
        error = OperationalError("QueuePool limit reached", None, None)
        assert is_transient_db_error(error) is True

    def test_lost_connection_is_transient(self):
        """Lost connection errors should be retryable."""
        error = OperationalError("lost connection during query", None, None)
        assert is_transient_db_error(error) is True

    def test_integrity_error_not_transient(self):
        """Integrity errors should not be retryable."""
        error = IntegrityError("unique constraint violation", None, None)
        assert is_transient_db_error(error) is False

    def test_generic_timeout_is_transient(self):
        """Generic timeout errors should be retryable."""
        error = TimeoutError("operation timed out")
        assert is_transient_db_error(error) is True


class TestRetryOnDbError:
    """Tests for retry_on_db_error decorator."""

    def test_success_no_retry(self):
        """Function succeeds on first attempt, no retry needed."""
        mock_func = MagicMock(return_value="success")

        @retry_on_db_error(max_retries=3)
        def test_func():
            return mock_func()

        result = test_func()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_on_transient_error(self):
        """Function retries on transient error and succeeds."""
        call_count = 0

        @retry_on_db_error(max_retries=3, base_delay=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OperationalError("connection timeout", None, None)
            return "success"

        result = test_func()

        assert result == "success"
        assert call_count == 2

    def test_max_retries_exceeded(self):
        """Function raises after max retries exceeded."""
        @retry_on_db_error(max_retries=2, base_delay=0.01)
        def test_func():
            raise OperationalError("connection timeout", None, None)

        with pytest.raises(OperationalError):
            test_func()

    def test_no_retry_on_non_transient_error(self):
        """Function does not retry on non-transient error."""
        call_count = 0

        @retry_on_db_error(max_retries=3, base_delay=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise IntegrityError("unique constraint", None, None)

        with pytest.raises(IntegrityError):
            test_func()

        assert call_count == 1


class TestAsyncRetryOnDbError:
    """Tests for async_retry_on_db_error decorator."""

    @pytest.mark.asyncio
    async def test_async_success_no_retry(self):
        """Async function succeeds on first attempt."""
        mock_func = MagicMock(return_value="success")

        @async_retry_on_db_error(max_retries=3)
        async def test_func():
            return mock_func()

        result = await test_func()

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_on_transient_error(self):
        """Async function retries on transient error."""
        call_count = 0

        @async_retry_on_db_error(max_retries=3, base_delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OperationalError("connection lost", None, None)
            return "success"

        result = await test_func()

        assert result == "success"
        assert call_count == 2


class TestExecuteWithRetry:
    """Tests for execute_with_retry function."""

    def test_execute_success(self):
        """Execute succeeds on first attempt."""
        result = execute_with_retry(
            lambda: "success",
            max_retries=3
        )
        assert result == "success"

    def test_execute_retry_then_success(self):
        """Execute retries and eventually succeeds."""
        call_count = 0

        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OperationalError("timeout", None, None)
            return "success"

        result = execute_with_retry(
            flaky_func,
            max_retries=3,
            base_delay=0.01
        )

        assert result == "success"
        assert call_count == 2

    def test_execute_max_retries_exceeded(self):
        """Execute raises after all retries exhausted."""
        with pytest.raises(OperationalError):
            execute_with_retry(
                lambda: (_ for _ in ()).throw(
                    OperationalError("timeout", None, None)
                ),
                max_retries=2,
                base_delay=0.01
            )
