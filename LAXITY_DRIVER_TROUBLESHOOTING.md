# Laxity Driver Troubleshooting Guide

**Version**: 1.8.0
**Last Updated**: 2025-12-14
**Status**: Production Ready

---

## Quick Diagnosis Checklist

Before deep diving into specific issues, run through this checklist:

- [ ] Python 3.7+ installed? (`python --version`)
- [ ] Working directory is `SIDM2/`? (`cd SIDM2`)
- [ ] SID file exists at specified path?
- [ ] Output directory writable?
- [ ] Enough disk space (>100 MB available)?
- [ ] Can read SID file? (`ls -la your_file.sid`)
- [ ] File is Laxity format? (Use `player-id.exe` to verify)

---

## Installation Issues

### Issue 1: "Python not found" or "python not recognized"

**Error Message**:
```
'python' is not recognized as an internal or external command
```

**Root Cause**: Python not installed or not in system PATH

**Solution**:

1. **Install Python**:
   - Download from https://www.python.org/downloads/ (3.9+ recommended)
   - Check "Add Python to PATH" during installation
   - Restart terminal/command prompt

2. **Verify Installation**:
   ```bash
   python --version
   python -c "print('Python is working')"
   ```

3. **Alternative**: Use full path to Python
   ```bash
   C:\Python312\python.exe scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
   ```

4. **On Windows**: Use `py` launcher (if installed with Python)
   ```bash
   py -3 scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
   ```

---

### Issue 2: "Module not found: sidm2"

**Error Message**:
```
ModuleNotFoundError: No module named 'sidm2'
```

**Root Cause**: Working directory is not SIDM2 root

**Solution**:

1. **Verify Working Directory**:
   ```bash
   pwd  # On Linux/Mac
   cd   # On Windows (shows current directory)
   ```

2. **Must be in SIDM2 directory**:
   ```bash
   cd C:\Users\mit\claude\c64server\SIDM2
   ```

3. **Verify Structure**:
   ```bash
   ls -la scripts/sid_to_sf2.py  # Should exist
   ls -la sidm2/                  # Should exist
   ```

---

## Conversion Issues

### Issue 3: "File not found"

**Error Message**:
```
FileNotFoundError: Input file not found: my_music.sid
ERROR: Cannot find input file: my_music.sid
```

**Root Cause**: File path incorrect or file doesn't exist

**Solution**:

1. **Check File Exists**:
   ```bash
   ls Laxity/my_music.sid  # If in Laxity folder
   ls -la "C:\path\to\my_music.sid"  # Full path
   ```

2. **Use Correct Path**:
   ```bash
   # If file is in Laxity/ subdirectory
   python scripts/sid_to_sf2.py Laxity/my_music.sid output.sf2 --driver laxity

   # If using relative path
   python scripts/sid_to_sf2.py ./SID/my_music.sid output/my_music.sf2 --driver laxity

   # If using absolute path (most reliable)
   python scripts/sid_to_sf2.py "C:\Users\mit\claude\c64server\SIDM2\Laxity\my_music.sid" "C:\Users\mit\claude\c64server\SIDM2\output\my_music.sf2" --driver laxity
   ```

3. **Spaces in Path**: Use quotes
   ```bash
   python scripts/sid_to_sf2.py "My Music Folder/Song Title.sid" "output/Song Title.sf2" --driver laxity
   ```

4. **List Available Files**:
   ```bash
   ls Laxity/ | head -20  # Show first 20 files
   ls Laxity/ | wc -l     # Count total files
   ```

---

### Issue 4: "File not recognized as Laxity format"

**Error Message**:
```
WARNING: File may not be Laxity format
ERROR: Conversion failed - unsupported player type
```

**Root Cause**: SID file uses different player than Laxity NewPlayer v21

**Solution**:

1. **Verify Player Type**:
   ```bash
   tools/player-id.exe Laxity/my_music.sid
   ```

   **Expected Output**:
   ```
   my_music.sid    Laxity NewPlayer v21
   ```

   **If you see something else**:
   - File is NOT Laxity format
   - Use standard driver instead: `--driver driver11` or `--driver np20`
   - See CLAUDE.md for supported formats

2. **Check Multiple Files**:
   ```bash
   for file in Laxity/*.sid; do
     echo -n "$file: "
     tools/player-id.exe "$file"
   done
   ```

