# Source Code Repository Index

*Complete inventory of all source code available in the SIDM2 project*

---

## Overview

This repository contains one of the most comprehensive collections of C64 music/SID-related source code, combining:
- Modern C/C++ implementations (sf2pack, siddump, etc.)
- Classic 6502 assembly source code (Laxity NewPlayer v21, SID players)
- Python conversion algorithms
- Complete reference archives (codebase64)

**Total Source Files**: 200+ individual source files across C/C++, assembly, and Python

---

## 1. C/C++ Source Code

### sf2pack - SF2 to SID Packer (Complete Implementation)

**Location**: `tools/sf2pack/`

Complete C++ implementation of the SF2 to SID packer with pointer relocation:

```
sf2pack.cpp         - Main packer application
sf2pack.h           - Header files
packer_simple.cpp   - Simplified packing algorithm
packer_simple.h     - Packing header
c64memory.cpp       - C64 memory management
c64memory.h         - Memory header
opcodes.cpp         - 6502 opcode definitions
opcodes.h           - Opcode header
psidfile.cpp        - PSID file format handling
psidfile.h          - PSID header
Makefile            - Build configuration
README.md           - Documentation
```

**Build**: `cd tools/sf2pack && make`

### sf2export - SF2 Exporter

**Location**: `tools/sf2export/`

```
sf2export.cpp       - SF2 exporter implementation
Makefile            - Build configuration
README.md           - Documentation
```

### siddump - SID Register Dump Tool

**Location**: `G5/siddump108/` and `tools/`

```
siddump.c           - Main siddump application
cpu.c               - 6502 CPU emulator
cpu.h               - CPU emulator header
cpu_trace.c         - CPU trace/debug functionality (custom)
Makefile            - Build configuration
readme.txt          - Documentation
```

**Archive**: `G5/siddump108/siddump108.zip` (complete source)

### prg2sid - PRG to SID Converter

**Location**: `tools/prg2sid/`

```
p2s.c               - Main converter source
Makefile            - Build configuration
p2s.txt             - Documentation
```

---

## 2. 6502 Assembly Source Code

### Laxity NewPlayer v21 (PRIMARY REFERENCE)

**Location**: `learnings/21g5.txt` and `G5/21g5.txt`

**Complete 6502 assembly source code** for the Laxity NewPlayer v21 music player (~1000 lines):

```assembly
;---------------------------------------
; JCH NewPlayer v21.G5.........01-02-98
; by GLOVER/SAMAR/CRYSTAL SOUND
;---------------------------------------
```

**Key Sections**:
- Player init/drive routines (`$1000`)
- Instrument table format (8 bytes)
- Wave/Pulse/Filter table handlers
- Super command system
- Note frequency tables
- Complete playback engine

**Additional Files**:
- `learnings/21.g5_Final.txt` (11KB) - Final version documentation
- `G5/NewPlayer v21.G5 Final/21.g5_Final.d64` - Commodore D64 disk with source
- `G5/NewPlayer v21.G5 Final/21.g5 clean.prg` - Compiled player

**This is the foundation for creating a custom Laxity driver for SF2.**

### SID Player Framework (Custom Implementations)

**Location**: `tools/SIDPlayers/`

Complete assembly source for various music player setups and visualizations:

**Framework & Includes**:
```
INC/FreqTable.asm              - Frequency table definitions
INC/MemoryPreservation.asm     - Memory preservation routines
INC/NMIFix.asm                 - NMI interrupt handling
INC/StableRasterSetup.asm     - Raster interrupt setup
```

**Players**:
```
Default/Default.asm                                    - Basic player framework
SimpleBitmap/SimpleBitmap.asm                         - Bitmap-based player
SimpleRaster/SimpleRaster.asm                         - Raster-based player
RaistlinBars/RaistlinBars.asm                        - 3D bar visualization
RaistlinBarsWithLogo/RaistlinBarsWithLogo.asm        - With logo
RaistlinMirrorBars/RaistlinMirrorBars.asm            - Mirror effect
RaistlinMirrorBarsWithLogo/RaistlinMirrorBarsWithLogo.asm  - Complete version
```

**Assets**: CharSet.map, WaterSprites.map, SoundbarSine.bin

### Generated Disassemblies

