# AutoIt SF2 Loader

AutoIt script for automating SID Factory II file loading with keep-alive mechanism.

## Overview

This directory contains the AutoIt implementation for the SIDM2 project's hybrid automation approach. The AutoIt script solves the problem of SID Factory II closing immediately when launched programmatically.

**Problem**: SID Factory II closes in <2 seconds when launched via subprocess without user interaction.

**Solution**: AutoIt compiled script with keep-alive mechanism prevents auto-close and loads files automatically.

## Files

- `sf2_loader.au3` - AutoIt source code (150+ lines)
- `compile.bat` - Compilation script for Windows
- `sf2_loader.exe` - Compiled executable (created after compilation)
- `README.md` - This file

## Prerequisites

**To compile** (developers):
- AutoIt3 Full Installation: https://www.autoitscript.com/site/autoit/downloads/
- Windows OS

**To use** (end users):
- Windows OS
- Pre-compiled `sf2_loader.exe` (no AutoIt installation required)

## Compilation

### Windows

```batch
cd scripts/autoit
compile.bat
```

The batch script will:
1. Find AutoIt Aut2Exe compiler
2. Compile sf2_loader.au3 to sf2_loader.exe (64-bit)
3. Display success/error message

### Manual Compilation

If the batch script doesn't work:

```batch
"C:\Program Files (x86)\AutoIt3\Aut2Exe\Aut2exe.exe" /in "sf2_loader.au3" /out "sf2_loader.exe" /comp 4 /x64
```

## Usage

### Command Line (Manual Testing)

```batch
sf2_loader.exe "C:\Path\To\SIDFactoryII.exe" "C:\Path\To\file.sf2" "status.txt"
```

**Arguments**:
1. Editor path - Full path to SIDFactoryII.exe
2. SF2 file path - Full path to .sf2 file to load
3. Status file - Path where status updates will be written

**Status File Values**:
- `STARTING` - Script initializing
- `LAUNCHING` - Launching editor
- `WAITING_WINDOW` - Waiting for editor window
- `KEEP_ALIVE_STARTED` - Keep-alive mechanism active
- `LOADING_FILE` - Loading file via F10 menu
- `VERIFYING` - Checking if file loaded
- `SUCCESS:<title>` - File loaded successfully (title = window title)
- `ERROR:<message>` - Error occurred
- `WARNING:<message>` - Warning (file may not be loaded)

### Python Integration

**Recommended** - Use via Python bridge:

```python
from sidm2.sf2_editor_automation import SF2EditorAutomation

automation = SF2EditorAutomation()

# Automatic AutoIt mode (if sf2_loader.exe exists)
automation.launch_editor_with_file("file.sf2")
automation.start_playback()

# Or explicit mode selection
automation.launch_editor_with_file("file.sf2", use_autoit=True)
```

See: `docs/guides/SF2_EDITOR_AUTOIT_HYBRID_GUIDE.md` for full documentation.

## How It Works

### Keep-Alive Mechanism

The script sends periodic WM_NULL messages to the editor window every 500ms. This simulates user presence without interfering with the editor's operation.

```autoit
Func KeepAlive()
    If WinExists($g_hwnd) Then
        DllCall("user32.dll", "lresult", "SendMessageW", _
                "hwnd", $g_hwnd, _
                "uint", 0x0000, _  ; WM_NULL
                "wparam", 0, _
                "lparam", 0)
    EndIf
EndFunc
```

### File Loading Sequence

1. **Launch Editor** - Start SIDFactoryII.exe
2. **Find Window** - Poll for window handle (max 10 seconds)
3. **Start Keep-Alive** - Begin periodic null messages (500ms interval)
4. **Send F10** - Open file dialog
5. **Find Dialog** - Search for file dialog window
6. **Type Path** - Send file path characters
7. **Press Enter** - Confirm load
8. **Verify** - Check window title for .sf2
9. **Stop Keep-Alive** - Exit (editor stays open)

### Timing

- Window detection: 10 seconds max
- Dialog detection: 5 seconds max
- File load: 30 seconds max
- Keep-alive interval: 500ms (0.5 seconds)
- Total typical time: 3-7 seconds per file

