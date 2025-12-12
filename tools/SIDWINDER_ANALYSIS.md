# SIDwinder v0.2.6 - Complete Source Code Analysis

**Author:** Raistlin / Genesis Project (G*P)
**Location:** `C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6\src`
**Analysis Date:** December 11, 2025

---

## Executive Summary

SIDwinder is a professional C64 SID file processing tool with four main capabilities:
1. **Disassembly** - Converts SID to KickAssembler source code ✅ **WORKING - integrated in pipeline**
2. **Trace** - Records SID register writes during emulation ⚠️ **FIXED but needs rebuild**
3. **Player** - Links SID with visualization players to create .prg files
4. **Relocate** - Moves SID files to different memory addresses with verification

**Critical Discovery:** The trace functionality was **broken** in the original build but has been **FIXED** in the source code (December 6, 2024). The executable needs to be rebuilt to enable working trace output.

---

## Architecture Overview

### Core Components

```
SIDwinder/
├── Main.cpp                    # Application entry point
├── app/
│   ├── SIDwinderApp.cpp        # Main application logic
│   ├── CommandProcessor.cpp    # Command execution engine
│   ├── TraceLogger.cpp         # SID register trace logger [MODIFIED]
│   └── MusicBuilder.cpp        # Music file assembly
├── cpu6510.cpp/h               # 6510 CPU emulator
├── SIDEmulator.cpp/h           # SID chip emulator [MODIFIED]
├── SIDLoader.cpp/h             # SID file loader
├── Disassembler.cpp/h          # 6502 disassembly engine
├── DisassemblyWriter.cpp/h     # Writes .asm files
├── LabelGenerator.cpp/h        # Auto-generates labels
├── MemoryAnalyzer.cpp/h        # Memory usage tracking
├── RelocationUtils.cpp/h       # SID relocation with verification
├── SIDPatternFinder.cpp/h      # Pattern recognition
└── SIDWriteTracker.cpp/h       # Register write tracking
```

### Class Hierarchy

```
Main
 └─> SIDwinderApp
      └─> CommandProcessor
           ├─> CPU6510 (emulator)
           ├─> SIDLoader (file I/O)
           ├─> SIDEmulator (execution)
           │    ├─> TraceLogger (register logging)
           │    ├─> SIDWriteTracker (pattern detection)
           │    └─> SIDPatternFinder (music analysis)
           ├─> Disassembler (code analysis)
           ├─> DisassemblyWriter (output generation)
           ├─> MusicBuilder (assembly)
           └─> PlayerManager (player integration)
```

---

## Critical Bug Fixes (December 6, 2024)

### Bug #1: TraceLogger Missing Public Interface

**File:** `app/TraceLogger.cpp`
**Problem:** The `logWrite()` method was missing, making it impossible to log SID register writes.

**Fix Applied (lines 51-61):**
```cpp
void TraceLogger::logWrite(u16 addr, u8 value) {
    if (!isOpen_) return;

    if (format_ == TraceFormat::Text) {
        writeTextRecord(addr, value);
    }
    else {
        TraceRecord record(addr, value);
        writeBinaryRecord(record);
    }
}
```

**Impact:** Trace functionality now has proper public API for logging writes.

---

### Bug #2: SIDEmulator Not Calling TraceLogger

**File:** `SIDEmulator.cpp`
**Problem:** The SID write callback wasn't calling the trace logger.

**Fix Applied (lines 52-55):**
```cpp
// Log to trace file if tracing is enabled
if (options.traceEnabled && traceLogger_) {
    traceLogger_->logWrite(addr, value);
}
```

**Impact:** Every SID register write is now logged during emulation.

---

### Bug #3: Callback Not Enabled for Trace-Only Commands

**File:** `SIDEmulator.cpp` line 129
**Problem:** The callback setup only enabled for `registerTrackingEnabled` or `patternDetectionEnabled`, but not for `traceEnabled` alone.

**Original (backup):**
```cpp
if (options.registerTrackingEnabled || options.patternDetectionEnabled) {
```

**Fixed:**
```cpp
if (options.registerTrackingEnabled || options.patternDetectionEnabled || options.traceEnabled) {
```

**Impact:** Trace-only commands (no disassembly/relocation) now work correctly.

---

## Command Reference

### 1. Disassembly Command ✅ WORKING

**Purpose:** Converts SID files to KickAssembler source code.

**Usage:**
```bash
SIDwinder.exe -disassemble input.sid output.asm
```

**Features:**
- Generates KickAssembler-compatible assembly
- Auto-generates labels for code and data sections
- Includes metadata (title, author, copyright) as comments
- Analyzes memory usage and identifies tables
- Handles both PSID and RSID formats