**Location**: `output/SIDSF2player_Complete_Pipeline/*/`

50+ SIDwinder-generated disassembly files:
```
*_original_sidwinder.asm    - Disassembly of original Laxity SIDs
*_exported_sidwinder.asm    - Disassembly of SF2-exported SIDs
```

**Use**: Reference for debugging conversion accuracy

---

## 3. Python Source Code (Conversion Algorithms)

### Core Modules

**Location**: `sidm2/`

```python
sid_to_sf2.py           - Main SID to SF2 conversion algorithm
sf2_packer.py           - SF2 to SID packer (Python implementation)
cpu6502.py              - 6502 CPU emulator for relocation
cpu6502_emulator.py     - Full emulator with SID capture
sid_player.py           - SID file player and analyzer
sf2_player_parser.py    - SF2-exported SID parser
siddump_extractor.py    - Runtime sequence extraction
gate_inference.py       - Waveform-based gate detection
accuracy.py             - Accuracy calculation module
validation.py           - Validation utilities
audio_comparison.py     - Audio waveform comparison
```

### Utility Scripts

**Location**: `scripts/`

```python
convert_all.py                    - Batch conversion
test_roundtrip.py                 - Round-trip validation
validate_sid_accuracy.py          - Frame-by-frame accuracy
generate_validation_report.py     - Multi-file validation
run_validation.py                 - Validation system runner
generate_dashboard.py             - Dashboard generator
analyze_waveforms.py              - Waveform analysis
disassemble_sid.py                - 6502 disassembler
extract_addresses.py              - Data structure extraction
test_converter.py                 - Unit tests (69 tests)
test_sf2_format.py                - Format tests (12 tests)
test_complete_pipeline.py         - Pipeline tests (19 tests)
```

### Main Pipeline

**Location**: Root directory

```python
complete_pipeline_with_validation.py  - Complete 11-step pipeline
```

---

## 4. SF2 Driver Binaries (Templates)

**Location**: `G5/drivers/` and `learnings/drivers/`

Compiled SF2 driver PRG files (binary format - no source ASM):

### Driver 11 - The Standard (Primary Target)
```
sf2driver11_00.prg through sf2driver11_05.prg  - 6 versions
sf2driver11_04_01.prg                          - Variant
```

### Other Drivers
```
Driver 12 (Barber):      sf2driver12_00.prg, sf2driver12_00_01.prg
Driver 13 (Hubbard):     sf2driver13_00.prg, sf2driver13_00_01.prg
Driver 14 (Experiment):  sf2driver14_00.prg, sf2driver14_00_01.prg
Driver 15 (Tiny I):      sf2driver15_00.prg, 15_01.prg, 15_02.prg
Driver 16 (Tiny II):     sf2driver16_00.prg, 16_01.prg, 16_01_01.prg
NP20 (NewPlayer 20):     sf2driver_np20_00.prg
```

**Note**: These are compiled binaries. Original assembly source not included in repo.

---

## 5. Codebase64 Archive (Massive Reference Collection)

**Location**: `learnings/codebase64_latest.zip` (extracted)

Complete archive containing **100+ individual C64 source code projects**:

### Structure
```
base/               - Base routines and tools (60+ zipped projects)
sourcecode/         - Complete source projects (45+ archives)
books/              - Programming references
tools/              - Assemblers (ACME, KickASS)
lib/                - Library code
6502_6510_maths/    - Mathematical routines
magazines/          - Scene magazines
projects/           - Game/demo projects
sid/                - SID-related code
```

### Key Contents

**Assemblers**:
- ACME 0.93 - Cross assembler with source
- KickASS 6502 - Modern assembler

**Music/SID**:
- MODPLAY64 - MOD player source
- Hard Restart Bottle - Gate/restart documentation
- Various music player implementations

**Game/Demo Source**:
- Complete game projects
- Demo effects source code
- Scrollers, loaders, IRQ handlers

**Single-File Archives** (.tar.gz):
```
acme_vim.tar.gz
vector.tar.gz
bresenham.tar.gz
hard_restart_bottle_0.1.tar.gz
acme.xml.tar.gz
```

---

## 6. Build Configuration

