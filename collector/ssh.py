"""SSH collector implementation using Netmiko."""

from __future__ import annotations

import logging
from typing import Any

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
    SSHException,
)

from collector.base import BaseCollector, CollectionResult
from collector.credentials import DeviceCredentials
from collector.exceptions import (
    AuthenticationError,
    CommandExecutionError,
    ConnectionError,
    TimeoutError,
    UnsupportedDeviceType,
)

logger = logging.getLogger(__name__)

# Supported device types
SUPPORTED_DEVICE_TYPES = {
    "cisco_ios",
    "cisco_xr",
    "cisco_nxos",
    "cisco_xe",
    "cisco_asa",
    "juniper_junos",
    "arista_eos",
    "hp_procurve",
    "dell_os10",
}


class SSHCollector(BaseCollector):
    """SSH-based collector using Netmiko for network devices.
    
    Supports multiple vendor platforms through Netmiko's device type system.
    Handles authentication, privilege escalation, and command execution.
    """
    
    def __init__(
        self,
        hostname: str,
        device_type: str,
        credentials: DeviceCredentials,
        port: int | None = None,
        timeout: int = 30,
        session_log: str | None = None,
        ssh_config_file: str | None = None,
        jump_host: str | None = None,
    ):
        """Initialize SSH collector.
        
        Args:
            hostname: Device hostname or IP address
            device_type: Netmiko device type (cisco_ios, juniper_junos, etc.)
            credentials: Device credentials
            port: SSH port (default: 22)
            timeout: Connection and command timeout in seconds
            session_log: Path to session log file (optional, for debugging)
            ssh_config_file: Path to SSH config file for ProxyJump/bastion (optional)
            jump_host: Jump host name for explicit ProxyJump (optional)
        """
        super().__init__(hostname, device_type, credentials, port, timeout)
        
        # Validate device type
        if device_type not in SUPPORTED_DEVICE_TYPES:
            raise UnsupportedDeviceType(device_type)
        
        self.session_log = session_log
        self.ssh_config_file = ssh_config_file
        self.jump_host = jump_host
        self.connection = None
        self._connection_params: dict[str, Any] = {}
    
    def _build_connection_params(self) -> dict[str, Any]:
        """Build Netmiko connection parameters.
        
        Returns:
            Dictionary of connection parameters for ConnectHandler
        """
        params = {
            "device_type": self.device_type,
            "host": self.hostname,
            "username": self.credentials.username,
            "timeout": self.timeout,
            "session_timeout": self.timeout,
            "banner_timeout": 15,
            "conn_timeout": self.timeout,
        }
        
        # Add port if specified
        if self.port:
            params["port"] = self.port
        
        # Add password or SSH key
        if self.credentials.password:
            params["password"] = self.credentials.password
        else:
            params["use_keys"] = True
            params["key_file"] = self.credentials.ssh_key_file
        
        # Add enable secret (for privilege escalation)
        if self.credentials.secret:
            params["secret"] = self.credentials.secret
        
        # Add session log if specified
        if self.session_log:
            params["session_log"] = self.session_log
        
        # Add SSH config file for ProxyJump/bastion support
        if self.ssh_config_file:
            params["ssh_config_file"] = self.ssh_config_file
            logger.debug(f"Using SSH config file: {self.ssh_config_file}")
        
        # Add explicit jump host if specified (Netmiko will use -J equivalent)
        if self.jump_host:
            # For Netmiko, we need to use the ssh_config_file with jump_host defined
            # Or we can use ProxyCommand directly
            logger.info(f"Jump host specified: {self.jump_host}")
            # Netmiko doesn't have direct jump_host parameter, it relies on SSH config
            # We'll log this for debugging
        
        return params
    
    def connect(self) -> None:
        """Establish SSH connection to the device.
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
            TimeoutError: If connection times out
        """
        if self.connected:
            logger.warning(f"Already connected to {self.hostname}")
            return
        
        logger.info(f"Connecting to {self.hostname} ({self.device_type})")
        
        try:
            self._connection_params = self._build_connection_params()
            
            # Log connection parameters (without sensitive data)
            safe_params = {k: v for k, v in self._connection_params.items() 
                          if k not in ['password', 'secret']}
            logger.info(f"Connection parameters: {safe_params}")
            
            # Check if SSH config will be used
            if self.ssh_config_file:
                logger.info(f"Attempting to use SSH config: {self.ssh_config_file}")
                import subprocess
                # Test if SSH config has an entry for this host
                try:
                    result = subprocess.run(
                        ['ssh', '-G', self.hostname],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if 'proxyjump' in result.stdout.lower():
                        logger.info("SSH config has ProxyJump configured for this host")
                    else:
                        logger.warning(
                            f"SSH config does NOT have ProxyJump for {self.hostname}. "
                            f"Add 'Host {self.hostname}' entry with ProxyJump to SSH config."
                        )
                except Exception as e:
                    logger.warning(f"Could not check SSH config: {e}")
            
            logger.info("Initiating Netmiko connection...")
            self.connection = ConnectHandler(**self._connection_params)
            self.connected = True
            
            logger.info(f"Successfully connected to {self.hostname}")
            
            # Enter enable mode if needed (Cisco devices)
            if self.device_type.startswith("cisco") and self.credentials.secret:
                try:
                    self.connection.enable()
                    logger.debug(f"Entered enable mode on {self.hostname}")
                except Exception as e:
                    logger.warning(f"Could not enter enable mode: {e}")
        
        except NetmikoAuthenticationException as e:
            logger.error(f"Authentication failed for {self.hostname}: {e}")
            raise AuthenticationError(self.hostname, self.credentials.username) from e
        
        except NetmikoTimeoutException as e:
            logger.error(f"Connection timeout for {self.hostname}: {e}")
            raise TimeoutError(
                self.hostname,
                self.timeout,
                "Connection"
            ) from e
        
        except SSHException as e:
            logger.error(f"SSH error for {self.hostname}: {e}")
            raise ConnectionError(self.hostname, str(e)) from e
        
        except Exception as e:
            logger.error(f"Unexpected error connecting to {self.hostname}: {e}")
            raise ConnectionError(self.hostname, f"Unexpected error: {e}") from e
    
    def disconnect(self) -> None:
        """Close SSH connection to the device."""
        if not self.connected or not self.connection:
            return
        
        try:
            logger.info(f"Disconnecting from {self.hostname}")
            self.connection.disconnect()
            self.connected = False
            self.connection = None
            logger.info(f"Disconnected from {self.hostname}")
        except Exception as e:
            logger.error(f"Error disconnecting from {self.hostname}: {e}")
            # Still mark as disconnected
            self.connected = False
            self.connection = None
    
    def execute_command(self, command: str) -> str:
        """Execute a single command on the device.
        
        Args:
            command: Command to execute
            
        Returns:
            Command output as string
            
        Raises:
            CommandExecutionError: If command execution fails
            TimeoutError: If command times out
            ConnectionError: If not connected
        """
        if not self.connected or not self.connection:
            raise ConnectionError(
                self.hostname,
                "Not connected. Call connect() first."
            )
        
        logger.info(f"[{self.hostname}] Executing command: {command}")
        
        try:
            # Use send_command which handles pagination automatically
            # For long-running commands like 'show run', increase timeout
            timeout = self.timeout
            if command.lower().startswith('show run'):
                timeout = max(120, self.timeout * 3)  # At least 2 minutes for show run
                logger.info(f"[{self.hostname}] Using extended timeout for 'show run': {timeout}s")
            
            logger.debug(f"[{self.hostname}] Sending command with timeout={timeout}s...")
            output = self.connection.send_command(
                command,
                read_timeout=timeout,
                strip_prompt=True,
                strip_command=True,
            )
            
            logger.info(
                f"[{self.hostname}] Command '{command}' completed successfully: {len(output)} bytes received"
            )
            
            return output
        
        except NetmikoTimeoutException as e:
            logger.error(f"[{self.hostname}] Command '{command}' TIMED OUT after {timeout}s")
            logger.error(f"[{self.hostname}] Timeout details: {e}")
            raise TimeoutError(
                self.hostname,
                timeout,
                f"Command '{command}'"
            ) from e
        
        except Exception as e:
            logger.error(f"[{self.hostname}] Command '{command}' FAILED with exception: {type(e).__name__}")
            logger.error(f"[{self.hostname}] Error message: {str(e)}")
            if hasattr(e, '__dict__'):
                logger.error(f"[{self.hostname}] Error attributes: {e.__dict__}")
            raise CommandExecutionError(
                self.hostname,
                command,
                str(e)
            ) from e
    
    def execute_commands(self, commands: list[str]) -> CollectionResult:
        """Execute multiple commands on the device.
        
        Args:
            commands: List of commands to execute
            
        Returns:
            CollectionResult with outputs and metadata
        """
        outputs = {}
        errors = {}
        
        for command in commands:
            try:
                output = self.execute_command(command)
                outputs[command] = output
            except (CommandExecutionError, TimeoutError) as e:
                logger.error(f"Command failed on {self.hostname}: {command} - {e}")
                errors[command] = str(e)
            except Exception as e:
                logger.error(
                    f"Unexpected error executing '{command}' on {self.hostname}: {e}"
                )
                errors[command] = f"Unexpected error: {e}"
        
        success = len(errors) == 0
        
        # Get device prompt as metadata
        prompt = ""
        if self.connection:
            try:
                prompt = self.connection.find_prompt()
            except:
                pass
        
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
                "prompt": prompt,
                "username": self.credentials.username,
            }
        )
    
    def get_device_info(self) -> dict[str, Any]:
        """Get basic device information.
        
        Returns:
            Dictionary with device information (prompt, type, etc.)
            
        Raises:
            ConnectionError: If not connected
        """
        if not self.connected or not self.connection:
            raise ConnectionError(
                self.hostname,
                "Not connected. Call connect() first."
            )
        
        info = {
            "hostname": self.hostname,
            "device_type": self.device_type,
            "connected": self.connected,
        }
        
        try:
            info["prompt"] = self.connection.find_prompt()
        except:
            info["prompt"] = None
        
        return info
