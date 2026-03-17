"""Execution Environment Protection (EEP) module.

Provides isolated execution environments for tasks to prevent:
- Worker crashes from task failures
- Resource exhaustion
- Memory leaks in long-running workers
- Security breaches spreading across tasks
"""

from workers.eep.config import EEPConfig
from workers.eep.exceptions import (
    EEPError,
    ExecutionTimeoutError,
    IsolationError,
    MemoryLimitExceededError,
    ProcessCrashedError,
)
from workers.eep.executor import IsolatedExecutor
from workers.eep.logging_utils import EEPLoggerAdapter, setup_eep_logger
from workers.eep.monitor import ResourceMetrics, ResourceMonitor, ResourceSnapshot
from workers.eep.result import ExecutionResult, ExecutionStatus

__all__ = [
    "EEPConfig",
    "EEPError",
    "ExecutionTimeoutError",
    "IsolationError",
    "MemoryLimitExceededError",
    "ProcessCrashedError",
    "IsolatedExecutor",
    "ExecutionResult",
    "ExecutionStatus",
    "ResourceMonitor",
    "ResourceMetrics",
    "ResourceSnapshot",
    "setup_eep_logger",
    "EEPLoggerAdapter",
]
