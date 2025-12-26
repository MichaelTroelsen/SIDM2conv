#!/usr/bin/env python3
"""
Unit Tests for SF2 Debug Logger

Tests the core functionality of the SF2 debug logging module without GUI dependencies.
"""

import unittest
import sys
import os
import json
import time
import tempfile
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_debug_logger import (
    SF2DebugLogger, SF2LogLevel, SF2EventType,
    configure_sf2_logger, get_sf2_logger
)


class TestSF2LoggerInitialization(unittest.TestCase):
    """Test logger initialization and configuration"""

    def test_logger_creates_with_defaults(self):
        """Test 1.1: Logger creates with default settings"""
        logger = SF2DebugLogger()
        self.assertIsNotNone(logger)
        self.assertEqual(logger.event_count, 1)  # Initial event
        self.assertEqual(len(logger.event_history), 1)

    def test_logger_creates_with_custom_settings(self):
        """Test 1.2: Logger creates with custom settings"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            logger = SF2DebugLogger(
                name="TestLogger",
                level=logging.DEBUG,
                log_file=log_file,
                ultraverbose=False
            )

            self.assertIsNotNone(logger)
            self.assertTrue(os.path.exists(log_file))
            self.assertEqual(logger.logger.name, "TestLogger")

            # FIX: Close file handlers before cleanup
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
            if logger.json_handler:
                logger.json_handler.close()
        finally:
            if os.path.exists(log_file):
                try:
                    os.unlink(log_file)
                except PermissionError:
                    pass  # File still in use, skip cleanup

    def test_ultraverbose_mode_enables(self):
        """Test 1.3: Ultra-verbose mode enables correctly"""
        logger = SF2DebugLogger(ultraverbose=True)
        self.assertTrue(logger.ultraverbose)
        self.assertEqual(logger.logger.level, SF2LogLevel.ULTRAVERBOSE.value)

    def test_file_handler_creates_log_file(self):
        """Test 1.4: File handler creates log file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        try:
            logger = SF2DebugLogger(log_file=log_file)
            logger.log_action("Test message")

            self.assertTrue(os.path.exists(log_file))
            with open(log_file, 'r') as f:
                content = f.read()
                self.assertIn("Test message", content)

            # FIX: Close file handlers before cleanup
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
            if logger.json_handler:
                logger.json_handler.close()
        finally:
            if os.path.exists(log_file):
                try:
                    os.unlink(log_file)
                except PermissionError:
                    pass  # File still in use, skip cleanup

    def test_json_handler_creates_json_file(self):
        """Test 1.5: JSON handler creates JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name

        json_file = log_file.replace('.log', '.json')

        try:
            logger = SF2DebugLogger(log_file=log_file, json_log=True)
            logger.log_action("Test JSON message")

            self.assertTrue(os.path.exists(json_file))
            with open(json_file, 'r') as f:
                content = f.read()
                # Should be valid JSON lines
                lines = content.strip().split('\n')
                for line in lines:
                    if line:
                        data = json.loads(line)
                        self.assertIn('event_id', data)
                        self.assertIn('timestamp', data)

            # FIX: Close file handlers before cleanup
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)
            if logger.json_handler:
                logger.json_handler.close()
        finally:
            if os.path.exists(log_file):
                try:
                    os.unlink(log_file)
                except PermissionError:
                    pass
            if os.path.exists(json_file):
                try:
                    os.unlink(json_file)
                except PermissionError:
                    pass


class TestEventLogging(unittest.TestCase):
    """Test event logging functionality"""

    def setUp(self):
        """Create logger for each test"""
        self.logger = SF2DebugLogger(console_output=False)  # No console spam

    def test_log_event_creates_correct_structure(self):
        """Test 2.1: log_event() creates correct structure"""
        self.logger.log_event(SF2EventType.ACTION, {
            'message': 'Test action',
            'details': 'Test details'
        })

        # Should have 2 events now (init + this one)
        self.assertEqual(self.logger.event_count, 2)
        event = self.logger.event_history[-1]

        self.assertIn('event_id', event)
        self.assertIn('timestamp', event)
        self.assertIn('elapsed_ms', event)
        self.assertIn('event_type', event)
        self.assertIn('data', event)
        self.assertEqual(event['event_type'], 'action')

    def test_event_id_increments_sequentially(self):
        """Test 2.2: Event ID increments sequentially"""
        start_count = self.logger.event_count

        for i in range(10):
            self.logger.log_action(f"Action {i}")

        self.assertEqual(self.logger.event_count, start_count + 10)

        # Check event IDs are sequential
        event_ids = [e['event_id'] for e in self.logger.event_history[-10:]]
        for i in range(1, len(event_ids)):
            self.assertEqual(event_ids[i], event_ids[i-1] + 1)

    def test_timestamp_format_is_iso8601(self):
        """Test 2.3: Timestamp format is ISO 8601"""
        self.logger.log_action("Timestamp test")
        event = self.logger.event_history[-1]

        timestamp = event['timestamp']
        # ISO 8601 format: 2025-12-26T10:30:45.123456
        self.assertRegex(timestamp, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')

    def test_elapsed_time_calculates_correctly(self):
        """Test 2.4: Elapsed time calculates correctly"""
        start_time = time.time()
        time.sleep(0.1)  # Wait 100ms

        self.logger.log_action("Elapsed test")
        event = self.logger.event_history[-1]

        elapsed_ms = event['elapsed_ms']
        elapsed_sec = elapsed_ms / 1000.0

        # Should be close to 0.1 seconds (±50ms tolerance)
        self.assertGreater(elapsed_sec, 0.05)
        self.assertLess(elapsed_sec, 0.20)

    def test_event_history_stores_events(self):
        """Test 2.5: Event history stores last 1000 events"""
        # Generate 1500 events
        for i in range(1500):
            self.logger.log_action(f"Event {i}")

        # Event history should cap at 1000
        self.assertEqual(len(self.logger.event_history), 1000)

        # Event count should still be 1500 + 1 (initial)
        self.assertEqual(self.logger.event_count, 1501)

        # Latest events should be preserved
        last_event = self.logger.event_history[-1]
        self.assertIn('Event 1499', last_event['data']['message'])


class TestConvenienceMethods(unittest.TestCase):
    """Test convenience logging methods"""

    def setUp(self):
        """Create logger for each test"""
        self.logger = SF2DebugLogger(console_output=False)

    def test_log_keypress_logs_correct_data(self):
        """Test 3.1: log_keypress() logs correct data"""
        self.logger.log_keypress('Enter', ['Ctrl'], 'MainWindow')

        event = self.logger.event_history[-1]
        self.assertEqual(event['event_type'], 'keypress')
        self.assertEqual(event['data']['key'], 'Enter')
        self.assertEqual(event['data']['modifiers'], ['Ctrl'])
        self.assertEqual(event['data']['widget'], 'MainWindow')

    def test_log_file_load_logs_all_stages(self):
        """Test 3.2: log_file_load() logs all stages"""
        filepath = 'test.sf2'

        # Start
        self.logger.log_file_load(filepath, 'start', {
            'file_size_bytes': 10892
        })
        event1 = self.logger.event_history[-1]
        self.assertEqual(event1['event_type'], 'file_load_start')
        self.assertEqual(event1['data']['file_size_bytes'], 10892)

        # Complete
        self.logger.log_file_load(filepath, 'complete', {
            'total_time_ms': 156
        })
        event2 = self.logger.event_history[-1]
        self.assertEqual(event2['event_type'], 'file_load_complete')
        self.assertEqual(event2['data']['total_time_ms'], 156)

        # Error
        self.logger.log_file_load(filepath, 'error', {
            'error': 'Invalid file'
        })
        event3 = self.logger.event_history[-1]
        self.assertEqual(event3['event_type'], 'file_load_error')
        self.assertEqual(event3['data']['error'], 'Invalid file')

    def test_log_playback_logs_all_actions(self):
        """Test 3.3: log_playback() logs all actions"""
        # Start
        self.logger.log_playback('start')
        event = self.logger.event_history[-1]
        self.assertEqual(event['event_type'], 'playback_start')

        # Position with metrics
        self.logger.log_playback('position', position_ms=5000, duration_ms=30000)
        event = self.logger.event_history[-1]
        self.assertEqual(event['event_type'], 'playback_position')
        self.assertEqual(event['data']['position_ms'], 5000)
        self.assertEqual(event['data']['duration_ms'], 30000)
        self.assertAlmostEqual(event['data']['progress_percent'], 16.67, places=1)

        # Stop
        self.logger.log_playback('stop')
        event = self.logger.event_history[-1]
        self.assertEqual(event['event_type'], 'playback_stop')

    def test_log_music_state_logs_playing_stopped(self):
        """Test 3.4: log_music_state() logs playing/stopped"""
        # Playing
        self.logger.log_music_state(True, {'file': 'test.sf2'})
        event = self.logger.event_history[-1]
        self.assertEqual(event['event_type'], 'music_playing')
        self.assertTrue(event['data']['playing'])

        # Stopped
        self.logger.log_music_state(False, {'state': 'STOPPED'})
        event = self.logger.event_history[-1]
        self.assertEqual(event['event_type'], 'music_stopped')
        self.assertFalse(event['data']['playing'])

    def test_log_action_logs_generic_actions(self):
        """Test 3.5: log_action() logs generic actions"""
        self.logger.log_action("Generic action", {
            'detail1': 'value1',
            'detail2': 42
        })

        event = self.logger.event_history[-1]
        self.assertEqual(event['event_type'], 'action')
        self.assertEqual(event['data']['message'], 'Generic action')
        self.assertEqual(event['data']['detail1'], 'value1')
        self.assertEqual(event['data']['detail2'], 42)


class TestMetricsAndSummary(unittest.TestCase):
    """Test metrics and summary functionality"""

    def setUp(self):
        """Create logger for each test"""
        self.logger = SF2DebugLogger(console_output=False)

    def test_get_event_summary_returns_correct_counts(self):
        """Test 4.1: get_event_summary() returns correct counts"""
        # Generate various events
        self.logger.log_action("Action 1")
        self.logger.log_file_load("test.sf2", "start")
        self.logger.log_playback("start")

        summary = self.logger.get_event_summary()

        self.assertIn('total_events', summary)
        self.assertIn('elapsed_seconds', summary)
        self.assertIn('events_per_second', summary)
        self.assertIn('event_types', summary)
        self.assertIn('recent_events', summary)

        self.assertGreater(summary['total_events'], 0)
        self.assertEqual(len(summary['recent_events']), min(10, summary['total_events']))

    def test_event_throughput_calculates_correctly(self):
        """Test 4.2: Event throughput calculates correctly"""
        # Generate some events
        for i in range(100):
            self.logger.log_action(f"Action {i}")

        summary = self.logger.get_event_summary()
        throughput = summary['events_per_second']

        # FIX: Adjusted threshold for fast systems (logger can do >100K events/sec!)
        self.assertGreater(throughput, 0)
        self.assertLess(throughput, 200000)  # Allow for very fast systems

    def test_event_type_distribution_is_accurate(self):
        """Test 4.3: Event type distribution is accurate"""
        # Generate known distribution
        for i in range(10):
            self.logger.log_action(f"Action {i}")
        for i in range(5):
            self.logger.log_file_load(f"file{i}.sf2", "start")

        summary = self.logger.get_event_summary()
        event_types = summary['event_types']

        self.assertEqual(event_types.get('action', 0), 10)
        self.assertEqual(event_types.get('file_load_start', 0), 5)

    def test_dump_event_history_creates_valid_json(self):
        """Test 4.4: dump_event_history() creates valid JSON"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json_file = f.name

        try:
            # Generate some events
            for i in range(50):
                self.logger.log_action(f"Action {i}")

            # Get event count before dump (dump creates an extra event)
            events_before_dump = len(self.logger.event_history)

            # Dump to JSON
            self.logger.dump_event_history(json_file)

            # Validate JSON
            self.assertTrue(os.path.exists(json_file))
            with open(json_file, 'r') as f:
                data = json.load(f)

            self.assertIn('summary', data)
            self.assertIn('events', data)
            # FIX: Account for dump creating an event
            self.assertGreaterEqual(len(data['events']), events_before_dump)
            self.assertLessEqual(len(data['events']), events_before_dump + 1)
        finally:
            if os.path.exists(json_file):
                os.unlink(json_file)

    def test_recent_events_list_limited_to_10(self):
        """Test 4.5: Recent events list limited to 10"""
        # Generate 50 events
        for i in range(50):
            self.logger.log_action(f"Action {i}")

        summary = self.logger.get_event_summary()
        recent = summary['recent_events']

        self.assertEqual(len(recent), 10)
        # Should be the last 10 events
        self.assertIn('Action 49', recent[-1]['data']['message'])


def run_unit_tests():
    """Run all unit tests and return results"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSF2LoggerInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestEventLogging))
    suite.addTests(loader.loadTestsFromTestCase(TestConvenienceMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestMetricsAndSummary))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    print("=" * 70)
    print("SF2 Debug Logger - Unit Tests")
    print("=" * 70)
    print()

    result = run_unit_tests()

    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print()

    if result.wasSuccessful():
        print("✅ ALL UNIT TESTS PASSED!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
