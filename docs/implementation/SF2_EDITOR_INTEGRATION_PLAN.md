# SF2 Editor Integration - Ultra-Think Implementation Plan

**Version**: 1.0.0
**Date**: 2025-12-26
**Status**: 🎯 Comprehensive Implementation Strategy
**Scope**: Full SF2 Editor automation with conversion pipeline integration

---

## Executive Summary - Ultra-Think Analysis

**Vision**: Complete SF2 validation and conversion pipeline with SID Factory II editor automation

**Key Objectives**:
1. ✅ Automate SF2 Editor operations (load, play, stop, pack, exit)
2. ✅ Integrate editor validation into conversion pipeline
3. ✅ Add comprehensive logging for all editor operations
4. ✅ Enable SF2→SID packing via editor (alternative to sf2_packer.py)
5. ✅ Verify SF2 files work correctly in the actual editor

**Benefits**:
- 🔍 **Validation**: Confirm SF2 files load in actual editor
- 🎵 **Playback Testing**: Verify audio plays correctly
- 📦 **Editor Packing**: Use editor's native packing (100% accurate)
- 🐛 **Bug Detection**: Catch editor-specific issues early
- 📊 **Pipeline Metrics**: Track editor performance and success rates

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                SF2 Editor Integration Architecture              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Conversion Pipeline (Enhanced)                   │  │
│  │                                                           │  │
│  │  1. SID → SF2 Conversion                                │  │
│  │  2. SF2 Structure Validation                            │  │
│  │  3. ⭐ SF2 Editor Validation (NEW)                      │  │
│  │     ├─ Load in editor                                   │  │
│  │     ├─ Verify tables display                            │  │
│  │     ├─ Test playback                                    │  │
│  │     └─ Exit cleanly                                     │  │
│  │  4. SF2 → SID Packing                                   │  │
│  │     ├─ Python packer (existing)                         │  │
│  │     └─ ⭐ Editor packer (NEW, alternative)             │  │
│  │  5. SID Validation                                      │  │
│  │  6. Audio Rendering                                     │  │
│  │  7. Accuracy Metrics                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         SF2 Editor Automation Module                     │  │
│  │                                                           │  │
│  │  Class: SF2EditorAutomation                             │  │
│  │  • launch_editor(sf2_path)                              │  │
│  │  • wait_for_load()                                      │  │
│  │  • verify_tables()                                      │  │
│  │  • start_playback()                                     │  │
│  │  • stop_playback()                                      │  │
│  │  • pack_to_sid(output_path)                            │  │
│  │  • close_editor()                                       │  │
│  │  • get_editor_state()                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Logging Integration                              │  │
│  │                                                           │  │
│  │  • SF2EventType.EDITOR_LAUNCH                           │  │
│  │  • SF2EventType.EDITOR_LOAD_COMPLETE                    │  │
│  │  • SF2EventType.EDITOR_PLAYBACK_START                   │  │
│  │  • SF2EventType.EDITOR_PLAYBACK_STOP                    │  │
│  │  • SF2EventType.EDITOR_PACK_START                       │  │
│  │  • SF2EventType.EDITOR_PACK_COMPLETE                    │  │
│  │  • SF2EventType.EDITOR_EXIT                             │  │
│  │  • SF2EventType.EDITOR_ERROR                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Enhanced Logging Foundation (2 hours)

**1.1 Complete Playback Logging** ✅
- File: `pyscript/sf2_playback.py`
- Add logging to all playback methods
- Track SF2→SID→WAV conversion steps
- Log external tool invocations (SID2WAV.EXE)
- Track playback state changes

**1.2 Add Keypress/Mouse Event Logging** ✅
- File: `pyscript/sf2_viewer_gui.py`
- Override `keyPressEvent()` method
- Override `mousePressEvent()` method
- Log tab changes
- Log button clicks

**1.3 Add New Event Types** ✅
- File: `sidm2/sf2_debug_logger.py`
- Add EDITOR_* event types (8 new types)
- Add KEYPRESS, MOUSE_CLICK, TAB_CHANGE types
- Add convenience methods for editor logging

---

### Phase 2: SF2 Editor Automation (4 hours)

**2.1 Create Automation Module**
- File: `sidm2/sf2_editor_automation.py` (NEW - 500 lines)
- Class: `SF2EditorAutomation`
- Methods:
  - `launch_editor(sf2_path, timeout=30)` - Launch editor with file
  - `wait_for_load(timeout=10)` - Wait for file to load
  - `is_editor_running()` - Check if editor process exists
  - `get_window_handle()` - Get editor window handle (Windows API)
  - `close_editor(force=False)` - Close editor cleanly
  - `kill_editor()` - Force kill if needed

