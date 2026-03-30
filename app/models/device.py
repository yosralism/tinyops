from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Device(Base):
    __tablename__ = "devices"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    mgmt_ip: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    site_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    area: Mapped[str | None] = mapped_column(String(128), nullable=True)
    software_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True)

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
    
    # Relationships
    outputs: Mapped[list["DeviceOutput"]] = relationship(
        "DeviceOutput", back_populates="device", cascade="all, delete-orphan"
    )
    facts: Mapped[list["DeviceFact"]] = relationship(
        "DeviceFact", back_populates="device", cascade="all, delete-orphan"
    )
    connection_profile: Mapped["ConnectionProfile"] = relationship(
        "ConnectionProfile", back_populates="device", uselist=False
    )
