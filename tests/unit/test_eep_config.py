"""Unit tests for EEP configuration."""

from pathlib import Path

import pytest

from workers.eep import EEPConfig


class TestEEPConfig:
    """Test EEP configuration validation."""

    def test_default_config(self):
        """Test default configuration values."""
        config = EEPConfig()
        
        assert config.max_execution_time == 3600
        assert config.memory_limit_mb == 512
        assert config.cpu_limit == 1.0
        assert config.enable_network is True
        assert config.temp_dir == Path("/tmp/eep")
        assert config.kill_timeout == 5

    def test_custom_config(self):
        """Test custom configuration values."""
        config = EEPConfig(
            max_execution_time=600,
            memory_limit_mb=1024,
            cpu_limit=2.0,
            enable_network=False,
            temp_dir="/tmp/eep",
            kill_timeout=10,
        )
        
        assert config.max_execution_time == 600
        assert config.memory_limit_mb == 1024
        assert config.cpu_limit == 2.0
        assert config.enable_network is False
        assert config.temp_dir == Path("/tmp/eep")
        assert config.kill_timeout == 10

    def test_validate_positive_timeout(self):
        """Test timeout must be positive."""
        with pytest.raises(ValueError, match="max_execution_time must be positive"):
            EEPConfig(max_execution_time=0)
        
        with pytest.raises(ValueError, match="max_execution_time must be positive"):
            EEPConfig(max_execution_time=-1)

    def test_validate_positive_memory_limit(self):
        """Test memory limit must be positive."""
        with pytest.raises(ValueError, match="memory_limit_mb must be positive"):
            EEPConfig(memory_limit_mb=0)
        
        with pytest.raises(ValueError, match="memory_limit_mb must be positive"):
            EEPConfig(memory_limit_mb=-100)

    def test_validate_positive_cpu_limit(self):
        """Test CPU limit cannot be negative."""
        with pytest.raises(ValueError, match="cpu_limit cannot be negative"):
            EEPConfig(cpu_limit=-1.0)
        
        # 0 is allowed (no limit)
        config = EEPConfig(cpu_limit=0.0)
        assert config.cpu_limit == 0.0

    def test_validate_positive_kill_timeout(self):
        """Test kill timeout cannot be negative."""
        with pytest.raises(ValueError, match="kill_timeout cannot be negative"):
            EEPConfig(kill_timeout=-5)
        
        # 0 is allowed
        config = EEPConfig(kill_timeout=0)
        assert config.kill_timeout == 0

    def test_config_mutability(self):
        """Test that config fields can be modified (not frozen)."""
        config = EEPConfig()
        
        # Config is not frozen, so we can modify it
        config.max_execution_time = 1000
        assert config.max_execution_time == 1000

    def test_realistic_production_config(self):
        """Test realistic production configuration."""
        config = EEPConfig(
            max_execution_time=600,  # 10 minutes
            memory_limit_mb=256,     # 256MB
            cpu_limit=1.0,           # 1 CPU core
            enable_network=True,     # Network needed for SSH
            kill_timeout=10,         # 10s grace period
        )
        
        assert config.max_execution_time == 600
        assert config.memory_limit_mb == 256
        assert config.cpu_limit == 1.0
        assert config.enable_network is True
        assert config.kill_timeout == 10
