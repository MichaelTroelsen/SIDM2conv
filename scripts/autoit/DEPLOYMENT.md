# AutoIt Hybrid Automation - Deployment Guide

Quick deployment guide for setting up the AutoIt hybrid automation system on a new machine.

## Quick Start (5 Minutes)

### Windows Only

```batch
# 1. Install AutoIt3 (if not already installed)
# Download from: https://www.autoitscript.com/site/autoit/downloads/
# Install "Full Installation" option

# 2. Compile AutoIt script
cd scripts/autoit
compile.bat

# 3. Verify installation
python pyscript/test_autoit_integration.py

# 4. Test with example
python pyscript/example_autoit_usage.py
```

Done! The system is ready for automated file loading.

---

## Detailed Deployment Steps

### Step 1: Prerequisites

**Required**:
- Windows OS (Windows 10/11 recommended)
- Python 3.8+ with packages:
  - `psutil`
  - `pywin32` (Windows only)
- SID Factory II installed

**Optional** (for AutoIt mode):
- AutoIt3 Full Installation (for compilation only)
- Compiled `sf2_loader.exe` can be distributed without AutoIt

### Step 2: Install AutoIt3 (One-Time Setup)

**Download**:
- Visit: https://www.autoitscript.com/site/autoit/downloads/
- Download: "AutoIt Full Installation"
- Version: 3.3.16.1 or later

**Install**:
1. Run installer
2. Choose "Full Installation"
3. Accept default installation path
4. Complete installation

**Verify**:
```batch
# Check if compiler exists
dir "C:\Program Files (x86)\AutoIt3\Aut2Exe\Aut2exe.exe"
```

### Step 3: Compile AutoIt Script

**Navigate to AutoIt directory**:
```batch
cd scripts/autoit
```

**Compile**:
```batch
compile.bat
```

**Expected output**:
```
========================================================================
Compiling SF2 Loader AutoIt Script
========================================================================

Found AutoIt compiler: C:\Program Files (x86)\AutoIt3\Aut2Exe\Aut2exe.exe

Source file: sf2_loader.au3
Output file: sf2_loader.exe

Compiling to 64-bit executable...

========================================================================
SUCCESS: Compilation complete!
========================================================================

sf2_loader.exe
```

**Verify**:
```batch
# Check compiled executable
dir sf2_loader.exe
```

### Step 4: Configure Editor Path

**Edit** `config/sf2_automation.ini`:

```ini
[Editor]
paths = bin/SIDFactoryII.exe
        C:/Program Files/SIDFactoryII/SIDFactoryII.exe
        C:/Program Files (x86)/SIDFactoryII/SIDFactoryII.exe
        YOUR_CUSTOM_PATH_HERE
```

Add your SID Factory II installation path if not in default locations.

### Step 5: Verify Installation

**Run integration tests**:
```batch
python pyscript/test_autoit_integration.py
```

**Expected output**:
```
Tests run: 27+
Tests passed: 27+
Tests failed: 0

[OK] All tests passed!
```

**Run configuration tests**:
```batch
python pyscript/test_automation_config.py
```

### Step 6: Test with Example

**Run example script**:
```batch
python pyscript/example_autoit_usage.py
```

**Select** option 1 (Auto-detect mode) and follow prompts.

---

## Deployment Verification Checklist

Use this checklist to verify complete deployment:

### Files Checklist

- [ ] `scripts/autoit/sf2_loader.au3` - AutoIt source code
- [ ] `scripts/autoit/sf2_loader.exe` - **Compiled executable** (created by compile.bat)
- [ ] `scripts/autoit/compile.bat` - Compilation script
- [ ] `scripts/autoit/README.md` - AutoIt documentation
- [ ] `config/sf2_automation.ini` - Configuration file
- [ ] `sidm2/automation_config.py` - Config module
- [ ] `sidm2/sf2_editor_automation.py` - Main automation module
- [ ] `pyscript/test_autoit_integration.py` - Integration tests
- [ ] `pyscript/test_automation_config.py` - Configuration tests
- [ ] `pyscript/example_autoit_usage.py` - Usage examples

### Configuration Checklist

- [ ] AutoIt3 installed (for compilation)
- [ ] `sf2_loader.exe` compiled successfully
- [ ] Editor path configured in `config/sf2_automation.ini`
- [ ] Editor path verified (file exists)
- [ ] Python packages installed (`psutil`, `pywin32`)

### Testing Checklist

- [ ] Integration tests pass (`test_autoit_integration.py`)
- [ ] Configuration tests pass (`test_automation_config.py`)
- [ ] Example script runs without errors
- [ ] Can create SF2EditorAutomation instance
- [ ] AutoIt mode available (or manual mode fallback works)

### Functionality Checklist

- [ ] Can launch editor manually
- [ ] Can detect running editor process
- [ ] Can attach to running editor
- [ ] Can load SF2 file (manually if AutoIt not compiled)
- [ ] Can start/stop playback
- [ ] Can close editor

---

## Deployment Scenarios

### Scenario 1: Developer Machine (Full Setup)

**Goal**: Enable all features including AutoIt compilation

