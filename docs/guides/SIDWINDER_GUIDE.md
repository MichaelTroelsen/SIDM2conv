# SIDwinder Integration Guide

**Complete guide to using SIDwinder with SIDM2**

**Version**: SIDwinder v0.2.6  
**Last Updated**: 2025-12-07

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Pipeline Integration](#pipeline-integration)
6. [Known Limitations](#known-limitations)
7. [Rebuilding SIDwinder](#rebuilding-sidwinder)
8. [Quick Reference](#quick-reference)

---

## Overview

SIDwinder is a comprehensive C64 SID file processor with four main capabilities:
- **Disassemble**: Convert SID files to KickAssembler source code
- **Trace**: Capture SID register writes frame-by-frame  
- **Player**: Link SID files with visualization players
- **Relocate**: Move SID files to different memory addresses

**Integration Status**: ✅ Disassemble working | ⚠️ Trace needs rebuild | 🔧 Player/Relocate manual use

---

## Features

### 1. Disassemble (✅ Working)

Converts SID files to KickAssembler-compatible assembly source code.

**Usage**:
```bash
tools/SIDwinder.exe -disassemble SID/song.sid output.asm
```

**Output**: Complete 6502 disassembly with:
- Metadata comments (title, author, copyright)
- Labeled code sections and data blocks
- KickAssembler syntax

**Status**: Fully integrated in pipeline (Step 9)

### 2. Trace (⚠️ Needs Rebuild)

Captures SID register writes frame-by-frame for analysis.

**Usage**:
```bash
tools/SIDwinder.exe -trace=output.txt SID/song.sid
```

**Current Issue**: Empty output due to bugs in source code  
**Fix Available**: Patches applied to source, needs recompilation  
**Status**: Files generated in pipeline but empty until rebuild

### 3. Player (🔧 Manual Use)

Links SID files with visualization players for C64 playback with graphics.

**Usage**:
```bash
tools/SIDwinder.exe -player=RaistlinBars music.sid music.prg
```

**Available Players**:
- Default
- RaistlinBars
- RaistlinBarsWithLogo
- RaistlinMirrorBars
- RaistlinMirrorBarsWithLogo
- SimpleBitmap
- SimpleRaster

### 4. Relocate (🔧 Manual Use)

Moves SID files to different memory addresses.

**Usage**:
```bash
tools/SIDwinder.exe -relocate=$2000 input.sid output.sid
```

---

## Installation

SIDwinder is pre-installed in the `tools/` directory.

**Files**:
- `tools/SIDwinder.exe` - Main executable
- `tools/SIDPlayers/` - Visualization players
- `tools/sidwinder_trace_fix.patch` - Source code patches

**No additional setup required** for disassembly and player features.

---

## Usage

### Basic Commands

```bash
# Disassemble a SID file
tools/SIDwinder.exe -disassemble input.sid output.asm

# Trace register writes (after rebuild)
tools/SIDwinder.exe -trace=output.txt input.sid

# Create player PRG  
tools/SIDwinder.exe -player=RaistlinBars music.sid music.prg

# Relocate to different address
tools/SIDwinder.exe -relocate=$3000 input.sid output.sid
```

### Advanced Options

```bash
# Specify subtune
tools/SIDwinder.exe -disassemble input.sid output.asm -subtune=2

# Set trace duration
tools/SIDwinder.exe -trace=output.txt input.sid -seconds=60

# Verbose output
tools/SIDwinder.exe -disassemble input.sid output.asm -v
```

---

## Pipeline Integration

SIDwinder is integrated into `complete_pipeline_with_validation.py`:

### Step 6: SIDwinder Trace

Generates frame-by-frame register traces for validation.

**Output Files**:
- `Original/{filename}_original.txt` - Original SID trace
- `New/{filename}_exported.txt` - Exported SID trace

**Status**: Files created but empty until rebuild

### Step 9: SIDwinder Disassembly

Generates assembly source code for analysis.

**Output Files**:
- `Original/{filename}_original_sidwinder.asm` - Original SID
- `New/{filename}_exported_sidwinder.asm` - Exported SID

**Known Issue**: Exported SID disassembly fails for 17/18 files due to packer bug

---

## Known Limitations

### 1. Exported SID Disassembly Failure

**Impact**: 17/18 exported SIDs fail with "Execution at $0000" error

**Root Cause**: Pointer relocation bug in `sidm2/sf2_packer.py`

**Scope**: Only affects SIDwinder's strict CPU emulation  
**Workaround**: Original SIDs disassemble perfectly  
**Note**: Files play correctly in VICE, SID2WAV, siddump

### 2. Trace Output Empty

**Impact**: Trace files generated but contain no data

**Root Cause**: Bugs in SIDwinder source code:
- Line 124: Callback not enabled for trace-only mode
- TraceLogger: Missing logWrite() method

**Fix**: Patches applied, executable needs rebuild  
**Status**: Working in source, pending recompilation

---

## Rebuilding SIDwinder

### Prerequisites

**Build Tools**:
- Visual Studio 2019 or later (with C++ support)
- CMake 3.15+
- Windows SDK

**Source Location**:
```
C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6\src\
```

### Build Steps

**Option 1: Using Visual Studio**

1. Open Developer Command Prompt
2. Navigate to source directory
3. Run build script:
```cmd
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6
build.bat
```

4. Copy executable:
```cmd
copy build\Release\SIDwinder.exe C:\Users\mit\claude\c64server\SIDM2\tools\
```

**Option 2: Using CMake**

```cmd
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

### Patch Status

✅ **Patches Applied** to source files:

**SIDEmulator.cpp**:
- Line 52-55: Added trace logging to SID write callback
- Line 129: Added traceEnabled to callback condition

**TraceLogger.h**:
- Line 52-56: Added public logWrite() method

**TraceLogger.cpp**:
- Line 51-61: Implemented logWrite() method

**Patch file**: `tools/sidwinder_trace_fix.patch`

### Verification

After rebuild, test trace functionality:

```bash
tools/SIDwinder.exe -trace=test.txt SID/Angular.sid
# Should produce non-empty test.txt with register writes
```

---

## Quick Reference

### Common Tasks

| Task | Command |
|------|---------|
| Disassemble SID | `SIDwinder.exe -disassemble input.sid output.asm` |
| Trace registers | `SIDwinder.exe -trace=trace.txt input.sid` |
| Create player | `SIDwinder.exe -player=RaistlinBars in.sid out.prg` |
| Relocate SID | `SIDwinder.exe -relocate=$2000 in.sid out.sid` |

### Pipeline Files

| File Pattern | Purpose |
|--------------|---------|
| `*_original.txt` | SIDwinder trace of original SID |
| `*_exported.txt` | SIDwinder trace of exported SID |
| `*_original_sidwinder.asm` | Disassembly of original SID |
| `*_exported_sidwinder.asm` | Disassembly of exported SID |

### Status Indicators

| Symbol | Meaning |
|--------|---------|
| ✅ | Fully working |
| ⚠️ | Works but needs rebuild/fix |
| ❌ | Known limitation |
| 🔧 | Manual use only |

---

## References

- [SIDwinder Source](C:\Users\mit\Downloads\SIDwinder-0.2.6)
- [Patch File](../tools/sidwinder_trace_fix.patch)
- [Quick Reference](../tools/SIDWINDER_QUICK_REFERENCE.md)
- [Pipeline Documentation](../../CLAUDE.md#sidwinder-tool-details)

---

**Document Status**: Consolidated from 3 SIDwinder documents  
**Next Review**: After SIDwinder rebuild  
**Maintainer**: SIDM2 Project
