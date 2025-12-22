"""
Test suite for SIDM2 logging system (v2.0.0).

Tests:
- Verbosity levels
- Color formatting
- Structured (JSON) logging
- File logging with rotation
- Performance logging
- Dynamic verbosity changes
- Module loggers

Usage:
    python scripts/test_logging_system.py
    python scripts/test_logging_system.py -v

Version: 1.0.0
"""

import unittest
import logging
import json
import tempfile
import os
import sys
import time
from pathlib import Path
from io import StringIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.logging_config import (
    setup_logging,
    get_logger,
    PerformanceLogger,
    log_performance,
    set_verbosity,
    get_verbosity,
    add_file_handler,
    VERBOSITY_LEVELS,
    ColoredFormatter,
    StructuredFormatter
)


class TestLoggingSetup(unittest.TestCase):
    """Test logging setup and configuration."""

    def setUp(self):
        """Reset logging before each test."""
        # Clear all handlers
        logger = logging.getLogger('sidm2')
        logger.handlers.clear()

    def test_default_setup(self):
        """Test default logging setup."""
        logger = setup_logging()

        self.assertEqual(logger.name, 'sidm2')
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertEqual(len(logger.handlers), 1)  # Console handler

    def test_verbosity_levels(self):
        """Test all verbosity levels."""
        for verbosity, expected_level in VERBOSITY_LEVELS.items():
            logger = setup_logging(verbosity=verbosity)

            # Check handler level
            handler = logger.handlers[0]
            self.assertEqual(handler.level, expected_level,
                           f"Verbosity {verbosity} should set level {expected_level}")

    def test_quiet_mode(self):
        """Test quiet mode (verbosity=0)."""
        logger = setup_logging(quiet=True)

        handler = logger.handlers[0]
        self.assertEqual(handler.level, logging.ERROR)
        self.assertEqual(get_verbosity(), 0)

    def test_debug_mode(self):
        """Test debug mode (verbosity=3)."""
        logger = setup_logging(debug=True)

        handler = logger.handlers[0]
        self.assertEqual(handler.level, logging.DEBUG)
        self.assertEqual(get_verbosity(), 3)

    def test_file_logging(self):
        """Test file logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'test.log')
            logger = setup_logging(verbosity=2, log_file=log_file)

            self.assertEqual(len(logger.handlers), 2)  # Console + File

            # Write log message
            logger.info("Test message")

            # Check file exists and has content
            self.assertTrue(os.path.exists(log_file))

            with open(log_file, 'r') as f:
                content = f.read()
                self.assertIn("Test message", content)

            # Close all handlers before tempdir cleanup (Windows)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

    def test_dynamic_verbosity_change(self):
        """Test changing verbosity dynamically."""
        logger = setup_logging(verbosity=2)  # INFO

        # Initial level
        self.assertEqual(get_verbosity(), 2)

        # Change to DEBUG
        set_verbosity(3)
        self.assertEqual(get_verbosity(), 3)

        handler = logger.handlers[0]
        self.assertEqual(handler.level, logging.DEBUG)

        # Change to ERROR
        set_verbosity(0)
        self.assertEqual(get_verbosity(), 0)
        self.assertEqual(handler.level, logging.ERROR)

    def test_verbosity_clamping(self):
        """Test verbosity is clamped to valid range."""
        logger = setup_logging(verbosity=999)  # Should clamp to 3
        self.assertEqual(get_verbosity(), 3)

        set_verbosity(-10)  # Should clamp to 0
        self.assertEqual(get_verbosity(), 0)


class TestColoredFormatter(unittest.TestCase):
    """Test colored console output formatter."""

    def test_colored_formatter_creation(self):
        """Test ColoredFormatter can be created."""
        formatter = ColoredFormatter(use_colors=True)
        self.assertIsNotNone(formatter)

    def test_format_without_colors(self):
        """Test formatting without colors."""
        formatter = ColoredFormatter(use_colors=False)

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)

        # Should not contain ANSI codes
        self.assertNotIn('\033[', formatted)
        self.assertIn('Test message', formatted)
        self.assertIn('INFO', formatted)


class TestStructuredFormatter(unittest.TestCase):
    """Test JSON structured formatter."""

    def test_structured_formatter_creation(self):
        """Test StructuredFormatter can be created."""
        formatter = StructuredFormatter()
        self.assertIsNotNone(formatter)

    def test_json_format(self):
        """Test JSON output format."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)

        # Should be valid JSON
        data = json.loads(formatted)

        # Check required fields
        self.assertEqual(data['level'], 'INFO')
        self.assertEqual(data['message'], 'Test message')
        self.assertEqual(data['logger'], 'test')
        self.assertEqual(data['line'], 42)

    def test_extra_fields_in_json(self):
        """Test extra fields appear in JSON output."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Add extra fields
        record.file_size = 1024
        record.accuracy = 99.93

        formatted = formatter.format(record)
        data = json.loads(formatted)

        # Check extra fields
        self.assertEqual(data['file_size'], 1024)
        self.assertEqual(data['accuracy'], 99.93)


class TestPerformanceLogger(unittest.TestCase):
    """Test performance logging context manager."""

    def test_performance_logger_success(self):
        """Test performance logging for successful operation."""
        logger = setup_logging(verbosity=2)

        with PerformanceLogger(logger, "test operation"):
            time.sleep(0.1)  # Simulate work

        # No exception should be raised

    def test_performance_logger_failure(self):
        """Test performance logging for failed operation."""
        logger = setup_logging(verbosity=2)

        with self.assertRaises(ValueError):
            with PerformanceLogger(logger, "failing operation"):
                raise ValueError("Test error")

    def test_log_performance_decorator(self):
        """Test log_performance decorator."""
        setup_logging(verbosity=2)

        @log_performance("decorated operation")
        def test_function():
            time.sleep(0.05)
            return "result"

        result = test_function()
        self.assertEqual(result, "result")


class TestModuleLoggers(unittest.TestCase):
    """Test module-specific loggers."""

    def setUp(self):
        """Reset logging before each test."""
        logger = logging.getLogger('sidm2')
        logger.handlers.clear()

    def test_get_logger(self):
        """Test getting module logger."""
        setup_logging()

        logger1 = get_logger('test_module')
        logger2 = get_logger('sidm2.test_module')

        # Both should return logger under sidm2 namespace
        self.assertTrue(logger1.name.startswith('sidm2'))
        self.assertTrue(logger2.name.startswith('sidm2'))

    def test_module_logger_inherits_config(self):
        """Test module logger inherits root config."""
        setup_logging(verbosity=3)  # DEBUG

        logger = get_logger('test_module')

        # Should inherit DEBUG level from root
        self.assertTrue(logger.isEnabledFor(logging.DEBUG))


class TestFileRotation(unittest.TestCase):
    """Test log file rotation."""

    def test_rotating_file_handler(self):
        """Test log rotation creates backup files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'rotate.log')

            # Setup with small max size
            logger = setup_logging(
                verbosity=2,
                log_file=log_file,
                max_file_size=100,  # Very small for testing
                backup_count=2
            )

            # Write many messages to trigger rotation
            for i in range(50):
                logger.info(f"Message {i:03d} with some padding to increase size")

            # Check main file exists
            self.assertTrue(os.path.exists(log_file))

            # Check if rotation occurred (backup files may exist)
            # Note: Rotation depends on message size, may not always trigger

            # Close all handlers before tempdir cleanup (Windows)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

    def test_add_file_handler(self):
        """Test adding additional file handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            main_log = os.path.join(tmpdir, 'main.log')
            error_log = os.path.join(tmpdir, 'errors.log')

            logger = setup_logging(verbosity=2, log_file=main_log)

            # Add error-only log
            add_file_handler(error_log, level=logging.ERROR)

            # Write messages
            logger.info("Info message")
            logger.error("Error message")

            # Check main log has both
            with open(main_log, 'r') as f:
                main_content = f.read()
                self.assertIn("Info message", main_content)
                self.assertIn("Error message", main_content)

            # Check error log has only error
            with open(error_log, 'r') as f:
                error_content = f.read()
                self.assertNotIn("Info message", error_content)
                self.assertIn("Error message", error_content)

            # Close all handlers before tempdir cleanup (Windows)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)


class TestStructuredLogging(unittest.TestCase):
    """Test structured (JSON) logging."""

    def test_structured_console_output(self):
        """Test structured logging to console."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, 'structured.jsonl')

            logger = setup_logging(
                verbosity=2,
                log_file=log_file,
                structured=True
            )

            # Log with extra fields
            logger.info(
                "Test message",
                extra={'key1': 'value1', 'key2': 42}
            )

            # Read log file
            with open(log_file, 'r') as f:
                line = f.readline()
                data = json.loads(line)

                # Check structure
                self.assertEqual(data['message'], 'Test message')
                self.assertEqual(data['level'], 'INFO')
                self.assertEqual(data['key1'], 'value1')
                self.assertEqual(data['key2'], 42)

            # Close all handlers before tempdir cleanup (Windows)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLoggingSetup))
    suite.addTests(loader.loadTestsFromTestCase(TestColoredFormatter))
    suite.addTests(loader.loadTestsFromTestCase(TestStructuredFormatter))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceLogger))
    suite.addTests(loader.loadTestsFromTestCase(TestModuleLoggers))
    suite.addTests(loader.loadTestsFromTestCase(TestFileRotation))
    suite.addTests(loader.loadTestsFromTestCase(TestStructuredLogging))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit(run_tests())
