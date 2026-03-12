"""EEP configuration settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EEPConfig:
    """Configuration for Execution Environment Protection.
    
    Attributes:
        max_execution_time: Maximum time (seconds) a task can run before being terminated
        memory_limit_mb: Maximum memory (MB) a task can use (Unix only)
        cpu_limit: CPU cores allocated to task (0 = no limit)
        enable_network: Whether task can access network
        temp_dir: Temporary directory for task files
        kill_timeout: Time to wait after SIGTERM before SIGKILL (seconds)
    """
    
    max_execution_time: int = 3600  # 1 hour default
    memory_limit_mb: int = 512
    cpu_limit: float = 1.0
    enable_network: bool = True
    temp_dir: Path = field(default_factory=lambda: Path("/tmp/eep"))
    kill_timeout: int = 5
    
    def __post_init__(self):
        """Validate configuration values."""
        if self.max_execution_time <= 0:
            raise ValueError("max_execution_time must be positive")
        
        if self.memory_limit_mb <= 0:
            raise ValueError("memory_limit_mb must be positive")
        
        if self.cpu_limit < 0:
            raise ValueError("cpu_limit cannot be negative")
        
        if self.kill_timeout < 0:
            raise ValueError("kill_timeout cannot be negative")
        
        # Ensure temp_dir is a Path object
        if not isinstance(self.temp_dir, Path):
            self.temp_dir = Path(self.temp_dir)
