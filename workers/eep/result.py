"""Core execution result and status tracking."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from workers.eep.monitor import ResourceMetrics


class ExecutionStatus(str, Enum):
    """Status of isolated execution."""
    
    SUCCESS = "success"
    TIMEOUT = "timeout"
    FAILED = "failed"
    CRASHED = "crashed"


@dataclass
class ExecutionResult:
    """Result of an isolated execution.
    
    Attributes:
        status: Execution status
        data: Return value from the task (if successful)
        error: Error message or exception (if failed)
        exit_code: Process exit code (None if still running or timeout)
        execution_time: Actual execution time in seconds
        stdout: Captured stdout from subprocess
        stderr: Captured stderr from subprocess
        resource_metrics: Resource usage metrics (if monitoring enabled)
    """
    
    status: ExecutionStatus
    data: Any = None
    error: str | None = None
    exit_code: int | None = None
    execution_time: float = 0.0
    stdout: str = ""
    stderr: str = ""
    resource_metrics: ResourceMetrics | None = None
    
    @property
    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ExecutionStatus.SUCCESS
    
    @property
    def is_timeout(self) -> bool:
        """Check if execution timed out."""
        return self.status == ExecutionStatus.TIMEOUT
    
    @property
    def is_failed(self) -> bool:
        """Check if execution failed."""
        return self.status == ExecutionStatus.FAILED
    
    @property
    def is_crashed(self) -> bool:
        """Check if process crashed."""
        return self.status == ExecutionStatus.CRASHED
