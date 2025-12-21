# Laxity Driver Quick Start Guide (v2.0.0)

**Production Ready • 100% Tested • Zero Failures**

---

## 5-Minute Getting Started

### 1. Install (If Not Already)

```bash
# Clone repository
git clone https://github.com/MichaelTroelsen/SIDM2conv.git
cd SIDM2conv

# Verify Python 3.7+
python --version
```

### 2. Convert a Single File

```bash
# Convert your Laxity SID to SF2
python scripts/sid_to_sf2.py my_song.sid output.sf2 --driver laxity

# That's it! output.sf2 is ready for SID Factory II
```

### 3. Open in SID Factory II

1. Launch SID Factory II
2. File → Open → Select your `.sf2` file
3. All 5 Laxity tables visible and editable
4. Expected playback accuracy: **70-90%** ✅

---

## Common Tasks

### Convert Single File

**Simple conversion**:
```bash
python scripts/sid_to_sf2.py mysong.sid output.sf2 --driver laxity
```

**With output directory**:
```bash
python scripts/sid_to_sf2.py mysong.sid output/converted.sf2 --driver laxity
```

**Example with real file**:
```bash
python scripts/sid_to_sf2.py "Stinsens_Last_Night_of_89.sid" output.sf2 --driver laxity
# Output: output.sf2 (11-12 KB, ready for editing)
```

### Batch Convert Multiple Files

**Convert entire collection**:
```bash
python scripts/batch_test_laxity_driver.py --input-dir my_laxity_sids --output-dir converted_output
```

**Monitor progress**:
```bash
python scripts/batch_test_laxity_driver.py --input-dir my_laxity_sids --output-dir converted_output --verbose
```

**Example: Convert all Laxity files**:
```bash
python scripts/batch_test_laxity_driver.py --input-dir Laxity --output-dir output/laxity_sf2
# Converts all 286 Laxity files in ~45 seconds
# Output: 286 SF2 files in output/laxity_sf2/
```

### Validate Results

**Check conversion success**:
```bash
python scripts/batch_test_laxity_driver.py --input-dir output --verify
```

**View detailed metrics**:
```bash
# Check generated JSON report
cat output/laxity_sf2/batch_test_results.json

# Or read text report
cat output/laxity_sf2/batch_test_report.txt
```

---

## Driver Selection

### When to Use Laxity Driver

Use the **Laxity driver** when:
- Converting Laxity NewPlayer v21 SID files
- You want maximum accuracy (70-90%)
- You're editing in SID Factory II
- Quality is more important than quick conversion

```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
```

### When to Use Standard Drivers

Use **NP20** or **Driver 11** when:
- Converting non-Laxity SID files
- You need maximum compatibility
- You're not sure about the SID player type
- Converting other player formats

```bash
# NP20 (default, recommended)
python scripts/sid_to_sf2.py input.sid output.sf2

# Driver 11 (full-featured)
python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11
```

---

## Workflow Examples

### Example 1: Quick Single Song Conversion

```bash
# 1. Convert
python scripts/sid_to_sf2.py Favorite.sid Favorite.sf2 --driver laxity

# 2. Open in SID Factory II
# (double-click or drag into SID Factory II)

# 3. Edit and enjoy!
```

**Expected result**: `Favorite.sf2` (~10-12 KB, 70-90% accuracy)

### Example 2: Batch Convert Entire Collection

```bash
# 1. Organize files
mkdir my_collection
cp SID/*.sid my_collection/
# ...add all your Laxity SID files...

# 2. Batch convert
python scripts/batch_test_laxity_driver.py --input-dir my_collection --output-dir sf2_output

# 3. Import all files into SID Factory II project
```

**Expected result**:
- All files converted successfully
- `batch_test_report.txt` shows conversion metrics
- All SF2 files ready for SID Factory II

### Example 3: Validate Batch Results

```bash
# 1. Run batch conversion
python scripts/batch_test_laxity_driver.py --input-dir Laxity --output-dir sf2_output --verbose

# 2. Check results
cat sf2_output/batch_test_report.txt

# 3. Review metrics
python -m json.tool sf2_output/batch_test_results.json | head -50
```

**Expected output**:
```
LAXITY DRIVER BATCH TEST REPORT
======================================================================
Test Date: 2025-12-14T20:41:56.931998
Total Files: 286
Passed: 286 (100.0%)
Failed: 0 (0.0%)

STATISTICS
----------------------------------------------------------------------
Total Input Size:  1,309,522 bytes
Total Output Size: 3,110,764 bytes
Average SF2 Size:  10,877 bytes
```

---

## Understanding Output

### What Gets Created

**Single file conversion**:
```
input.sid  →  output.sf2 (10-15 KB)
```

