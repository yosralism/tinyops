"""Device collection tasks for Celery workers."""

from __future__ import annotations

import time
from datetime import datetime
from multiprocessing import Queue
from typing import Any

from workers.celery_app import celery_app
from workers.eep import EEPConfig, ExecutionStatus, IsolatedExecutor


def _device_collection_logic(
    device_id: int,
    hostname: str,
    mgmt_ip: str,
    commands: list[str],
    progress_queue: Queue,
) -> dict[str, Any]:
    """
    Core device collection logic that runs in isolated subprocess.
    
    This function is executed in a separate process for isolation.
    It reports progress back through the queue.
    
    Args:
        device_id: Database ID of the device
        hostname: Device hostname
        mgmt_ip: Management IP address
        commands: List of commands to execute
        progress_queue: Queue for reporting progress to parent process
    
    Returns:
        Dictionary with collection results
    """
    # Report initial progress
    progress_queue.put({
        "state": "PROGRESS",
        "meta": {
            "device_id": device_id,
            "hostname": hostname,
            "status": "Connecting to device...",
            "progress": 10,
        },
    })
    
    # Simulate connection time
    time.sleep(1)
    
    # Execute commands
    results = {}
    total_commands = len(commands)
    
    for idx, command in enumerate(commands, 1):
        progress_queue.put({
            "state": "PROGRESS",
            "meta": {
                "device_id": device_id,
                "hostname": hostname,
                "status": f"Executing: {command}",
                "progress": 10 + int((idx / total_commands) * 80),
            },
        })
        
        # Simulate command execution time
        time.sleep(0.5)
        
        # Simulate command output
        results[command] = {
            "success": True,
            "output": f"[Simulated output for '{command}' from {hostname}]",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    # Report final progress
    progress_queue.put({
        "state": "PROGRESS",
        "meta": {
            "device_id": device_id,
            "hostname": hostname,
            "status": "Collection complete",
            "progress": 100,
        },
    })
    
    return {
        "device_id": device_id,
        "hostname": hostname,
        "mgmt_ip": mgmt_ip,
        "status": "success",
        "commands_executed": len(commands),
        "results": results,
        "collected_at": datetime.utcnow().isoformat(),
    }


@celery_app.task(bind=True, name="collect_device_data")
def collect_device_data(
    self,
    device_id: int,
    hostname: str,
    mgmt_ip: str,
    commands: list[str] | None = None,
) -> dict[str, Any]:
    """
    Collect data from a network device using isolated execution.
    
    This task runs the actual collection logic in an isolated subprocess
    to prevent worker crashes and resource leaks.
    
    Args:
        device_id: Database ID of the device
        hostname: Device hostname
        mgmt_ip: Management IP address
        commands: List of commands to execute (default: show version, show interfaces)
    
    Returns:
        Dictionary with collection results
    
    Raises:
        Exception: If task fails or times out
    """
    if commands is None:
        commands = ["show version", "show interfaces status"]
    
    # Create progress queue for subprocess communication
    progress_queue = Queue()
    
    # Create EEP executor with configuration
    executor = IsolatedExecutor(
        config=EEPConfig(
            max_execution_time=600,  # 10 minutes timeout
            memory_limit_mb=256,     # 256MB memory limit
            cpu_limit=1.0,           # 1 CPU core
        )
    )
    
    # Run collection in isolated subprocess
    result = executor.run(
        target_func=_device_collection_logic,
        args=(device_id, hostname, mgmt_ip, commands, progress_queue),
    )
    
    # Process progress updates from subprocess
    while not progress_queue.empty():
        progress_update = progress_queue.get_nowait()
        self.update_state(
            state=progress_update["state"],
            meta=progress_update["meta"],
        )
    
    # Handle execution results
    if result.is_success:
        # Add task_id to result
        result.data["task_id"] = self.request.id
        return result.data
    
    elif result.is_timeout:
        raise Exception(
            f"Device collection timed out after {result.execution_time:.1f}s. "
            f"Device: {hostname} ({mgmt_ip})"
        )
    
    elif result.is_crashed:
        raise Exception(
            f"Collection process crashed (exit code {result.exit_code}). "
            f"Device: {hostname} ({mgmt_ip}). "
            f"Error: {result.error}"
        )
    
    else:  # is_failed
        raise Exception(
            f"Device collection failed: {result.error}. "
            f"Device: {hostname} ({mgmt_ip})"
        )


@celery_app.task(bind=True, name="collect_multiple_devices")
def collect_multiple_devices(
    self,
    device_ids: list[int],
) -> dict[str, Any]:
    """
    Trigger collection for multiple devices.
    
    This task spawns individual collection tasks for each device.
    Each collection runs in its own isolated subprocess.
    
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
