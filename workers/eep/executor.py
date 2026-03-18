"""Isolated task executor using subprocess."""

from __future__ import annotations

import logging
import multiprocessing
import pickle
import signal
import sys
import time
import traceback
from multiprocessing import Queue
from typing import Any, Callable

from workers.eep.config import EEPConfig
from workers.eep.exceptions import ExecutionTimeoutError, ProcessCrashedError
from workers.eep.logging_utils import (
    log_exception,
    log_execution_complete,
    log_execution_start,
    log_monitoring_metrics,
    log_timeout_handling,
)
from workers.eep.monitor import ResourceMetrics, ResourceMonitor
from workers.eep.result import ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


def _subprocess_wrapper(
    target_func: Callable,
    args: tuple,
    kwargs: dict,
    result_queue: Queue,
    config: EEPConfig,
) -> None:
    """Wrapper function that runs in the subprocess.
    
    This function:
    1. Executes the target function
    2. Captures the result or exception
    3. Sends result back via queue
    4. Applies resource limits (Unix only)
    """
    try:
        # Apply resource limits (Unix systems only)
        if sys.platform != "win32":
            try:
                import resource
                
                # Set memory limit (soft and hard limit)
                if config.memory_limit_mb > 0:
                    mem_bytes = config.memory_limit_mb * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
                    logger.debug(f"Set memory limit to {config.memory_limit_mb}MB")
            except (ImportError, ValueError) as e:
                logger.warning(f"Failed to set resource limits: {e}")
        
        # Execute the target function
        start_time = time.time()
        result = target_func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        # Check result size and log warning if large
        try:
            result_size = sys.getsizeof(result)
            if result_size > 10 * 1024 * 1024:  # 10MB
                logger.warning(f"Large result detected: {result_size / (1024*1024):.1f}MB")
        except Exception as size_error:
            logger.debug(f"Could not determine result size: {size_error}")
        
        # Send success result
        try:
            result_queue.put({
                "status": ExecutionStatus.SUCCESS,
                "data": result,
                "execution_time": execution_time,
            })
            logger.debug("Result successfully put into queue")
        except Exception as queue_error:
            logger.error(f"Failed to put result in queue: {queue_error}")
            # Try to send error instead
            result_queue.put({
                "status": ExecutionStatus.FAILED,
                "error": f"Failed to serialize result: {queue_error}",
                "exception_type": "SerializationError",
            })
        
    except MemoryError as e:
        # Memory limit exceeded
        result_queue.put({
            "status": ExecutionStatus.FAILED,
            "error": f"Memory limit exceeded: {e}",
            "exception_type": "MemoryError",
        })
        
    except Exception as e:
        # Any other exception
        result_queue.put({
            "status": ExecutionStatus.FAILED,
            "error": str(e),
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc(),
        })


