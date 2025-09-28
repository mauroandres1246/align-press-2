"""
Structured logging utilities using structlog.

This module provides centralized logging configuration with structured
JSON output and contextual information for debugging and monitoring.
"""

import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Any, Dict, Optional, Union
from datetime import datetime

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

from .config_loader import load_app_config, ConfigError


class AlignPressLogger:
    """
    Centralized logger configuration for Align-Press.
    """

    def __init__(self):
        """Initialize logger."""
        self._configured = False
        self._loggers: Dict[str, Any] = {}

    def configure_logging(
        self,
        log_level: str = "INFO",
        log_format: str = "json",
        output_path: Optional[Path] = None,
        console_output: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> None:
        """
        Configure structured logging.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Log format ("json" or "text")
            output_path: Path for log files (None for console only)
            console_output: Whether to output to console
            max_file_size: Maximum size for log files before rotation
            backup_count: Number of backup files to keep
        """
        if self._configured:
            return

        # Convert log level
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)

        if STRUCTLOG_AVAILABLE:
            self._configure_structlog(
                numeric_level, log_format, output_path,
                console_output, max_file_size, backup_count
            )
        else:
            self._configure_stdlib_logging(
                numeric_level, output_path, console_output,
                max_file_size, backup_count
            )

        self._configured = True

    def _configure_structlog(
        self,
        log_level: int,
        log_format: str,
        output_path: Optional[Path],
        console_output: bool,
        max_file_size: int,
        backup_count: int
    ) -> None:
        """Configure structlog-based logging."""
        # Shared processors
        shared_processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]

        # Configure structlog
        if log_format == "json":
            # JSON output processors
            processors = shared_processors + [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer()
            ]
        else:
            # Human-readable output processors
            processors = shared_processors + [
                structlog.processors.add_log_level,
                structlog.dev.ConsoleRenderer(colors=console_output)
            ]

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Configure stdlib logging for handlers
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)

            if log_format == "json":
                formatter = logging.Formatter('%(message)s')
            else:
                formatter = logging.Formatter(
                    '%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
                )
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        # File handler
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                output_path,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)

            # Always use JSON format for file output
            formatter = logging.Formatter('%(message)s')
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    def _configure_stdlib_logging(
        self,
        log_level: int,
        output_path: Optional[Path],
        console_output: bool,
        max_file_size: int,
        backup_count: int
    ) -> None:
        """Configure standard library logging (fallback when structlog unavailable)."""
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
        )

        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        # File handler
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                output_path,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    def get_logger(self, name: str) -> Any:
        """
        Get a logger instance.

        Args:
            name: Logger name (typically __name__)

        Returns:
            Logger instance (structlog or stdlib)
        """
        if not self._configured:
            self.configure_from_app_config()

        if name in self._loggers:
            return self._loggers[name]

        if STRUCTLOG_AVAILABLE:
            logger = structlog.get_logger(name)
        else:
            logger = logging.getLogger(name)

        self._loggers[name] = logger
        return logger

    def configure_from_app_config(self) -> None:
        """Configure logging from application configuration."""
        try:
            app_config = load_app_config()

            # Generate log file path with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"alignpress_{timestamp}.log"
            log_path = Path(app_config.log_output_path) / log_filename

            self.configure_logging(
                log_level=app_config.log_level.value,
                log_format=app_config.log_format,
                output_path=log_path,
                console_output=True
            )

        except (ConfigError, Exception):
            # Fallback to basic configuration
            self.configure_logging(
                log_level="INFO",
                log_format="text",
                output_path=None,
                console_output=True
            )

    def add_context(self, **kwargs) -> None:
        """
        Add context variables to all subsequent log messages.

        Args:
            **kwargs: Context variables to add
        """
        if STRUCTLOG_AVAILABLE:
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(**kwargs)

    def clear_context(self) -> None:
        """Clear all context variables."""
        if STRUCTLOG_AVAILABLE:
            structlog.contextvars.clear_contextvars()

    def log_detection_event(
        self,
        logger: Any,
        event_type: str,
        logo_name: str,
        position_mm: Optional[tuple] = None,
        deviation_mm: Optional[float] = None,
        angle_deg: Optional[float] = None,
        processing_time_ms: Optional[float] = None,
        **extra_context
    ) -> None:
        """
        Log a structured detection event.

        Args:
            logger: Logger instance
            event_type: Type of event (detection_start, detection_complete, etc.)
            logo_name: Name of the logo
            position_mm: Detected position in millimeters
            deviation_mm: Position deviation
            angle_deg: Detected angle
            processing_time_ms: Processing time in milliseconds
            **extra_context: Additional context variables
        """
        event_data = {
            "event_type": event_type,
            "logo_name": logo_name,
            **extra_context
        }

        if position_mm is not None:
            event_data["position_mm"] = position_mm

        if deviation_mm is not None:
            event_data["deviation_mm"] = deviation_mm

        if angle_deg is not None:
            event_data["angle_deg"] = angle_deg

        if processing_time_ms is not None:
            event_data["processing_time_ms"] = processing_time_ms

        if STRUCTLOG_AVAILABLE:
            logger.info("Detection event", **event_data)
        else:
            logger.info(f"Detection event: {event_type} for {logo_name}", extra=event_data)

    def log_performance_metrics(
        self,
        logger: Any,
        operation: str,
        duration_ms: float,
        memory_usage_mb: Optional[float] = None,
        fps: Optional[float] = None,
        **extra_metrics
    ) -> None:
        """
        Log performance metrics.

        Args:
            logger: Logger instance
            operation: Operation name
            duration_ms: Duration in milliseconds
            memory_usage_mb: Memory usage in MB
            fps: Frames per second
            **extra_metrics: Additional metrics
        """
        metrics_data = {
            "operation": operation,
            "duration_ms": duration_ms,
            **extra_metrics
        }

        if memory_usage_mb is not None:
            metrics_data["memory_usage_mb"] = memory_usage_mb

        if fps is not None:
            metrics_data["fps"] = fps

        if STRUCTLOG_AVAILABLE:
            logger.info("Performance metrics", **metrics_data)
        else:
            logger.info(f"Performance: {operation} took {duration_ms:.1f}ms", extra=metrics_data)

    def log_system_event(
        self,
        logger: Any,
        event_type: str,
        component: str,
        status: str = "info",
        message: Optional[str] = None,
        **extra_context
    ) -> None:
        """
        Log a system event.

        Args:
            logger: Logger instance
            event_type: Type of event (startup, shutdown, error, etc.)
            component: Component name
            status: Event status (info, warning, error)
            message: Human-readable message
            **extra_context: Additional context
        """
        event_data = {
            "event_type": event_type,
            "component": component,
            "status": status,
            **extra_context
        }

        log_message = message or f"{component} {event_type}"

        if STRUCTLOG_AVAILABLE:
            if status == "error":
                logger.error(log_message, **event_data)
            elif status == "warning":
                logger.warning(log_message, **event_data)
            else:
                logger.info(log_message, **event_data)
        else:
            log_level = getattr(logger, status.lower(), logger.info)
            log_level(log_message, extra=event_data)


