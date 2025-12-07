# SIDwinder Quick Reference

## Status

| Feature | Status | Notes |
|---------|--------|-------|
| 🔧 Disassemble | ✅ WORKING | Integrated in pipeline (Step 9) |
| 📊 Trace | ⚠️ NEEDS REBUILD | Integrated in pipeline (Step 6) |
| 🎮 Player | ✅ WORKING | Not in pipeline (manual use) |
| 📍 Relocate | ✅ WORKING | Not in pipeline (manual use) |

---

## Commands

### Disassemble (WORKING - In Pipeline)
```bash
# Basic usage
tools/SIDwinder.exe -disassemble input.sid output.asm

# Example
tools/SIDwinder.exe -disassemble SID/Angular.sid output/Angular.asm

# Output: KickAssembler-compatible .asm file
```

### Trace (NEEDS REBUILD - In Pipeline)
```bash
# Text format (recommended) - .txt extension
tools/SIDwinder.exe -trace=output.txt input.sid

# Binary format - .bin extension
tools/SIDwinder.exe -trace=output.bin input.sid

# Custom duration (30 seconds = 1500 frames @ 50Hz)
tools/SIDwinder.exe -trace=output.txt -seconds=30 input.sid

# Example
tools/SIDwinder.exe -trace=angular.txt SID/Angular.sid
```

**Current behavior:** Files created but only contain "FRAME: " markers (empty)
**After rebuild:** Will contain register write data:
```
FRAME: D400:$29,D401:$FD,D404:$11,D405:$03,D406:$F8,...
FRAME: D400:$7B,D401:$05,D404:$41,...
```

### Player (WORKING - Manual)
```bash
# Default player (SimpleRaster)
tools/SIDwinder.exe -player music.sid music.prg

# Specific player
tools/SIDwinder.exe -player=RaistlinBars music.sid music.prg
tools/SIDwinder.exe -player=SimpleBitmap music.sid music.prg

# With custom logo
tools/SIDwinder.exe -player=RaistlinBarsWithLogo \
  -define KoalaFile="logo.kla" music.sid music.prg

# Custom player address
tools/SIDwinder.exe -player -playeraddr=$3000 music.sid music.prg
```

**Available Players:**
- `SimpleRaster` - Default raster player
- `SimpleBitmap` - Bitmap-based player
- `RaistlinBars` - Spectrum analyzer
- `RaistlinBarsWithLogo` - With logo support
- `RaistlinMirrorBarsWithLogo` - Mirrored bars

### Relocate (WORKING - Manual)
```bash
# Basic relocation
tools/SIDwinder.exe -relocate=$2000 input.sid output.sid

# Skip verification (faster)
tools/SIDwinder.exe -relocate=$3000 -noverify input.sid output.sid

# With metadata override
tools/SIDwinder.exe -relocate=$2000 \
  -sidname="New Title" \
  -sidauthor="New Author" \
  input.sid output.sid
```

---

## Common Options

### Metadata Overrides
```bash
-sidname="Song Title"           # Override title
-sidauthor="Artist Name"        # Override author
-sidcopyright="(C) 2025 Name"   # Override copyright
```

### General Options
```bash
-verbose                # Verbose output
-force                  # Overwrite existing files
-log=file.log          # Custom log file
-frames=N              # Number of frames (for trace)
```

---

## Pipeline Integration

### Automatic Usage

The pipeline uses SIDwinder automatically in **2 places**:

#### Step 6: Trace Generation (files created, empty until rebuild)
```python
# Original SID trace
generate_sidwinder_trace(sid_file, original_trace, seconds=30)
# Output: output/{song}/Original/{song}_original.txt

# Exported SID trace
generate_sidwinder_trace(exported_sid, exported_trace, seconds=30)
# Output: output/{song}/New/{song}_exported.txt
```

#### Step 9: Disassembly Generation (working for original SIDs)
```python
# Original SID disassembly (NEW - works perfectly)
generate_sidwinder_disassembly(sid_file, orig_asm_file)
# Output: output/{song}/Original/{song}_original_sidwinder.asm

# Exported SID disassembly (limited - packer bug)
generate_sidwinder_disassembly(exported_sid, exp_asm_file)
# Output: output/{song}/New/{song}_exported_sidwinder.asm
```

### Manual Testing

Test before rebuilding:
```bash
# Disassembly (works now)
tools/SIDwinder.exe -disassemble SID/Angular.sid test.asm
cat test.asm | head -50

# Trace (needs rebuild)
tools/SIDwinder.exe -trace=test.txt SID/Angular.sid
cat test.txt | head -50
# Currently shows only: FRAME: FRAME: FRAME: ...
# After rebuild shows: FRAME: D400:$29,D401:$FD,...
```

---

## File Locations

