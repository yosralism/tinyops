"""EEP-specific exceptions."""

from __future__ import annotations


class EEPError(Exception):
    """Base exception for EEP-related errors."""
    pass


class ExecutionTimeoutError(EEPError):
    """Raised when task execution exceeds the configured timeout."""
    
    def __init__(self, timeout: int, message: str | None = None):
        self.timeout = timeout
        if message is None:
            message = f"Task execution exceeded timeout of {timeout} seconds"
        super().__init__(message)


class MemoryLimitExceededError(EEPError):
    """Raised when task exceeds memory limit."""
    
    def __init__(self, limit_mb: int, actual_mb: int | None = None):
        self.limit_mb = limit_mb
        self.actual_mb = actual_mb
        if actual_mb:
            message = f"Task exceeded memory limit of {limit_mb}MB (used {actual_mb}MB)"
        else:
            message = f"Task exceeded memory limit of {limit_mb}MB"
        super().__init__(message)


class ProcessCrashedError(EEPError):
    """Raised when the isolated process crashes unexpectedly."""
    
    def __init__(self, exit_code: int, message: str | None = None):
        self.exit_code = exit_code
        if message is None:
            message = f"Process crashed with exit code {exit_code}"
        super().__init__(message)


class IsolationError(EEPError):
    """Raised when process isolation setup fails."""
    pass