3. **Batch Check**:
   ```bash
   # Identify all file types in collection
   tools/player-id.exe Laxity/*.sid | grep -v "Laxity"

   # Count Laxity files
   tools/player-id.exe Laxity/*.sid | grep "Laxity" | wc -l
   ```

---

### Issue 5: "Conversion timeout"

**Error Message**:
```
ERROR: Conversion timed out (30 seconds)
TIMEOUT: File took too long to convert
```

**Root Cause**:
- File is very large (rare)
- System is slow
- Disk I/O bottleneck

**Solution**:

1. **Increase Timeout** (edit script):
   ```python
   # In convert_all_laxity.py, change:
   timeout=30  # seconds
   # To:
   timeout=60  # Allow 60 seconds
   ```

2. **Try Single File First**:
   ```bash
   # Single file has no timeout
   python scripts/sid_to_sf2.py Laxity/big_file.sid output/big_file.sf2 --driver laxity
   ```

3. **Check System Resources**:
   ```bash
   # Windows: Check available disk space
   dir C:\  # Look at "bytes available"

   # Check available RAM
   tasklist  # See running processes
   ```

4. **Reduce Load** (skip batch conversion):
   ```bash
   # Instead of batch, convert one file at a time
   # This gives system more breathing room
   ```

---

### Issue 6: "Output file not created" or "Corrupted output"

**Error Message**:
```
ERROR: Output file not created
ERROR: Output file is 0 bytes
ERROR: SF2 format invalid
```

**Root Cause**:
- Disk full
- Permission denied
- Memory exhaustion
- Process crashed

**Solution**:

1. **Check Output Directory**:
   ```bash
   ls -la output/  # Should exist and be writable
   mkdir -p output  # Create if missing
   ```

2. **Check Disk Space**:
   ```bash
   # Windows: Check available space
   dir C:\  # Look for "bytes available"

   # Need at least 100 MB free
   # Each file: 8-41 KB, batch of 286: ~3.1 MB
   ```

3. **Check File Permissions**:
   ```bash
   # Try writing to output
   echo "test" > output/test.txt
   rm output/test.txt
   ```

4. **Verify Output File**:
   ```bash
   ls -la output/my_music.sf2  # Check size
   xxd output/my_music.sf2 | head -5  # Check header
   ```

5. **Try Verbose Mode**:
   ```bash
   python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity -v
   ```
   This shows more details about what's happening.

---

## Runtime Issues

### Issue 7: "Laxity converter not available"

**Error Message**:
```
ValueError: Laxity converter not available
ERROR: Cannot import LaxityConverter
```

**Root Cause**: `sidm2/laxity_converter.py` missing or not found

**Solution**:

1. **Verify File Exists**:
   ```bash
   ls -la sidm2/laxity_converter.py
   ```

2. **Check Imports**:
   ```bash
   python -c "from sidm2.laxity_converter import LaxityConverter; print('OK')"
   ```

3. **Verify Directory Structure**:
   ```bash
   ls -la sidm2/  # Should contain laxity_converter.py
   ```

4. **Reinstall** (if missing):
   ```bash
   # If accidentally deleted, check git
   git status sidm2/laxity_converter.py
   git restore sidm2/laxity_converter.py
   ```

---

### Issue 8: "Driver file not found"

**Error Message**:
```
ERROR: Driver file not found: drivers/laxity/sf2driver_laxity_00.prg
ValueError: Driver PRG missing
```

**Root Cause**: `drivers/laxity/sf2driver_laxity_00.prg` missing or wrong path

**Solution**:

1. **Verify Driver Exists**:
   ```bash
   ls -la drivers/laxity/sf2driver_laxity_00.prg
   ```

2. **Check Size** (should be ~8 KB):
   ```bash
   ls -lh drivers/laxity/sf2driver_laxity_00.prg
   # Should show: -rw-r--r-- ... 8192 ... sf2driver_laxity_00.prg
   ```

3. **If Missing, Restore**:
   ```bash
   git status drivers/laxity/
   git restore drivers/laxity/sf2driver_laxity_00.prg
   ```

4. **Verify File is Valid**:
   ```bash
   # Check file header (should start with specific bytes)
   xxd drivers/laxity/sf2driver_laxity_00.prg | head -3
   ```

---

