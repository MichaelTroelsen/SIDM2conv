# SIDM2 Troubleshooting Guide

Complete troubleshooting guide for the SID to SF2 converter.

**Version**: v2.5.0
**Last Updated**: 2025-12-21

---

## Quick Diagnosis Checklist

Before diving into specific issues, try these quick checks:

- [ ] **File exists**: `dir SID\yourfile.sid` (Windows) or `ls SID/yourfile.sid` (Mac/Linux)
- [ ] **Valid SID file**: `tools\player-id.exe SID\yourfile.sid`
- [ ] **Dependencies installed**: `python -c "import sidm2"`
- [ ] **Python version**: `python --version` (should be 3.x)
- [ ] **Current directory**: You should be in the SIDM2 project root
- [ ] **Enable verbose logging**: Add `--verbose` to see detailed error messages

**Quick test command**:
```bash
python scripts/sid_to_sf2.py SID/Angular.sid test.sf2 --verbose
```

If this works, the issue is likely with your specific file or configuration.

---

## Common Errors by Category

### 1. File Not Found Issues

#### Error: "Input SID File Not Found"

**What it means**: The converter cannot find the SID file you specified.

**Common causes**:
- Typo in filename or path
- File is in a different directory
- Using relative path when absolute is needed
- Wrong current working directory

**Solutions**:

1. **Verify file exists**:
   ```bash
   # Windows
   dir SID\yourfile.sid

   # Mac/Linux
   ls SID/yourfile.sid
   ```

2. **Use absolute path**:
   ```bash
   # Windows
   python scripts/sid_to_sf2.py C:\full\path\to\file.sid output.sf2

   # Mac/Linux
   python scripts/sid_to_sf2.py /full/path/to/file.sid output.sf2
   ```

3. **Check current directory**:
   ```bash
   # Should be in SIDM2 project root
   pwd  # or cd on Windows
   ```

4. **List available files**:
   ```bash
   # Windows
   dir SID\*.sid

   # Mac/Linux
   ls SID/*.sid
   ```

#### Error: "Output Directory Does Not Exist"

**What it means**: The output directory doesn't exist and auto-creation is disabled.

**Solutions**:

1. **Create directory manually**:
   ```bash
   mkdir -p output/MySong/New  # Mac/Linux
   mkdir output\MySong\New     # Windows
   ```

2. **Enable auto-creation**:
   ```bash
   python scripts/sid_to_sf2.py input.sid output/MySong/New/output.sf2 --create-dirs
   ```

3. **Or configure in config file**:
   ```json
   {
     "output": {
       "create_dirs": true
     }
   }
   ```

#### Error: "SF2 Driver Template Not Found"

**What it means**: Required SF2 driver template file is missing from the repository.

**Solutions**:

1. **Verify repository structure**:
   ```bash
   dir G5\drivers\  # Windows
   ls G5/drivers/   # Mac/Linux
   ```

2. **Re-clone repository** if files are missing:
   ```bash
   git clone https://github.com/MichaelTroelsen/SIDM2conv.git
   ```

3. **Check for repository corruption**:
   ```bash
   git status
   git fsck
   ```

---

### 2. Invalid SID Files

#### Error: "Invalid Or Corrupted SID File"

**What it means**: The file is not a valid PSID/RSID format or is corrupted.

**Common causes**:
- File is not a SID file
- Download incomplete or corrupted
- Wrong file format (not PSID/RSID)
- File is compressed (.gz, .zip)

**Solutions**:

1. **Verify file type**:
   ```bash
   # Should show "PSID" or "RSID" at the beginning
   xxd SID/file.sid | head -1
   ```

2. **Check file size**:
   ```bash
   # Should be > 124 bytes (minimum SID header size)
   ls -lh SID/file.sid  # Mac/Linux
   dir SID\file.sid     # Windows
   ```

3. **Use player-id to verify**:
   ```bash
   tools/player-id.exe SID/file.sid
   ```

4. **Re-download from source**:
   - HVSC: https://www.hvsc.c64.org/
   - CSDb: https://csdb.dk/
   - Verify MD5 checksum if available

5. **Check for compression**:
   ```bash
   # Decompress if needed
   gunzip file.sid.gz
   unzip file.sid.zip
   ```

#### Error: "Unknown Magic Bytes"

**What it means**: File header doesn't match PSID or RSID format.

**Valid formats**:
- PSID (PlaySID format) - Most common
- RSID (RealSID format) - More accurate

**Check format**:
```bash
# First 4 bytes should be "PSID" or "RSID"
xxd SID/file.sid | head -1
# Should show: "50 53 49 44" (PSID) or "52 53 49 44" (RSID)
```

---

### 3. Missing Dependencies

