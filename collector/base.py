"""Base collector interface for network devices."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from collector.credentials import DeviceCredentials


@dataclass
class CollectionResult:
    """Result of a device collection operation.
    
    Attributes:
        success: Whether collection succeeded
        outputs: Dictionary mapping command to output
        errors: Dictionary mapping command to error message
        metadata: Additional metadata (connection time, device info, etc.)
    """
    
    success: bool
    outputs: dict[str, str]
    errors: dict[str, str]
    metadata: dict[str, Any]


class BaseCollector(ABC):
    """Abstract base class for device collectors.
    
    All collectors (SSH, Telnet, SNMP) must implement this interface.
    """
    
    def __init__(
        self,
        hostname: str,
        device_type: str,
        credentials: DeviceCredentials,
        port: int | None = None,
        timeout: int = 30,
    ):
        """Initialize collector.
        
        Args:
            hostname: Device hostname or IP address
            device_type: Device platform (cisco_ios, juniper_junos, etc.)
            credentials: Authentication credentials
            port: Connection port (optional, defaults vary by protocol)
            timeout: Connection and command timeout in seconds
        """
        self.hostname = hostname
        self.device_type = device_type
        self.credentials = credentials
        self.port = port
        self.timeout = timeout
        self.connected = False
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the device.
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
            TimeoutError: If connection times out
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the device.
        
        Should be safe to call even if not connected.
        """
        pass
    
    @abstractmethod
    def execute_command(self, command: str) -> str:
        """Execute a single command on the device.
        
        Args:
            command: Command to execute
            
        Returns:
            Command output as string
            
        Raises:
            CommandExecutionError: If command execution fails
            TimeoutError: If command times out
        """
        pass
    
    def execute_commands(self, commands: list[str]) -> CollectionResult:
        """Execute multiple commands on the device.
        
        Args:
            commands: List of commands to execute
            
        Returns:
            CollectionResult with outputs and any errors
        """
        outputs = {}
        errors = {}
        
        for command in commands:
            try:
                output = self.execute_command(command)
                outputs[command] = output
            except Exception as e:
                errors[command] = str(e)
        
        success = len(errors) == 0
        
        return CollectionResult(
            success=success,
            outputs=outputs,
            errors=errors,
            metadata={
                "hostname": self.hostname,
                "device_type": self.device_type,
                "commands_attempted": len(commands),
                "commands_succeeded": len(outputs),
                "commands_failed": len(errors),
            }
        )
    
    def collect(self, commands: list[str]) -> CollectionResult:
        """High-level method to connect, collect, and disconnect.
        
        Args:
            commands: List of commands to execute
            
        Returns:
            CollectionResult with outputs and metadata
        """
        try:
            self.connect()
            result = self.execute_commands(commands)
            return result
        finally:
            self.disconnect()
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