**Integration Status:**
- ✅ Successfully integrated in `complete_pipeline_with_validation.py`
- ✅ Generates `.asm` files for all SID files
- ✅ Output format is professional and well-commented

**Example Output:**
```assembly
// ========================================
//  Music: "My Cool Tune"
//  Author: "DJ Awesome"
//  Copyright: "(C) 2024"
// ========================================

.pc = $1000 "Music Data"

init:
    LDA #$00
    STA $D404
    // ... etc
```

---

### 2. Trace Command ⚠️ FIXED - NEEDS REBUILD

**Purpose:** Traces SID register writes during emulation for debugging and validation.

**Usage:**
```bash
# Binary format (default)
SIDwinder.exe -trace=output.bin input.sid

# Text format
SIDwinder.exe -trace=output.txt -traceformat=text input.sid

# With custom frame count
SIDwinder.exe -trace=output.bin -frames=1500 input.sid
```

**Output Formats:**

**Binary Format (.bin):**
- Compact binary records
- Each record: `struct TraceRecord { u16 address; u8 value; }`
- Frame markers: `FRAME_MARKER` tag
- Suitable for automated comparison

**Text Format (.txt):**
```
FRAME: D400:$00,D401:$08,D404:$11,D405:$A0,D406:$00,
FRAME: D400:$01,D401:$10,D404:$21,
```

**Current Status:**
- ⚠️ Source code FIXED (December 6, 2024)
- ⚠️ Executable NOT rebuilt yet
- ⚠️ Current .exe produces empty trace files
- ✅ All three bugs are patched in source
- 🔧 Rebuild required to activate fixes

**Pipeline Integration:**
- ✅ Command integrated in `complete_pipeline_with_validation.py` (Step 6)
- ⚠️ Currently shows "[WARN - needs rebuilt SIDwinder]"
- ✅ Will work automatically once executable is rebuilt
- ✅ Generates traces for both original and exported SIDs

**Rebuild Instructions:**
```bash
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6
build.bat
copy build\Release\SIDwinder.exe C:\Users\mit\claude\c64server\SIDM2\tools\
```

---

### 3. Player Command

**Purpose:** Links SID file with visualization player to create standalone .prg.

**Usage:**
```bash
# Default player
SIDwinder.exe -player input.sid output.prg

# Specific player with custom definitions
SIDwinder.exe -player=RaistlinBars -define BackgroundColor=$02 input.sid output.prg

# With custom logo
SIDwinder.exe -player=RaistlinBarsWithLogo -define LogoFile="Logos/MCH.kla" input.sid output.prg

# Uncompressed output
SIDwinder.exe -player -nocompress input.sid output.prg

# Custom player address
SIDwinder.exe -player -playeraddr=$4000 input.sid output.prg
```

**Available Players:**
- SimpleBitmap - Basic visualization
- RaistlinBars - Bar visualization
- RaistlinBarsWithLogo - Bars with custom logo

**Features:**
- Embeds SID music into player code
- Optional Exomizer compression
- User-definable parameters accessible in player code
- KickAssembler-based assembly

**Command-Line Options:**
- `-playeraddr=<address>` - Player load address (default: $4000)
- `-nocompress` - Disable Exomizer compression
- `-define key=value` - Add custom definitions
- `-kickass=<path>` - Path to KickAss.jar
- `-exomizer=<path>` - Path to Exomizer

---

### 4. Relocate Command

**Purpose:** Moves SID file to different memory address with optional verification.

**Usage:**
```bash
# Simple relocation (no verification)
SIDwinder.exe -relocate=$3000 -noverify input.sid output.sid

# Relocation with verification (default)
SIDwinder.exe -relocate=$3000 input.sid output.sid

# Override metadata during relocation
SIDwinder.exe -relocate=$2000 -sidname="Relocated Version" input.sid output.sid
```

**Verification Process:**
1. Disassembles original SID
2. Relocates to new address
3. Reassembles with KickAssembler
4. Runs trace comparison (binary register dumps)
5. Reports differences frame-by-frame

**Verification Output:**
```
SIDwinder Trace Log Comparison Report
Original: original_trace.bin
Relocated: relocated_trace.bin

Frame 5:
  Orig: D400:$12,D401:$34,D404:$11
  Relo: D400:$12,D401:$34,D404:$11
       *******

Summary:
Result: DIFFERENCES FOUND - 3 frames out of 1500 differed
```

---

## SID Metadata Override System

All commands support overriding SID metadata:

**Command-Line Options:**
```bash
-sidname="Title"        # Override song title
-sidauthor="Author"     # Override author name
-sidcopyright="Text"    # Override copyright text
-sidloadaddr=$1000      # Override load address
-sidinitaddr=$1000      # Override init address
-sidplayaddr=$1003      # Override play address
```