### Makefiles
```
tools/sf2pack/Makefile          - sf2pack build
tools/sf2export/Makefile        - sf2export build
G5/siddump108/Makefile          - siddump build
tools/prg2sid/Makefile          - prg2sid build
```

### Build Scripts
```
tools/build_siddump_trace.bat   - Windows batch build for trace version
```

---

## 7. Disk Images (Source Containers)

**Location**: `G5/NewPlayer v21.G5 Final/`

Commodore D64 disk images containing source code:
```
21.g5_Final.d64        - NewPlayer v21 source disk
21.g5_Demos_Final.d64  - Demonstration disk
NP-PACK5.5.d64         - Packing tool disk
```

**Access**: Use C64 emulator (VICE) or D64 tools to extract files

---

## Quick Reference by Task

### Creating Custom Laxity Driver
**Primary Source**: `learnings/21g5.txt` (complete assembly source)
**Format Reference**: `docs/reference/SF2_FORMAT_SPEC.md`
**Packer Implementation**: `tools/sf2pack/*.cpp` (C++) or `sidm2/sf2_packer.py` (Python)

### Understanding SF2 Drivers
**Driver Specs**: `docs/reference/DRIVER_REFERENCE.md`
**Binary Templates**: `G5/drivers/sf2driver*.prg`
**Conversion Strategy**: `docs/reference/CONVERSION_STRATEGY.md`

### Building Tools
**sf2pack**: `cd tools/sf2pack && make`
**siddump**: `cd G5/siddump108 && make`
**sf2export**: `cd tools/sf2export && make`

### 6502 Development
**Assemblers**: `learnings/codebase64_latest/tools/ACME/` or `KickASS/`
**Player Framework**: `tools/SIDPlayers/Default/Default.asm`
**Laxity Source**: `learnings/21g5.txt`

### Python Algorithm Development
**Core Package**: `sidm2/*.py`
**Utilities**: `scripts/*.py`
**Tests**: `scripts/test_*.py`

---

## File Paths (Absolute)

All source code locations with absolute Windows paths:

### C/C++ Source
```
C:\Users\mit\claude\c64server\SIDM2\tools\sf2pack\*.cpp
C:\Users\mit\claude\c64server\SIDM2\tools\sf2export\*.cpp
C:\Users\mit\claude\c64server\SIDM2\G5\siddump108\*.c
C:\Users\mit\claude\c64server\SIDM2\tools\prg2sid\p2s.c
C:\Users\mit\claude\c64server\SIDM2\tools\*.c
```

### 6502 Assembly
```
C:\Users\mit\claude\c64server\SIDM2\learnings\21g5.txt
C:\Users\mit\claude\c64server\SIDM2\G5\21g5.txt
C:\Users\mit\claude\c64server\SIDM2\tools\SIDPlayers\**\*.asm
C:\Users\mit\claude\c64server\SIDM2\output\**\*_sidwinder.asm
```

### Python
```
C:\Users\mit\claude\c64server\SIDM2\sidm2\*.py
C:\Users\mit\claude\c64server\SIDM2\scripts\*.py
C:\Users\mit\claude\c64server\SIDM2\complete_pipeline_with_validation.py
```

### Archives
```
C:\Users\mit\claude\c64server\SIDM2\learnings\codebase64_latest.zip
C:\Users\mit\claude\c64server\SIDM2\G5\siddump108\siddump108.zip
```

---

## Summary Statistics

**By Language**:
- **C/C++ Source Files**: 20+ files (sf2pack, siddump, sf2export, prg2sid)
- **6502 Assembly Files**: 50+ files (21g5.txt, SIDPlayers, disassemblies)
- **Python Source Files**: 40+ files (sidm2 package, scripts, tests)
- **Archive Projects**: 100+ individual projects (codebase64)

**Total Lines of Code**:
- C/C++: ~5,000 lines
- Assembly: ~50,000 lines (including codebase64)
- Python: ~10,000 lines

**Key Asset**: The **21g5.txt** file (Laxity NewPlayer v21 source) is the foundation for creating a custom Laxity driver for SF2 format.

---

## Version History

- **Created**: 2025-12-13
- **Last Updated**: 2025-12-13

This inventory represents a complete snapshot of all source code available in the SIDM2 project for SID file conversion and C64 music development.
