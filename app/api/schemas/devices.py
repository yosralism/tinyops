from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    mgmt_ip: str = Field(min_length=1, max_length=64)
    vendor: str | None = Field(default=None, max_length=64)
    site: str | None = Field(default=None, max_length=128)
    tags: dict | None = None


class DeviceRead(BaseModel):
    id: int
    hostname: str
    mgmt_ip: str
    vendor: str | None
    site: str | None
    tags: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True