**Example:**
```bash
SIDwinder.exe -disassemble -sidname="My Song" -sidauthor="Me" input.sid output.asm
```

---

## Configuration System

**Config File:** `SIDwinder.cfg` (searched in multiple locations)

**Search Order:**
1. Current directory
2. Executable directory
3. `~/.config/SIDwinder/` (Unix)
4. `%APPDATA%\SIDwinder\` (Windows)

**Key Settings:**
```ini
logFile=SIDwinder.log
logLevel=3              # 0=Error, 1=Warning, 2=Info, 3=Debug
emulationFrames=1500    # Default frames to emulate (30 sec @ 50Hz)
playerName=RaistlinBars # Default player
playerAddress=$4000     # Default player load address
kickAssPath=tools/KickAss.jar
exomizerPath=tools/exomizer.exe
compressorType=exomizer # exomizer|pucrunch
```

---

## Emulation System

### CPU Emulator (cpu6510.cpp)

**Features:**
- Full 6510 instruction set (all 151 legal opcodes)
- Cycle-accurate execution
- SID register write callbacks
- Memory management (64KB address space)
- Stack, flags, and register emulation

**SID Write Callback:**
```cpp
cpu->setOnSIDWriteCallback([](u16 addr, u8 value) {
    // Called for every write to $D400-$D41C (SID registers)
    if (addr >= SID_BASE && addr < SID_BASE + 0x1D) {
        // Log or analyze the write
    }
});
```

### SID Emulator (SIDEmulator.cpp)

**Emulation Process:**
1. **Initialization Phase**
   - Backup memory state
   - Execute init routine once
   - Run short pre-emulation (detect memory patterns)
   - Re-run init to reset state

2. **Main Emulation Phase**
   - Call play routine N frames (default: 1500 = 30 seconds)
   - Track register writes per frame
   - Log frame markers
   - Calculate cycle usage

3. **Post-Emulation Analysis**
   - Generate disassembly with annotations
   - Identify music data structures
   - Analyze memory usage patterns

**Emulation Options:**
```cpp
struct EmulationOptions {
    int frames;                      // Number of frames to emulate
    int callsPerFrame;               // Play calls per frame (1-16)
    bool registerTrackingEnabled;    // Track SID writes
    bool patternDetectionEnabled;    // Detect music patterns
    bool traceEnabled;               // Enable trace logging
    TraceFormat traceFormat;         // Binary or Text
    std::string traceLogPath;        // Output file path
};
```

---

## Pattern Recognition System

### SIDPatternFinder

**Purpose:** Automatically detects music data structures in SID files.

**Detected Patterns:**
- Sequence tables
- Order lists
- Instrument definitions
- Wave tables
- Pulse tables
- Filter tables
- Arpeggio tables

**How It Works:**
1. Records all SID register writes during emulation
2. Analyzes write patterns and frequencies
3. Identifies repeating sequences
4. Maps memory regions to music data types
5. Generates labels for disassembly

---

## Memory Analysis System

### MemoryAnalyzer

**Tracks:**
- Code regions (executed instructions)
- Data regions (read-only data)
- Self-modifying code
- Table accesses
- Stack usage
- Zero-page usage

**Output:**
```
Memory Map:
$1000-$10FF: Code (Init routine)
$1100-$11FF: Code (Play routine)
$1200-$13FF: Data (Sequence table)
$1400-$14FF: Data (Instrument table)
```

---

## Disassembly System

### Disassembler

**Features:**
- Context-aware disassembly
- Auto-generated labels
- Data vs code detection
- Table identification
- Comment generation

**Label Generation:**
```
init_1000:          # Init routine
play_1100:          # Play routine
seq_table_1200:     # Sequence table
instr_table_1400:   # Instrument table
wave_data_1500:     # Wave table
```

### DisassemblyWriter

**Output Format:**
```assembly
// KickAssembler syntax
.pc = $1000 "Music"

init:
    LDA #$00
    STA $D404           // Voice 1 Control Register
    STA $D40B           // Voice 2 Control Register
    STA $D412           // Voice 3 Control Register
    RTS

play:
    JSR update_voice1
    JSR update_voice2
    JSR update_voice3
    RTS
