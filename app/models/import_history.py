from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, Integer, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class DeviceImportHistory(Base):
    """Track device import operations from Excel files.
    
    Each record represents one import/sync operation, storing statistics
    and change summary for audit and troubleshooting purposes.
    """
    __tablename__ = "device_import_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    changes_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
