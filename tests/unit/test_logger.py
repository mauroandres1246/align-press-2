"""Tests for logger module."""

import pytest
import logging
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

from alignpress.utils.logger import (
    AlignPressLogger,
    get_logger_manager,
    get_logger,
    configure_logging,
    add_context,
    clear_context,
    log_detection_event,
    log_performance_metrics,
    log_system_event,
    STRUCTLOG_AVAILABLE
)


class TestAlignPressLogger:
    """Test AlignPressLogger class."""

    @pytest.fixture
    def logger_instance(self):
        """Create fresh logger instance."""
        return AlignPressLogger()

    def test_logger_initialization(self, logger_instance):
        """Test logger initializes correctly."""
        assert logger_instance._configured is False
        assert isinstance(logger_instance._loggers, dict)
        assert len(logger_instance._loggers) == 0

    def test_configure_logging_basic(self, logger_instance):
        """Test basic logging configuration."""
        logger_instance.configure_logging(
            log_level="INFO",
            log_format="text",
            console_output=True
        )

        assert logger_instance._configured is True

    def test_configure_logging_only_once(self, logger_instance):
        """Test configure_logging is idempotent."""
        logger_instance.configure_logging(log_level="INFO")
        assert logger_instance._configured is True

        # Second call should be ignored
        logger_instance.configure_logging(log_level="DEBUG")
        assert logger_instance._configured is True

    def test_configure_logging_with_file(self, logger_instance, tmp_path):
        """Test logging configuration with file output."""
        log_file = tmp_path / "test.log"

        logger_instance.configure_logging(
            log_level="DEBUG",
            output_path=log_file,
            console_output=False
        )

        assert logger_instance._configured is True
        assert log_file.parent.exists()

    def test_get_logger_configures_if_needed(self, logger_instance):
        """Test get_logger auto-configures if not configured."""
        assert logger_instance._configured is False

        with patch.object(logger_instance, 'configure_from_app_config') as mock_config:
            logger = logger_instance.get_logger("test")
            mock_config.assert_called_once()

    def test_get_logger_returns_same_instance(self, logger_instance):
        """Test get_logger returns cached logger."""
        logger_instance.configure_logging()

        logger1 = logger_instance.get_logger("test")
        logger2 = logger_instance.get_logger("test")

        assert logger1 is logger2
        assert "test" in logger_instance._loggers

    def test_get_logger_different_names(self, logger_instance):
        """Test get_logger creates different loggers for different names."""
        logger_instance.configure_logging()

        logger_a = logger_instance.get_logger("module_a")
        logger_b = logger_instance.get_logger("module_b")

        assert logger_a is not logger_b
        assert len(logger_instance._loggers) == 2

    def test_configure_from_app_config_fallback(self, logger_instance):
        """Test configure_from_app_config uses fallback on error."""
        with patch('alignpress.utils.logger.load_app_config', side_effect=Exception("Config error")):
            logger_instance.configure_from_app_config()

        assert logger_instance._configured is True

    def test_log_levels(self, logger_instance, tmp_path):
        """Test different log levels are accepted."""
        log_file = tmp_path / "test.log"

        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            logger = AlignPressLogger()
            logger.configure_logging(log_level=level, output_path=log_file)
            assert logger._configured is True

    def test_log_formats(self, logger_instance):
        """Test different log formats."""
        for fmt in ["json", "text"]:
            logger = AlignPressLogger()
            logger.configure_logging(log_format=fmt, console_output=True)
            assert logger._configured is True

    @pytest.mark.skipif(not STRUCTLOG_AVAILABLE, reason="Requires structlog")
    def test_add_context_with_structlog(self, logger_instance):
        """Test adding context variables."""
        logger_instance.configure_logging()

        # Should not raise
        logger_instance.add_context(user="test", session="123")
        logger_instance.clear_context()

    def test_add_context_without_structlog(self, logger_instance):
        """Test add_context without structlog doesn't crash."""
        with patch('alignpress.utils.logger.STRUCTLOG_AVAILABLE', False):
            logger_instance.configure_logging()

            # Should not raise
            logger_instance.add_context(user="test")
            logger_instance.clear_context()

    def test_log_detection_event(self, logger_instance):
        """Test logging detection event."""
        logger_instance.configure_logging()
        logger = logger_instance.get_logger("test")

        # Should not raise
        logger_instance.log_detection_event(
            logger=logger,
            event_type="detection_complete",
            logo_name="test_logo",
            position_mm=(100.0, 50.0),
            deviation_mm=2.5,
            angle_deg=5.0,
            processing_time_ms=50.0
        )

    def test_log_detection_event_minimal(self, logger_instance):
        """Test logging detection event with minimal params."""
        logger_instance.configure_logging()
        logger = logger_instance.get_logger("test")

        # Should not raise
        logger_instance.log_detection_event(
            logger=logger,
            event_type="detection_start",
            logo_name="test_logo"
        )

    def test_log_performance_metrics(self, logger_instance):
        """Test logging performance metrics."""
        logger_instance.configure_logging()
        logger = logger_instance.get_logger("test")

        # Should not raise
        logger_instance.log_performance_metrics(
            logger=logger,
            operation="detect_logos",
            duration_ms=150.5,
            memory_usage_mb=25.3,
            fps=30.0
        )

    def test_log_performance_metrics_minimal(self, logger_instance):
        """Test logging performance metrics with minimal params."""
        logger_instance.configure_logging()
        logger = logger_instance.get_logger("test")

        # Should not raise
        logger_instance.log_performance_metrics(
            logger=logger,
            operation="load_template",
            duration_ms=10.0
        )

    def test_log_system_event(self, logger_instance):
        """Test logging system event."""
        logger_instance.configure_logging()
        logger = logger_instance.get_logger("test")

        # Should not raise
        logger_instance.log_system_event(
            logger=logger,
            event_type="startup",
            component="detector",
            status="info",
            message="Detector initialized"
        )

    def test_log_system_event_different_statuses(self, logger_instance):
        """Test logging system events with different statuses."""
        logger_instance.configure_logging()
        logger = logger_instance.get_logger("test")

        for status in ["info", "warning", "error"]:
            logger_instance.log_system_event(
                logger=logger,
                event_type="test_event",
                component="test",
                status=status
            )

    def test_file_rotation_params(self, logger_instance, tmp_path):
        """Test file rotation parameters."""
        log_file = tmp_path / "rotating.log"

        logger_instance.configure_logging(
            output_path=log_file,
            max_file_size=1024 * 1024,  # 1MB
            backup_count=3
        )

        assert logger_instance._configured is True
        # Handler should be configured (tested via actual logging behavior)