## Testing

### Test Script Manually

```batch
REM 1. Create test status file
echo. > test_status.txt

REM 2. Run loader
sf2_loader.exe "C:\path\to\SIDFactoryII.exe" "C:\path\to\test.sf2" "test_status.txt"

REM 3. Check status
type test_status.txt

REM 4. Verify editor is open with file loaded
```

### Python Tests

```bash
python pyscript/test_autoit_integration.py
```

See test results in `test_output/` directory.

## Configuration

Edit `sf2_loader.au3` to adjust timings:

```autoit
Global Const $KEEP_ALIVE_INTERVAL = 500   ; Keep-alive frequency (ms)
Global Const $MAX_WAIT_WINDOW = 10000     ; Window wait timeout (ms)
Global Const $MAX_WAIT_DIALOG = 5000      ; Dialog wait timeout (ms)
Global Const $MAX_WAIT_LOAD = 30000       ; File load timeout (ms)
```

After editing, recompile with `compile.bat`.

## Troubleshooting

### Compilation Fails

**Error**: "AutoIt Aut2Exe compiler not found"

**Solution**:
1. Install AutoIt3: https://www.autoitscript.com/site/autoit/downloads/
2. Choose "Full Installation"
3. Run compile.bat again

### Editor Doesn't Launch

**Error**: "ERROR: Editor not found: <path>"

**Solution**:
- Verify SIDFactoryII.exe path is correct
- Check file exists: `dir "C:\path\to\SIDFactoryII.exe"`

### File Doesn't Load

**Status**: "WARNING: File may not be loaded"

**Possible causes**:
- F10 doesn't open file dialog in this editor version
- File dialog title doesn't match detection patterns
- File path contains special characters

**Debug**:
1. Run loader manually and watch editor window
2. Check if F10 opens dialog
3. Check console output for dialog detection messages

### Keep-Alive Not Working

**Symptom**: Editor still closes

**Solutions**:
1. Reduce keep-alive interval (try 250ms)
2. Try alternative keep-alive method (WM_SETCURSOR)
3. Update AutoIt to latest version

## Performance

- **Success Rate**: 95-99% (expected)
- **Speed**: 3-7 seconds per file
- **Throughput**: 10-20 files/minute
- **Resource Usage**: Low (AutoIt is lightweight)

## Limitations

- **Windows Only** - AutoIt is Windows-specific
- **Requires Compilation** - Source must be compiled to .exe
- **Editor-Specific** - Designed for SID Factory II
- **F10 Dependency** - Assumes F10 opens file dialog

## Alternatives

If AutoIt doesn't work for your use case:

1. **Manual Workflow** - User loads file, Python automates rest
   - See: `docs/guides/SF2_EDITOR_MANUAL_WORKFLOW_GUIDE.md`

2. **Other Automation Tools** - AutoHotkey, Sikuli, etc.
   - See: `docs/analysis/GUI_AUTOMATION_COMPREHENSIVE_ANALYSIS.md`

## Version History

- **1.0.0** (2025-12-26) - Initial implementation
  - Keep-alive mechanism
  - F10-based file loading
  - Status file communication
  - Dialog detection
  - Window title verification

## License

Part of SIDM2 project. See project LICENSE file.

## Support

For issues or questions:
- See: `docs/guides/SF2_EDITOR_AUTOIT_HYBRID_GUIDE.md`
- See: `test_output/EDITOR_AUTOMATION_FILE_LOADING_INVESTIGATION.md`
- Create issue at: https://github.com/MichaelTroelsen/SIDM2conv/issues

## Related Documentation

- **Python Bridge**: `sidm2/sf2_editor_automation.py`
- **Full Guide**: `docs/guides/SF2_EDITOR_AUTOIT_HYBRID_GUIDE.md`
- **Investigation**: `test_output/EDITOR_AUTOMATION_FILE_LOADING_INVESTIGATION.md`
- **Manual Workflow**: `docs/guides/SF2_EDITOR_MANUAL_WORKFLOW_GUIDE.md`
