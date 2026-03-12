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
    MemoryLimitExceededError,
    ProcessCrashedError,
)

__all__ = [
    "EEPConfig",
    "EEPError",
    "ExecutionTimeoutError",
    "MemoryLimitExceededError",
    "ProcessCrashedError",
]
