from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Integer, String, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class DeviceFact(Base):
    """Store parsed, structured facts from device outputs.
    
    Each record represents a parsed fact extracted from device output.
    Facts are normalized and indexed for fast querying and reporting.
    """
    __tablename__ = "device_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fact_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    fact_key: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    fact_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    collection_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    source_command: Mapped[str | None] = mapped_column(String(500), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    
    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="facts")
