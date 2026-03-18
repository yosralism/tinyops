"""Credential management for device connections."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceCredentials:
    """Device authentication credentials.
    
    Attributes:
        username: SSH username
        password: SSH password
        secret: Enable password (for Cisco privilege escalation)
        ssh_key_file: Path to SSH private key (optional)
    """
    
    username: str
    password: str | None = None
    secret: str | None = None
    ssh_key_file: str | None = None
    
    def __post_init__(self):
        """Validate that either password or ssh_key_file is provided."""
        if not self.password and not self.ssh_key_file:
            raise ValueError("Either password or ssh_key_file must be provided")


class CredentialManager:
    """Manage device credentials from environment or configuration.
    
    Priority order:
    1. Per-device credentials (future: from database)
    2. Environment variables
    3. Default credentials from config
    """
    
    @staticmethod
    def get_default_credentials() -> DeviceCredentials:
        """Get default credentials from environment variables.
        
        Returns:
            DeviceCredentials with values from environment
            
        Raises:
            ValueError: If required environment variables are missing
        """
        username = os.getenv("DEVICE_USERNAME")
        password = os.getenv("DEVICE_PASSWORD")
        secret = os.getenv("DEVICE_ENABLE_SECRET")
        ssh_key = os.getenv("DEVICE_SSH_KEY_FILE")
        
        if not username:
            raise ValueError("DEVICE_USERNAME environment variable is required")
        
        if not password and not ssh_key:
            raise ValueError(
                "Either DEVICE_PASSWORD or DEVICE_SSH_KEY_FILE "
                "environment variable is required"
            )
        
        return DeviceCredentials(
            username=username,
            password=password,
            secret=secret,
            ssh_key_file=ssh_key,
        )
    
    @staticmethod
    def get_credentials_for_device(
        device_id: int,
        hostname: str,
    ) -> DeviceCredentials:
        """Get credentials for a specific device.
        
        Args:
            device_id: Database ID of the device
            hostname: Device hostname
            
        Returns:
            DeviceCredentials for the device
            
        Note:
            Currently returns default credentials.
            Future: Query database for per-device credentials.
        """
        # TODO: Query database for per-device credentials
        # For now, return default credentials
        return CredentialManager.get_default_credentials()
    
    @staticmethod
    def validate_credentials(credentials: DeviceCredentials) -> bool:
        """Validate that credentials are properly configured.
        
        Args:
            credentials: DeviceCredentials to validate
            
        Returns:
            True if credentials are valid
        """
        if not credentials.username:
            return False
        
        if not credentials.password and not credentials.ssh_key_file:
            return False
        
        if credentials.ssh_key_file:
            # Verify SSH key file exists
            import os.path
            if not os.path.isfile(credentials.ssh_key_file):
                return False
        
        return True