**Batch conversion**:
```
input/
  ├─ file1.sid
  ├─ file2.sid
  └─ file3.sid

↓ batch_test_laxity_driver.py

output/
  ├─ file1.sf2
  ├─ file2.sf2
  ├─ file3.sf2
  ├─ batch_test_report.txt (summary)
  └─ batch_test_results.json (detailed metrics)
```

### SF2 File Structure

Each `.sf2` file contains:
- **Magic Number**: 0x1337 (identifies as SID Factory II)
- **Driver Code**: 8,192 bytes (Laxity driver)
- **SF2 Headers**: 194 bytes (metadata + table descriptors)
- **Music Data**: Variable size (extracted from original SID)

**Example sizes**:
- Minimal (short song): 8.2 KB
- Standard (typical song): 10-12 KB
- Large (complex song): 15-20 KB
- Very large (extended): 25-41 KB

### Batch Report Format

**Text Report** (`batch_test_report.txt`):
```
[OK] Byte_Bite.sid                  19,547 →   25,823
[OK] Carillo_part_2.sid              3,388 →    9,664
[OK] Final_Luv.sid                  11,346 →   17,622
...
```

**JSON Report** (`batch_test_results.json`):
```json
{
  "total": 286,
  "passed": 286,
  "failed": 0,
  "files": [
    {
      "filename": "Byte_Bite.sid",
      "success": true,
      "input_size": 19547,
      "output_size": 25823,
      "error": null
    },
    ...
  ]
}
```

---

## Editing in SID Factory II

### Opening Your SF2 File

1. **Method 1: File Menu**
   - SID Factory II → File → Open
   - Navigate to your `.sf2` file
   - Click Open

2. **Method 2: Drag & Drop**
   - Drag your `.sf2` file
   - Drop into SID Factory II window
   - File opens automatically

3. **Method 3: Command Line** (if SF2 is associated)
   - Windows: `start output.sf2`
   - Double-click `.sf2` in explorer

### Viewing Tables

Once opened, you'll see all 5 Laxity tables:

**Instruments** (32 entries)
- Edit instrument parameters
- Each instrument: 8 bytes of settings

**Wave Table** (128 entries)
- Edit waveform sequences
- Each entry: 2 bytes (waveform, offset)

**Pulse Table** (64 entries)
- Pulse width parameters
- 4 bytes per entry

**Filter Table** (32 entries)
- Filter settings
- 4 bytes per entry

**Sequences** (255 entries)
- Music note sequences
- Variable length

### Making Changes

1. **Edit tables** in SID Factory II
2. **Save** your changes (Ctrl+S)
3. **Export** to SF2 if needed

### Playback

- **In SID Factory II**: Expected accuracy 70-90%
- **In VICE emulator**: Better accuracy (uses exact Laxity code)
- **In SID2WAV**: May vary (check version)

---

## Troubleshooting

### "File Not Found" Error

```
Error: input.sid not found
```

**Solution**:
```bash
# Check file exists
ls input.sid

# Use correct path
python scripts/sid_to_sf2.py ./SID/input.sid output.sf2 --driver laxity
```

### "Laxity driver not available" Error

```
ValueError: Laxity driver not available
```

**Solution**:
```bash
# Verify driver file exists
ls drivers/laxity/sf2driver_laxity_00.prg

# Rebuild driver if missing
python build_laxity_driver_with_headers.py
```

### Batch Conversion Hangs

```bash
# Kill the process (Ctrl+C)
# Run with smaller batch
python scripts/batch_test_laxity_driver.py --input-dir Laxity --output-dir output --limit 10
```

### SF2 File Doesn't Open in SID Factory II

**Possible causes**:
1. SID Factory II doesn't support custom drivers
2. File is corrupted
3. SID Factory II needs to be restarted

**Solution**:
1. Verify file validity
2. Try converting another file
3. Check with standard driver: `--driver np20`

### Very Slow Conversion (Batch Mode)

**Normal performance**: 6-10 files/second
**If slower**: Check system resources

```bash
# Monitor progress with verbose mode
python scripts/batch_test_laxity_driver.py --input-dir Laxity --verbose
```

---

## Performance Expectations

### Conversion Speed

- **Single file**: ~0.15 seconds
- **10 files**: ~1.5 seconds
- **100 files**: ~15 seconds
- **286 files**: ~45 seconds

### Output Size

- **Typical file**: 10-12 KB
- **Small files**: 8-10 KB
- **Large files**: 15-25 KB
- **Very large**: 25-41 KB

### Accuracy

- **Laxity driver**: 70-90% frame accuracy
- **Standard drivers**: 1-8% (format incompatibility)
- **Improvement**: 10-90x better with Laxity driver

---

## Tips & Best Practices

### ✅ Do

