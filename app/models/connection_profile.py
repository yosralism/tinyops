"""Connection Profile model for managing SSH connection topology."""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class ConnectionProfile(Base):
    """Connection profile defining how to reach devices via jumphosts.
    
    Profiles can be role-based (applies to all devices with a specific role)
    or device-specific (overrides role-based profile for a specific device).
    
    Priority determines which profile to use when multiple profiles apply:
    - Device-specific profiles typically have priority 100
    - Role-based profiles typically have priority 10
    - Higher priority wins
    """
    
    __tablename__ = "connection_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    
    # Assignment: either role-based OR device-specific
    applies_to_role = Column(String(50), nullable=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True, index=True)
    
    # Priority for conflict resolution (higher = more specific)
    priority = Column(Integer, nullable=False, default=10, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Connection topology stored as JSONB for flexibility
    # Structure: {"hops": [...], "device": {...}}
    topology = Column(JSONB, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    device = relationship("Device", back_populates="connection_profile")
    
    def __repr__(self):
        if self.device_id:
            return f"<ConnectionProfile {self.name} (device_id={self.device_id})>"
        return f"<ConnectionProfile {self.name} (role={self.applies_to_role})>"
