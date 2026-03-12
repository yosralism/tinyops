"""Device collection tasks for Celery workers."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from workers.celery_app import celery_app


@celery_app.task(bind=True, name="collect_device_data")
def collect_device_data(
    self,
    device_id: int,
    hostname: str,
    mgmt_ip: str,
    commands: list[str] | None = None,
) -> dict[str, Any]:
    """
    Simulate collecting data from a network device.
    
    This is a test task that simulates the device collection workflow:
    1. Connect to device (simulated)
    2. Execute commands (simulated)
    3. Store results
    
    Args:
        device_id: Database ID of the device
        hostname: Device hostname
        mgmt_ip: Management IP address
        commands: List of commands to execute (default: show version, show interfaces)
    
    Returns:
        Dictionary with collection results
    """
    if commands is None:
        commands = ["show version", "show interfaces status"]
    
    # Update task state to show progress
    self.update_state(
        state="PROGRESS",
        meta={
            "device_id": device_id,
            "hostname": hostname,
            "status": "Connecting to device...",
            "progress": 10,
        },
    )
    
    # Simulate connection time
    time.sleep(1)
    
    # Simulate command execution
    results = {}
    total_commands = len(commands)
    
    for idx, command in enumerate(commands, 1):
        self.update_state(
            state="PROGRESS",
            meta={
                "device_id": device_id,
                "hostname": hostname,
                "status": f"Executing: {command}",
                "progress": 10 + int((idx / total_commands) * 80),
            },
        )
        
        # Simulate command execution time
        time.sleep(0.5)
        
        # Simulate command output
        results[command] = {
            "success": True,
            "output": f"[Simulated output for '{command}' from {hostname}]",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    # Final state
    self.update_state(
        state="PROGRESS",
        meta={
            "device_id": device_id,
            "hostname": hostname,
            "status": "Collection complete",
            "progress": 100,
        },
    )
    
    return {
        "device_id": device_id,
        "hostname": hostname,
        "mgmt_ip": mgmt_ip,
        "status": "success",
        "commands_executed": len(commands),
        "results": results,
        "collected_at": datetime.utcnow().isoformat(),
        "task_id": self.request.id,
    }


@celery_app.task(bind=True, name="collect_multiple_devices")
def collect_multiple_devices(
    self,
    device_ids: list[int],
) -> dict[str, Any]:
    """
    Trigger collection for multiple devices.
    
    This task spawns individual collection tasks for each device.
    
    Args:
        device_ids: List of device IDs to collect from
    
    Returns:
        Dictionary with spawned task IDs
    """
    from workers.tasks.device_tasks import collect_device_data
    
    task_ids = []
    
    for device_id in device_ids:
        # In a real implementation, we would fetch device details from DB
        # For now, simulate with placeholder data
        result = collect_device_data.apply_async(
            args=[
                device_id,
                f"device-{device_id}",
                f"10.0.0.{device_id}",
            ],
            queue="devices",
        )
        task_ids.append({"device_id": device_id, "task_id": result.id})
    
    return {
        "status": "tasks_spawned",
        "total_devices": len(device_ids),
        "task_ids": task_ids,
        "spawned_at": datetime.utcnow().isoformat(),
    }