#### Error: "Laxity Driver Not Available"

**What it means**: The Laxity converter module is not installed.

**Solutions**:

1. **Install package in development mode**:
   ```bash
   pip install -e .
   ```

2. **Verify installation**:
   ```bash
   python -c "import sidm2.laxity_converter; print('OK')"
   ```

3. **Alternative - Use standard drivers**:
   ```bash
   # Standard drivers have 1-8% accuracy for Laxity files
   # vs 99.93% with Laxity driver
   python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11
   ```

4. **Check Python path**:
   ```bash
   python -c "import sys; print('\n'.join(sys.path))"
   # Should include the SIDM2 directory
   ```

#### Error: "Galway Converter Not Available"

**What it means**: Martin Galway converter modules are not installed.

**Solutions**:

1. **Install package**:
   ```bash
   pip install -e .
   ```

2. **Verify installation**:
   ```bash
   python -c "import sidm2; print(hasattr(sidm2, 'MartinGalwayAnalyzer'))"
   # Should print True
   ```

3. **Alternative - Use standard drivers**:
   ```bash
   python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11
   ```

#### Error: "Module Not Found: sidm2"

**What it means**: The sidm2 package is not in Python's path.

**Solutions**:

1. **Run from project root**:
   ```bash
   cd /path/to/SIDM2
   python scripts/sid_to_sf2.py ...
   ```

2. **Install package**:
   ```bash
   pip install -e .
   ```

3. **Add to PYTHONPATH** (temporary):
   ```bash
   # Windows
   set PYTHONPATH=%CD%

   # Mac/Linux
   export PYTHONPATH=$(pwd)
   ```

---

### 4. Conversion Failures

#### Error: "Conversion Failed at Table Extraction"

**What it means**: Could not extract music tables from the SID file.

**Common causes**:
- Unsupported player format
- Memory layout different from expected
- Corrupted player code

**Solutions**:

1. **Check player type**:
   ```bash
   tools/player-id.exe SID/file.sid
   ```

2. **Supported formats**:
   - ✅ Laxity NewPlayer v21 (use `--driver laxity`)
   - ✅ SF2-exported SIDs (100% accuracy)
   - ⚠️ Other formats (experimental, use `--driver driver11`)

3. **Try different driver**:
   ```bash
   # Try Laxity driver
   python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity

   # Or standard driver
   python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11
   ```

4. **Enable verbose logging**:
   ```bash
   python scripts/sid_to_sf2.py input.sid output.sf2 --verbose
   # Check output for specific error details
   ```

5. **Check memory layout**:
   ```bash
   # Use siddump to inspect SID registers
   tools/siddump.exe input.sid -t10 > output.dump
   ```

#### Error: "Failed to Write SF2 File"

**What it means**: Could not write the output SF2 file.

**Common causes**:
- Permission denied
- Disk full
- Path too long (Windows)
- File is open in another program

**Solutions**:

1. **Check disk space**:
   ```bash
   df -h .  # Mac/Linux
   dir      # Windows (look at "bytes free")
   ```

2. **Check permissions**:
   ```bash
   # Try writing to a different directory
   python scripts/sid_to_sf2.py input.sid ~/output.sf2
   ```

3. **Close SID Factory II** if output file is open

4. **Shorten path** (Windows path length limit: 260 chars):
   ```bash
   # Instead of long path, use shorter
   python scripts/sid_to_sf2.py input.sid out.sf2
   ```

#### Error: "Accuracy Too Low"

**What it means**: Conversion succeeded but accuracy is below 70%.

**Expected accuracy**:
- SF2-exported SIDs: 100% (perfect roundtrip)
- Laxity NewPlayer v21 with Laxity driver: 99.93%
- Laxity NewPlayer v21 with standard drivers: 1-8%
- Other formats: Varies (experimental)

**Solutions**:

1. **Use correct driver for Laxity files**:
   ```bash
   # Check player type first
   tools/player-id.exe input.sid

   # If it's Laxity NewPlayer v21, use Laxity driver
   python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
   ```

2. **Verify player type matches driver**:
   - Laxity NewPlayer v21 → Use `--driver laxity`
   - Martin Galway → Use `--driver galway`
   - SF2-exported → Use `--driver driver11` (any driver works)
   - Unknown → Try `--driver driver11` (experimental)

3. **Check validation report**:
   ```bash
   python scripts/validate_sid_accuracy.py SID/original.sid output/exported.sid
   ```

---

### 5. Permission Problems

#### Error: "Cannot Create Output Directory"

**What it means**: Insufficient permissions to create the output directory.

**Solutions**:

1. **Windows - Run as Administrator** (if needed):
   - Right-click Command Prompt → "Run as administrator"

