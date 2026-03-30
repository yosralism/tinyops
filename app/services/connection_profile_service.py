"""Connection Profile Service for managing SSH connection topology."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.connection_profile import ConnectionProfile
from app.models.credential_ref import CredentialReference

# Load environment variables
load_dotenv()


@dataclass
class ResolvedCredentials:
    """Resolved credentials from environment."""
    username: str
    password: Optional[str] = None
    ssh_key_path: Optional[str] = None


@dataclass
class ResolvedHop:
    """A single resolved hop in the connection chain."""
    host: str
    port: int
    credentials: ResolvedCredentials


@dataclass
class ResolvedConnection:
    """Fully resolved connection with all hops."""
    profile_name: str
    hops: list[ResolvedHop]
    target_host: str
    target_port: int


class ConnectionProfileService:
    """Service for managing connection profiles."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def resolve_connection_for_device(self, device_id: int) -> Optional[ResolvedConnection]:
        """
        Resolve connection profile for a device.
        
        Returns fully resolved connection with credentials from environment,
        or None if no profile found.
        """
        # Import here to avoid circular dependency
        from app.models.device import Device
        
        # Get device
        device = self.session.get(Device, device_id)
        if not device:
            return None
        
        # Find applicable profile (device-specific or role-based)
        profile = self._get_profile_for_device(device_id, device.role)
        if not profile:
            return None
        
        # Resolve the connection (default to port 22 for devices)
        return self.resolve_connection(profile, device.mgmt_ip, 22)
    
    def _get_profile_for_device(self, device_id: int, role: str) -> Optional[ConnectionProfile]:
        """Get profile for device (device-specific takes precedence over role-based)."""
        
        # Try device-specific profile first
        stmt = select(ConnectionProfile).where(
            ConnectionProfile.device_id == device_id
        ).order_by(ConnectionProfile.priority.desc())
        
        result = self.session.execute(stmt)
        profile = result.scalars().first()
        
        if profile:
            return profile
        
        # Fall back to role-based profile
        stmt = select(ConnectionProfile).where(
            ConnectionProfile.applies_to_role == role
        ).order_by(ConnectionProfile.priority.desc())
        
        result = self.session.execute(stmt)
        return result.scalars().first()
    
    def resolve_connection(
        self,
        profile: ConnectionProfile,
        target_host: str,
        target_port: int = 22
    ) -> ResolvedConnection:
        """
        Resolve a connection profile to actual credentials and hosts.
        
        Args:
            profile: The connection profile
            target_host: Target device IP/hostname
            target_port: Target device port
        
        Returns:
            ResolvedConnection with all hops resolved
        """
        hops = []
        
        # Parse topology JSONB to get hop sequence
        topology = profile.topology
        if not topology or "hops" not in topology:
            raise ValueError(f"Invalid topology in profile '{profile.name}'")
        
        # Resolve each hop
        for hop in topology["hops"]:
            host = hop.get("host")
            port = hop.get("port", 22)
            cred_ref_name = hop.get("credential_ref")
            
            # Get credential reference
            cred_ref = self._get_credential_ref(cred_ref_name)
            if not cred_ref:
                raise ValueError(f"Credential reference '{cred_ref_name}' not found")
            
            # Resolve credentials from environment
            credentials = self.resolve_credentials(cred_ref)
            
            hops.append(ResolvedHop(
                host=host,
                port=port,
                credentials=credentials
            ))
        
        return ResolvedConnection(
            profile_name=profile.name,
            hops=hops,
            target_host=target_host,
            target_port=target_port
        )
    
    def _get_credential_ref(self, name: str) -> Optional[CredentialReference]:
        """Get credential reference by name."""
        stmt = select(CredentialReference).where(
            CredentialReference.name == name
        )
        result = self.session.execute(stmt)
        return result.scalars().first()
    
    def resolve_credentials(self, cred_ref: CredentialReference) -> ResolvedCredentials:
        """
        Resolve credentials from environment variables.
        
        Args:
            cred_ref: Credential reference with env var names
        
        Returns:
            ResolvedCredentials with actual values
        """
        username = os.getenv(cred_ref.username_env_var)
        password = os.getenv(cred_ref.password_env_var) if cred_ref.password_env_var else None
        ssh_key_path = os.getenv(cred_ref.ssh_key_env_var) if cred_ref.ssh_key_env_var else None
        
        if not username:
            raise ValueError(
                f"Username environment variable '{cred_ref.username_env_var}' not set"
            )
        
        # At least one authentication method required
        if not password and not ssh_key_path:
            # Allow for trust-based authentication (no password needed)
            # This is valid for intermediate jumphosts that trust the previous hop
            pass
        
        return ResolvedCredentials(
            username=username,
            password=password,
            ssh_key_path=ssh_key_path
        )