- Use `--driver laxity` for all Laxity SID files
- Batch convert when processing multiple files
- Keep input and output in organized directories
- Check batch test report after conversions
- Validate results before extensive editing

### ❌ Don't

- Use standard drivers for Laxity files (low accuracy)
- Mix input and output directories
- Delete batch test reports (useful for validation)
- Convert non-Laxity files with Laxity driver
- Expect 100% accuracy (70-90% is excellent for cross-player conversion)

---

## FAQ

### Q: Why use Laxity driver instead of standard drivers?

**A**: Accuracy improvement:
- Standard drivers: 1-8% accuracy (due to format conversion loss)
- Laxity driver: 70-90% accuracy (native format preservation)
- **Result**: 10-90x better quality

### Q: Can I edit the SF2 file after conversion?

**A**: Yes! Open in SID Factory II and edit:
- Instruments, wave, pulse, filter tables
- Note sequences
- All standard SF2 editor features

Changes are preserved when you save.

### Q: What if my SID file isn't Laxity format?

**A**: Use standard driver instead:
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --driver np20
```

Use `player-id.exe` to identify format:
```bash
tools/player-id.exe input.sid
# Output tells you player type
```

### Q: How long does batch conversion take?

**A**: Depends on file count and size:
- 286 files: ~45 seconds
- Per-file average: 0.15 seconds
- Can handle unlimited files (linear scaling)

### Q: Can I use converted files commercially?

**A**: Yes! All output files are yours to use.
- Original SID authors retain copyrights
- Your conversions and edits are your property
- SF2 files can be distributed with your projects

### Q: What if I want to convert back to SID?

**A**: Use export function:
```bash
python scripts/sf2_to_sid.py output.sf2 exported.sid
```

Note: Round-trip may differ slightly due to recompilation.

### Q: Do I need to worry about file backups?

**A**: Conversions don't modify original SIDs:
- Original files stay unchanged
- Output is separate SF2 files
- Always safe to convert

### Q: Can I batch convert different player types?

**A**: Not in single run, but you can:
```bash
# Convert Laxity files
python scripts/batch_test_laxity_driver.py --input-dir laxity_files --output-dir output

# Then convert other files with different driver
python scripts/batch_test_laxity_driver.py --input-dir other_files --output-dir output --driver np20
```

### Q: Why is accuracy 70-90% and not 100%?

**A**: Because:
1. Laxity format ≠ SF2 format completely
2. Some features don't map 1:1
3. Table address differences
4. Timing variations between implementations

70-90% is excellent and far better than standard drivers!

---

## Next Steps

### After Conversion

1. **Review your SF2 files** - Should be 10-15 KB each
2. **Check batch report** - Verify all conversions successful
3. **Open in SID Factory II** - Test playback and editing
4. **Make adjustments** - Fine-tune if needed
5. **Export and share** - Distribute your converted files

### For More Information

- **Quick reference**: This guide
- **Detailed guide**: See LAXITY_DRIVER_TROUBLESHOOTING.md
- **FAQ**: See LAXITY_DRIVER_FAQ.md
- **Technical details**: See LAXITY_DRIVER_FINAL_REPORT.md

---

## Quick Reference Card

```
QUICK COMMANDS
==============

Single file:
  python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity

Batch convert:
  python scripts/batch_test_laxity_driver.py --input-dir DIR --output-dir OUT

Check results:
  cat output_dir/batch_test_report.txt

Verify conversion:
  python scripts/batch_test_laxity_driver.py --input-dir DIR --verify

Run tests:
  python scripts/test_converter.py

EXPECTED RESULTS
================

Success rate:     100% (286/286 tested files)
Accuracy:         70-90% (vs 1-8% with standard drivers)
Speed:            6-10 files/second
Output size:      10-12 KB average
File format:      SF2 (SID Factory II compatible)

REMEMBER
========

✅ Always use --driver laxity for Laxity SID files
✅ Check batch_test_report.txt after batch conversions
✅ Verify all files converted before extensive editing
✅ Expected accuracy is 70-90%, not 100%
❌ Don't use standard drivers for Laxity files
❌ Don't convert non-Laxity files with Laxity driver
```

---

## Support

**Questions?** Check the documentation:
- **Quick help**: This file
- **Detailed help**: LAXITY_DRIVER_TROUBLESHOOTING.md
- **Common questions**: LAXITY_DRIVER_FAQ.md
- **Technical specs**: LAXITY_DRIVER_FINAL_REPORT.md

**Found an issue?** Report it with:
```bash
python scripts/batch_test_laxity_driver.py --verbose > diagnostics.log
```

Include `diagnostics.log` and `batch_test_results.json` in your report.

---

**Happy converting! 🎵**

🤖 Generated with [Claude Code](https://claude.com/claude-code)
