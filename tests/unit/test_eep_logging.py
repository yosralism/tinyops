"""Unit tests for EEP logging utilities."""

import logging

import pytest

from workers.eep import EEPLoggerAdapter, setup_eep_logger


class TestEEPLogging:
    """Test EEP logging utilities."""

    def test_setup_eep_logger_default(self):
        """Test default logger setup."""
        logger = setup_eep_logger(name="test.eep.default")
        
        assert logger.name == "test.eep.default"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_setup_eep_logger_custom_level(self):
        """Test logger with custom level."""
        logger = setup_eep_logger(
            name="test.eep.custom",
            level=logging.DEBUG,
        )
        
        assert logger.level == logging.DEBUG

    def test_setup_eep_logger_custom_format(self):
        """Test logger with custom format."""
        custom_format = "%(levelname)s - %(message)s"
        logger = setup_eep_logger(
            name="test.eep.format",
            format_string=custom_format,
        )
        
        formatter = logger.handlers[0].formatter
        assert formatter is not None

    def test_logger_adapter_with_context(self, caplog):
        """Test logger adapter adds context."""
        base_logger = logging.getLogger("test.adapter")
        adapter = EEPLoggerAdapter(
            base_logger,
            extra={"task_id": "abc123", "device_id": 42}
        )
        
        with caplog.at_level(logging.INFO):
            adapter.info("Test message")
        
        assert len(caplog.records) == 1
        assert "Test message" in caplog.text
        assert "task_id=abc123" in caplog.text
        assert "device_id=42" in caplog.text

    def test_logger_adapter_multiple_context(self, caplog):
        """Test logger adapter with multiple context fields."""
        base_logger = logging.getLogger("test.multi")
        adapter = EEPLoggerAdapter(
            base_logger,
            extra={
                "task_id": "xyz789",
                "device_id": 100,
                "hostname": "router-01",
                "site_id": "dc1",
            }
        )
        
        with caplog.at_level(logging.INFO):
            adapter.info("Collection started")
        
        assert "Collection started" in caplog.text
        assert "task_id=xyz789" in caplog.text
        assert "device_id=100" in caplog.text
        assert "hostname=router-01" in caplog.text
        assert "site_id=dc1" in caplog.text

    def test_logger_adapter_no_context(self, caplog):
        """Test logger adapter without context."""
        base_logger = logging.getLogger("test.nocontext")
        adapter = EEPLoggerAdapter(base_logger, extra={})
        
        with caplog.at_level(logging.INFO):
            adapter.info("Simple message")
        
        assert "Simple message" in caplog.text

    def test_logger_adapter_different_levels(self, caplog):
        """Test logger adapter with different log levels."""
        base_logger = logging.getLogger("test.levels")
        adapter = EEPLoggerAdapter(
            base_logger,
            extra={"context": "test"}
        )
        
        with caplog.at_level(logging.DEBUG):
            adapter.debug("Debug message")
            adapter.info("Info message")
            adapter.warning("Warning message")
            adapter.error("Error message")
        
        assert len(caplog.records) == 4
        assert caplog.records[0].levelname == "DEBUG"
        assert caplog.records[1].levelname == "INFO"
        assert caplog.records[2].levelname == "WARNING"
        assert caplog.records[3].levelname == "ERROR"

    def test_setup_multiple_loggers(self):
        """Test setting up multiple independent loggers."""
        logger1 = setup_eep_logger(name="test.logger1", level=logging.INFO)
        logger2 = setup_eep_logger(name="test.logger2", level=logging.DEBUG)
        
        assert logger1.name != logger2.name
        assert logger1.level == logging.INFO
        assert logger2.level == logging.DEBUG

    def test_logger_removes_existing_handlers(self):
        """Test logger setup removes existing handlers."""
        logger = setup_eep_logger(name="test.handlers")
        initial_count = len(logger.handlers)
        
        # Setup again
        logger = setup_eep_logger(name="test.handlers")
        
        # Should still have same number of handlers (old ones removed)
        assert len(logger.handlers) == initial_count
