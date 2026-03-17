"""Unit tests for EEP exceptions."""

import pytest

from workers.eep import (
    EEPError,
    ExecutionTimeoutError,
    IsolationError,
    MemoryLimitExceededError,
    ProcessCrashedError,
)


class TestEEPExceptions:
    """Test EEP exception hierarchy."""

    def test_base_exception(self):
        """Test base EEPError."""
        error = EEPError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)

    def test_timeout_error(self):
        """Test ExecutionTimeoutError."""
        error = ExecutionTimeoutError(timeout=300)
        assert isinstance(error, EEPError)
        assert "300" in str(error)
        assert error.timeout == 300

    def test_memory_error(self):
        """Test MemoryLimitExceededError."""
        error = MemoryLimitExceededError(limit_mb=512, actual_mb=600)
        assert isinstance(error, EEPError)
        assert "512" in str(error)
        assert error.limit_mb == 512
        assert error.actual_mb == 600

    def test_crash_error(self):
        """Test ProcessCrashedError."""
        error = ProcessCrashedError(exit_code=-11)
        assert isinstance(error, EEPError)
        assert "crashed" in str(error).lower()
        assert error.exit_code == -11

    def test_isolation_error(self):
        """Test IsolationError."""
        error = IsolationError("Failed to set resource limits")
        assert isinstance(error, EEPError)
        assert "isolation" in str(error).lower() or "Failed" in str(error)

    def test_exception_inheritance(self):
        """Test all exceptions inherit from EEPError."""
        exceptions = [
            ExecutionTimeoutError(timeout=300),
            MemoryLimitExceededError(limit_mb=512),
            ProcessCrashedError(exit_code=-11),
            IsolationError("test"),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, EEPError)
            assert isinstance(exc, Exception)

    def test_exception_with_context(self):
        """Test exceptions can carry context."""
        error = ExecutionTimeoutError(
            timeout=600,
            message="Task 'collect_device_data' timed out after 600s"
        )
        message = str(error)
        assert "collect_device_data" in message
        assert "600" in message

    def test_raise_and_catch(self):
        """Test raising and catching EEP exceptions."""
        with pytest.raises(EEPError):
            raise ExecutionTimeoutError(timeout=300)
        
        with pytest.raises(ExecutionTimeoutError):
            raise ExecutionTimeoutError(timeout=300)
        
        # Catch specific exception
        try:
            raise MemoryLimitExceededError(limit_mb=512)
        except EEPError as e:
            assert isinstance(e, MemoryLimitExceededError)
