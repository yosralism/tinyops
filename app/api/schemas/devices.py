from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=255)
    mgmt_ip: str = Field(min_length=1, max_length=64)
    vendor: str | None = Field(default=None, max_length=64)
    site_id: str | None = Field(default=None, max_length=64)
    role: str | None = Field(default=None, max_length=64)
    region: str | None = Field(default=None, max_length=128)
    area: str | None = Field(default=None, max_length=128)
    software_version: str | None = Field(default=None, max_length=64)
    platform: str | None = Field(default=None, max_length=64)


class DeviceUpdate(BaseModel):
    hostname: str | None = Field(default=None, min_length=1, max_length=255)
    mgmt_ip: str | None = Field(default=None, min_length=1, max_length=64)
    vendor: str | None = Field(default=None, max_length=64)
    site_id: str | None = Field(default=None, max_length=64)
    role: str | None = Field(default=None, max_length=64)
    region: str | None = Field(default=None, max_length=128)
    area: str | None = Field(default=None, max_length=128)
    software_version: str | None = Field(default=None, max_length=64)
    platform: str | None = Field(default=None, max_length=64)


class DeviceRead(BaseModel):
    id: int
    hostname: str
    mgmt_ip: str
    vendor: str | None
    site_id: str | None
    role: str | None
    region: str | None
    area: str | None
    software_version: str | None
    platform: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeviceImportResult(BaseModel):
    total_rows: int
    created: int
    updated: int
    skipped: int
    errors: list[dict[str, str]]