2. **Mac/Linux - Check permissions**:
   ```bash
   ls -ld output/
   # Should show write permissions
   ```

3. **Use a different output location**:
   ```bash
   # Write to your home directory instead
   python scripts/sid_to_sf2.py input.sid ~/SIDM2_output/output.sf2
   ```

4. **Fix permissions**:
   ```bash
   # Mac/Linux
   chmod 755 output/

   # Windows - Properties → Security → Edit permissions
   ```

#### Error: "Output File Already Exists"

**What it means**: File exists and overwrite protection is enabled.

**Solutions**:

1. **Use --overwrite flag**:
   ```bash
   python scripts/sid_to_sf2.py input.sid output.sf2 --overwrite
   ```

2. **Delete existing file**:
   ```bash
   rm output.sf2  # Mac/Linux
   del output.sf2 # Windows
   ```

3. **Use different output name**:
   ```bash
   python scripts/sid_to_sf2.py input.sid output_v2.sf2
   ```

4. **Configure overwrite in config**:
   ```json
   {
     "output": {
       "overwrite": true
     }
   }
   ```

---

### 6. Platform-Specific Issues

#### Windows Issues

**Problem: "Access is denied"**

Solution:
```cmd
# Run Command Prompt as Administrator
# Or use a directory you have write access to
python scripts/sid_to_sf2.py input.sid %USERPROFILE%\output.sf2
```

**Problem: "Path too long"**

Solution:
```cmd
# Enable long paths in Windows 10+
# Or use shorter paths
cd C:\SIDM2
python scripts/sid_to_sf2.py input.sid out.sf2
```

**Problem: "tools/siddump.exe not found"**

Solution:
```cmd
# Use backslashes on Windows
dir tools\siddump.exe

# Or use forward slashes (Python accepts both)
dir tools/siddump.exe
```

**Problem: Unicode characters in error messages show as �**

Solution:
```cmd
# Set console to UTF-8
chcp 65001

# Or ignore - it's just a display issue, functionality works
```

#### Mac/Linux Issues

**Problem: "Permission denied" when running tools**

Solution:
```bash
# Make tools executable
chmod +x tools/siddump.exe
chmod +x tools/player-id.exe
chmod +x tools/SID2WAV.EXE

# Or run through wine (if needed)
wine tools/siddump.exe input.sid
```

**Problem: "Command not found: python"**

Solution:
```bash
# Try python3 instead
python3 scripts/sid_to_sf2.py input.sid output.sf2

# Or create alias
alias python=python3
```

**Problem: "No module named 'sidm2'"**

Solution:
```bash
# Ensure you're in project root
cd /path/to/SIDM2

# Install package
pip3 install -e .

# Or set PYTHONPATH
export PYTHONPATH=$(pwd)
```

---

## Debug Mode Instructions

### Enable Verbose Logging

```bash
# Add --verbose flag for detailed output
python scripts/sid_to_sf2.py input.sid output.sf2 --verbose
```

**What verbose mode shows**:
- File paths being accessed
- Memory addresses being read
- Table extraction details
- Conversion step-by-step progress
- Warning and debug messages

### Generate Debug Reports

```bash
# Complete pipeline with full validation
python complete_pipeline_with_validation.py

# Check output directory for debug files:
# - *_analysis_report.txt - Player analysis
# - *_original.dump - SID register dump
# - *_exported.dump - Converted register dump
# - *.hex - Hex dumps
# - info.txt - Conversion summary
```

### Enable Python Debug Mode

```bash
# Run with Python debugger
python -m pdb scripts/sid_to_sf2.py input.sid output.sf2

# Or add breakpoint in code
import pdb; pdb.set_trace()
```

### Check Validation Results

```bash
# Run validation system
python scripts/run_validation.py --notes "Debug run"

# View interactive dashboard
# Open: validation/dashboard.html
```

---

## Frequently Asked Questions (FAQ)

### General Questions

**Q: What SID formats are supported?**

A:
- ✅ **Laxity NewPlayer v21** - 99.93% accuracy with `--driver laxity`
- ✅ **SF2-exported SIDs** - 100% accuracy (perfect roundtrip)
- ⚠️ **Other formats** - Experimental, use `--driver driver11`

**Q: Why is my conversion accuracy low?**

A: Make sure you're using the correct driver:
```bash
# Check player type
tools/player-id.exe input.sid

# If Laxity NewPlayer v21, use:
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
# Expected accuracy: 99.93%

# If using standard driver on Laxity files:
# Expected accuracy: 1-8% (format incompatibility)
```

**Q: How do I know if conversion was successful?**

