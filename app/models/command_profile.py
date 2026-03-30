from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CommandProfile(Base):
    """Command profile for device collection.
    
    Profiles are named sets of commands for different purposes:
    - healthcheck: Basic monitoring
    - security_audit: Security posture
    - compliance_audit: Config compliance
    - capacity_planning: Performance metrics
    """
    __tablename__ = "command_profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)  # Relative to commands/ dir
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
