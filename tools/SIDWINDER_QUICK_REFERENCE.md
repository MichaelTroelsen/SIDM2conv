# SIDwinder v0.2.6 - Quick Reference Guide

**Analysis Date:** December 11, 2025

---

## Critical Discovery: Trace Bug Fixed in Source

**Status:** ✅ Fixed in source code (Dec 6, 2024) | ⚠️ Needs executable rebuild

**Three Bugs Fixed:**
1. `TraceLogger.cpp` - Added missing `logWrite()` method
2. `SIDEmulator.cpp` - Added trace logger callback in SID write handler
3. `SIDEmulator.cpp` - Added `|| options.traceEnabled` to enable callbacks for trace-only commands

**Action Required:**
```bash
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6
build.bat
copy build\Release\SIDwinder.exe C:\Users\mit\claude\c64server\SIDM2\tools\
```

---

## Command Quick Reference

### Disassembly ✅ WORKING
```bash
SIDwinder.exe -disassemble input.sid output.asm
```
- Generates KickAssembler source code
- Auto-generates labels
- Includes metadata as comments
- **Pipeline Status:** Integrated in Step 9

### Trace ⚠️ FIXED - NEEDS REBUILD
```bash
# Binary format (compact)
SIDwinder.exe -trace=output.bin input.sid

# Text format (readable)
SIDwinder.exe -trace=output.txt -traceformat=text input.sid

# Custom frame count
SIDwinder.exe -trace=output.bin -frames=1500 input.sid
```
- Records SID register writes frame-by-frame
- Binary: struct records with frame markers
- Text: `FRAME: D400:$00,D401:$08,D404:$11,...`
- **Pipeline Status:** Integrated in Step 6 (will work after rebuild)

### Player (Not Yet Integrated)
```bash
# Basic player
SIDwinder.exe -player input.sid output.prg

# Custom player with definitions
SIDwinder.exe -player=RaistlinBars -define BgColor=$02 input.sid output.prg

# With logo
SIDwinder.exe -player=RaistlinBarsWithLogo -define LogoFile="logo.kla" input.sid output.prg
```
- Creates standalone .prg with visualization
- Optional compression with Exomizer
- User-definable parameters

### Relocate (Not Yet Integrated)
```bash
# Simple relocation
SIDwinder.exe -relocate=$3000 -noverify input.sid output.sid

# With verification (trace comparison)
SIDwinder.exe -relocate=$3000 input.sid output.sid
```
- Moves SID to new memory address
- Optional trace-based verification
- Frame-by-frame difference reports

---

## Metadata Override Options

All commands support:
```bash
-sidname="Title"
-sidauthor="Author"
-sidcopyright="(C) 2025"
-sidloadaddr=$1000
-sidinitaddr=$1000
-sidplayaddr=$1003
```

---

## Configuration File: SIDwinder.cfg

**Location:** Current dir, exe dir, or `~/.config/SIDwinder/`

**Key Settings:**
```ini
logFile=SIDwinder.log
logLevel=3                    # 0-3 (Error to Debug)
emulationFrames=1500          # 30 sec @ 50Hz
playerName=RaistlinBars
playerAddress=$4000
kickAssPath=tools/KickAss.jar
exomizerPath=tools/exomizer.exe
```

---

## Integration Status in SIDM2 Pipeline

| Command | Status | Pipeline Step | Notes |
|---------|--------|---------------|-------|
| Disassembly | ✅ Working | Step 9 | Generates .asm files |
| Trace | ⚠️ Fixed, needs rebuild | Step 6 | Will work after rebuild |
| Player | ⏳ Available | - | Future integration opportunity |
| Relocate | ⏳ Available | - | Could validate packer |

---

## Why Rebuild Is Important

**Current State:**
- Trace files are generated but empty
- Pipeline shows "[WARN - needs rebuilt SIDwinder]"
- Missing validation data

**After Rebuild:**
- Complete frame-by-frame SID register traces
- Can compare original vs exported SIDs
- Debug packer pointer relocation issues
- Validate conversion accuracy

**Benefits:**
- Complete Step 6 of pipeline (currently incomplete)
- Enable trace comparison for validation
- Provide debugging data for "Execution at $0000" issues
- Improve conversion quality metrics

---

## Source Code Modifications (Dec 6, 2024)

### File 1: app/TraceLogger.cpp
**Added:** Public `logWrite()` method (lines 51-61)
```cpp
void TraceLogger::logWrite(u16 addr, u8 value) {
    if (!isOpen_) return;
    if (format_ == TraceFormat::Text) {
        writeTextRecord(addr, value);
    } else {
        TraceRecord record(addr, value);
        writeBinaryRecord(record);
    }
}
```

### File 2: SIDEmulator.cpp
**Change 1:** Added trace logging to callback (lines 52-55)
```cpp
// Log to trace file if tracing is enabled
if (options.traceEnabled && traceLogger_) {
    traceLogger_->logWrite(addr, value);
}
```

**Change 2:** Enable callback for trace commands (line 129)
```cpp
// Added: || options.traceEnabled
if (options.registerTrackingEnabled || options.patternDetectionEnabled || options.traceEnabled) {
```

---

## Future Integration Opportunities

### 1. Pattern Recognition
- Use `SIDPatternFinder` to improve table extraction
- Automatically identify music data structures
- Validate extraction accuracy

### 2. Trace Comparison
- Use `TraceLogger::compareTraceLogs()` for validation
- Frame-by-frame difference reports
- Debug packer issues

### 3. Player Generation
- Create standalone players from SF2 files
- Add visualization to exported SIDs
- Generate demo-ready .prg files

### 4. Relocation Verification
- Validate SF2→SID packing accuracy
- Ensure pointer relocations are correct
- Bit-perfect reproduction testing

---

## Verification After Rebuild

```bash
# Test trace functionality
tools/SIDwinder.exe -trace=test.txt -traceformat=text SID/Angular.sid

# Check output
cat test.txt
# Should contain: FRAME: D400:$00,D401:$08,...
# NOT empty!

# Run full pipeline
python complete_pipeline_with_validation.py

# Check trace files
ls output/SIDSF2player_Complete_Pipeline/*/Original/*_original.txt
ls output/SIDSF2player_Complete_Pipeline/*/New/*_exported.txt
# Should contain frame data, not be empty
```

---

## Summary

**SIDwinder Capabilities:**
- ✅ Professional 6502 disassembler with auto-labeling
- ✅ SID register trace logger (fixed, needs rebuild)
- ✅ Music player generator with visualization
- ✅ SID relocation with verification

**Immediate Action:**
1. Rebuild SIDwinder.exe to activate trace fixes
2. Verify trace output contains data
3. Complete pipeline Step 6 validation
4. Use trace comparison for packer debugging

**Long-Term Value:**
- Complete validation system for SF2→SID conversion
- Debugging tools for pointer relocation issues
- Foundation for advanced analysis features
- Player generation for demo releases

---

**For detailed analysis, see:** `SIDWINDER_ANALYSIS.md`
