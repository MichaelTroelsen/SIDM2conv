# Conversion Cockpit Technical Reference

**Version**: 1.0.0
**Date**: 2025-12-22
**Author**: SIDM2 Project

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Reference](#module-reference)
3. [Signal/Slot System](#signalslot-system)
4. [Configuration System](#configuration-system)
5. [Pipeline Executor](#pipeline-executor)
6. [Custom Widgets](#custom-widgets)
7. [Testing](#testing)
8. [Development Guide](#development-guide)
9. [API Reference](#api-reference)

---

## Architecture Overview

### System Design

Conversion Cockpit follows a **Model-View-Controller (MVC)** architecture with Qt's Signal/Slot pattern for communication:

```
┌──────────────────────────────────────────────────────────┐
│                     View (GUI)                           │
│  conversion_cockpit_gui.py - Main Window & Tabs          │
│  cockpit_widgets.py - Custom Widgets                     │
└──────────────┬────────────────────────┬──────────────────┘
               │                        │
        Signals │                        │ Slots
               ↓                        ↑
┌──────────────────────────────────────────────────────────┐
│                  Controller                              │
│  conversion_executor.py - Batch Processing Logic         │
└──────────────┬───────────────────────────────────────────┘
               │
         Uses  │
               ↓
┌──────────────────────────────────────────────────────────┐
│                    Model                                 │
│  pipeline_config.py - Configuration & Presets            │
│  QProcess - Subprocess Management                        │
│  External Tools - scripts/, tools/                       │
└──────────────────────────────────────────────────────────┘
```

### Component Relationships

```
CockpitMainWindow (QMainWindow)
├── Dashboard Tab
│   ├── StatsCard widgets (3)
│   ├── ProgressWidget
│   └── Control buttons
│
├── Files Tab
│   └── FileListWidget (drag-drop, selection)
│
├── Configuration Tab
│   ├── Mode selection (Simple/Advanced/Custom)
│   ├── Driver configuration
│   ├── Pipeline steps (14 checkboxes)
│   └── Execution options
│
├── Results Tab
│   └── QTableWidget (sortable, filterable)
│
└── Logs Tab
    └── LogStreamWidget (color-coded, searchable)

ConversionExecutor (QObject)
├── QProcess management
├── Signal emissions
├── File result tracking
└── Pipeline orchestration

PipelineConfig (dataclass)
├── Mode management
├── Preset definitions
├── QSettings persistence
└── Step enablement logic
```

### Technology Stack

- **Framework**: PyQt6 6.x
- **Python Version**: 3.8+
- **GUI**: Qt6 Widgets
- **Process Management**: QProcess
- **Configuration**: QSettings (Windows Registry / platform-specific)
- **Threading**: Qt Event Loop (no manual threading)
- **External Tools**: subprocess via QProcess

### Design Patterns

1. **Signal/Slot Pattern**: Asynchronous communication between GUI and backend
2. **Observer Pattern**: Multiple UI components observe executor state
3. **Strategy Pattern**: Configurable pipeline steps
4. **Singleton Configuration**: One config instance shared across components
5. **Factory Pattern**: Dynamic widget creation based on configuration

---

## Module Reference

### conversion_cockpit_gui.py (1,047 lines)

**Purpose**: Main application window with 5 tabs and control logic

**Key Classes**:
- `CockpitMainWindow(QMainWindow)` - Main window
- Tab creation methods for each of 5 tabs
- Signal handlers for executor events
- UI update methods

**Key Methods**:
```python
def __init__(self, parent=None)
    # Initialize main window, create tabs, connect signals

def create_dashboard_tab() -> QWidget
    # Create Dashboard with stats cards, progress, control panel

def create_files_tab() -> QWidget
    # Create Files tab with file list, browse, drag-drop

def create_config_tab() -> QWidget
    # Create Configuration tab with mode, driver, steps

def create_results_tab() -> QWidget
    # Create Results tab with sortable table

def create_logs_tab() -> QWidget
    # Create Logs tab with color-coded log display

def on_start_clicked()
    # Handle START button click, begin batch processing

def on_pause_clicked()
    # Handle PAUSE button click, suspend processing

def on_stop_clicked()
    # Handle STOP button click, cancel batch

def on_batch_started(total_files: int)
    # Handle batch_started signal from executor

def on_file_completed(filename: str, results: Dict)
    # Handle file_completed signal, update results table

def on_files_changed(selected_files: List[str])
    # Handle file selection changes, update stats
```

**Dependencies**:
- PyQt6.QtWidgets (QMainWindow, QPushButton, QTabWidget, etc.)
- PyQt6.QtCore (Qt, pyqtSignal, QSettings)
- conversion_executor (ConversionExecutor)
- pipeline_config (PipelineConfig)
- cockpit_widgets (StatsCard, ProgressWidget, FileListWidget, LogStreamWidget)

---

### conversion_executor.py (475 lines)

**Purpose**: Backend engine for batch conversion with pipeline orchestration

**Key Classes**:
- `ConversionExecutor(QObject)` - Main executor
- `FileResult(dataclass)` - Per-file result structure

**Signals**:
```python
batch_started = pyqtSignal(int)                    # total_files
file_started = pyqtSignal(str, int, int)           # filename, index, total
step_started = pyqtSignal(str, int, int)           # step_name, step_num, total
step_completed = pyqtSignal(str, bool, str)        # step_name, success, message
file_completed = pyqtSignal(str, dict)             # filename, results_dict
batch_completed = pyqtSignal(dict)                 # summary_dict
progress_updated = pyqtSignal(int)                 # percentage (0-100)
log_message = pyqtSignal(str, str)                 # level, message
error_occurred = pyqtSignal(str, str)              # filename, error_message
```

**Key Methods**:
```python
def start_batch(files: List[str])
    # Begin batch processing of files

def pause()
    # Pause after current file completes

def resume()
    # Resume paused batch

def stop()
    # Stop batch immediately

def _process_next_file()
    # Process next file in queue

def _run_pipeline_for_file(sid_file: str)
    # Execute enabled pipeline steps for one file

def _run_step(step_name: str, sid_file: str) -> Tuple[bool, str]
    # Run single pipeline step using QProcess

def _get_step_command(step_name: str, sid_file: str) -> List[str]
    # Generate command array for step

def _get_output_file_for_step(step_name: str, sid_file: str) -> Optional[str]
    # Get output file path for redirection

def _on_output_ready()
    # Handle subprocess output, emit log_message signals

def _collect_results(sid_file: str) -> Dict
    # Parse output files, collect metrics
```

**FileResult Structure**:
```python
@dataclass
class FileResult:
    filename: str           # Input SID filename
    driver: str             # Driver used (laxity/driver11/np20)
    steps_completed: int    # Number of steps completed
    total_steps: int        # Total steps attempted
    accuracy: float         # Frame accuracy percentage
    status: str             # passed/failed/warning
    duration: float         # Processing time in seconds
    errors: List[str]       # Error messages
```

---

### pipeline_config.py (259 lines)

**Purpose**: Configuration management with presets and persistence

**Key Classes**:
- `PipelineStep(Enum)` - Enum of all 14 pipeline steps
- `PipelineConfig(dataclass)` - Configuration container

**PipelineStep Enum**:
```python
class PipelineStep(Enum):
    # Format: (step_id, description, default_enabled)
    CONVERSION = ("conversion", "SID → SF2 Conversion", True)
    SIDDUMP_ORIGINAL = ("siddump_original", "Siddump (Original)", False)
    SIDDECOMPILER = ("siddecompiler", "SIDdecompiler Analysis", False)
    PACKING = ("packing", "SF2 → SID Packing", True)
    SIDDUMP_EXPORTED = ("siddump_exported", "Siddump (Exported)", True)
    WAV_ORIGINAL = ("wav_original", "WAV Rendering (Original)", True)
    WAV_EXPORTED = ("wav_exported", "WAV Rendering (Exported)", True)
    HEXDUMP = ("hexdump", "Hexdump Generation", False)
    SIDWINDER_TRACE = ("sidwinder_trace", "SIDwinder Trace", False)
    INFO_REPORT = ("info_report", "Info Report", True)
    ANNOTATED_DISASM = ("annotated_disasm", "Annotated Disassembly", False)
    SIDWINDER_DISASM = ("sidwinder_disasm", "SIDwinder Disassembly", False)
    VALIDATION = ("validation", "Validation (File checks)", True)
    MIDI_COMPARISON = ("midi_comparison", "MIDI Comparison", False)
```

**PipelineConfig Fields**:
```python
@dataclass
class PipelineConfig:
    mode: str = "simple"                         # simple/advanced/custom
    primary_driver: str = "laxity"               # laxity/driver11/np20
    generate_both: bool = True                   # Generate NP20 + Driver 11
    output_directory: str = "output"             # Output base directory
    overwrite_existing: bool = True              # Overwrite existing files
    create_nested_dirs: bool = True              # Create nested directories
    enabled_steps: Dict[str, bool] = field(default_factory=dict)
    log_level: str = "INFO"                      # DEBUG/INFO/WARN/ERROR
    log_to_file: bool = False                    # Save logs to file
    log_file_path: str = ""                      # Log file path
    log_json_format: bool = False                # JSON log format
    validation_duration: str = "30s"             # 10s/30s/60s/120s
    run_accuracy_validation: bool = True         # Run validation step
    step_timeout: int = 120                      # Timeout in seconds
    stop_on_error: bool = False                  # Stop batch on error
```

**Key Methods**:
```python
@staticmethod
def get_simple_preset() -> Dict[str, bool]
    # Returns dict with 7 steps enabled

@staticmethod
def get_advanced_preset() -> Dict[str, bool]
    # Returns dict with all 14 steps enabled

def apply_preset(preset_name: str)
    # Apply Simple/Advanced preset

def get_enabled_steps() -> List[str]
    # Return list of enabled step IDs

def save_to_settings(settings: QSettings)
    # Persist config to QSettings

def load_from_settings(settings: QSettings)
    # Load config from QSettings
```

---

### cockpit_widgets.py (437 lines)

**Purpose**: Custom PyQt6 widgets for Conversion Cockpit

**Key Classes**:

#### StatsCard(QGroupBox)
```python
class StatsCard(QGroupBox):
    """Statistics card widget for dashboard"""

    def __init__(title: str, stats: List[Tuple[str, str]])
        # Create card with title and key-value pairs

    def update_stat(key: str, value: str)
        # Update specific stat value
```

#### ProgressWidget(QWidget)
```python
class ProgressWidget(QWidget):
    """Progress widget with file and step progress bars"""

    def set_file_progress(current: int, total: int)
        # Update file progress bar

    def set_step_progress(current: int, total: int)
        # Update step progress bar

    def reset()
        # Reset both progress bars to 0
```

#### FileListWidget(QWidget)
```python
class FileListWidget(QWidget):
    """File list widget with checkboxes and drag-drop"""

    files_changed = pyqtSignal(list)  # Emits selected files

    def add_file(file_path: str, checked: bool = True)
        # Add single file to list

    def add_files(file_paths: List[str], checked: bool = True)
        # Add multiple files

    def get_selected_files() -> List[str]
        # Return list of checked files

    def select_all()
        # Check all items

    def select_none()
        # Uncheck all items

    def dragEnterEvent(event: QDragEnterEvent)
        # Handle drag enter

    def dropEvent(event: QDropEvent)
        # Handle file drop, add .sid files
```

#### LogStreamWidget(QTextEdit)
```python
class LogStreamWidget(QTextEdit):
    """Color-coded log display with auto-scroll"""

    COLORS = {
        "ERROR": "#d32f2f",   # Red
        "WARN": "#f57c00",    # Orange
        "INFO": "#333333",    # Dark gray
        "DEBUG": "#0288d1"    # Blue
    }

    def append_log(level: str, message: str)
        # Append color-coded log message

    def clear()
        # Clear log display
```

---

## Signal/Slot System

### Signal Flow Diagram

```
ConversionExecutor Signals → CockpitMainWindow Slots

batch_started(int) ────────────→ on_batch_started(int)
                                 ├→ Update dashboard stats
                                 ├→ Reset progress bars
                                 └→ Disable UI controls

file_started(str, int, int) ───→ on_file_started(str, int, int)
                                 ├→ Update current file display
                                 ├→ Update file progress bar
                                 └→ Log message

step_started(str, int, int) ───→ on_step_started(str, int, int)
                                 ├→ Update step progress bar
                                 ├→ Update current operation
                                 └→ Log message

step_completed(str, bool, str) → on_step_completed(str, bool, str)
                                 └→ Log step result

file_completed(str, dict) ─────→ on_file_completed(str, dict)
                                 ├→ Add row to results table
                                 ├→ Update results stats
                                 └→ Log completion

batch_completed(dict) ─────────→ on_batch_completed(dict)
                                 ├→ Enable UI controls
                                 ├→ Show completion dialog
                                 └→ Log summary

log_message(str, str) ─────────→ on_log_message(str, str)
                                 └→ Append to log widget

error_occurred(str, str) ──────→ on_error_occurred(str, str)
                                 ├→ Log error
                                 └→ Show error dialog (optional)
```

### Signal Connection Code

**In CockpitMainWindow.__init__()**:
```python
# Connect executor signals to slots
self.executor.batch_started.connect(self.on_batch_started)
self.executor.file_started.connect(self.on_file_started)
self.executor.step_started.connect(self.on_step_started)
self.executor.step_completed.connect(self.on_step_completed)
self.executor.file_completed.connect(self.on_file_completed)
self.executor.batch_completed.connect(self.on_batch_completed)
self.executor.progress_updated.connect(self.on_progress_updated)
self.executor.log_message.connect(self.on_log_message)
self.executor.error_occurred.connect(self.on_error_occurred)

# Connect widget signals
self.file_list_widget.files_changed.connect(self.on_files_changed)
```

---

## Configuration System

### QSettings Integration

**Storage Location**:
- **Windows**: `HKEY_CURRENT_USER\Software\SIDM2\ConversionCockpit`
- **macOS**: `~/Library/Preferences/com.SIDM2.ConversionCockpit.plist`
- **Linux**: `~/.config/SIDM2/ConversionCockpit.conf`

**Saved Settings**:
```python
# Mode and driver
settings.setValue("mode", config.mode)
settings.setValue("primary_driver", config.primary_driver)

# Directories
settings.setValue("output_directory", config.output_directory)

# Pipeline steps (saved as arrays)
settings.beginWriteArray("enabled_steps")
for step_id, enabled in config.enabled_steps.items():
    settings.setArrayIndex(index)
    settings.setValue("step_id", step_id)
    settings.setValue("enabled", enabled)
settings.endArray()

# Logging
settings.setValue("log_level", config.log_level)
settings.setValue("log_to_file", config.log_to_file)

# Execution
settings.setValue("step_timeout", config.step_timeout)
settings.setValue("stop_on_error", config.stop_on_error)
```

### Preset System

**Simple Preset** (7 steps):
```python
{
    "conversion": True,           # Required
    "packing": True,              # Pack back to SID
    "siddump_exported": True,     # Dump exported
    "wav_original": True,         # Render original audio
    "wav_exported": True,         # Render exported audio
    "info_report": True,          # Generate info.txt
    "validation": True,           # Validate accuracy
}
```

**Advanced Preset** (14 steps):
All steps enabled.

**Custom Preset**:
User-defined combination, saved to QSettings.

---

## Pipeline Executor

### Batch Processing Flow

```
start_batch(files) called
    ↓
Initialize: is_running = True, current_file_index = 0
    ↓
Emit: batch_started(total_files)
    ↓
┌─────────────────────────────────────┐
│ For each file in files_to_process: │
└─────────────────────────────────────┘
    ↓
Emit: file_started(filename, index, total)
    ↓
Get enabled_steps from config
    ↓
┌─────────────────────────────────────┐
│ For each step in enabled_steps:    │
└─────────────────────────────────────┘
    ↓
Emit: step_started(step_name, step_num, total_steps)
    ↓
Get command: _get_step_command(step_name, sid_file)
    ↓
Create QProcess
    ↓
Start process with command
    ↓
Wait for completion (with timeout)
    ↓
Emit: step_completed(step_name, success, message)
    ↓
If stop_on_error and failed: break
    ↓
End of steps loop
    ↓
Collect results: _collect_results(sid_file)
    ↓
Emit: file_completed(filename, results_dict)
    ↓
Increment current_file_index
    ↓
End of files loop
    ↓
Calculate summary statistics
    ↓
Emit: batch_completed(summary_dict)
```

### QProcess Management

**Creating Process**:
```python
self.process = QProcess()
self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
self.process.readyReadStandardOutput.connect(self._on_output_ready)
```

**Starting Process**:
```python
command = ["python", "scripts/sid_to_sf2.py", input_file, output_file]
self.process.start(command[0], command[1:])

if not self.process.waitForStarted(3000):  # 3 second timeout
    return False, "Failed to start process"

if not self.process.waitForFinished(120000):  # 2 minute timeout
    self.process.kill()
    return False, "Process timeout"

exit_code = self.process.exitCode()
return exit_code == 0, f"Exit code: {exit_code}"
```

**Capturing Output**:
```python
def _on_output_ready(self):
    """Capture and emit subprocess output"""
    if self.process:
        output = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
        for line in output.strip().split('\n'):
            if line:
                level = self._extract_log_level(line)  # Parse [INFO], [ERROR], etc.
                self.log_message.emit(level, line)
```

---

## Custom Widgets

### StatsCard Implementation

**Visual Structure**:
```
┌─────────────────────────┐
│ TITLE                   │
├─────────────────────────┤
│ Key 1:        Value 1   │
│ Key 2:        Value 2   │
│ Key 3:        Value 3   │
└─────────────────────────┘
```

**Key Code**:
```python
class StatsCard(QGroupBox):
    def __init__(self, title: str, stats: List[Tuple[str, str]]):
        super().__init__(title)
        self.stats_labels = {}  # Store references to value labels

        layout = QVBoxLayout()
        for key, value in stats:
            row_layout = QHBoxLayout()

            key_label = QLabel(f"{key}:")
            value_label = QLabel(value)

            row_layout.addWidget(key_label)
            row_layout.addWidget(value_label)
            layout.addLayout(row_layout)

            self.stats_labels[key] = value_label  # Store reference

        self.setLayout(layout)

    def update_stat(self, key: str, value: str):
        """Update stat value by key"""
        if key in self.stats_labels:
            self.stats_labels[key].setText(value)
```

### FileListWidget with Drag-Drop

**Drag-Drop Implementation**:
```python
class FileListWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)  # Enable drag-drop

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept drag if it contains URLs (files)"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle file drop"""
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith('.sid'):  # Filter .sid files
                    files.append(file_path)

            if files:
                self.add_files(files)  # Add to list
                event.acceptProposedAction()
```

---

## Testing

### Unit Tests (test_conversion_cockpit.py)

**Test Classes**:
1. `TestPipelineConfig` - Test configuration management
2. `TestPipelineStep` - Test step enum properties
3. `TestConversionExecutorMocked` - Test executor with mocked dependencies
4. `TestCockpitWidgetsLogic` - Test widget logic (non-GUI parts)
5. `TestFilePathGeneration` - Test output path generation
6. `TestConfigurationPersistence` - Test QSettings save/load

**Running Unit Tests**:
```bash
python pyscript/test_conversion_cockpit.py
```

**Expected Output**:
```
test_default_configuration (__main__.TestPipelineConfig) ... ok
test_simple_preset (__main__.TestPipelineConfig) ... ok
...
Ran 30 tests in 0.123s

OK
```

### Integration Tests (test_conversion_cockpit_integration.py)

**Test Classes**:
1. `TestOutputDirectoryCreation` - Test directory creation
2. `TestConfigurationWorkflow` - Test mode switching
3. `TestPipelineStepSelection` - Test step selection logic
4. `TestFileListOperations` - Test file selection logic
5. `TestResultsCalculation` - Test accuracy calculations
6. `TestTimeEstimation` - Test time estimation logic
7. `TestLogFormatting` - Test log formatting
8. `TestErrorHandling` - Test error scenarios
9. `TestBatchProcessingSimulation` - Test batch logic

**Running Integration Tests**:
```bash
python scripts/test_conversion_cockpit_integration.py
```

**Expected Output**:
```
=====================================================
INTEGRATION TEST SUMMARY
=====================================================
Tests Run: 45
Successes: 45
Failures: 0
Errors: 0
=====================================================
```

---

## Development Guide

### Setting Up Development Environment

1. **Clone Repository**:
```bash
git clone https://github.com/YourUsername/SIDM2.git
cd SIDM2
```

2. **Install Dependencies**:
```bash
python -m pip install PyQt6
```

3. **Launch in Development Mode**:
```bash
python pyscript/conversion_cockpit_gui.py
```

### Adding a New Pipeline Step

**Step 1: Update PipelineStep Enum**

Edit `pyscript/pipeline_config.py`:
```python
class PipelineStep(Enum):
    # ... existing steps
    NEW_STEP = ("new_step", "New Step Description", False)
```

**Step 2: Add Command Mapping**

Edit `pyscript/conversion_executor.py`, in `_get_step_command()`:
```python
command_map = {
    # ... existing mappings
    "new_step": [
        "python", str(scripts_dir / "new_script.py"),
        sid_file, output_file
    ],
}
```

**Step 3: Add Output File Mapping (if needed)**

In `_get_output_file_for_step()`:
```python
output_map = {
    # ... existing mappings
    "new_step": str(output_base / f"{base_name}_new_output.txt"),
}
```

**Step 4: Update Presets (if needed)**

In `pipeline_config.py`:
```python
@staticmethod
def get_advanced_preset() -> Dict[str, bool]:
    return {
        # ... existing steps
        "new_step": True,  # Enable in advanced mode
    }
```

**Step 5: Test**:
```bash
# Run unit tests
python pyscript/test_conversion_cockpit.py

# Launch GUI and verify new step appears
python pyscript/conversion_cockpit_gui.py
```

### Adding a New Widget

**Step 1: Create Widget Class**

Edit `pyscript/cockpit_widgets.py`:
```python
class NewWidget(QWidget):
    """New custom widget"""

    # Define signals if needed
    value_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout()
        # Add widgets to layout
        self.setLayout(layout)

    def update_value(self, value: str):
        """Update widget value"""
        # Implementation
```

**Step 2: Use Widget in Main GUI**

Edit `pyscript/conversion_cockpit_gui.py`:
```python
from cockpit_widgets import NewWidget

class CockpitMainWindow(QMainWindow):
    def __init__(self):
        # ...
        self.new_widget = NewWidget()
        # Add to layout
        # Connect signals
```

### Debugging Tips

**Enable Verbose Logging**:
```python
# In conversion_executor.py
self.config.log_level = "DEBUG"
```

**Print Signal Emissions**:
```python
# In conversion_executor.py
def _emit_log(self, level: str, message: str):
    print(f"[{level}] {message}")  # Debug print
    self.log_message.emit(level, message)
```

**Qt Debug Output**:
```bash
# Set Qt environment variable
set QT_DEBUG_PLUGINS=1
python pyscript/conversion_cockpit_gui.py
```

---

## API Reference

### CockpitMainWindow

```python
class CockpitMainWindow(QMainWindow):
    """Main application window"""

    def __init__(self, parent=None)
        """Initialize main window"""

    # Public Methods
    def start_conversion()
        """Begin batch conversion"""

    def pause_conversion()
        """Pause batch after current file"""

    def stop_conversion()
        """Stop batch immediately"""

    # Signal Handlers
    def on_batch_started(total_files: int)
        """Handle batch started signal"""

    def on_file_completed(filename: str, results: Dict)
        """Handle file completed signal"""

    def on_batch_completed(summary: Dict)
        """Handle batch completed signal"""
```

### ConversionExecutor

```python
class ConversionExecutor(QObject):
    """Batch conversion executor"""

    # Signals
    batch_started = pyqtSignal(int)
    file_completed = pyqtSignal(str, dict)
    batch_completed = pyqtSignal(dict)
    log_message = pyqtSignal(str, str)

    # Public Methods
    def start_batch(files: List[str])
        """Start batch processing"""

    def pause()
        """Pause after current file"""

    def resume()
        """Resume paused batch"""

    def stop()
        """Stop batch immediately"""

    # Private Methods
    def _run_step(step_name: str, sid_file: str) -> Tuple[bool, str]
        """Run single pipeline step"""

    def _collect_results(sid_file: str) -> Dict
        """Collect results from output files"""
```

### PipelineConfig

```python
@dataclass
class PipelineConfig:
    """Configuration container"""

    mode: str
    primary_driver: str
    enabled_steps: Dict[str, bool]
    # ... other fields

    @staticmethod
    def get_simple_preset() -> Dict[str, bool]
        """Get simple mode preset"""

    @staticmethod
    def get_advanced_preset() -> Dict[str, bool]
        """Get advanced mode preset"""

    def apply_preset(preset_name: str)
        """Apply preset by name"""

    def get_enabled_steps() -> List[str]
        """Get list of enabled step IDs"""

    def save_to_settings(settings: QSettings)
        """Save to QSettings"""

    def load_from_settings(settings: QSettings)
        """Load from QSettings"""
```

---

## Performance Considerations

### UI Responsiveness

**Problem**: Long-running operations block UI

**Solution**: QProcess with signal/slot pattern
- QProcess runs in separate process (not thread)
- Qt event loop continues running
- Signals trigger UI updates asynchronously

### Memory Management

**Log Widget Line Limit**:
```python
class LogStreamWidget(QTextEdit):
    def __init__(self, max_lines: int = 10000):
        self.max_lines = max_lines
        self.line_count = 0

    def append_log(self, level: str, message: str):
        # Add new line
        self.line_count += 1

        # Remove old lines if exceeding limit
        if self.line_count > self.max_lines:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down,
                              QTextCursor.MoveMode.KeepAnchor,
                              self.line_count - self.max_lines)
            cursor.removeSelectedText()
            self.line_count = self.max_lines
```

### File Processing Speed

**Simple Mode**: ~70 seconds per file
- 7 steps × ~10 seconds each
- QProcess overhead: ~5-10 seconds total

**Advanced Mode**: ~120-180 seconds per file
- 14 steps × ~10 seconds each (varies by step)
- Disassembly and trace steps take longer (30-60 seconds)

**Optimization**:
- Use Custom mode to disable unnecessary steps
- Increase timeouts for slow machines
- Process files on SSD for faster I/O

---

## Troubleshooting Development Issues

### Issue: PyQt6 Import Errors

**Problem**: `ModuleNotFoundError: No module named 'PyQt6'`

**Solution**:
```bash
python -m pip install --upgrade PyQt6
```

### Issue: Signals Not Firing

**Problem**: Signal handlers not called

**Checklist**:
1. Verify signal is defined on QObject-derived class
2. Verify connection with `signal.connect(slot)`
3. Check signal parameters match slot parameters
4. Ensure slot is not raising exceptions

**Debug**:
```python
def on_signal(self, arg):
    print(f"Signal received: {arg}")  # Debug print
    # Implementation
```

### Issue: QProcess Not Starting

**Problem**: `process.waitForStarted()` returns False

**Checklist**:
1. Verify command path exists (`Path(cmd).exists()`)
2. Check command is executable
3. Verify arguments are correctly formatted
4. Check for permission issues

**Debug**:
```python
print(f"Command: {command}")
print(f"CWD: {os.getcwd()}")
print(f"Exists: {Path(command[0]).exists()}")
```

---

## Future Enhancements

**Planned Features**:

1. **Concurrent Processing** - Run multiple files in parallel
2. **Progress Estimation** - More accurate time estimates based on history
3. **Batch History** - Remember last 10 batch configurations
4. **Export Reports** - PDF/HTML reports of batch results
5. **Embedded Dashboard** - Show validation dashboard HTML in Results tab
6. **Remote Monitoring** - Web interface for monitoring batch jobs
7. **Plugin System** - Extensible pipeline step plugins

---

**End of Technical Reference**

For user documentation, see: `CONVERSION_COCKPIT_USER_GUIDE.md`

Generated by SIDM2 Project - 2025-12-22
