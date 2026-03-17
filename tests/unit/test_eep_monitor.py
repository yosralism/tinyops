"""Unit tests for EEP resource monitoring."""

import time

import psutil
import pytest

from workers.eep import ResourceMetrics, ResourceMonitor, ResourceSnapshot


class TestResourceSnapshot:
    """Test ResourceSnapshot dataclass."""

    def test_snapshot_creation(self):
        """Test creating a resource snapshot."""
        snapshot = ResourceSnapshot(
            timestamp=1.5,
            cpu_percent=45.2,
            memory_mb=128.5,
            memory_percent=15.0,
            num_threads=3,
            io_read_mb=10.0,
            io_write_mb=5.0,
        )
        
        assert snapshot.timestamp == 1.5
        assert snapshot.cpu_percent == 45.2
        assert snapshot.memory_mb == 128.5
        assert snapshot.memory_percent == 15.0
        assert snapshot.num_threads == 3
        assert snapshot.io_read_mb == 10.0
        assert snapshot.io_write_mb == 5.0

    def test_snapshot_defaults(self):
        """Test snapshot with minimal data."""
        snapshot = ResourceSnapshot(
            timestamp=0.0,
            cpu_percent=0.0,
            memory_mb=0.0,
            memory_percent=0.0,
            num_threads=1,
        )
        
        assert snapshot.timestamp == 0.0
        assert snapshot.cpu_percent == 0.0
        assert snapshot.io_read_mb == 0.0  # Default value


class TestResourceMetrics:
    """Test ResourceMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating resource metrics."""
        snapshots = [
            ResourceSnapshot(1.0, 40.0, 100.0, 10.0, 2, 1.0, 0.5),
            ResourceSnapshot(2.0, 60.0, 120.0, 12.0, 2, 2.0, 1.0),
            ResourceSnapshot(3.0, 50.0, 110.0, 11.0, 2, 3.0, 1.5),
        ]
        
        metrics = ResourceMetrics(
            snapshots=snapshots,
            peak_memory_mb=120.0,
            avg_memory_mb=110.0,
            peak_cpu_percent=60.0,
            avg_cpu_percent=50.0,
        )
        
        assert metrics.peak_memory_mb == 120.0
        assert metrics.avg_memory_mb == 110.0
        assert metrics.peak_cpu_percent == 60.0
        assert metrics.avg_cpu_percent == 50.0
        assert len(metrics.snapshots) == 3

    def test_empty_metrics(self):
        """Test metrics with no snapshots."""
        metrics = ResourceMetrics()
        
        assert len(metrics.snapshots) == 0
        assert metrics.peak_memory_mb == 0.0


class TestResourceMonitor:
    """Test ResourceMonitor class."""

    def test_monitor_initialization(self):
        """Test monitor initialization with current process."""
        current_pid = psutil.Process().pid
        monitor = ResourceMonitor(pid=current_pid, interval=0.1)
        
        assert monitor.pid == current_pid
        assert monitor.interval == 0.1
        # Test public interface, not private attributes

    def test_monitor_invalid_pid(self):
        """Test monitor with invalid PID handles gracefully."""
        # psutil doesn't raise on init, but when accessing process info
        monitor = ResourceMonitor(pid=999999)
        # The exception happens when sampling, not on initialization
        assert monitor.pid == 999999

    def test_monitor_start_stop(self):
        """Test starting and stopping monitor."""
        monitor = ResourceMonitor(pid=psutil.Process().pid)
        
        monitor.start()
        # Monitor is started, we can sample
        
        time.sleep(0.1)
        
        monitor.stop()
        # After stop, monitor is stopped

    def test_monitor_sample(self):
        """Test taking a resource snapshot."""
        monitor = ResourceMonitor(pid=psutil.Process().pid)
        monitor.start()
        
        time.sleep(0.1)
        snapshot = monitor.sample()
        
        assert snapshot is not None
        assert snapshot.timestamp > 0
        assert snapshot.memory_mb >= 0
        assert snapshot.num_threads >= 1

    def test_monitor_multiple_samples(self):
        """Test taking multiple snapshots."""
        monitor = ResourceMonitor(pid=psutil.Process().pid, interval=0.05)
        monitor.start()
        
        # Take 3 samples
        snapshots = []
        for _ in range(3):
            time.sleep(0.05)
            snapshot = monitor.sample()
            if snapshot:
                snapshots.append(snapshot)
        
        assert len(snapshots) == 3
        
        # Timestamps should be increasing
        timestamps = [s.timestamp for s in snapshots]
        assert timestamps == sorted(timestamps)

    def test_monitor_get_metrics(self):
        """Test getting aggregated metrics."""
        monitor = ResourceMonitor(pid=psutil.Process().pid, interval=0.05)
        monitor.start()
        
        # Take some samples
        for _ in range(3):
            time.sleep(0.05)
            monitor.sample()
        
        monitor.stop()
        metrics = monitor.get_metrics()
        
        assert isinstance(metrics, ResourceMetrics)
        assert metrics.peak_memory_mb >= 0
        assert metrics.avg_memory_mb >= 0
        assert metrics.peak_cpu_percent >= 0
        assert metrics.avg_cpu_percent >= 0
        assert len(metrics.snapshots) == 3

    def test_monitor_no_samples(self):
        """Test getting metrics with no samples."""
        monitor = ResourceMonitor(pid=psutil.Process().pid)
        monitor.start()
        monitor.stop()
        
        metrics = monitor.get_metrics()
        
        assert metrics.peak_memory_mb == 0.0
        assert metrics.avg_memory_mb == 0.0
        assert metrics.peak_cpu_percent == 0.0
        assert metrics.avg_cpu_percent == 0.0
        assert len(metrics.snapshots) == 0

    def test_monitor_metrics_calculation(self):
        """Test that metrics are calculated correctly."""
        monitor = ResourceMonitor(pid=psutil.Process().pid)
        monitor.start()
        
        # Take enough samples to get meaningful data
        for _ in range(5):
            time.sleep(0.05)
            monitor.sample()
        
        monitor.stop()
        metrics = monitor.get_metrics()
        
        # Peak should be >= average
        assert metrics.peak_memory_mb >= metrics.avg_memory_mb
        assert metrics.peak_cpu_percent >= metrics.avg_cpu_percent
        
        # Averages should be > 0 for a running process
        assert metrics.avg_memory_mb > 0

    def test_monitor_process_terminated(self):
        """Test monitor behavior when process terminates."""
        import subprocess
        
        # Start a short-lived process
        proc = subprocess.Popen(["sleep", "0.1"])
        monitor = ResourceMonitor(pid=proc.pid, interval=0.05)
        monitor.start()
        
        # Wait for process to finish
        proc.wait()
        time.sleep(0.2)
        
        # Sampling should handle terminated process gracefully
        monitor.sample()  # Should not raise exception
        monitor.stop()