class IsolatedExecutor:
    """Executor that runs tasks in isolated subprocesses.
    
    Example:
        executor = IsolatedExecutor(config=EEPConfig(
            max_execution_time=300,
            memory_limit_mb=256
        ))
        
        result = executor.run(
            target_func=my_function,
            args=(arg1, arg2),
            kwargs={'key': 'value'}
        )
        
        if result.is_success:
            print(f"Result: {result.data}")
        elif result.is_timeout:
            print("Task timed out!")
    """
    
    def __init__(self, config: EEPConfig, enable_monitoring: bool = False):
        """Initialize the executor with configuration.
        
        Args:
            config: EEP configuration
            enable_monitoring: Whether to enable resource monitoring
        """
        self.config = config
        self.enable_monitoring = enable_monitoring
        self._process: multiprocessing.Process | None = None
        self._result_queue: Queue | None = None
        self._monitor: ResourceMonitor | None = None
    
    def run(
        self,
        target_func: Callable,
        args: tuple = (),
        kwargs: dict | None = None,
    ) -> ExecutionResult:
        """Run a function in an isolated subprocess.
        
        Args:
            target_func: Function to execute in isolation
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
        
        Returns:
            ExecutionResult with status and data
        """
        if kwargs is None:
            kwargs = {}
        
        # Log execution start
        log_execution_start(
            logger,
            func_name=target_func.__name__,
            timeout=self.config.max_execution_time,
            memory_limit=self.config.memory_limit_mb,
            enable_monitoring=self.enable_monitoring,
        )
        
        start_time = time.time()
        
        # Create queue for inter-process communication
        self._result_queue = multiprocessing.Queue()
        
        # Create and start subprocess
        self._process = multiprocessing.Process(
            target=_subprocess_wrapper,
            args=(target_func, args, kwargs, self._result_queue, self.config),
        )
        
        try:
            self._process.start()
            
            # Start resource monitoring if enabled
            if self.enable_monitoring and self._process.pid:
                self._monitor = ResourceMonitor(
                    pid=self._process.pid,
                    interval=1.0,  # Sample every second
                )
                self._monitor.start()
                logger.debug(f"Started resource monitoring for PID {self._process.pid}")
            
            # Wait for process to complete or timeout
            remaining_time = self.config.max_execution_time
            while remaining_time > 0 and self._process.is_alive():
                # Sample resources if monitoring
                if self._monitor and self._monitor.is_monitoring():
                    self._monitor.sample()
                
                # Wait briefly before next check
                wait_time = min(1.0, remaining_time)
                self._process.join(timeout=wait_time)
                remaining_time -= wait_time
            
            execution_time = time.time() - start_time
            
            # Stop monitoring and get metrics
            metrics = None
            if self._monitor:
                self._monitor.stop()
                metrics = self._monitor.get_metrics()
                
                # Log resource metrics
                log_monitoring_metrics(
                    logger,
                    peak_memory_mb=metrics.peak_memory_mb,
                    avg_memory_mb=metrics.avg_memory_mb,
                    peak_cpu_percent=metrics.peak_cpu_percent,
                    avg_cpu_percent=metrics.avg_cpu_percent,
                    num_samples=len(metrics.snapshots),
                )
            
            # Check if process finished
            if self._process.is_alive():
                # Timeout occurred
                log_timeout_handling(
                    logger,
                    pid=self._process.pid,
                    timeout=self.config.max_execution_time,
                    elapsed=execution_time,
                    termination_type="SIGTERM",
                )
                return self._handle_timeout(execution_time, target_func.__name__)
            
            # Process finished, try to get result
            # Don't rely on queue.empty() as it's unreliable with multiprocessing
            try:
                logger.debug("Waiting for result from subprocess queue...")
                # Use longer timeout for large results (e.g., show run output)
                # Large outputs can take time to pickle/unpickle across queue
                result_data = self._result_queue.get(timeout=30)
                logger.info("Result retrieved successfully from subprocess")
                result = self._build_result(result_data, execution_time, metrics)
                
                # Log execution complete
                log_execution_complete(
                    logger,
                    func_name=target_func.__name__,
                    status=result.status.value,
                    execution_time=result.execution_time,
                    peak_memory_mb=metrics.peak_memory_mb if metrics else None,
                    avg_cpu_percent=metrics.avg_cpu_percent if metrics else None,
                )
                
                return result
                
            except Exception as queue_error:
                # Failed to get result from queue
                logger.error(f"Failed to retrieve result from queue: {queue_error}")
                logger.error(f"Queue error type: {type(queue_error).__name__}")
                
                # Check if process crashed
                exit_code = self._process.exitcode
                if exit_code != 0:
                    logger.error(
                        f"Process crashed: exit_code={exit_code}, "
                        f"func={target_func.__name__}"
                    )
                    return ExecutionResult(
                        status=ExecutionStatus.CRASHED,
                        error=f"Process crashed with exit code {exit_code}. Queue error: {queue_error}",
                        exit_code=exit_code,
                        execution_time=execution_time,
                    )
                
                # Process completed but result retrieval failed
                logger.error(
                    f"Process completed (exit_code=0) but failed to retrieve result. "
                    f"This usually indicates the result was too large to serialize. "
                    f"Queue error: {queue_error}"
                )
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    error=f"Result retrieval failed (likely too large): {queue_error}",
                    execution_time=execution_time,
                )
        
        except Exception as e:
            log_exception(logger, f"isolated execution of {target_func.__name__}", e)
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=f"Executor error: {e}",
                execution_time=time.time() - start_time,
            )
        
        finally:
            self._cleanup()
    
    def _handle_timeout(self, execution_time: float, func_name: str = "unknown") -> ExecutionResult:
        """Handle timeout by terminating the process.
        
        Args:
            execution_time: How long the task ran before timeout
            func_name: Name of the function that timed out
        
        Returns:
            ExecutionResult with TIMEOUT status
        """
        if self._process and self._process.is_alive():
            pid = self._process.pid
            
            # Try graceful termination first
            log_timeout_handling(
                logger,
                pid=pid,
                timeout=self.config.max_execution_time,
                elapsed=execution_time,
                termination_type="SIGTERM",
            )
            self._process.terminate()
            
            # Wait for graceful shutdown
            self._process.join(timeout=self.config.kill_timeout)
            
            # Force kill if still alive
            if self._process.is_alive():
                log_timeout_handling(
                    logger,
                    pid=pid,
                    timeout=self.config.max_execution_time,
                    elapsed=execution_time,
                    termination_type="SIGKILL",
                )
                self._process.kill()
                self._process.join(timeout=2)
            else:
                log_timeout_handling(
                    logger,
                    pid=pid,
                    timeout=self.config.max_execution_time,
                    elapsed=execution_time,
                    termination_type="COMPLETED",
                )
        
        return ExecutionResult(
            status=ExecutionStatus.TIMEOUT,
            error=f"Execution exceeded timeout of {self.config.max_execution_time}s",
            execution_time=execution_time,
        )
    
    def _build_result(
        self,
        result_data: dict,
        execution_time: float,
        metrics: ResourceMetrics | None = None,
    ) -> ExecutionResult:
        """Build ExecutionResult from subprocess result data.
        
        Args:
            result_data: Data received from subprocess queue
            execution_time: Actual execution time
            metrics: Resource metrics if monitoring was enabled
        
        Returns:
            ExecutionResult object
        """
        status = result_data.get("status", ExecutionStatus.FAILED)
        
        result = ExecutionResult(
            status=status,
            data=result_data.get("data"),
            error=result_data.get("error"),
            exit_code=self._process.exitcode if self._process else None,
            execution_time=result_data.get("execution_time", execution_time),
            stdout="",  # Could be extended to capture stdout
            stderr=result_data.get("traceback", ""),
        )
        
        # Attach resource metrics if available
        if metrics:
            result.resource_metrics = metrics
        
        return result
    
    def _cleanup(self) -> None:
        """Clean up subprocess and queue resources."""
        if self._process:
            if self._process.is_alive():
                logger.warning("Cleaning up still-running process")
                self._process.terminate()
                self._process.join(timeout=2)
                if self._process.is_alive():
                    self._process.kill()
            
            self._process = None
        
        if self._result_queue:
            self._result_queue.close()
            self._result_queue = None
