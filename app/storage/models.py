from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.storage.base import Base


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


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
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