# Global logger instance
_global_logger_manager: Optional[AlignPressLogger] = None


def get_logger_manager() -> AlignPressLogger:
    """
    Get global logger manager instance.

    Returns:
        Global AlignPressLogger instance
    """
    global _global_logger_manager

    if _global_logger_manager is None:
        _global_logger_manager = AlignPressLogger()

    return _global_logger_manager


def get_logger(name: str) -> Any:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    manager = get_logger_manager()
    return manager.get_logger(name)


def configure_logging(**kwargs) -> None:
    """
    Configure logging with given parameters.

    Args:
        **kwargs: Configuration parameters for AlignPressLogger.configure_logging()
    """
    manager = get_logger_manager()
    manager.configure_logging(**kwargs)


def add_context(**kwargs) -> None:
    """
    Add context variables to all subsequent log messages.

    Args:
        **kwargs: Context variables to add
    """
    manager = get_logger_manager()
    manager.add_context(**kwargs)


def clear_context() -> None:
    """Clear all context variables."""
    manager = get_logger_manager()
    manager.clear_context()


# Convenience functions for structured logging
def log_detection_event(logger: Any, **kwargs) -> None:
    """Log a detection event. See AlignPressLogger.log_detection_event for args."""
    manager = get_logger_manager()
    manager.log_detection_event(logger, **kwargs)


def log_performance_metrics(logger: Any, **kwargs) -> None:
    """Log performance metrics. See AlignPressLogger.log_performance_metrics for args."""
    manager = get_logger_manager()
    manager.log_performance_metrics(logger, **kwargs)


def log_system_event(logger: Any, **kwargs) -> None:
    """Log a system event. See AlignPressLogger.log_system_event for args."""
    manager = get_logger_manager()
    manager.log_system_event(logger, **kwargs)