**Steps**:
1. Install AutoIt3
2. Compile `sf2_loader.exe`
3. Configure editor path
4. Run tests
5. Ready for development and automation

**Time**: 10-15 minutes

---

### Scenario 2: End User Machine (Pre-compiled)

**Goal**: Use pre-compiled AutoIt executable

**Steps**:
1. Copy `sf2_loader.exe` to `scripts/autoit/`
2. Configure editor path in `config/sf2_automation.ini`
3. Run verification: `python pyscript/test_autoit_integration.py`
4. Ready for automated file loading

**Time**: 2-3 minutes

**Note**: No AutoIt installation required

---

### Scenario 3: Manual Workflow Only

**Goal**: Use manual workflow without AutoIt

**Steps**:
1. Configure editor path in `config/sf2_automation.ini`
2. Set `enabled = false` in `[AutoIt]` section (optional)
3. Use manual workflow (user loads file, automation takes over)
4. Ready for semi-automated validation

**Time**: 1-2 minutes

**Note**: No AutoIt required

---

## Troubleshooting

### Issue: AutoIt won't compile

**Error**: "AutoIt Aut2Exe compiler not found"

**Solution**:
1. Verify AutoIt3 is installed
2. Check installation path: `C:\Program Files (x86)\AutoIt3\`
3. Reinstall with "Full Installation" option
4. Manually run: `"C:\Program Files (x86)\AutoIt3\Aut2Exe\Aut2exe.exe" /in "sf2_loader.au3" /out "sf2_loader.exe" /x64`

---

### Issue: Editor path not found

**Error**: "SIDFactoryII.exe not found in configured locations"

**Solution**:
1. Find your SIDFactoryII.exe location
2. Edit `config/sf2_automation.ini`
3. Add path to `[Editor] paths` section
4. Verify: `dir "YOUR_PATH\SIDFactoryII.exe"`

---

### Issue: Integration tests fail

**Error**: Various test failures

**Solution**:
1. Check Python packages: `pip install psutil pywin32`
2. Verify config file exists: `config/sf2_automation.ini`
3. Check editor path is correct
4. Run with verbose: `python pyscript/test_autoit_integration.py --verbose`

---

### Issue: AutoIt mode not available

**Warning**: "AutoIt enabled but script not found"

**Solution**:
1. Compile script: `scripts/autoit/compile.bat`
2. Or copy pre-compiled `sf2_loader.exe` to `scripts/autoit/`
3. Verify: `dir scripts\autoit\sf2_loader.exe`

---

## Configuration Options

### Enable/Disable AutoIt

**Edit** `config/sf2_automation.ini`:

```ini
[AutoIt]
# Set to false to force manual workflow
enabled = true  # or false
```

### Adjust Timeouts

```ini
[AutoIt]
# Increase if file loading is slow
timeout = 60  # seconds

[Validation]
# Increase if file loads slowly
file_load_timeout = 30  # seconds
```

### Configure Logging

```ini
[Logging]
enabled = true
level = INFO  # or DEBUG for troubleshooting
log_file = logs/sf2_automation.log
```

---

## Distribution

### Option 1: Full Source Distribution

Include all files from the project. Users compile AutoIt themselves.

**Pros**: Full control, can modify scripts
**Cons**: Requires AutoIt installation

---

### Option 2: Pre-compiled Distribution

Include pre-compiled `sf2_loader.exe`.

**Pros**: No AutoIt installation required
**Cons**: Users can't modify AutoIt script

**Package**:
```
SIDM2/
├── scripts/autoit/
│   ├── sf2_loader.exe     # Pre-compiled
│   ├── sf2_loader.au3     # Source (optional)
│   ├── compile.bat        # Optional
│   └── README.md
├── config/
│   └── sf2_automation.ini
├── sidm2/
│   ├── automation_config.py
│   └── sf2_editor_automation.py
└── pyscript/
    ├── test_autoit_integration.py
    └── example_autoit_usage.py
```

---

## Version Information

- **AutoIt Script Version**: 1.0.0
- **Configuration Version**: 1.0.0
- **Python Bridge Version**: 1.0.0
- **Deployment Guide Version**: 1.0.0
- **Last Updated**: 2025-12-26

---

## Support

For issues or questions:
- See: `docs/guides/SF2_EDITOR_AUTOIT_HYBRID_GUIDE.md`
- See: `scripts/autoit/README.md`
- Create issue at: https://github.com/MichaelTroelsen/SIDM2conv/issues

---

## Next Steps

After successful deployment:

1. **Review documentation**:
   - `docs/guides/SF2_EDITOR_AUTOIT_HYBRID_GUIDE.md` - Complete guide
   - `docs/guides/SF2_EDITOR_MANUAL_WORKFLOW_GUIDE.md` - Manual workflow
   - `scripts/autoit/README.md` - AutoIt details

2. **Try examples**:
   - Run: `python pyscript/example_autoit_usage.py`
   - Try all 4 examples (auto-detect, force AutoIt, manual, batch)

3. **Integrate into workflow**:
   - Use `SF2EditorAutomation` in your scripts
   - Enable automated validation
   - Build batch processing pipelines

---

**Deployment Complete!**

You now have a fully functional AutoIt hybrid automation system for SID Factory II.
