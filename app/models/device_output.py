from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Boolean, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class DeviceOutput(Base):
    """Store raw command outputs from devices.
    
    Each record represents one command execution on a device.
    Stores both the command and its raw output for historical tracking.
    """
    __tablename__ = "device_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    command: Mapped[str] = mapped_column(String(500), nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    collection_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    task_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    
    # MinIO storage reference (optional, for large outputs)
    minio_bucket: Mapped[str | None] = mapped_column(String(100), nullable=True)
    minio_object_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="outputs")