## Batch Processing Issues

### Issue 9: "Batch conversion stops on first error"

**Error Message**:
```
[  1/286] Converting file...FAILED
[ERROR] Batch conversion terminated
```

**Root Cause**: Single file in batch causes entire batch to fail

**Solution**:

1. **Identify Problem File**:
   - Note the filename from error message
   - Try converting that file alone to see detailed error

2. **Skip Problem File**:
   ```bash
   # Edit convert_all_laxity.py:
   # Add file to skip list
   skip_files = {'problem_file.sid'}  # Add at line 15
   ```

3. **Run Batch Again**:
   ```bash
   python convert_all_laxity.py
   # Will skip problem file and continue
   ```

4. **Report Issue**:
   - Note the filename
   - Save the error message
   - Create GitHub issue if reproducible

---

### Issue 10: "Batch conversion too slow"

**Error Message** (not really an error, just slow):
```
[  1/286] (  0.3%) file.sid
[  2/286] (  0.7%) file.sid
... waiting forever ...
```

**Root Cause**: Slow system, disk bottleneck, or other processes consuming resources

**Solution**:

1. **Close Other Programs**:
   - Close browsers, IDE, other heavy processes
   - Check Task Manager for CPU/disk usage
   - Kill unnecessary background processes

2. **Check System Load**:
   ```bash
   # Windows: Task Manager
   tasklist | findstr python  # Show all Python processes

   # Expected speed: 8-10 files/second
   # If much slower, system is bottlenecked
   ```

3. **Run During Off-Hours**:
   - Batch conversion is network-friendly
   - Safe to run overnight
   - Run when system has fewer other tasks

4. **Monitor Progress**:
   - Script shows progress bar
   - 286 files = ~35 seconds on fast system
   - Should see visible progress each second

---

## Accuracy & Quality Issues

### Issue 11: "Conversion accuracy is low"

**Context**: "70-90% accuracy" is expected, not a bug

**If you're seeing <70% accuracy**:

1. **Verify You're Using Laxity Driver**:
   ```bash
   # Check command includes --driver laxity
   python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity

   # Not this (uses Driver 11):
   python scripts/sid_to_sf2.py input.sid output.sf2

   # Not this (uses NP20):
   python scripts/sid_to_sf2.py input.sid output.sf2 --driver np20
   ```

2. **Compare With Standard Drivers**:
   ```bash
   # Test with both drivers to see difference
   python scripts/sid_to_sf2.py input.sid output_laxity.sf2 --driver laxity
   python scripts/sid_to_sf2.py input.sid output_driver11.sf2 --driver driver11

   # Laxity should be noticeably better
   ```

3. **Expected Results**:
   - Laxity driver: 70-90% accuracy
   - Driver 11: 1-8% accuracy
   - NP20: 1-8% accuracy
   - If Laxity is not better, something is wrong

---

### Issue 12: "File plays but sounds different"

**This is Expected** (not a bug)

**Why Different?**
- Original uses Laxity player, SF2 uses different rendering
- Small differences in timing and effects are normal
- 70-90% accuracy means ~10-30% differences

**To Verify It's Working Correctly**:
1. Open SF2 in SID Factory II
2. Listen to both original and converted
3. Melody should be similar
4. Rhythm might be slightly different
5. Effects might not be exact

**If Completely Wrong**:
- See Issue 4: "File not recognized as Laxity format"
- May have used wrong driver

---

## Performance & Optimization

### Issue 13: "Want faster conversions"

**Current Performance**: 8.1 files/second (35.2 seconds for 286 files)

**Optimization Tips**:

1. **Use SSD** (if available):
   - Much faster than HDD
   - Can improve throughput 2-3x

2. **Close Other Programs**:
   - Reduces context switching
   - Frees up system memory
   - Can improve speed 10-20%

3. **Avoid Network Paths**:
   - Keep input/output on local disk
   - Network drives are much slower
   - Can reduce speed 50%+

4. **Check Disk Health**:
   ```bash
   # Windows: Disk utilities can show issues
   # Fragmented or failing disk = slower conversion
   ```

---

### Issue 14: "Memory usage seems high"

**Context**: Memory usage is very low (<50 MB typical)

**If Seeing >100 MB Memory Usage**:

1. **Check for Memory Leak**:
   ```bash
   # Run single file conversion
   python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
   # Should use <50 MB
   ```

