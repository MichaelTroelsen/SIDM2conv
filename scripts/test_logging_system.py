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

try:                        # guarded so `python scripts/test_logging_system.py`
    import pytest           # (the documented standalone usage) still runs
except ImportError:         # without pytest installed
    pytest = None
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


if pytest is not None:
    @pytest.fixture(autouse=True)
    def _restore_sidm2_logger_state():
        """Undo what setup_logging() does to the GLOBAL `sidm2` logger.

        setup_logging() sets `logger.propagate = False` (logging_config.py:311)
        and never restores it. Every test in this file calls setup_logging --
        about seventeen times across the classes below -- so the FIRST one to
        run leaves the package logger detached from root for the rest of the
        session.

        That is not a local problem. pyscript/test_stage7_emissions.py captures
        by attaching a handler to the ROOT logger, so once propagate is False it
        sees '' forever and six of its tests fail with
        "AssertionError: '...' not found in ''". Under `-p no:randomly` this
        file happens to run after them and nothing shows; under
        `--randomly-seed=1` it runs first and they all fail. A file-based watch
        recorded the exact transition:

            CHANGED after scripts/test_logging_system.py::TestLoggingSetup::
            test_dynamic_verbosity_change : propagate True->False

        The fix belongs here rather than in logging_config: propagate=False is
        correct behaviour for a configured application logger, and graphify puts
        789 nodes at depth 2 behind that module. What was wrong is that a TEST
        applied it globally and left it.
        """
        logger = logging.getLogger('sidm2')
        prop, handlers, level = logger.propagate, list(logger.handlers), logger.level
        try:
            yield
        finally:
            logger.handlers[:] = handlers
            logger.propagate = prop
            logger.level = level


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


class TestNonAsciiOnANarrowConsole(unittest.TestCase):
    """A glyph the console cannot encode must not DELETE the log line.

    Measured 2026-09-03 under PYTHONIOENCODING=cp1252 (the ordinary Windows
    default): logging a U+2192 arrow raised
    `UnicodeEncodeError: 'charmap' codec can't encode character '\\u2192'`
    inside the handler. logging catches handler errors, so nothing crashed --
    the MESSAGE WAS DISCARDED and a traceback went to stderr instead. That is
    the bad shape: conversion_pipeline logs an arrow in "No registered
    extractor for 'driver11' -> using Laxity table extraction", so on a cp1252
    console the line naming the extractor is the one that disappears.

    This drives a real cp1252 stream rather than setting an env var, so it
    reproduces on any platform.
    """

    def _log_through_cp1252(self, message):
        import io
        buf = io.BytesIO()
        stream = io.TextIOWrapper(buf, encoding='cp1252', newline='')
        real_stdout = sys.stdout
        sys.stdout = stream
        try:
            logger = setup_logging(verbosity=2)
            logger.warning(message)
            for h in logger.handlers:
                h.flush()
            stream.flush()
        finally:
            sys.stdout = real_stdout
        return buf.getvalue().decode('cp1252')

    def test_an_unencodable_glyph_does_not_lose_the_message(self):
        out = self._log_through_cp1252('extractor → laxity')
        # the surrounding words survive -- the line was emitted, not dropped
        self.assertIn('extractor', out)
        self.assertIn('laxity', out)

    def test_the_glyph_is_escaped_not_collapsed_to_a_question_mark(self):
        """backslashreplace, not replace: which character it was is recoverable."""
        out = self._log_through_cp1252('extractor → laxity')
        self.assertIn('\\u2192', out)

    def test_plain_ascii_is_untouched(self):
        out = self._log_through_cp1252('ordinary message')
        self.assertIn('ordinary message', out)
        self.assertNotIn('\\u', out)


class TestLogFilesKeepNonAsciiToo(unittest.TestCase):
    """The FILE handler had the same encoding defect as the console, and worse.

    Measured 2026-09-04 on a cp1252 locale, before the fix: logging a U+2192
    arrow through a file handler wrote **ZERO BYTES**. The console version at
    least spills its traceback to stderr where a human may notice; a log file is
    read AFTER the fact and simply has no record of the line.

    All four construction sites in logging_config (rotating and plain, in both
    setup_logging and add_file_handler) passed no `encoding=`, so each took
    `locale.getencoding()`. They now pass encoding='utf-8' with
    errors='backslashreplace' as a backstop.
    """

    def _log_to_file(self, message, rotating, via_add_file_handler):
        import tempfile
        d = tempfile.mkdtemp()
        path = os.path.join(d, "t.log")
        size = (10 * 1024 * 1024) if rotating else 0
        if via_add_file_handler:
            setup_logging(verbosity=2)
            add_file_handler(path, max_file_size=size)
        else:
            setup_logging(verbosity=2, log_file=path, max_file_size=size)
        logger = logging.getLogger("sidm2")
        logger.warning(message)
        for h in logger.handlers:
            h.flush()
        raw = open(path, "rb").read()
        for h in list(logger.handlers):          # release before tempdir cleanup
            try:
                h.close()
                logger.removeHandler(h)
            except Exception:                                 # noqa: BLE001
                pass
        return raw

    def test_all_four_file_handler_paths_keep_a_non_ascii_glyph(self):
        for rotating in (True, False):
            for via_add in (False, True):
                with self.subTest(rotating=rotating, add_file_handler=via_add):
                    raw = self._log_to_file("extractor → laxity",
                                            rotating, via_add)
                    self.assertTrue(raw, "the log file is EMPTY -- the line was discarded")
                    self.assertIn("extractor".encode(), raw)
                    self.assertIn("→".encode("utf-8"), raw,
                                  "the glyph did not survive as UTF-8")

    def test_plain_ascii_is_unaffected(self):
        raw = self._log_to_file("ordinary message", False, False)
        self.assertIn(b"ordinary message", raw)


class TestZZPropagateIsRestoredBetweenTests(unittest.TestCase):
    """THE REGRESSION GUARD for the autouse fixture at the top of this file.

    Named ZZ so it sorts LAST in definition order: under `-p no:randomly` every
    setup_logging() call above has already run by the time this executes, so
    without the fixture `propagate` is False here and this fails deterministically
    rather than by luck of the seed.

    It asserts the ENTRY state, not the exit state, which is the property that
    actually matters -- any test anywhere may attach a handler to the root logger
    and expect `sidm2.*` records to reach it.
    """

    def test_the_package_logger_still_propagates_to_root(self):
        self.assertTrue(
            logging.getLogger('sidm2').propagate,
            "sidm2.propagate is False on entry to this test, so a previous test "
            "in this file leaked setup_logging()'s global state. Every "
            "root-logger capture in the suite is blind from here on -- see "
            "pyscript/test_stage7_emissions.py.")


if __name__ == '__main__':
    exit(run_tests())