**2.2 Process Management**
- Use `subprocess.Popen()` for launch
- Use `psutil` for process monitoring
- Track PID and window handles
- Implement timeout handling
- Add process cleanup on exit

**2.3 Window Detection**
- Use Windows API (`win32gui`, `win32process`)
- Find window by title ("SID Factory II" or "SIDFactoryII")
- Verify window is responsive
- Handle multiple instances

---

### Phase 3: Editor State Detection (3 hours)

**3.1 File Load Detection**
- Method: `wait_for_load()`
- Check window title for filename
- Monitor process stability (not crashing)
- Timeout after 10 seconds
- Return success/failure

**3.2 Playback Detection**
- Method: `is_playing()`
- Check for music playing (tricky - need heuristics)
- Options:
  - Monitor audio output (pyaudio)
  - Check process CPU usage (increases when playing)
  - Use timer (if playback started, assume playing for duration)

**3.3 Error Detection**
- Method: `check_for_errors()`
- Look for error dialogs
- Monitor crash/exit
- Check logs if editor creates them

---

### Phase 4: Playback Control (2 hours)

**4.1 Start Playback**
- Method: `start_playback()`
- Send keyboard shortcut (Space or Enter)
- Use Windows API `SendMessage()` or `PostMessage()`
- Alternatives:
  - `pyautogui` for keyboard automation
  - `pynput` for keyboard control
- Wait for playback to start
- Return success/failure

**4.2 Stop Playback**
- Method: `stop_playback()`
- Send stop shortcut (Space or ESC)
- Verify playback stopped
- Return success/failure

**4.3 Position Tracking**
- Method: `get_playback_position()` (optional)
- If editor exposes position, track it
- Otherwise, use timer-based estimation

---

### Phase 5: SF2→SID Packing via Editor (3 hours)

**5.1 Export Menu Automation**
- Method: `pack_to_sid(output_path)`
- Navigate to File → Export menu
- Use keyboard shortcuts or GUI automation
- Handle file save dialog
- Wait for export to complete

**5.2 Command-Line Export (Alternative)**
- Check if editor supports command-line export
- Syntax: `SIDFactoryII.exe /export input.sf2 output.sid`
- If supported, use this (much easier!)
- Otherwise, use GUI automation

**5.3 Export Validation**
- Verify output SID file created
- Check file size > 0
- Validate PSID header
- Compare with Python packer output
- Log any differences

---

### Phase 6: Pipeline Integration (3 hours)

**6.1 Add Editor Validation Step**
- File: `scripts/complete_conversion_pipeline.py` (enhance)
- New step: "SF2 Editor Validation"
- Load SF2 in editor
- Verify no errors
- Optionally test playback
- Close editor
- Log results

**6.2 Add Editor Packing Option**
- File: `scripts/sid_to_sf2.py` (enhance)
- Add `--pack-method` flag: `python` or `editor`
- If `editor`: use editor packing instead of sf2_packer.py
- Compare outputs
- Log which method used

**6.3 Pipeline Configuration**
- File: `pipeline_config.json` (NEW)
- Enable/disable editor validation
- Configure timeouts
- Choose packing method
- Set editor path

---

### Phase 7: Comprehensive Logging (2 hours)

**7.1 Editor Event Logging**
- Log every editor operation:
  - Launch (with path, PID)
  - Load (with filename, load time)
  - Playback start/stop (with timestamps)
  - Pack (with input/output, duration)
  - Exit (with exit code)
  - Errors (with details)

**7.2 Performance Metrics**
- Track editor launch time
- Track file load time
- Track pack time
- Compare with Python methods
- Generate performance report

**7.3 Error Tracking**
- Track editor crashes
- Track load failures
- Track pack failures
- Generate error report
- Identify problematic files

---

## Technical Implementation Details

### Process Automation

