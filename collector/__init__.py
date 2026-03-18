"""Network device collectors for SSH/Telnet access."""

from collector.base import BaseCollector
from collector.exceptions import (
    CollectorError,
    ConnectionError,
    AuthenticationError,
    CommandExecutionError,
    TimeoutError,
)
from collector.ssh import SSHCollector

__all__ = [
    "BaseCollector",
    "CollectorError",
    "ConnectionError",
    "AuthenticationError",
    "CommandExecutionError",
    "TimeoutError",
    "SSHCollector",
]
