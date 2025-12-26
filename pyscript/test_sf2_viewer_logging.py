#!/usr/bin/env python3
"""
Automated Test for SF2 Viewer with Logging Enabled

Tests the complete logging system by launching SF2 Viewer,
loading a file, and validating all logging functionality.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

# Test configuration
TEST_SF2_FILE = "output/keep_Stinsens_Last_Night_of_89/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2"
TEST_LOG_FILE = "test_output/logs/sf2_viewer_test.log"
TEST_JSON_FILE = "test_output/logs/sf2_viewer_test.json"
TEST_DURATION = 10  # seconds

def setup_test_environment():
    """Set up test environment with logging enabled"""
    print("=" * 70)
    print("SF2 Viewer Logging Test - Automated")
    print("=" * 70)
    print()

    # Create test output directory
    os.makedirs("test_output/logs", exist_ok=True)

    # Clean up old log files
    for log_file in [TEST_LOG_FILE, TEST_JSON_FILE]:
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
                print(f"[OK] Cleaned up old log: {log_file}")
            except Exception as e:
                print(f"[WARN] Could not remove {log_file}: {e}")

    # Check if test file exists
    if not os.path.exists(TEST_SF2_FILE):
        print(f"[ERROR] Test file not found: {TEST_SF2_FILE}")
        print()
        print("Available SF2 files:")
        import glob
        sf2_files = glob.glob("output/**/*.sf2", recursive=True)
        for f in sf2_files[:10]:
            print(f"  - {f}")
        return None

    print(f"[OK] Test file found: {TEST_SF2_FILE}")
    file_size = os.path.getsize(TEST_SF2_FILE)
    print(f"  Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print()

    return TEST_SF2_FILE

def run_sf2_viewer_test(sf2_file):
    """Run SF2 Viewer with logging enabled"""
    print("Starting SF2 Viewer with ultra-verbose logging...")
    print(f"Duration: {TEST_DURATION} seconds")
    print()

    # Set up environment variables for logging
    env = os.environ.copy()
    env['SF2_ULTRAVERBOSE'] = '1'
    env['SF2_DEBUG_LOG'] = TEST_LOG_FILE
    env['SF2_JSON_LOG'] = '1'

    print("Environment variables:")
    print(f"  SF2_ULTRAVERBOSE = 1")
    print(f"  SF2_DEBUG_LOG = {TEST_LOG_FILE}")
    print(f"  SF2_JSON_LOG = 1")
    print()

    # Launch SF2 Viewer
    cmd = [
        sys.executable,
        "pyscript/sf2_viewer_gui.py",
        sf2_file
    ]

    print(f"Command: {' '.join(cmd)}")
    print()
    print("Launching SF2 Viewer...")

    try:
        # Start process
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"[OK] Process started (PID: {process.pid})")
        print(f"  Waiting {TEST_DURATION} seconds...")

        # Wait for test duration
        time.sleep(TEST_DURATION)

        # Terminate process
        print("  Terminating process...")
        process.terminate()

        # Wait for process to end
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

        print(f"[OK] Process terminated")
        print()

        return True

    except Exception as e:
        print(f"[ERROR] Failed to run SF2 Viewer: {e}")
        return False

def validate_log_files():
    """Validate that log files were created and contain expected content"""
    print("=" * 70)
    print("Validating Log Files")
    print("=" * 70)
    print()

    results = {
        'log_file_created': False,
        'json_file_created': False,
        'log_file_size': 0,
        'json_file_size': 0,
        'log_events_found': 0,
        'json_events_found': 0,
        'event_types': set()
    }

    # Check text log file
    if os.path.exists(TEST_LOG_FILE):
        results['log_file_created'] = True
        results['log_file_size'] = os.path.getsize(TEST_LOG_FILE)
        print(f"[OK] Text log file created: {TEST_LOG_FILE}")
        print(f"  Size: {results['log_file_size']:,} bytes")

        # Count events in log file
        with open(TEST_LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            results['log_events_found'] = len(lines)

            # Show first few lines
            print(f"  Events: {len(lines)} log lines")
            print()
            print("  First 5 log entries:")
            for line in lines[:5]:
                print(f"    {line.strip()}")
    else:
        print(f"[FAIL] Text log file NOT created: {TEST_LOG_FILE}")

    print()

    # Check JSON log file
    if os.path.exists(TEST_JSON_FILE):
        results['json_file_created'] = True
        results['json_file_size'] = os.path.getsize(TEST_JSON_FILE)
        print(f"[OK] JSON log file created: {TEST_JSON_FILE}")
        print(f"  Size: {results['json_file_size']:,} bytes")

        # Parse JSON events
        with open(TEST_JSON_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            results['json_events_found'] = len(lines)

            print(f"  Events: {len(lines)} JSON events")
            print()

            # Parse and categorize events
            event_types = {}
            for line in lines:
                try:
                    event = json.loads(line)
                    event_type = event.get('event_type', 'unknown')
                    results['event_types'].add(event_type)
                    event_types[event_type] = event_types.get(event_type, 0) + 1
                except json.JSONDecodeError:
                    pass

            print("  Event Type Distribution:")
            for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
                print(f"    {event_type:30s}: {count:4d} events")

            print()
            print("  Sample Events:")
            for i, line in enumerate(lines[:3]):
                try:
                    event = json.loads(line)
                    print(f"    Event {i+1}:")
                    print(f"      Type: {event.get('event_type')}")
                    print(f"      Time: {event.get('timestamp')}")
                    print(f"      Message: {event.get('data', {}).get('message', 'N/A')}")
                except json.JSONDecodeError:
                    pass
    else:
        print(f"[FAIL] JSON log file NOT created: {TEST_JSON_FILE}")

    print()
    return results

def generate_test_report(results):
    """Generate test report"""
    print("=" * 70)
    print("Test Report")
    print("=" * 70)
    print()

    # Overall status
    success_criteria = [
        results['log_file_created'],
        results['json_file_created'],
        results['log_events_found'] > 10,
        results['json_events_found'] > 10,
        len(results['event_types']) >= 5
    ]

    passed = sum(success_criteria)
    total = len(success_criteria)
    success_rate = (passed / total) * 100

    print(f"Overall Status: {passed}/{total} criteria passed ({success_rate:.0f}%)")
    print()

    # Detailed results
    print("Criteria:")
    print(f"  [{'PASS' if results['log_file_created'] else 'FAIL'}] Text log file created")
    print(f"  [{'PASS' if results['json_file_created'] else 'FAIL'}] JSON log file created")
    print(f"  [{'PASS' if results['log_events_found'] > 10 else 'FAIL'}] Text log has events (>10)")
    print(f"  [{'PASS' if results['json_events_found'] > 10 else 'FAIL'}] JSON log has events (>10)")
    print(f"  [{'PASS' if len(results['event_types']) >= 5 else 'FAIL'}] Multiple event types logged (>=5)")
    print()

    print("Statistics:")
    print(f"  Text log size: {results['log_file_size']:,} bytes")
    print(f"  JSON log size: {results['json_file_size']:,} bytes")
    print(f"  Text log events: {results['log_events_found']}")
    print(f"  JSON log events: {results['json_events_found']}")
    print(f"  Event types: {len(results['event_types'])}")
    print()

    print("Event Types Logged:")
    for event_type in sorted(results['event_types']):
        print(f"  - {event_type}")
    print()

    # Final verdict
    if success_rate == 100:
        print("[PASS] TEST PASSED - All logging functionality working correctly!")
    elif success_rate >= 80:
        print("[WARN] TEST MOSTLY PASSED - Some minor issues detected")
    else:
        print("[FAIL] TEST FAILED - Logging system not working correctly")

    print()
    return success_rate == 100

def main():
    """Main test function"""
    # Setup
    sf2_file = setup_test_environment()
    if not sf2_file:
        sys.exit(1)

    # Run test
    if not run_sf2_viewer_test(sf2_file):
        print("[FAIL] Test failed: Could not run SF2 Viewer")
        sys.exit(1)

    # Give logs time to flush
    time.sleep(1)

    # Validate
    results = validate_log_files()

    # Report
    success = generate_test_report(results)

    # Exit
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
