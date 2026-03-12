"""Jobs API endpoints for task orchestration."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.routes.auth import User, get_current_active_user
from workers.tasks.device_tasks import collect_device_data, collect_multiple_devices

router = APIRouter(prefix="/jobs", tags=["jobs"])


class DeviceCollectionRequest(BaseModel):
    """Request to collect data from a device."""

    device_id: int = Field(description="Device database ID")
    hostname: str = Field(min_length=1, description="Device hostname")
    mgmt_ip: str = Field(min_length=1, description="Management IP address")
    commands: list[str] | None = Field(
        default=None, description="Commands to execute (optional)"
    )


class MultiDeviceCollectionRequest(BaseModel):
    """Request to collect data from multiple devices."""

    device_ids: list[int] = Field(min_items=1, description="List of device IDs")


class TaskResponse(BaseModel):
    """Response with task ID."""

    task_id: str = Field(description="Celery task ID")
    status: str = Field(description="Initial task status")
    message: str = Field(description="Human-readable message")


class TaskStatusResponse(BaseModel):
    """Task status response."""

    task_id: str
    state: str
    result: Any | None = None
    info: dict[str, Any] | None = None


@router.post("/collect-device", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_device_collection(
    payload: DeviceCollectionRequest,
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """
    Trigger a device data collection task.
    
    This creates a Celery task that will collect data from the specified device.
    The task runs asynchronously and returns immediately with a task ID.
    """
    task = collect_device_data.apply_async(
        args=[
            payload.device_id,
            payload.hostname,
            payload.mgmt_ip,
            payload.commands,
        ],
        queue="devices",
    )

    return TaskResponse(
        task_id=task.id,
        status="PENDING",
        message=f"Collection task queued for device {payload.hostname}",
    )


@router.post("/collect-multiple", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_multiple_collection(
    payload: MultiDeviceCollectionRequest,
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """
    Trigger collection for multiple devices.
    
    This spawns individual collection tasks for each device.
    """
    task = collect_multiple_devices.apply_async(
        args=[payload.device_ids],
        queue="devices",
    )

    return TaskResponse(
        task_id=task.id,
        status="PENDING",
        message=f"Batch collection task queued for {len(payload.device_ids)} devices",
    )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
) -> TaskStatusResponse:
    """
    Get the status of a task by its ID.
    
    Returns the current state, result (if completed), and progress information.
    """
    from workers.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)

    response = TaskStatusResponse(
        task_id=task_id,
        state=result.state,
        result=None,
        info=None,
    )

    if result.state == "PENDING":
        response.info = {"status": "Task is waiting to be executed"}
    elif result.state == "PROGRESS":
        response.info = result.info
    elif result.state == "SUCCESS":
        response.result = result.result
        response.info = {"status": "Task completed successfully"}
    elif result.state == "FAILURE":
        response.info = {
            "status": "Task failed",
            "error": str(result.info),
        }
    else:
        response.info = {"status": result.state}

    return response
