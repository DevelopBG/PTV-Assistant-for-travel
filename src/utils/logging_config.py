"""
Centralized logging configuration for PTV Transit Assistant.

Provides consistent logging setup across all modules with support for:
- Environment-based log level configuration via LOG_LEVEL env var
- Consistent log format with timestamps, module names, and log levels
- File-based logging with optional rotation
- Easy module-specific logger retrieval

Usage:
    from src.utils.logging_config import setup_logging, get_logger

    # At application startup (optional - configures root logger)
    setup_logging()

    # In each module
    logger = get_logger(__name__)
    logger.info("Operation completed")
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional


# Default configuration
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_BACKUP_COUNT = 5


def get_log_level() -> int:
    """
    Get logging level from LOG_LEVEL environment variable.

    Supported values: DEBUG, INFO, WARNING, ERROR, CRITICAL (case-insensitive)

    Returns:
        logging level constant (e.g., logging.INFO)
    """
    level_name = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_name, logging.INFO)


def setup_logging(
    level: Optional[int] = None,
    log_file: Optional[str] = None,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    """
    Configure the root logger with console and optional file handlers.

    This should be called once at application startup. Individual modules
    should use get_logger(__name__) to get module-specific loggers.

    Args:
        level: Logging level (default: from LOG_LEVEL env var or INFO)
        log_file: Optional file path for logging output (enables file logging)
        log_format: Log message format string
        date_format: Timestamp format string
        max_bytes: Maximum log file size before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)

    Example:
        # Basic setup (console only)
        setup_logging()

        # With file logging
        setup_logging(log_file="logs/app.log")

        # Debug mode
        setup_logging(level=logging.DEBUG)
    """
    if level is None:
        level = get_log_level()

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(log_format, date_format)

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional, with rotation)
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    This is the recommended way to get loggers in each module.
    The logger inherits settings from the root logger configured
    by setup_logging().

    Args:
        name: Logger name (typically __name__ for module-specific logging)

    Returns:
        Configured logger instance

    Example:
        # In your module
        from src.utils.logging_config import get_logger

        logger = get_logger(__name__)
        logger.info("Starting operation")
        logger.debug("Debug details: %s", details)
        logger.error("Operation failed: %s", error)
    """
    return logging.getLogger(name)
