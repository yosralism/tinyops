"""Device collection tasks for Celery workers."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from multiprocessing import Queue
from typing import Any

from dotenv import load_dotenv

from workers.celery_app import celery_app
from workers.eep import EEPConfig, ExecutionStatus, IsolatedExecutor
from collector.ssh import SSHCollector
from collector.multi_hop_ssh import MultiHopSSHCollector
from collector.credentials import CredentialManager, DeviceCredentials
from collector.exceptions import (
    CollectorError,
    ConnectionError,
    AuthenticationError,
    CommandExecutionError,
    TimeoutError as CollectorTimeoutError,
)
from app.services.connection_profile_service import ConnectionProfileService
from app.db.session import sync_session_maker

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def _device_collection_logic(
    device_id: int,
    hostname: str,
    mgmt_ip: str,
    device_type: str,
    commands: list[str],
    progress_queue: Queue,
    ssh_config_file: str | None = None,
    session_log: str | None = None,
) -> dict[str, Any]:
    """
    Core device collection logic that runs in isolated subprocess.
    
    This function executes real SSH connections to network devices and
    collects command outputs. It reports progress back through the queue.
    
    Args:
        device_id: Database ID of the device
        hostname: Device hostname
        mgmt_ip: Management IP address
        device_type: Device platform type (cisco_ios, juniper_junos, cisco_iosxr, etc.)
        commands: List of commands to execute
        progress_queue: Queue for reporting progress to parent process
        ssh_config_file: Path to SSH config file for ProxyJump support (legacy)
        session_log: Path to save SSH session log (optional)
        use_connection_profile: Whether to use connection profile system (default: True)
    
    Returns:
        Dictionary with collection results
    
    Raises:
        CollectorError: If collection fails
    """
    # Report initial progress
    progress_queue.put({
        "state": "PROGRESS",
        "meta": {
            "device_id": device_id,
            "hostname": hostname,
            "status": "Initializing collector...",
            "progress": 5,
        },
    })
    
    try:
        # Get device from database to determine role (for credential selection)
        device_role = None
        try:
            with sync_session_maker() as session:
                from app.models.device import Device
                device = session.get(Device, device_id)
                if device:
                    device_role = device.role
        except Exception as e:
            logger.warning(f"Failed to get device role from database: {e}")
        
        # Get credentials for device (uses role for IGW/RR/P)
        credentials = CredentialManager.get_credentials_for_device(
            device_id=device_id,
            hostname=hostname,
            role=device_role,
        )
        
        # Try to use connection profile
        collector = None
        try:
            # Use synchronous session in subprocess
            with sync_session_maker() as session:
                service = ConnectionProfileService(session)
                resolved = service.resolve_connection_for_device(device_id)
            
            if resolved:
                logger.info(f"Using connection profile '{resolved.profile_name}' for {hostname} ({len(resolved.hops)} hops)")
                
                # Report connecting via profile
                progress_queue.put({
                    "state": "PROGRESS",
                    "meta": {
                        "device_id": device_id,
                        "hostname": hostname,
                        "status": f"Connecting via {resolved.profile_name} ({len(resolved.hops)} hops)...",
                        "progress": 10,
                    },
                })
                
                # Use MultiHopSSHCollector
                collector = MultiHopSSHCollector(
                    resolved_connection=resolved,
                    target_device_type=device_type,
                    target_credentials=credentials,
                    session_log=session_log,
                    conn_timeout=60,
                )
            else:
                logger.info(f"No connection profile found for {hostname}, using direct connection")
        
        except Exception as e:
            logger.warning(f"Failed to resolve connection profile for {hostname}: {e}, falling back to direct")
            import traceback
            logger.debug(traceback.format_exc())
        
        # Fallback to direct connection
        if collector is None:
            progress_queue.put({
                "state": "PROGRESS",
                "meta": {
                    "device_id": device_id,
                    "hostname": hostname,
                    "status": f"Connecting directly to {mgmt_ip}...",
                    "progress": 10,
                },
            })
            
            collector = SSHCollector(
                hostname=mgmt_ip,
                device_type=device_type,
                credentials=credentials,
                timeout=60,
                ssh_config_file=ssh_config_file,
                session_log=session_log,
            )
        
        # Connect to device
        collector.connect()
        
        # Report connected
        progress_queue.put({
            "state": "PROGRESS",
            "meta": {
                "device_id": device_id,
                "hostname": hostname,
                "status": "Connected successfully",
                "progress": 20,
            },
        })
        
        # Execute commands
        results = {}
        errors = {}
        total_commands = len(commands)
        
        # Setup output directories for direct file writing
        from pathlib import Path
        collection_logs_base = Path("collection_logs")
        
        for idx, command in enumerate(commands, 1):
            progress_queue.put({
                "state": "PROGRESS",
                "meta": {
                    "device_id": device_id,
                    "hostname": hostname,
                    "status": f"Executing: {command}",
                    "progress": 20 + int((idx / total_commands) * 70),
                },
            })
            
            try:
                logger.info(f"[{hostname}] Executing command: {command}")
                output = collector.execute_command(command)
                output_size = len(output)
                logger.info(f"[{hostname}] Command '{command}' succeeded, output length: {output_size} bytes")
                
                # Save output directly to file (skip terminal length 0 - it's just setup)
                if command != "terminal length 0":
                    # Generate command key (same as bulk_collect.py does)
                    command_key = command.lower().replace(" ", "_")
                    
                    # Create output directory
                    output_dir = collection_logs_base / command_key
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Write output to file
                    output_file = output_dir / f"{hostname}_{mgmt_ip}.txt"
                    with open(output_file, 'w') as f:
                        f.write(output)
                    
                    logger.info(f"[{hostname}] Saved {command} output to {output_file}")
                    
                    # Return only metadata to queue (no large output!)
                    results[command] = {
                        "success": True,
                        "output_size_bytes": output_size,
                        "output_file": str(output_file),
                        "saved_to_disk": True,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                else:
                    # Terminal length 0 - just mark as success, no file needed
                    results[command] = {
                        "success": True,
                        "output_size_bytes": output_size,
                        "saved_to_disk": False,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    
            except (CommandExecutionError, CollectorTimeoutError) as e:
                error_msg = str(e)
                logger.error(f"[{hostname}] Command '{command}' FAILED: {error_msg}")
                logger.error(f"[{hostname}] Error type: {type(e).__name__}")
                if hasattr(e, '__dict__'):
                    logger.error(f"[{hostname}] Error details: {e.__dict__}")
                errors[command] = error_msg
                results[command] = {
                    "success": False,
                    "error": error_msg,
                    "error_type": type(e).__name__,
                    "timestamp": datetime.utcnow().isoformat(),
                }
        
        # Disconnect
        collector.disconnect()
        
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
            "device_type": device_type,
            "status": "success" if not errors else "partial",
            "commands_executed": len(commands),
            "commands_succeeded": len([r for r in results.values() if r.get("success")]),
            "commands_failed": len(errors),
            "results": results,
            "errors": errors if errors else None,
            "collected_at": datetime.utcnow().isoformat(),
        }
    
    except AuthenticationError as e:
        progress_queue.put({
            "state": "PROGRESS",
            "meta": {
                "device_id": device_id,
                "hostname": hostname,
                "status": f"Authentication failed: {e}",
                "progress": 0,
            },
        })
        raise
    
    except ConnectionError as e:
        progress_queue.put({
            "state": "PROGRESS",
            "meta": {
                "device_id": device_id,
                "hostname": hostname,
                "status": f"Connection failed: {e}",
                "progress": 0,
            },
        })
        raise
    
    except Exception as e:
        progress_queue.put({
            "state": "PROGRESS",
            "meta": {
                "device_id": device_id,
                "hostname": hostname,
                "status": f"Collection failed: {e}",
                "progress": 0,
            },
        })
        raise


@celery_app.task(bind=True, name="collect_device_data")
def collect_device_data(
    self,
    device_id: int,
    hostname: str,
    mgmt_ip: str,
    device_type: str = "cisco_xr",
    commands: list[str] | None = None,
    ssh_config_file: str | None = None,
    session_log: str | None = None,
) -> dict[str, Any]:
    """
    Collect data from a network device using isolated execution with real SSH.
    
    This task runs the actual SSH collection in an isolated subprocess
    to prevent worker crashes and resource leaks. Uses Netmiko for SSH.
    
    Args:
        device_id: Database ID of the device
        hostname: Device hostname
        mgmt_ip: Management IP address
        device_type: Device platform type (cisco_iosxr, cisco_ios, juniper_junos, etc.)
        commands: List of commands to execute (default: show version, show ipv4 interface brief)
        ssh_config_file: Path to SSH config file for ProxyJump support (optional)
        session_log: Path to save SSH session log (optional)
    
    Returns:
        Dictionary with collection results including:
        - device_id, hostname, mgmt_ip, device_type
        - status (success/partial/failed)
        - commands_executed, commands_succeeded, commands_failed
        - results (dict of command -> output/error)
        - errors (if any)
        - collected_at timestamp
        - task_id
    
    Raises:
        Exception: If task fails or times out
    """
    if commands is None:
        # Default Cisco IOS XR commands
        commands = ["show version", "show ipv4 interface brief"]
    
    # Handle SSH config - use different variable to avoid caching issues
    ssh_cfg = ssh_config_file  # Copy parameter value
    if ssh_cfg is None:
        import os
        ssh_cfg = os.getenv("SSH_CONFIG_FILE")
        if ssh_cfg:
            logger.info(f"Using SSH config from environment: {ssh_cfg}")
    
    logger.info(
        f"Starting device collection: device_id={device_id}, "
        f"hostname={hostname}, mgmt_ip={mgmt_ip}, device_type={device_type}, "
        f"ssh_config={ssh_cfg}"
    )
    
    # Create progress queue for subprocess communication
    progress_queue = Queue()
    
    # Create EEP executor with configuration
    executor = IsolatedExecutor(
        config=EEPConfig(
            max_execution_time=600,  # 10 minutes timeout
            memory_limit_mb=512,     # 512MB memory limit (increased for large outputs like show run)
            cpu_limit=1.0,           # 1 CPU core
            enable_network=True,     # Network access required for SSH
        ),
        enable_monitoring=True,      # Track resource usage
    )
    
    # Run collection in isolated subprocess
    result = executor.run(
        target_func=_device_collection_logic,
        args=(device_id, hostname, mgmt_ip, device_type, commands, progress_queue, ssh_cfg, session_log),
    )
    
    # Process progress updates from subprocess
    while not progress_queue.empty():
        try:
            progress_update = progress_queue.get_nowait()
            self.update_state(
                state=progress_update["state"],
                meta=progress_update["meta"],
            )
        except:
            break
    
    # Handle execution results
    if result.is_success:
        # Add task_id and execution metrics to result
        result.data["task_id"] = self.request.id
        result.data["execution_time_seconds"] = result.execution_time
        
        if result.resource_metrics:
            result.data["resource_usage"] = {
                "peak_memory_mb": result.resource_metrics.peak_memory_mb,
                "avg_cpu_percent": result.resource_metrics.avg_cpu_percent,
            }
        
        logger.info(
            f"Device collection completed: device_id={device_id}, "
            f"status={result.data.get('status')}, "
            f"execution_time={result.execution_time:.1f}s"
        )
        
        return result.data
    
    elif result.is_timeout:
        error_msg = (
            f"Device collection timed out after {result.execution_time:.1f}s. "
            f"Device: {hostname} ({mgmt_ip})"
        )
        logger.error(error_msg)
        raise Exception(error_msg)
    
    elif result.is_crashed:
        error_msg = (
            f"Collection process crashed (exit code {result.exit_code}). "
            f"Device: {hostname} ({mgmt_ip}). "
            f"Error: {result.error}"
        )
        logger.error(error_msg)
        raise Exception(error_msg)
    
    else:  # is_failed
        error_msg = (
            f"Device collection failed: {result.error}. "
            f"Device: {hostname} ({mgmt_ip})"
        )
        logger.error(error_msg)
        raise Exception(error_msg)


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
