"""
Tests for centralized logging configuration.
"""

import logging
import os
import tempfile
import pytest

from src.utils.logging_config import (
    setup_logging,
    get_logger,
    get_log_level,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_FORMAT,
)


class TestGetLogLevel:
    """Tests for get_log_level function."""

    def test_default_level(self, monkeypatch):
        """Test default log level when env var not set."""
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        assert get_log_level() == logging.INFO

    def test_debug_level(self, monkeypatch):
        """Test DEBUG log level from env var."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        assert get_log_level() == logging.DEBUG

    def test_info_level(self, monkeypatch):
        """Test INFO log level from env var."""
        monkeypatch.setenv("LOG_LEVEL", "INFO")
        assert get_log_level() == logging.INFO

    def test_warning_level(self, monkeypatch):
        """Test WARNING log level from env var."""
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        assert get_log_level() == logging.WARNING

    def test_warn_alias(self, monkeypatch):
        """Test WARN alias for WARNING level."""
        monkeypatch.setenv("LOG_LEVEL", "WARN")
        assert get_log_level() == logging.WARNING

    def test_error_level(self, monkeypatch):
        """Test ERROR log level from env var."""
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        assert get_log_level() == logging.ERROR

    def test_critical_level(self, monkeypatch):
        """Test CRITICAL log level from env var."""
        monkeypatch.setenv("LOG_LEVEL", "CRITICAL")
        assert get_log_level() == logging.CRITICAL

    def test_case_insensitive(self, monkeypatch):
        """Test case-insensitive log level parsing."""
        monkeypatch.setenv("LOG_LEVEL", "debug")
        assert get_log_level() == logging.DEBUG

        monkeypatch.setenv("LOG_LEVEL", "Debug")
        assert get_log_level() == logging.DEBUG

    def test_invalid_level_defaults_to_info(self, monkeypatch):
        """Test invalid log level defaults to INFO."""
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        assert get_log_level() == logging.INFO


class TestSetupLogging:
    """Tests for setup_logging function."""

    def teardown_method(self):
        """Clean up after each test."""
        # Reset root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.WARNING)

    def test_setup_console_handler(self):
        """Test that setup_logging adds console handler."""
        setup_logging(level=logging.INFO)
        root_logger = logging.getLogger()

        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_setup_file_handler(self):
        """Test that setup_logging adds file handler when log_file specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            setup_logging(level=logging.DEBUG, log_file=log_file)

            root_logger = logging.getLogger()

            assert len(root_logger.handlers) == 2
            assert any(
                isinstance(h, logging.handlers.RotatingFileHandler)
                for h in root_logger.handlers
            )

    def test_setup_creates_log_directory(self):
        """Test that setup_logging creates log directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "logs", "subdir", "test.log")
            setup_logging(log_file=log_file)

            assert os.path.exists(os.path.dirname(log_file))

    def test_setup_removes_existing_handlers(self):
        """Test that setup_logging clears existing handlers before adding new ones."""
        root_logger = logging.getLogger()
        initial_count = len(root_logger.handlers)

        # Add a dummy handler
        root_logger.addHandler(logging.StreamHandler())
        assert len(root_logger.handlers) == initial_count + 1

        # Setup logging should clear all handlers and add exactly one console handler
        setup_logging()
        # After setup, we should have exactly 1 handler (the console handler we added)
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_setup_uses_env_level_by_default(self, monkeypatch):
        """Test that setup_logging uses LOG_LEVEL env var when level not specified."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_explicit_level_overrides_env(self, monkeypatch):
        """Test that explicit level parameter overrides env var."""
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        setup_logging(level=logging.ERROR)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a Logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_with_dunder_name(self):
        """Test get_logger with __name__ pattern."""
        logger = get_logger(__name__)
        assert isinstance(logger, logging.Logger)
        assert logger.name == __name__

    def test_logger_inherits_root_level(self):
        """Test that module logger inherits root logger level."""
        setup_logging(level=logging.DEBUG)
        logger = get_logger("test_module")

        # Logger should be able to log at DEBUG level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def teardown_method(self):
        """Clean up after each test."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.WARNING)

    def test_log_message_written_to_file(self):
        """Test that log messages are written to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            setup_logging(level=logging.INFO, log_file=log_file)

            logger = get_logger("test_logger")
            logger.info("Test message")

            # Read log file
            with open(log_file, "r") as f:
                content = f.read()

            assert "Test message" in content
            assert "INFO" in content
            assert "test_logger" in content

    def test_log_format_contains_expected_fields(self):
        """Test that log format contains timestamp, level, module, message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            setup_logging(level=logging.INFO, log_file=log_file)

            logger = get_logger("my_module")
            logger.warning("A warning occurred")

            with open(log_file, "r") as f:
                content = f.read()

            # Check for expected format components
            assert "WARNING" in content
            assert "my_module" in content
            assert "A warning occurred" in content
            # Check timestamp format (YYYY-MM-DD HH:MM:SS)
            import re
            assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", content)

    def test_debug_messages_not_logged_at_info_level(self):
        """Test that DEBUG messages are filtered at INFO level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            setup_logging(level=logging.INFO, log_file=log_file)

            logger = get_logger("test_logger")
            logger.debug("Debug message - should not appear")
            logger.info("Info message - should appear")

            with open(log_file, "r") as f:
                content = f.read()

            assert "Debug message" not in content
            assert "Info message" in content

    def test_multiple_loggers_share_root_config(self):
        """Test that multiple module loggers share root configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            setup_logging(level=logging.INFO, log_file=log_file)

            logger1 = get_logger("module1")
            logger2 = get_logger("module2")

            logger1.info("Message from module1")
            logger2.info("Message from module2")

            with open(log_file, "r") as f:
                content = f.read()

            assert "module1" in content
            assert "module2" in content
            assert "Message from module1" in content
            assert "Message from module2" in content