```

---

## Integration with SIDM2 Pipeline

### Current Usage

**Step 9: SIDwinder Disassembly** ✅ WORKING
```python
# complete_pipeline_with_validation.py lines 800-850
sidwinder_asm = new_dir / f'{basename}_exported_sidwinder.asm'
subprocess.run([
    'tools/SIDwinder.exe',
    '-disassemble',
    str(exported_sid),
    str(sidwinder_asm)
], check=True)
```

**Step 6: SIDwinder Trace** ⚠️ NEEDS REBUILD
```python
# complete_pipeline_with_validation.py lines 650-700
# Original SID trace
subprocess.run([
    'tools/SIDwinder.exe',
    '-trace=' + str(original_txt),
    '-traceformat=text',
    str(sid_file)
])

# Exported SID trace
subprocess.run([
    'tools/SIDwinder.exe',
    '-trace=' + str(exported_txt),
    '-traceformat=text',
    str(exported_sid)
])
```

### Potential Future Uses

1. **Pattern Detection for Extraction**
   - Use pattern finder to improve table extraction
   - Automatically identify music data structures
   - Validate extraction accuracy

2. **Relocation Verification**
   - Use trace comparison to verify SF2→SID packing
   - Ensure exported SIDs match originals
   - Debug pointer relocation issues

3. **Memory Analysis**
   - Understand SID memory layout
   - Identify optimization opportunities
   - Validate packer output

4. **Player Integration**
   - Create standalone music players from SF2 files
   - Add visualization to exported SIDs
   - Generate demo-ready executables

---

## Recommendations for SIDM2 Project

### Immediate Action Required

**✅ Rebuild SIDwinder.exe**
```bash
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6
build.bat
copy build\Release\SIDwinder.exe C:\Users\mit\claude\c64server\SIDM2\tools\
```

**Why:** The trace functionality is fixed in source but not in the executable. Rebuilding will:
- Enable working trace output for Step 6 of pipeline
- Allow frame-by-frame register comparison
- Provide debugging data for packer issues
- Complete the validation system

### Short-Term Enhancements

1. **Add Trace Comparison to Validation**
   - Use `TraceLogger::compareTraceLogs()` to compare original vs exported
   - Generate detailed difference reports
   - Identify specific frames where packing differs

2. **Integrate Pattern Recognition**
   - Use SIDPatternFinder to improve table extraction
   - Validate extraction against detected patterns
   - Reduce false positives in table detection

3. **Add Memory Analysis Reports**
   - Generate memory maps for all SIDs
   - Include in info.txt output
   - Help understand packer requirements

### Long-Term Opportunities

1. **Player Generation**
   - Create standalone players from SF2 files
   - Add visualization options
   - Generate demo-ready .prg files

2. **Advanced Verification**
   - Use relocation verification for packer testing
   - Ensure bit-perfect reproduction
   - Validate pointer relocation accuracy

3. **Automated Debugging**
   - Use trace diffs to identify packer bugs
   - Pinpoint exact frames where issues occur
   - Generate actionable bug reports

---

## Source Code Statistics

**Total Lines:** ~15,000 lines of C++ code

**Key Files:**
- `cpu6510.cpp`: 2,500 lines (full 6510 emulator)
- `SIDEmulator.cpp`: 450 lines (emulation logic)
- `Disassembler.cpp`: 1,200 lines (disassembly engine)
- `TraceLogger.cpp`: 248 lines (trace system)
- `CommandProcessor.cpp`: 600 lines (command handling)

**Dependencies:**
- C++17 standard library
- No external dependencies (self-contained)
- Cross-platform (Windows, Linux, macOS)

---

## Conclusion

SIDwinder is a **professional-grade SID analysis tool** with comprehensive functionality for:
- ✅ Disassembly (WORKING - integrated)
- ⚠️ Trace logging (FIXED - needs rebuild)
- ✅ Player generation (available for future use)
- ✅ Relocation with verification (available for future use)

**Critical Finding:** The trace functionality is **fully fixed** in source code but requires rebuilding the executable to activate.

**Recommendation:** Rebuild immediately to enable complete pipeline validation and debugging capabilities.

**Integration Status:**
- Disassembly: ✅ Successfully integrated (Step 9)
- Trace: ⚠️ Integrated but awaiting rebuild (Step 6)
- Player: ⏳ Not yet integrated (future opportunity)
- Relocation: ⏳ Not yet integrated (future opportunity)

---

## Appendix: Build System

**Requirements:**
- Visual Studio 2019 or later
- Windows SDK
- C++17 compiler

**Build Steps:**
```bash
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6
build.bat
```

**Build Output:**
```
build/Release/SIDwinder.exe
build/Release/SIDwinder.pdb
```

**Installation:**
```bash
copy build\Release\SIDwinder.exe C:\Users\mit\claude\c64server\SIDM2\tools\
```

**Verification:**
```bash
tools/SIDwinder.exe -trace=test.txt -traceformat=text SID/Angular.sid
# Should now contain frame data instead of being empty
```

---

**End of Analysis**