| File | Location | Purpose |
|------|----------|---------|
| Executable | `tools/SIDwinder.exe` | Main program |
| Source | `C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6\src\` | Source code |
| Patches | `tools/sidwinder_trace_fix.patch` | Trace fixes |
| Build script | `C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6\build.bat` | Rebuild |
| Config | `tools/SIDwinder.cfg` | Auto-generated config |
| Log | `tools/SIDwinder.log` | Error log |

---

## Rebuild (To Activate Trace)

**See SIDWINDER_REBUILD_GUIDE.md for complete instructions!**

**Quick rebuild:**
```cmd
# 1. Install CMake: https://cmake.org/download/
# 2. Install C++ compiler (Visual Studio Build Tools or MinGW)
# 3. Rebuild SIDwinder
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6
build.bat
copy build\Release\SIDwinder.exe C:\Users\mit\claude\c64server\SIDM2\tools\
```

**Verify trace is working:**
```bash
tools/SIDwinder.exe -trace=verify.txt SID/Angular.sid
grep -c "D400" verify.txt
# Should show: 1000+ (many register writes)
# Currently shows: 0 (no register writes, only "FRAME: " markers)
```

**Why rebuild is needed:**
- Source code IS patched with trace fixes (3 files)
- Executable (tools/SIDwinder.exe) is from BEFORE patches
- Needs rebuild to activate logWrite() functionality

---

## Output Formats

### Disassembly (.asm)
```asm
//; ------------------------------------------
//; Generated by SIDwinder 0.2.6
//; Name: Angular
//; Author: Thomas Mogensen (DRAX)
//; ------------------------------------------

.const SIDLoad = $1000
.const SID0 = $D400

* = SIDLoad
    jmp Label_0
    jmp Label_4
...
```

### Trace (.txt)
**After rebuild:**
```
FRAME: D400:$29,D401:$FD,D404:$11,D405:$03,D406:$F8,D407:$09,...
FRAME: D400:$7B,D401:$05,D404:$41,D407:$09,D408:$10,D40B:$10,...
```

**Current (before rebuild):**
```
FRAME:
FRAME:
FRAME:
```

### Trace (.bin)
- Binary format (4 bytes per record)
- Address (2) + Value (1) + Unused (1)
- Frame marker: 0xFFFFFFFF
- Currently: Only 0xFF bytes (empty frames)

---

## Troubleshooting

### Trace shows only "FRAME:" markers
**Cause:** Unpatched executable
**Fix:** Rebuild SIDwinder with patches

### "Unsupported output format" error
**Cause:** Internal bug (doesn't affect file generation)
**Fix:** Ignore error, check if file was created

### Empty trace file
**Cause:** Same as above
**Fix:** Rebuild needed

### Player files not found
**Cause:** Missing SIDPlayers directory
**Fix:** Ensure `tools/SIDPlayers/` exists

---

## Complete Pipeline Output

The complete pipeline generates **14 files per SID** (5 in Original/, 9 in New/):

### Original/ Directory (5 files)
1. `{filename}_original.dump` - Siddump register capture ✅
2. `{filename}_original.hex` - Binary hexdump (xxd) ✅
3. `{filename}_original.txt` - **SIDwinder trace** ⚠️ (empty until rebuild)
4. `{filename}_original.wav` - 30-second audio ✅
5. `{filename}_original_sidwinder.asm` - **SIDwinder disassembly** ✅

### New/ Directory (9 files)
1. `{filename}.sf2` - Converted SF2 file ✅
2. `{filename}_exported.sid` - Packed SID file ✅
3. `{filename}_exported.dump` - Siddump register capture ✅
4. `{filename}_exported.hex` - Binary hexdump ✅
5. `{filename}_exported.txt` - **SIDwinder trace** ⚠️ (empty until rebuild)
6. `{filename}_exported.wav` - 30-second audio ✅
7. `{filename}_exported_disassembly.md` - Python disassembly ✅
8. `{filename}_exported_sidwinder.asm` - **SIDwinder disassembly** ⚠️ (limited)
9. `info.txt` - Comprehensive conversion report ✅

**Status Legend:**
- ✅ Working perfectly
- ⚠️ Needs rebuild (trace) or limited by packer (disassembly)

---

## Tips

1. **Always use absolute paths** in Python scripts
2. **Ignore SIDwinder exit codes** - check file existence instead
3. **Text format preferred** for traces (easier to read/diff)
4. **30 seconds = 1500 frames** @ 50Hz PAL timing
5. **Compare with siddump** for validation
6. **Original SIDs disassemble perfectly** - exported SIDs have limitations

---

## Examples

### Complete Workflow
```bash
# 1. Disassemble (works now)
tools/SIDwinder.exe -disassemble SID/song.sid output/song.asm

# 2. Trace (after rebuild - see SIDWINDER_REBUILD_GUIDE.md)
tools/SIDwinder.exe -trace=output/song.txt -seconds=30 SID/song.sid

# 3. Create player (manual use)
tools/SIDwinder.exe -player=RaistlinBars SID/song.sid output/song.prg

# 4. Relocate (manual use)
tools/SIDwinder.exe -relocate=$2000 SID/song.sid output/song_relocated.sid
```

### Pipeline Equivalent
```bash
# Does disassemble + trace automatically (steps 6 & 9 in pipeline)
# Also does conversion, siddump, WAV, hexdump, info.txt, validation
python complete_pipeline_with_validation.py

# Generates 14 files per SID:
# - 5 files in Original/ (including SIDwinder disassembly & trace)
# - 9 files in New/ (including both Python & SIDwinder disassembly)
```

---

## Related Documentation

- **Rebuild Guide**: `SIDWINDER_REBUILD_GUIDE.md` - Complete CMake installation and build instructions
- **Integration Summary**: `SIDWINDER_INTEGRATION_SUMMARY.md` - Integration work summary
- **Pipeline Report**: `PIPELINE_EXECUTION_REPORT.md` - Latest execution results
- **Main Docs**: `README.md` (SIDwinder Integration section)
- **Technical Details**: `CLAUDE.md` (SIDwinder Tool Details section)
- **Documentation Index**: `COMPLETE_DOCUMENTATION_INDEX.md` - Navigation hub

---

*Quick Reference - Updated 2025-12-06 - Pipeline v1.2*
