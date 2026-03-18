"""Collector-specific exceptions."""

from __future__ import annotations


class CollectorError(Exception):
    """Base exception for all collector errors."""
    pass


class ConnectionError(CollectorError):
    """Raised when connection to device fails."""
    
    def __init__(self, hostname: str, message: str):
        self.hostname = hostname
        super().__init__(f"Connection failed to {hostname}: {message}")


class AuthenticationError(CollectorError):
    """Raised when authentication fails."""
    
    def __init__(self, hostname: str, username: str):
        self.hostname = hostname
        self.username = username
        super().__init__(f"Authentication failed for {username}@{hostname}")


class CommandExecutionError(CollectorError):
    """Raised when command execution fails."""
    
    def __init__(self, hostname: str, command: str, error: str):
        self.hostname = hostname
        self.command = command
        super().__init__(f"Command '{command}' failed on {hostname}: {error}")


class TimeoutError(CollectorError):
    """Raised when connection or command times out."""
    
    def __init__(self, hostname: str, timeout: int, operation: str = "operation"):
        self.hostname = hostname
        self.timeout = timeout
        super().__init__(f"{operation} timed out after {timeout}s on {hostname}")


class UnsupportedDeviceType(CollectorError):
    """Raised when device type is not supported."""
    
    def __init__(self, device_type: str):
        self.device_type = device_type
        supported = ["cisco_ios", "cisco_nxos", "juniper_junos", "arista_eos", "cisco_xr"]
        super().__init__(
            f"Device type '{device_type}' not supported. "
            f"Supported types: {', '.join(supported)}"
        )