A: Check the output:
- No error messages = success
- Check `info.txt` for warnings
- Run validation: `python scripts/validate_sid_accuracy.py original.sid exported.sid`
- Listen to both WAV files for comparison

**Q: Can I convert multiple files at once?**

A: Yes, use the batch converter:
```bash
# Convert all SIDs in directory
python scripts/convert_all.py

# Or with custom output
python scripts/convert_all.py --output-dir custom_output/
```

### Error-Specific Questions

**Q: "FileNotFoundError" but file exists**

A: Check:
1. File path is correct (case-sensitive on Mac/Linux)
2. You're in the project root directory
3. No special characters in filename
4. Use absolute path to be sure

**Q: "Module not found" errors**

A: Install dependencies:
```bash
# Install in development mode
pip install -e .

# Or manually add to path
export PYTHONPATH=$(pwd)  # Mac/Linux
set PYTHONPATH=%CD%       # Windows
```

**Q: Output SF2 doesn't play in SID Factory II**

A:
1. Check file size (should be > 8KB)
2. Verify it's a valid SF2 file (check header)
3. Try different driver: `--driver driver11`
4. Check for conversion errors in output

**Q: "Permission denied" on output**

A:
1. Close SID Factory II if file is open
2. Check directory permissions
3. Try different output location
4. Use `--overwrite` if updating existing file

### Performance Questions

**Q: Conversion is slow**

A: Normal conversion should take < 1 second per file. If slow:
1. Disable siddump extraction: Set `config.extraction.use_siddump=false`
2. Use standard drivers instead of Laxity/Galway
3. Check system resources (CPU, disk)
4. Large files (>20KB) take longer

**Q: Validation takes forever**

A: Validation with 30-second duration is CPU-intensive:
1. Use shorter duration: `--duration 10`
2. Use quick validation: `scripts/run_validation.py --quick`
3. Skip validation if not needed

---

## Getting More Help

### Documentation

- **Quick Start**: `README.md#quick-start`
- **Complete Guide**: `CLAUDE.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Laxity Driver**: `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md`
- **Error Reference**: `docs/COMPONENTS_REFERENCE.md#error-handling-module`

### Community & Support

- **GitHub Issues**: https://github.com/MichaelTroelsen/SIDM2conv/issues
- **Bug Reports**: Include verbose output + file details
- **Feature Requests**: Describe use case + expected behavior

### Diagnostic Information to Include

When reporting issues, include:

1. **Command used**:
   ```bash
   python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity --verbose
   ```

2. **Error message** (full output)

3. **File information**:
   ```bash
   tools/player-id.exe input.sid
   ```

4. **System information**:
   ```bash
   python --version
   pip list | grep sidm2  # or findstr on Windows
   ```

5. **Verbose output** (if available)

6. **Platform**: Windows/Mac/Linux + version

### Quick Diagnostic Script

```bash
# Save as check_system.sh (Mac/Linux) or check_system.bat (Windows)
echo "=== SIDM2 Diagnostics ==="
echo ""
echo "Python version:"
python --version
echo ""
echo "Current directory:"
pwd  # or cd on Windows
echo ""
echo "SIDM2 package:"
python -c "import sidm2; print('OK')" 2>&1
echo ""
echo "Laxity converter:"
python -c "import sidm2.laxity_converter; print('OK')" 2>&1
echo ""
echo "Tools:"
ls tools/*.exe  # or dir tools\*.exe on Windows
echo ""
echo "Test SID files:"
ls SID/*.sid | head -5  # or dir SID\*.sid on Windows
```

---

## Quick Reference

### Most Common Commands

```bash
# Basic conversion
python scripts/sid_to_sf2.py input.sid output.sf2

# Laxity SID (99.93% accuracy)
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity

# With verbose output
python scripts/sid_to_sf2.py input.sid output.sf2 --verbose

# Overwrite existing
python scripts/sid_to_sf2.py input.sid output.sf2 --overwrite

# Batch convert all
python scripts/convert_all.py

# Validate conversion
python scripts/validate_sid_accuracy.py original.sid exported.sid
```

### Most Common Fixes

| Error | Quick Fix |
|-------|-----------|
| File not found | Use absolute path: `python scripts/sid_to_sf2.py C:\full\path\file.sid output.sf2` |
| Module not found | Install: `pip install -e .` |
| Permission denied | Add `--overwrite` or close SID Factory II |
| Low accuracy | Use `--driver laxity` for Laxity files |
| Missing template | Re-clone repository: `git clone ...` |
| Output exists | Add `--overwrite` flag |

---

**Document Version**: v2.5.0
**Last Updated**: 2025-12-21
**Related**: `UX_IMPROVEMENT_PLAN.md`, `sidm2/errors.py`, `README.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
