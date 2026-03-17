"""Structured logging configuration for EEP."""

from __future__ import annotations

import logging
import sys
from typing import Any


def setup_eep_logger(
    name: str = "workers.eep",
    level: int = logging.INFO,
    format_string: str | None = None,
) -> logging.Logger:
    """Set up structured logging for EEP.
    
    Args:
        name: Logger name
        level: Logging level
        format_string: Custom format string (optional)
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Set format
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "[%(filename)s:%(lineno)d] - %(message)s"
        )
    
    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


class EEPLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for adding EEP context to log messages.
    
    Example:
        logger = EEPLoggerAdapter(logging.getLogger(__name__), {
            "task_id": "abc123",
            "device_id": 42
        })
        logger.info("Starting collection")
        # Output: "Starting collection [task_id=abc123, device_id=42]"
    """
    
    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        """Add context to log message."""
        extra = self.extra or {}
        if extra:
            context = ", ".join(f"{k}={v}" for k, v in extra.items())
            msg = f"{msg} [{context}]"
        return msg, kwargs


def log_execution_start(
    logger: logging.Logger,
    func_name: str,
    timeout: int,
    memory_limit: int,
    enable_monitoring: bool = False,
) -> None:
    """Log execution start with configuration details."""
    logger.info(
        f"Starting isolated execution: func={func_name}, "
        f"timeout={timeout}s, memory_limit={memory_limit}MB, "
        f"monitoring={'enabled' if enable_monitoring else 'disabled'}"
    )


def log_execution_complete(
    logger: logging.Logger,
    func_name: str,
    status: str,
    execution_time: float,
    peak_memory_mb: float | None = None,
    avg_cpu_percent: float | None = None,
) -> None:
    """Log execution completion with results."""
    message = (
        f"Execution complete: func={func_name}, status={status}, "
        f"time={execution_time:.2f}s"
    )
    
    if peak_memory_mb is not None and avg_cpu_percent is not None:
        message += f", peak_mem={peak_memory_mb:.1f}MB, avg_cpu={avg_cpu_percent:.1f}%"
    
    if status == "SUCCESS":
        logger.info(message)
    elif status in ("TIMEOUT", "CRASHED"):
        logger.warning(message)
    else:
        logger.error(message)


def log_timeout_handling(
    logger: logging.Logger,
    pid: int,
    timeout: int,
    elapsed: float,
    termination_type: str,
) -> None:
    """Log timeout handling steps."""
    if termination_type == "SIGTERM":
        logger.warning(
            f"Task timeout after {elapsed:.1f}s (limit: {timeout}s), "
            f"sending SIGTERM to PID {pid}"
        )
    elif termination_type == "SIGKILL":
        logger.error(
            f"Process {pid} did not respond to SIGTERM, "
            f"sending SIGKILL"
        )
    elif termination_type == "COMPLETED":
        logger.info(f"Process {pid} terminated gracefully after SIGTERM")


def log_monitoring_metrics(
    logger: logging.Logger,
    peak_memory_mb: float,
    avg_memory_mb: float,
    peak_cpu_percent: float,
    avg_cpu_percent: float,
    num_samples: int,
) -> None:
    """Log resource monitoring summary."""
    logger.info(
        f"Resource usage summary: "
        f"peak_mem={peak_memory_mb:.1f}MB, avg_mem={avg_memory_mb:.1f}MB, "
        f"peak_cpu={peak_cpu_percent:.1f}%, avg_cpu={avg_cpu_percent:.1f}%, "
        f"samples={num_samples}"
    )


def log_exception(
    logger: logging.Logger,
    operation: str,
    exception: Exception,
    include_traceback: bool = True,
) -> None:
    """Log exception with context."""
    logger.error(
        f"Exception in {operation}: {type(exception).__name__}: {exception}",
        exc_info=include_traceback,
    )
