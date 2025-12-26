# SF2 Logging Testing Plan - Ultra-Think Approach

**Version**: 1.0.0
**Date**: 2025-12-26
**Status**: 🎯 Comprehensive Test Strategy
**Test Subject**: SF2 Debug Logging System
**Test File**: Stinsens_Last_Night_of_89.sf2

---

## Executive Summary - Ultra-Think Analysis

**Testing Philosophy**: Comprehensive validation of logging infrastructure through:
1. **Unit Tests** - Individual logging functions
2. **Integration Tests** - GUI + Logging interactions
3. **End-to-End Tests** - Complete user workflows
4. **Output Validation** - Log file structure and content
5. **Performance Tests** - Overhead and throughput measurement

**Success Criteria**:
- ✅ All events logged correctly with accurate data
- ✅ Timing metrics within expected ranges
- ✅ JSON output valid and parseable
- ✅ No logging errors or exceptions
- ✅ Performance overhead < 30% in ultra-verbose mode

---

## Table of Contents

1. [Test Architecture](#test-architecture)
2. [Test Categories](#test-categories)
3. [Test Environment](#test-environment)
4. [Test Cases](#test-cases)
5. [Validation Criteria](#validation-criteria)
6. [Test Execution Plan](#test-execution-plan)
7. [Expected Results](#expected-results)

---

## Test Architecture

### Testing Pyramid

```
                    ┌─────────────────┐
                    │   E2E Tests     │  ← Full workflows (3 tests)
                    │  (Slow, Few)    │
                    └─────────────────┘
                  ┌───────────────────────┐
                  │  Integration Tests    │  ← GUI + Logging (10 tests)
                  │   (Medium Speed)      │
                  └───────────────────────┘
              ┌─────────────────────────────────┐
              │       Unit Tests                │  ← Individual functions (20 tests)
              │      (Fast, Many)               │
              └─────────────────────────────────┘
```

### Test Components

```
┌──────────────────────────────────────────────────────────────┐
│                    SF2 Logging Test Suite                     │
│                                                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │  Unit Tests    │  │ Integration    │  │   E2E Tests    │ │
│  │                │  │    Tests       │  │                │ │
│  │ • Logger init  │  │ • GUI events   │  │ • Full load    │ │
│  │ • Event types  │  │ • File load    │  │ • Playback     │ │
│  │ • Formatting   │  │ • Playback     │  │ • Error flows  │ │
│  │ • Metrics      │  │ • Errors       │  │                │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           Log Output Validation                        │  │
│  │                                                         │  │
│  │  • Console output parsing                             │  │
│  │  • File log validation                                │  │
│  │  • JSON structure validation                          │  │
│  │  • Event sequence verification                        │  │
│  │  • Timing metrics validation                          │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           Performance Tests                            │  │
│  │                                                         │  │
│  │  • Overhead measurement                               │  │
│  │  • Throughput testing                                 │  │
│  │  • Memory usage tracking                              │  │
│  │  • File size growth analysis                          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## Test Categories

### Category 1: Unit Tests (20 tests)

**Logger Initialization**:
- Test 1.1: Logger creates with default settings
- Test 1.2: Logger creates with custom settings
- Test 1.3: Ultra-verbose mode enables correctly
- Test 1.4: File handler creates log file
- Test 1.5: JSON handler creates JSON file

**Event Logging**:
- Test 2.1: log_event() creates correct structure
- Test 2.2: Event ID increments sequentially
- Test 2.3: Timestamp format is ISO 8601
- Test 2.4: Elapsed time calculates correctly
- Test 2.5: Event history stores last 1000 events

**Convenience Methods**:
- Test 3.1: log_keypress() logs correct data
- Test 3.2: log_file_load() logs all stages
- Test 3.3: log_playback() logs all actions
- Test 3.4: log_music_state() logs playing/stopped
- Test 3.5: log_action() logs generic actions

**Metrics & Summary**:
- Test 4.1: get_event_summary() returns correct counts
- Test 4.2: Event throughput calculates correctly
- Test 4.3: Event type distribution is accurate
- Test 4.4: dump_event_history() creates valid JSON
- Test 4.5: Recent events list limited to 10

### Category 2: Integration Tests (10 tests)

**GUI + Logging Integration**:
- Test 5.1: SF2 Viewer initializes with logging
- Test 5.2: File browse logs dialog open/close
- Test 5.3: File load logs complete sequence
- Test 5.4: File load error logs exception details
- Test 5.5: Tab change logs (planned)

**File Operations**:
- Test 6.1: Load valid SF2 → logs start/complete
- Test 6.2: Load invalid SF2 → logs error
- Test 6.3: Parse timing metrics within range
- Test 6.4: File size logged correctly
- Test 6.5: UI update timing tracked

### Category 3: E2E Tests (3 tests)

**Complete Workflows**:
- Test 7.1: Load Stinsens SF2 → Verify event sequence
- Test 7.2: Load → Play → Stop → Verify all events
- Test 7.3: Multiple file loads → Verify history

### Category 4: Output Validation (8 tests)

**Log File Validation**:
- Test 8.1: Console output contains all events
- Test 8.2: File log contains timestamps
- Test 8.3: JSON output is valid JSON
- Test 8.4: JSON events have all required fields
- Test 8.5: Event sequence matches expected order

**Data Validation**:
- Test 9.1: File size metrics accurate (±10%)
- Test 9.2: Parse time reasonable (< 1 second)
- Test 9.3: Event IDs sequential without gaps
- Test 9.4: No duplicate events

### Category 5: Performance Tests (4 tests)

**Overhead Measurement**:
- Test 10.1: INFO mode overhead < 10%
- Test 10.2: DEBUG mode overhead < 15%
- Test 10.3: ULTRAVERBOSE overhead < 30%
- Test 10.4: Log file size within expected range

---

## Test Environment

### Test Files

```
Primary Test File:
  ./output/keep_Stinsens_Last_Night_of_89/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2
  - Size: ~10.6 KB
  - Type: Laxity NP21 converted to SF2
  - Expected blocks: 6
  - Expected tables: 6

Secondary Test Files:
  ./experiments/metadata_fix_test/Stinsens_FINAL.sf2
  - For validation comparison

Invalid Test File:
  Create invalid.sf2 (corrupted magic number)
  - For error testing
```

### Environment Variables

```bash
# Test configurations
SF2_ULTRAVERBOSE=0|1
SF2_DEBUG_LOG=test_output/sf2_test.log
SF2_JSON_LOG=0|1
```

### Output Directories

```
test_output/
├── logs/
│   ├── sf2_test_info.log
│   ├── sf2_test_debug.log
│   ├── sf2_test_ultraverbose.log
│   └── sf2_test.json
├── reports/
│   ├── test_results.json
│   ├── test_summary.txt
│   └── performance_metrics.csv
└── artifacts/
    ├── event_history.json
    └── screenshots/ (if GUI tests fail)
```

---

## Test Cases

### Test Case 1: Logger Initialization

**Objective**: Verify logger initializes correctly with all configurations

**Steps**:
1. Import sf2_debug_logger
2. Call configure_sf2_logger() with various settings
3. Verify logger instance created
4. Check handlers attached
5. Verify initial event logged

**Expected Results**:
- Logger instance not None
- Console handler present
- File handler present (if log_file specified)
- JSON handler present (if json_log=True)
- Initial "SF2 Debug Logger initialized" event in history

**Validation**:
```python
logger = configure_sf2_logger(level=logging.DEBUG, log_file='test.log', json_log=True)
assert logger is not None
assert len(logger.logger.handlers) >= 1  # Console handler
assert logger.event_count >= 1  # Initial event
assert logger.event_history[0]['event_type'] == 'state_change'
```

---

### Test Case 2: File Load Event Sequence

**Objective**: Verify complete file load logs all expected events

**Steps**:
1. Set SF2_DEBUG_LOG=test_output/file_load_test.log
2. Launch SF2 Viewer
3. Load Stinsens_Last_Night_of_89.sf2
4. Wait for load to complete
5. Capture log output
6. Validate event sequence

**Expected Event Sequence**:
```
1. [action] SF2 Viewer GUI initialized
2. [file_load_start] File load start: Stinsens_Last_Night_of_89.sf2
3. [action] Starting SF2 file parsing
4. [action] SF2 file parsed successfully
5. [action] Updating UI tabs
6. [action] UI tabs updated
7. [action] Playback enabled
8. [file_load_complete] File load complete: Stinsens_Last_Night_of_89.sf2
```

**Validation Criteria**:
- All 8 events present in order
- file_load_start has file_size_bytes field
- parse_time_ms > 0 and < 1000
- ui_update_time_ms > 0 and < 2000
- total_time_ms = parse_time_ms + ui_update_time_ms (±50ms)
- magic_id = '0x1337'

---

### Test Case 3: Playback Event Sequence

**Objective**: Verify playback lifecycle logs correctly

**Steps**:
1. Load Stinsens SF2 file
2. Click "Play Full Song" button
3. Wait 5 seconds
4. Click "Stop" button
5. Validate events

**Expected Event Sequence**:
```
1. [action] Play button clicked
2. [playback_start] Playback start
3. [music_playing] Music state: PLAYING
4. [playback_position] Position updates (every 5s or ultraverbose)
5. [action] Stop button clicked
6. [playback_stop] Playback stop
7. [music_stopped] Music state: STOPPED
```

**Validation Criteria**:
- Playback start has 'file' field
- Music state transitions: PLAYING → STOPPED
- Position events have position_ms, duration_ms, progress_percent
- Stop event logged after button click

---

### Test Case 4: Error Handling

**Objective**: Verify errors log correctly with details

**Steps**:
1. Create invalid.sf2 (corrupted file)
2. Attempt to load invalid.sf2
3. Capture error events

**Expected Event Sequence**:
```
1. [file_load_start] File load start: invalid.sf2
2. [file_load_error] File load error: invalid.sf2
   - error: "Invalid magic ID" or exception message
   - exception_type: "ValueError" or similar
   - elapsed_ms: time to detect error
```

**Validation Criteria**:
- Error event logged
- Exception type captured
- Error message descriptive
- No crash or unhandled exception

---

### Test Case 5: JSON Output Validation

**Objective**: Verify JSON log output is valid and complete

**Steps**:
1. Set SF2_JSON_LOG=1
2. Perform file load
3. Read JSON log file
4. Validate structure

**Expected JSON Structure**:
```json
{
  "event_id": 1,
  "timestamp": "2025-12-26T10:30:45.123456",
  "elapsed_ms": 1523,
  "event_type": "file_load_start",
  "data": {
    "message": "File load start: Stinsens_Last_Night_of_89.sf2",
    "filepath": "...",
    "file_size_bytes": 10892,
    "file_size_kb": 10.636
  }
}
```

**Validation Criteria**:
- Valid JSON (json.loads() succeeds)
- Each line is complete JSON object
- All required fields present
- Timestamp is ISO 8601
- event_id increments sequentially
- data dictionary contains message

---

### Test Case 6: Performance Overhead

**Objective**: Measure logging overhead in different modes

**Steps**:
1. Load Stinsens file WITHOUT logging (baseline)
2. Measure time: T_baseline
3. Load Stinsens file WITH INFO logging
4. Measure time: T_info
5. Load Stinsens file WITH ULTRAVERBOSE logging
6. Measure time: T_ultraverbose
7. Calculate overhead

**Expected Results**:
```
Baseline:      T_baseline = ~150ms
INFO mode:     T_info = ~165ms (overhead: ~10%)
DEBUG mode:    T_debug = ~180ms (overhead: ~20%)
ULTRAVERBOSE:  T_ultraverbose = ~200ms (overhead: ~30%)
```

**Validation Criteria**:
- INFO overhead < 15%
- DEBUG overhead < 25%
- ULTRAVERBOSE overhead < 35%
- No memory leaks (event history capped at 1000)

---

### Test Case 7: Event History Management

**Objective**: Verify event history maintains 1000 event limit

**Steps**:
1. Generate 1500 events (load/unload files repeatedly)
2. Check event_history length
3. Verify oldest events removed
4. Dump event history to JSON

**Expected Results**:
- event_history length = 1000 (not 1500)
- Latest events preserved
- Oldest 500 events removed
- event_id continues incrementing (1, 2, 3, ... 1500)
- JSON dump contains 1000 events

**Validation Criteria**:
- len(event_history) <= 1000
- event_history[-1]['event_id'] = latest event ID
- No gaps in recent event IDs

---

## Validation Criteria

### Event Structure Validation

Each event MUST contain:
```python
{
    'event_id': int,           # Sequential, positive
    'timestamp': str,          # ISO 8601 format
    'elapsed_ms': int,         # Milliseconds since logger init
    'event_type': str,         # Valid SF2EventType value
    'data': {
        'message': str,        # Human-readable message
        # ... type-specific fields
    }
}
```

### Timing Validation

Expected timing ranges for Stinsens file (~10.6 KB):
- Parse time: 10-100ms (typical: 40ms)
- UI update time: 50-200ms (typical: 100ms)
- Total load time: 100-500ms (typical: 150ms)

### File Size Validation

Expected file sizes for 1-minute session:
- INFO log: 5-20 KB
- DEBUG log: 20-100 KB
- ULTRAVERBOSE log: 100-1000 KB
- JSON log: 10-50 KB

---

## Test Execution Plan

### Phase 1: Unit Tests (5 minutes)

```bash
# Run unit tests
python pyscript/test_sf2_logger_unit.py -v

# Expected: 20/20 tests pass
```

### Phase 2: Integration Tests (10 minutes)

```bash
# Run GUI integration tests
python pyscript/test_sf2_viewer_logging.py -v

# Expected: 10/10 tests pass
```

### Phase 3: E2E Tests (5 minutes)

```bash
# Run end-to-end workflow tests
python pyscript/test_sf2_logging_e2e.py -v

# Expected: 3/3 tests pass
```

### Phase 4: Output Validation (5 minutes)

```bash
# Validate log output
python pyscript/test_log_output_validation.py -v

# Expected: 8/8 tests pass
```

### Phase 5: Performance Tests (10 minutes)

```bash
# Run performance benchmarks
python pyscript/test_sf2_logging_performance.py -v

# Expected: 4/4 tests pass, overhead < 30%
```

### Phase 6: Generate Report (2 minutes)

```bash
# Generate comprehensive test report
python pyscript/generate_test_report.py

# Output: test_output/reports/test_summary.txt
```

**Total Execution Time**: ~40 minutes (all tests)

---

## Expected Results

### Test Success Criteria

**Unit Tests**:
- ✅ 20/20 tests pass
- ✅ 100% code coverage for sf2_debug_logger.py

**Integration Tests**:
- ✅ 10/10 tests pass
- ✅ All events logged correctly
- ✅ No exceptions raised

**E2E Tests**:
- ✅ 3/3 workflows complete successfully
- ✅ Event sequences match expected
- ✅ Timing metrics within range

**Output Validation**:
- ✅ 8/8 validation tests pass
- ✅ JSON output valid
- ✅ Event sequence correct

**Performance Tests**:
- ✅ 4/4 tests pass
- ✅ Overhead < 30% in ultraverbose
- ✅ Memory usage stable

### Test Report Format

```
┌─────────────────────────────────────────────────────────────┐
│          SF2 Logging Test Report                            │
│          Date: 2025-12-26 10:30:45                          │
│          Test File: Stinsens_Last_Night_of_89.sf2           │
├─────────────────────────────────────────────────────────────┤
│ Test Category          │ Pass │ Fail │ Total │ Pass Rate   │
├────────────────────────┼──────┼──────┼───────┼─────────────┤
│ Unit Tests             │  20  │  0   │  20   │ 100%        │
│ Integration Tests      │  10  │  0   │  10   │ 100%        │
│ E2E Tests              │   3  │  0   │   3   │ 100%        │
│ Output Validation      │   8  │  0   │   8   │ 100%        │
│ Performance Tests      │   4  │  0   │   4   │ 100%        │
├────────────────────────┼──────┼──────┼───────┼─────────────┤
│ TOTAL                  │  45  │  0   │  45   │ 100% ✅     │
└─────────────────────────────────────────────────────────────┘

Performance Metrics:
  - INFO mode overhead:       8.5% ✅
  - DEBUG mode overhead:      12.3% ✅
  - ULTRAVERBOSE overhead:    24.7% ✅
  - Event throughput:         15.3 events/sec
  - Log file size (1 min):    45 KB

Event Statistics:
  - Total events logged:      156
  - file_load events:         2 (start, complete)
  - playback events:          8
  - action events:            42
  - Event history size:       156 (< 1000 limit)

Validation Results:
  - JSON output valid:        ✅
  - Event sequence correct:   ✅
  - Timing metrics valid:     ✅
  - No errors or exceptions:  ✅

OVERALL STATUS: ✅ ALL TESTS PASSED
```

---

## Test Artifacts

### Generated Files

```
test_output/
├── logs/
│   ├── sf2_test_info.log           (Console + INFO level)
│   ├── sf2_test_debug.log          (Console + DEBUG level)
│   ├── sf2_test_ultraverbose.log   (Console + ULTRAVERBOSE)
│   └── sf2_test.json               (JSON events)
├── reports/
│   ├── test_results.json           (Machine-readable results)
│   ├── test_summary.txt            (Human-readable summary)
│   ├── performance_metrics.csv     (Performance data)
│   └── event_timeline.html         (Visual event timeline)
└── artifacts/
    ├── event_history.json          (Exported event history)
    └── test_screenshots/           (GUI test screenshots)
```

---

## Conclusion

This comprehensive testing plan validates the SF2 debug logging system through:
- ✅ **45 automated tests** across 5 categories
- ✅ **Real-world file testing** (Stinsens SF2)
- ✅ **Performance validation** (overhead < 30%)
- ✅ **Output validation** (JSON, log files)
- ✅ **Event sequence verification** (complete workflows)

**Next Steps**:
1. Implement automated test suite
2. Execute tests with Stinsens file
3. Validate results against criteria
4. Generate comprehensive report
5. Fix any issues found
6. Document final results

**Expected Outcome**: 100% test pass rate with all logging functionality verified ✅

---

**End of Testing Plan**

**Version**: 1.0.0
**Status**: 📋 Ready for Implementation
**Author**: Claude Sonnet 4.5 (Ultra-Think Mode)
