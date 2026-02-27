from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.devices import DeviceCreate, DeviceRead
from app.storage.db import get_db_session
from app.storage.models import Device

router = APIRouter(tags=["devices"])

@router.post("/devices", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
async def create_device(
    payload: DeviceCreate,
    db: AsyncSession = Depends(get_db_session),
) -> DeviceRead:
    device = Device(
        hostname=payload.hostname,
        mgmt_ip=payload.mgmt_ip,
        vendor=payload.vendor,
        site_id=payload.site_id,
        role=payload.role,
        region=payload.region,
        area=payload.area,
        software_version=payload.software_version,
        platform=payload.platform,
    )
    db.add(device)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Device with this hostname or mgmt_ip already exists")
    await db.refresh(device)
    return device

@router.get("/devices", response_model=list[DeviceRead])
async def list_devices(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> list[DeviceRead]:
    stmt = select(Device).order_by(Device.id).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return list(res.scalars().all())

@router.get("/devices/{device_id}", response_model=DeviceRead)
async def get_device(
    device_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> DeviceRead:
    res = await db.execute(select(Device).where(Device.id == device_id))
    device = res.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device