2. **Monitor During Batch**:
   ```bash
   # On Windows: Open Task Manager
   # Watch Python process memory
   # Should stay <100 MB
   ```

3. **If Memory Usage Grows**:
   - May indicate memory leak
   - Try restarting Python
   - Run conversions in smaller batches

---

## Using Converted Files

### Issue 15: "Can't open SF2 in SID Factory II"

**Error Message**: "Invalid file format" or "Cannot open"

**Solution**:

1. **Verify SF2 File**:
   ```bash
   # Check file exists and has size
   ls -lh output/my_music.sf2
   # Should show size >8 KB (8192 bytes minimum)
   ```

2. **Try Different Method**:
   - File → Open (not Import)
   - Drag-drop onto SID Factory II window
   - Use command line to open

3. **Verify File Integrity**:
   ```bash
   # Check file is not corrupted
   xxd output/my_music.sf2 | head -10
   # Should show binary data, not garbled
   ```

4. **Update SID Factory II**:
   - Ensure using latest version
   - Older versions may not support Laxity driver
   - Check SIDM2 version requirements in README

---

### Issue 16: "Tables not editable in SF2 editor"

**This May Be Expected** (known limitation)

**Note**: Laxity driver v1.8.0 focuses on playback accuracy, table editing support is optional Phase 6 enhancement.

**Current Status**:
- Music plays correctly
- Tables readable by editor
- Direct editing not yet implemented

**Workaround**:
1. Play music in SF2 to verify correctness
2. Edit other aspects (sequences, instruments visible)
3. For Laxity-specific table editing, use original Laxity tools

---

## Getting Help

### Issue 17: "Problem not in this guide"

**Steps to Resolve**:

1. **Gather Information**:
   ```bash
   # Capture full error output
   python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity -v > error.log 2>&1

   # Get file information
   python -c "from sidm2.sid_parser import SIDParser; p = SIDParser('input.sid'); h = p.parse_header(); print(f'Player: {h.player_name}, Load: 0x{h.load_address:04X}')"
   ```

2. **Document the Issue**:
   - Exact command you ran
   - Full error message
   - System information (Python version, OS)
   - Input filename
   - Expected vs actual behavior

3. **Check Known Issues**:
   - See `CLAUDE.md` - Known Limitations section
   - See `README.md` for recent updates
   - Check git issues for similar problems

4. **Create GitHub Issue**:
   - Include all information above
   - Attach error logs if large
   - Mention which troubleshooting steps tried

---

## Quick Reference Table

| Issue | Quick Fix |
|-------|-----------|
| "Python not found" | Install Python 3.7+ and add to PATH |
| "Module not found: sidm2" | Change to SIDM2 directory: `cd SIDM2` |
| "File not found" | Use correct path: `python scripts/sid_to_sf2.py Laxity/file.sid output.sf2 --driver laxity` |
| "Not Laxity format" | Verify with `tools/player-id.exe file.sid` |
| "Conversion timeout" | Try single file: `timeout=60` or convert one-by-one |
| "Output file empty" | Check disk space: `dir C:\` (need 100 MB free) |
| "Driver not found" | Restore with `git restore drivers/laxity/` |
| "Batch too slow" | Close other programs, check Task Manager |
| "Low accuracy" | Verify using `--driver laxity` (not default driver) |
| "Can't open in SF2 editor" | Check file size: `ls -lh file.sf2` (>8KB) |

---

## Support Resources

- **Documentation**: See `LAXITY_DRIVER_QUICK_START.md` for basic usage
- **FAQ**: See `LAXITY_DRIVER_FAQ.md` for common questions
- **Technical Details**: See `LAXITY_DRIVER_FINAL_REPORT.md` for implementation
- **Project Guide**: See `CLAUDE.md` for AI assistant quick reference
- **Full Documentation**: See `README.md` for comprehensive documentation

---

**Still Having Issues?**

1. Reread the relevant section above
2. Check FAQ for your question
3. Review Quick Start guide for basic workflow
4. Run `python scripts/test_converter.py` to verify system integrity
5. Create GitHub issue with gathered information

Remember: Most issues can be resolved by using correct file paths, verifying file types, and ensuring sufficient disk space. The Laxity driver is production-ready and has 100% success on 286 test files.