**Launch Editor**:
```python
import subprocess
import psutil
import time

class SF2EditorAutomation:
    def __init__(self, editor_path="C:/Program Files/SIDFactoryII/SIDFactoryII.exe"):
        self.editor_path = editor_path
        self.process = None
        self.pid = None
        self.logger = get_sf2_logger()

    def launch_editor(self, sf2_path, timeout=30):
        """Launch editor with SF2 file"""
        start_time = time.time()

        self.logger.log_event(SF2EventType.EDITOR_LAUNCH, {
            'message': f'Launching SF2 Editor: {sf2_path}',
            'editor_path': self.editor_path,
            'sf2_file': sf2_path
        })

        try:
            # Launch editor with file
            self.process = subprocess.Popen(
                [self.editor_path, sf2_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.pid = self.process.pid

            # Wait for window to appear
            success = self.wait_for_window(timeout)

            launch_time = time.time() - start_time

            if success:
                self.logger.log_event(SF2EventType.EDITOR_LOAD_COMPLETE, {
                    'message': f'Editor loaded: {sf2_path}',
                    'pid': self.pid,
                    'launch_time_ms': int(launch_time * 1000)
                })
                return True
            else:
                self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                    'message': 'Editor failed to load',
                    'error': 'Window not found',
                    'timeout': timeout
                })
                return False

        except Exception as e:
            self.logger.log_event(SF2EventType.EDITOR_ERROR, {
                'message': f'Failed to launch editor: {e}',
                'exception': str(e)
            })
            return False
```

**Window Detection**:
```python
import win32gui
import win32process

def find_editor_window(self):
    """Find SF2 Editor window"""
    windows = []

    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "SID Factory II" in title or "SIDFactoryII" in title:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == self.pid:
                    results.append((hwnd, title))

    win32gui.EnumWindows(enum_callback, windows)
    return windows[0] if windows else None
```

**Playback Control**:
```python
import win32api
import win32con

def start_playback(self):
    """Start playback in editor"""
    self.logger.log_event(SF2EventType.EDITOR_PLAYBACK_START, {
        'message': 'Starting playback in editor'
    })

    hwnd = self.get_window_handle()
    if not hwnd:
        return False

    # Send Space key to start playback
    # VK_SPACE = 0x20
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, 0x20, 0)
    time.sleep(0.1)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, 0x20, 0)

    return True
```

---

## New Event Types

### Editor Events (8 new types)

```python
# Add to SF2EventType enum
EDITOR_LAUNCH = "editor_launch"
EDITOR_LOAD_COMPLETE = "editor_load_complete"
EDITOR_LOAD_ERROR = "editor_load_error"
EDITOR_PLAYBACK_START = "editor_playback_start"
EDITOR_PLAYBACK_STOP = "editor_playback_stop"
EDITOR_PACK_START = "editor_pack_start"
EDITOR_PACK_COMPLETE = "editor_pack_complete"
EDITOR_EXIT = "editor_exit"
EDITOR_ERROR = "editor_error"
```

### GUI Events (enhanced)

```python
# Add to SF2EventType enum
TAB_CHANGE = "tab_change"
WINDOW_FOCUS = "window_focus"
WINDOW_RESIZE = "window_resize"
```

---

## Pipeline Integration

### Enhanced Conversion Pipeline

```
Step 1:  SID → SF2 Conversion
         ↓
Step 2:  SF2 Structure Validation
         ↓
Step 3:  ⭐ SF2 Editor Validation (NEW)
         ├─ Launch editor
         ├─ Load SF2 file
         ├─ Verify tables display
         ├─ Test playback (optional)
         ├─ Stop playback
         └─ Close editor
         ↓
Step 4:  SF2 → SID Packing
         ├─ Option A: Python packer (fast)
         └─ Option B: ⭐ Editor packer (NEW, accurate)
         ↓
Step 5:  SID Validation
         ↓
Step 6:  Audio Rendering
         ↓
Step 7:  Accuracy Metrics
```

### Configuration Options

```json
{
  "pipeline": {
    "enable_editor_validation": true,
    "editor_validation_timeout": 30,
    "test_playback_in_editor": false,
    "packing_method": "python",  // or "editor"
    "editor_path": "C:/Program Files/SIDFactoryII/SIDFactoryII.exe"
  },
  "logging": {
    "log_editor_events": true,
    "log_keypress_events": false,
    "log_mouse_events": false
  }
}
```

---

## Testing Strategy

### Test Cases

**1. Editor Launch Test**
- Launch editor with Stinsens.sf2
- Verify window appears
- Verify PID tracked
- Close editor
- Verify clean exit

**2. File Load Test**
- Load valid SF2 → should succeed
- Load invalid SF2 → should fail gracefully
- Load corrupted SF2 → should detect error
- Track load times

**3. Playback Test**
- Start playback → verify plays
- Stop playback → verify stops
- Track playback duration
- Verify no crashes

**4. Packing Test**
- Pack SF2 → SID via editor
- Compare with Python packer output
- Verify file sizes similar
- Validate PSID headers match
- Test playback of both outputs

**5. Error Handling Test**
- Editor not found → graceful error
- File not found → graceful error
- Editor crashes → detect and report
- Timeout scenarios → handle correctly

---

## Performance Expectations

### Timing Benchmarks

