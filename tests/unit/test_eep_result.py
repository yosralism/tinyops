"""Unit tests for EEP execution results."""

import pytest

from workers.eep import ExecutionResult, ExecutionStatus, ResourceMetrics


class TestExecutionStatus:
    """Test ExecutionStatus enum."""

    def test_all_statuses(self):
        """Test all execution statuses exist."""
        assert ExecutionStatus.SUCCESS.value == "success"
        assert ExecutionStatus.TIMEOUT.value == "timeout"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.CRASHED.value == "crashed"

    def test_status_comparison(self):
        """Test status equality."""
        assert ExecutionStatus.SUCCESS == ExecutionStatus.SUCCESS
        assert ExecutionStatus.SUCCESS != ExecutionStatus.FAILED


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_successful_result(self):
        """Test successful execution result."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            data={"output": "success"},
            execution_time=2.5,
        )
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.data == {"output": "success"}
        assert result.error is None
        assert result.exit_code is None
        assert result.execution_time == 2.5
        assert result.resource_metrics is None

    def test_timeout_result(self):
        """Test timeout execution result."""
        result = ExecutionResult(
            status=ExecutionStatus.TIMEOUT,
            error="Execution exceeded timeout of 300s",
            execution_time=300.5,
        )
        
        assert result.status == ExecutionStatus.TIMEOUT
        assert result.data is None
        assert "timeout" in result.error.lower()
        assert result.execution_time == 300.5

    def test_failed_result(self):
        """Test failed execution result."""
        result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            error="ValueError: Invalid input",
            execution_time=0.1,
        )
        
        assert result.status == ExecutionStatus.FAILED
        assert "ValueError" in result.error
        assert result.data is None

    def test_crashed_result(self):
        """Test crashed execution result."""
        result = ExecutionResult(
            status=ExecutionStatus.CRASHED,
            error="Process crashed with exit code -11",
            exit_code=-11,
            execution_time=1.2,
        )
        
        assert result.status == ExecutionStatus.CRASHED
        assert result.exit_code == -11
        assert "crashed" in result.error.lower()

    def test_result_with_metrics(self):
        """Test result with resource metrics."""
        from workers.eep.monitor import ResourceSnapshot
        
        metrics = ResourceMetrics(
            snapshots=[
                ResourceSnapshot(
                    timestamp=1.0,
                    cpu_percent=40.0,
                    memory_mb=30.0,
                    memory_percent=5.0,
                    num_threads=1,
                    io_read_mb=0.0,
                    io_write_mb=0.0,
                )
            ],
            peak_memory_mb=45.2,
            avg_memory_mb=32.1,
            peak_cpu_percent=87.5,
            avg_cpu_percent=42.3,
        )
        
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            data={"result": 42},
            execution_time=5.0,
            resource_metrics=metrics,
        )
        
        assert result.resource_metrics is not None
        assert result.resource_metrics.peak_memory_mb == 45.2
        assert result.resource_metrics.avg_cpu_percent == 42.3

    def test_result_default_values(self):
        """Test result with default values."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            execution_time=1.0,
        )
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.data is None
        assert result.error is None
        assert result.exit_code is None
        assert result.resource_metrics is None
        assert result.execution_time == 1.0

    def test_result_boolean_check(self):
        """Test checking result success."""
        success = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            execution_time=1.0,
        )
        failed = ExecutionResult(
            status=ExecutionStatus.FAILED,
            error="error",
            execution_time=1.0,
        )
        
        assert success.status == ExecutionStatus.SUCCESS
        assert failed.status == ExecutionStatus.FAILED