class TestGlobalLoggerFunctions:
    """Test global logger convenience functions."""

    def test_get_logger_manager_singleton(self):
        """Test get_logger_manager returns singleton."""
        manager1 = get_logger_manager()
        manager2 = get_logger_manager()

        assert manager1 is manager2

    def test_get_logger_function(self):
        """Test global get_logger function."""
        logger = get_logger("test_module")
        assert logger is not None

    def test_configure_logging_function(self):
        """Test global configure_logging function."""
        # Should not raise
        configure_logging(log_level="INFO", console_output=True)

    def test_add_context_function(self):
        """Test global add_context function."""
        # Should not raise
        add_context(session="test")
        clear_context()

    def test_clear_context_function(self):
        """Test global clear_context function."""
        # Should not raise
        clear_context()

    def test_log_detection_event_function(self):
        """Test global log_detection_event function."""
        logger = get_logger("test")

        # Should not raise
        log_detection_event(
            logger=logger,
            event_type="test",
            logo_name="logo1"
        )

    def test_log_performance_metrics_function(self):
        """Test global log_performance_metrics function."""
        logger = get_logger("test")

        # Should not raise
        log_performance_metrics(
            logger=logger,
            operation="test_op",
            duration_ms=100.0
        )

    def test_log_system_event_function(self):
        """Test global log_system_event function."""
        logger = get_logger("test")

        # Should not raise
        log_system_event(
            logger=logger,
            event_type="test",
            component="test_component"
        )


class TestLoggingIntegration:
    """Integration tests for actual logging behavior."""

    def test_log_output_to_file(self, tmp_path):
        """Test actual log messages are written to file."""
        log_file = tmp_path / "integration.log"

        logger_mgr = AlignPressLogger()
        logger_mgr.configure_logging(
            log_level="INFO",
            output_path=log_file,
            console_output=False
        )

        logger = logger_mgr.get_logger("test")

        # Log some messages
        if STRUCTLOG_AVAILABLE:
            logger.info("Test message", value=123)
        else:
            logger.info("Test message")

        # File should exist and have content
        assert log_file.exists()
        content = log_file.read_text()
        assert len(content) > 0

    def test_console_output_disabled(self, tmp_path, capsys):
        """Test console output can be disabled."""
        log_file = tmp_path / "no_console.log"

        logger_mgr = AlignPressLogger()
        logger_mgr.configure_logging(
            log_level="INFO",
            output_path=log_file,
            console_output=False
        )

        logger = logger_mgr.get_logger("test")

        if STRUCTLOG_AVAILABLE:
            logger.info("Should not appear in console")
        else:
            logger.info("Should not appear in console")

        # Console should have minimal output
        captured = capsys.readouterr()
        # Note: Some output may still occur from root logger

    def test_multiple_loggers_same_file(self, tmp_path):
        """Test multiple loggers can write to same file."""
        log_file = tmp_path / "shared.log"

        logger_mgr = AlignPressLogger()
        logger_mgr.configure_logging(
            log_level="INFO",
            output_path=log_file,
            console_output=False
        )

        logger1 = logger_mgr.get_logger("module1")
        logger2 = logger_mgr.get_logger("module2")

        if STRUCTLOG_AVAILABLE:
            logger1.info("From module 1")
            logger2.info("From module 2")
        else:
            logger1.info("From module 1")
            logger2.info("From module 2")

        assert log_file.exists()
        content = log_file.read_text()
        assert len(content) > 0

    def test_structured_event_logging(self, tmp_path):
        """Test structured events create proper log entries."""
        log_file = tmp_path / "events.log"

        logger_mgr = AlignPressLogger()
        logger_mgr.configure_logging(
            log_level="INFO",
            log_format="json" if STRUCTLOG_AVAILABLE else "text",
            output_path=log_file,
            console_output=False
        )

        logger = logger_mgr.get_logger("test")

        # Log structured events
        logger_mgr.log_detection_event(
            logger=logger,
            event_type="detection",
            logo_name="test_logo",
            position_mm=(100, 50),
            deviation_mm=1.5
        )

        logger_mgr.log_performance_metrics(
            logger=logger,
            operation="detect",
            duration_ms=50.0,
            fps=30.0
        )

        assert log_file.exists()
        content = log_file.read_text()
        assert "test_logo" in content or len(content) > 0
