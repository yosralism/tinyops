"""Resource monitoring for EEP subprocess execution."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class ResourceSnapshot:
    """Snapshot of resource usage at a point in time.
    
    Attributes:
        timestamp: When the snapshot was taken (seconds since epoch)
        cpu_percent: CPU usage percentage (0-100 per core, can exceed 100)
        memory_mb: Memory usage in megabytes
        memory_percent: Memory usage percentage
        num_threads: Number of threads
        io_read_mb: Cumulative I/O read in MB (if available)
        io_write_mb: Cumulative I/O write in MB (if available)
    """
    
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    num_threads: int
    io_read_mb: float = 0.0
    io_write_mb: float = 0.0


@dataclass
class ResourceMetrics:
    """Aggregated resource metrics for a task execution.
    
    Attributes:
        snapshots: List of resource snapshots taken during execution
        peak_memory_mb: Peak memory usage
        avg_memory_mb: Average memory usage
        peak_cpu_percent: Peak CPU usage
        avg_cpu_percent: Average CPU usage
        total_io_read_mb: Total I/O read
        total_io_write_mb: Total I/O write
        duration_seconds: Total monitoring duration
    """
    
    snapshots: list[ResourceSnapshot] = field(default_factory=list)
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0
    peak_cpu_percent: float = 0.0
    avg_cpu_percent: float = 0.0
    total_io_read_mb: float = 0.0
    total_io_write_mb: float = 0.0
    duration_seconds: float = 0.0
    
    def add_snapshot(self, snapshot: ResourceSnapshot) -> None:
        """Add a resource snapshot and update aggregated metrics."""
        self.snapshots.append(snapshot)
        
        # Update peak values
        self.peak_memory_mb = max(self.peak_memory_mb, snapshot.memory_mb)
        self.peak_cpu_percent = max(self.peak_cpu_percent, snapshot.cpu_percent)
        
        # Recalculate averages
        if self.snapshots:
            self.avg_memory_mb = sum(s.memory_mb for s in self.snapshots) / len(self.snapshots)
            self.avg_cpu_percent = sum(s.cpu_percent for s in self.snapshots) / len(self.snapshots)
            
            # Calculate duration
            if len(self.snapshots) > 1:
                self.duration_seconds = (
                    self.snapshots[-1].timestamp - self.snapshots[0].timestamp
                )
    
    def to_dict(self) -> dict:
        """Convert metrics to dictionary for logging/storage."""
        return {
            "peak_memory_mb": round(self.peak_memory_mb, 2),
            "avg_memory_mb": round(self.avg_memory_mb, 2),
            "peak_cpu_percent": round(self.peak_cpu_percent, 2),
            "avg_cpu_percent": round(self.avg_cpu_percent, 2),
            "total_io_read_mb": round(self.total_io_read_mb, 2),
            "total_io_write_mb": round(self.total_io_write_mb, 2),
            "duration_seconds": round(self.duration_seconds, 2),
            "num_snapshots": len(self.snapshots),
        }


class ResourceMonitor:
    """Monitor resource usage of a process.
    
    Example:
        monitor = ResourceMonitor(pid=12345, interval=1.0)
        monitor.start()
        # ... process runs ...
        monitor.stop()
        metrics = monitor.get_metrics()
        print(f"Peak memory: {metrics.peak_memory_mb}MB")
    """
    
    def __init__(
        self,
        pid: int,
        interval: float = 1.0,
        enable_io: bool = False,
    ):
        """Initialize resource monitor.
        
        Args:
            pid: Process ID to monitor
            interval: Sampling interval in seconds
            enable_io: Whether to monitor I/O (may require privileges)
        """
        self.pid = pid
        self.interval = interval
        self.enable_io = enable_io
        self._process: Optional[psutil.Process] = None
        self._monitoring = False
        self._metrics = ResourceMetrics()
    
    def start(self) -> None:
        """Start monitoring the process."""
        try:
            self._process = psutil.Process(self.pid)
            self._monitoring = True
            logger.debug(f"Started monitoring process {self.pid}")
        except psutil.NoSuchProcess:
            logger.warning(f"Process {self.pid} not found, cannot monitor")
            self._monitoring = False
    
    def stop(self) -> None:
        """Stop monitoring the process."""
        self._monitoring = False
        logger.debug(f"Stopped monitoring process {self.pid}")
    
    def sample(self) -> Optional[ResourceSnapshot]:
        """Take a single resource usage sample.
        
        Returns:
            ResourceSnapshot if successful, None if process unavailable
        """
        if not self._process or not self._monitoring:
            return None
        
        try:
            # Get memory info
            mem_info = self._process.memory_info()
            memory_mb = mem_info.rss / (1024 * 1024)  # Convert bytes to MB
            memory_percent = self._process.memory_percent()
            
            # Get CPU usage (requires time between calls)
            cpu_percent = self._process.cpu_percent(interval=0.1)
            
            # Get thread count
            num_threads = self._process.num_threads()
            
            # Get I/O stats if enabled
            io_read_mb = 0.0
            io_write_mb = 0.0
            if self.enable_io:
                try:
                    io_counters = self._process.io_counters()
                    io_read_mb = io_counters.read_bytes / (1024 * 1024)
                    io_write_mb = io_counters.write_bytes / (1024 * 1024)
                except (psutil.AccessDenied, AttributeError):
                    # I/O monitoring not available
                    pass
            
            snapshot = ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                num_threads=num_threads,
                io_read_mb=io_read_mb,
                io_write_mb=io_write_mb,
            )
            
            self._metrics.add_snapshot(snapshot)
            return snapshot
            
        except psutil.NoSuchProcess:
            logger.debug(f"Process {self.pid} terminated")
            self._monitoring = False
            return None
        except Exception as e:
            logger.warning(f"Error sampling process {self.pid}: {e}")
            return None
    
    def get_metrics(self) -> ResourceMetrics:
        """Get aggregated resource metrics.
        
        Returns:
            ResourceMetrics with all collected data
        """
        return self._metrics
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring and self._process is not None
