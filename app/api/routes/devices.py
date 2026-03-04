from __future__ import annotations

import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.schemas.devices import DeviceCreate, DeviceRead, DeviceUpdate, DeviceImportResult
from app.storage.db import get_db_session
from app.storage.models import Device, User
from app.api.routes.auth import get_current_active_user

router = APIRouter(tags=["devices"])

@router.post("/devices", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
async def create_device(
    payload: DeviceCreate,
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> DeviceRead:
    res = await db.execute(select(Device).where(Device.id == device_id))
    device = res.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.put("/devices/{device_id}", response_model=DeviceRead)
async def update_device(
    device_id: int,
    payload: DeviceUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> DeviceRead:
    res = await db.execute(select(Device).where(Device.id == device_id))
    device = res.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)
    
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Device with this hostname or mgmt_ip already exists")
    await db.refresh(device)
    return device


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    res = await db.execute(select(Device).where(Device.id == device_id))
    device = res.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await db.delete(device)
    await db.commit()


@router.post("/devices/import", response_model=DeviceImportResult)
async def import_devices_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> DeviceImportResult:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    contents = await file.read()
    try:
        csv_text = contents.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
    
    csv_reader = csv.DictReader(io.StringIO(csv_text))
    
    total_rows = 0
    created = 0
    updated = 0
    skipped = 0
    errors = []
    seen_hostnames = set()
    seen_mgmt_ips = set()
    
    for row_num, row in enumerate(csv_reader, start=2):
        total_rows += 1
        hostname = row.get("hostname", "").strip()
        mgmt_ip = row.get("mgmt_ip", "").strip()
        
        if hostname in seen_hostnames or mgmt_ip in seen_mgmt_ips:
            errors.append({
                "row": str(row_num),
                "hostname": hostname,
                "error": "Duplicate hostname or mgmt_ip in this CSV"
            })
            skipped += 1
            continue
        
        seen_hostnames.add(hostname)
        seen_mgmt_ips.add(mgmt_ip)
        
        try:
            device_data = DeviceCreate(
                hostname=hostname,
                mgmt_ip=mgmt_ip,
                vendor=row.get("vendor") or None,
                site_id=row.get("site_id") or None,
                role=row.get("role") or None,
                region=row.get("region") or None,
                area=row.get("area") or None,
                software_version=row.get("software_version") or None,
                platform=row.get("platform") or None,
            )
        except Exception as e:
            errors.append({
                "row": str(row_num),
                "hostname": hostname or "(missing)",
                "error": str(e)
            })
            skipped += 1
            continue
        
        res = await db.execute(
            select(Device).where(
                (Device.hostname == device_data.hostname) | (Device.mgmt_ip == device_data.mgmt_ip)
            )
        )
        existing_device = res.scalar_one_or_none()
        
        try:
            if existing_device:
                for field, value in device_data.model_dump().items():
                    setattr(existing_device, field, value)
                updated += 1
            else:
                new_device = Device(**device_data.model_dump())
                db.add(new_device)
                created += 1
            
            await db.flush()
        except IntegrityError as e:
            await db.rollback()
            errors.append({
                "row": str(row_num),
                "hostname": hostname,
                "error": f"Database integrity error: {str(e.orig)}"
            })
            skipped += 1
            continue
    
    await db.commit()
    
    return DeviceImportResult(
        total_rows=total_rows,
        created=created,
        updated=updated,
        skipped=skipped,
        errors=errors
    )