| Operation | Expected Time | Acceptable Range |
|-----------|--------------|------------------|
| Editor launch | 2-5 seconds | < 10 seconds |
| File load | 0.5-2 seconds | < 5 seconds |
| Playback start | 0.1-0.5 seconds | < 2 seconds |
| Pack SF2→SID | 1-3 seconds | < 10 seconds |
| Editor close | 0.5-2 seconds | < 5 seconds |

### Success Criteria

- ✅ Editor launches successfully: >95%
- ✅ Files load correctly: >99%
- ✅ Playback works: >90%
- ✅ Packing succeeds: >95%
- ✅ No crashes: >99%

---

## Dependencies

### Python Packages

```bash
pip install psutil          # Process monitoring
pip install pywin32         # Windows API access
pip install pyautogui       # GUI automation (optional)
pip install pynput          # Keyboard/mouse control (optional)
```

### Windows API

- `win32gui` - Window management
- `win32process` - Process control
- `win32api` - Low-level API access
- `win32con` - Constants

---

## File Structure

### New Files

```
sidm2/
├── sf2_editor_automation.py        (NEW - 500 lines)
├── sf2_debug_logger.py             (ENHANCED - add event types)
└── pipeline_config.py              (NEW - 200 lines)

scripts/
├── complete_conversion_pipeline.py (ENHANCED - add editor step)
├── sid_to_sf2.py                   (ENHANCED - add pack method)
└── test_editor_automation.py       (NEW - 300 lines)

pyscript/
├── sf2_viewer_gui.py               (ENHANCED - add keypress/mouse)
└── sf2_playback.py                 (ENHANCED - complete logging)

docs/
└── implementation/
    └── SF2_EDITOR_INTEGRATION_PLAN.md (THIS FILE)
```

---

## Implementation Timeline

### Phase 1: Foundation (2 hours)
- ✅ Complete playback logging
- ✅ Add keypress/mouse events
- ✅ Add new event types

### Phase 2-3: Automation (7 hours)
- Create automation module
- Implement process management
- Add window detection
- Add state detection

### Phase 4-5: Control & Packing (5 hours)
- Implement playback control
- Add packing via editor
- Validate packing output

### Phase 6: Integration (3 hours)
- Add to conversion pipeline
- Create configuration system
- Add pipeline tests

### Phase 7: Testing (2 hours)
- Create test suite
- Run comprehensive tests
- Generate performance report

**Total Estimated Time**: 19 hours

---

## Risk Mitigation

### Risk 1: Editor Doesn't Support Command-Line

**Mitigation**: Fall back to GUI automation using pyautogui

### Risk 2: Window Detection Fails

**Mitigation**: Implement multiple detection methods (title, class name, PID)

### Risk 3: Playback Detection Unreliable

**Mitigation**: Use timer-based estimation, don't require perfect detection

### Risk 4: Editor Crashes During Automation

**Mitigation**: Implement robust error handling, cleanup processes, log crashes

### Risk 5: Performance Overhead Too High

**Mitigation**: Make editor validation optional, allow timeout configuration

---

## Success Metrics

### Functional Metrics

- ✅ Editor launches: 100% success rate
- ✅ Files load: 99% success rate
- ✅ Playback works: 90% success rate
- ✅ Packing succeeds: 95% success rate
- ✅ Clean exits: 99% success rate

### Performance Metrics

- ✅ Launch time: < 5 seconds average
- ✅ Load time: < 2 seconds average
- ✅ Pack time: < 3 seconds average
- ✅ Pipeline overhead: < 10 seconds per file

### Quality Metrics

- ✅ Editor packer matches Python packer: 100%
- ✅ No file corruption: 100%
- ✅ No crashes: >99%
- ✅ Comprehensive logging: 100% coverage

---

## Conclusion

This implementation plan provides a comprehensive strategy for integrating SID Factory II editor into the conversion pipeline with full automation and logging.

**Key Benefits**:
- 🔍 Real editor validation (not just Python validation)
- 📦 Alternative packing method (editor's native packer)
- 🐛 Early bug detection (editor-specific issues)
- 📊 Performance comparison (Python vs Editor)
- ✅ Production confidence (files work in actual editor)

**Next Steps**:
1. Implement Phase 1 (logging foundation)
2. Create automation module (Phase 2-3)
3. Add packing support (Phase 4-5)
4. Integrate into pipeline (Phase 6)
5. Test comprehensively (Phase 7)

---

**End of Implementation Plan**

**Version**: 1.0.0
**Status**: 📋 Ready for Implementation
**Estimated Effort**: 19 hours
**Author**: Claude Sonnet 4.5 (Ultra-Think Mode)
