# External Source Code Repositories

*Documentation of external C64 development repositories accessible to Claude Code*

---

## Overview

This project has access to five external source code repositories containing complete implementations of critical C64 tools and emulators. These repositories provide deep technical reference for understanding SID music format, emulation, debugging, and the SID Factory II editor.

**Access**: These repositories are configured in `.claude/settings.local.json` under `permissions.additionalDirectories`

---

## 1. RetroDebugger

**Path**: `C:\Users\mit\Downloads\RetroDebugger-master`

**Description**: Advanced real-time debugger for Commodore 64 and other retro platforms. Provides deep insight into SID playback, memory monitoring, and 6502 execution.

**Key Features**:
- Real-time SID register monitoring
- Memory viewer and editor
- 6502 disassembler and debugger
- Screen/sprite/charset viewers
- Breakpoints and watchpoints

**Relevance to SIDM2**:
- Understanding real-time SID register behavior
- Debugging SID player execution
- Analyzing memory layouts during playback
- Validating conversion accuracy

**Documentation**: See `docs/TOOLS_REFERENCE.md` and `tools/RETRODEBUGGER_ANALYSIS.md` in main project

**Key Source Directories**:
```
RetroDebugger-master/
├── src/               - Main source code
│   ├── Audio/        - Audio engine
│   ├── Debugger/     - Debugger core
│   ├── SID/          - SID chip emulation
│   └── C64/          - C64 emulation
├── libs/             - Dependencies
└── Resources/        - Assets and resources
```

---

## 2. SID-Depacker

**Path**: `C:\Users\mit\Downloads\SID-Depacker`

**Description**: Tool for unpacking and analyzing packed SID files. Handles various compression formats and player relocations.

**Key Features**:
- Unpacks compressed SID files
- Identifies packing methods
- Relocates player code
- Extracts music data

**Relevance to SIDM2**:
- Understanding SID file packing/unpacking
- Reference for `sf2_packer.py` implementation
- Handling packed Laxity SIDs
- Pointer relocation techniques

**Key Source Directories**:
```
SID-Depacker/
├── src/              - Depacker source code
├── packers/          - Known packer formats
└── tools/            - Utility scripts
```

---

## 3. SID Factory II (Complete Source)

**Path**: `C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master`

**Description**: **Complete source code for the SID Factory II editor** - the primary tool this project converts to. This is the most critical external repository.

**Key Features**:
- C++ editor source code
- All driver implementations (11-16, NP20)
- Converter framework (MOD, GT, CT)
- File format handlers
- SF2 format specifications

**Relevance to SIDM2**:
- **Creating custom Laxity driver** - Primary use case
- Understanding SF2 file format internals
- Converter architecture reference
- Driver implementation patterns
- Header block definitions

**Key Source Directories**:
```
sidfactory2-master/sidfactory2-master/
├── source/                    - Main editor source
│   ├── editor/               - Editor UI and logic
│   ├── player/               - Player runtime
│   ├── converters/           - Format converters
│   │   ├── ConverterMod.cpp - MOD converter reference
│   │   ├── ConverterGT.cpp  - GoatTracker converter
│   │   └── ConverterJCH.cpp - CheeseCutter converter
│   ├── drivers/              - Driver source code (CRITICAL)
│   │   ├── driver11/        - Driver 11 source
│   │   ├── driver12/        - Driver 12 source
│   │   ├── driver13/        - Driver 13 source
│   │   ├── driver14/        - Driver 14 source
│   │   ├── driver15/        - Driver 15 source
│   │   ├── driver16/        - Driver 16 source
│   │   └── np20/            - NP20 driver source
│   └── formats/              - File format handlers
├── docs/                     - Documentation
└── examples/                 - Example SF2 files
```

**CRITICAL FILES**:
- `source/drivers/*/` - **Driver assembly source code** (for creating custom Laxity driver)
- `source/converters/` - Converter architecture reference
- `source/formats/` - SF2 file format implementation
- `docs/` - Format specifications and developer docs

**FOR CUSTOM LAXITY DRIVER**:
This repository contains the **complete assembly source code for all SF2 drivers**. This is essential for creating a custom Laxity-native driver.

---

## 4. sidtool

**Path**: `C:\Users\mit\Downloads\sidtool-master\sidtool-master`

**Description**: Ruby-based command-line tool for analyzing and manipulating SID files. Provides utilities for SID file inspection, MIDI conversion, and music synthesis.

**Key Features**:
- SID file parsing and analysis
- MIDI file conversion
- Ruby code generation for playback
- SID chip state emulation
- Voice and synthesis management

**Relevance to SIDM2**:
- Reference implementation for SID file parsing (Ruby)
- MIDI conversion approach
- SID state machine patterns
- Voice handling and synthesis

**Key Source Directories**:
```
sidtool-master/sidtool-master/
├── lib/sidtool/      - Main library code
│   ├── file_reader.rb     - SID file parser
│   ├── sid.rb             - SID file representation
│   ├── state.rb           - SID chip state
│   ├── voice.rb           - Voice handling
│   ├── synth.rb           - Synthesis engine
│   ├── midi_file_writer.rb - MIDI export
│   └── ruby_file_writer.rb - Ruby code gen
├── bin/              - Command-line executables
└── spec/             - Test specifications
```

**Use Cases**:
- Understanding SID file structure
- Reference for player identification
- Extraction algorithm reference
- Format conversion techniques

---

## 5. VICE Emulator

**Path**: `C:\Users\mit\Downloads\vice-3.9`

**Description**: The most accurate Commodore 64 emulator. Contains complete C64 hardware emulation including SID chip.

**Key Features**:
- Cycle-accurate C64 emulation
- Multiple SID chip emulation (6581, 8580, ReSID)
- Built-in monitor/debugger
- SID register dump/trace
- File format handlers (PRG, SID, D64, etc.)

**Relevance to SIDM2**:
- Reference SID chip emulation (`cpu6502_emulator.py`)
- Understanding PSID/RSID format handling
- Accurate playback testing
- Register-level validation

**Key Source Directories**:
```
vice-3.9/
├── src/
│   ├── c64/              - C64 emulation core
│   ├── sid/              - SID chip emulation (CRITICAL)
│   │   ├── sid.c        - Main SID emulation
│   │   ├── resid/       - ReSID engine
│   │   └── resid-fp/    - ReSID floating-point
│   ├── c64dtv/          - C64 DTV
│   ├── drive/           - Disk drive emulation
│   ├── monitor/         - Built-in monitor
│   └── printerdrv/      - Printer emulation
├── doc/                  - Documentation
└── data/                 - ROMs and resources
```

**CRITICAL FILES**:
- `src/sid/sid.c` - SID chip emulation reference
- `src/sid/resid/` - High-quality SID engine
- `src/c64/` - Complete C64 hardware reference

---

## Quick Access Guide

### For Creating Custom Laxity Driver

**Primary Resource**: SID Factory II source
```
C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\source\drivers\
```

**What to examine**:
1. `driver11/` - Complete Driver 11 assembly source
2. `np20/` - NewPlayer 20 driver source
3. `converters/` - How other formats are converted
4. `formats/` - SF2 file format implementation

**Workflow**:
1. Study Driver 11 assembly source structure
2. Compare with Laxity NewPlayer v21 source (`learnings/21g5.txt`)
3. Create hybrid driver using Laxity playback engine
4. Package in SF2 format using Driver 11 as template

### For Understanding SID Emulation

**Primary Resource**: VICE source
```
C:\Users\mit\Downloads\vice-3.9\src\sid\
```

**Reference for**: Python 6502 emulator (`sidm2/cpu6502_emulator.py`)

### For Debugging and Validation

**Primary Resource**: RetroDebugger source
```
C:\Users\mit\Downloads\RetroDebugger-master\src\
```

**Use cases**:
- Understanding real-time SID behavior
- Memory layout analysis
- Register-level debugging

### For Packing/Unpacking

**Primary Resource**: SID-Depacker source
```
C:\Users\mit\Downloads\SID-Depacker\
```

**Reference for**: `sidm2/sf2_packer.py` implementation

---

## Integration with SIDM2 Project

### Current Integration Status

| External Repo | SIDM2 Integration | Status |
|---------------|-------------------|--------|
| **SID Factory II** | Referenced in docs, binary drivers used | ⚠️ Not analyzed for custom driver |
| **VICE** | Used for testing (x64sc.exe), SID emulation reference | ✅ Analysis complete |
| **RetroDebugger** | Documented in `RETRODEBUGGER_ANALYSIS.md` | ✅ Analysis complete |
| **SID-Depacker** | Referenced for packer implementation | ⚠️ Not fully integrated |
| **sidtool** | Reference for SID analysis and manipulation | ⚠️ Available for reference |

### Next Steps

1. **Analyze SID Factory II driver source** (CRITICAL for custom Laxity driver)
   - Read `source/drivers/driver11/*.asm`
   - Understand driver structure and SF2 integration
   - Compare with Laxity player architecture

2. **Study converter framework**
   - Examine `source/converters/ConverterMod.cpp` as reference
   - Understand how to integrate new player formats
   - Apply patterns to Laxity converter

3. **Extract build process**
   - Understand how SF2 drivers are assembled
   - Identify required tools (assembler, linker)
   - Create build pipeline for custom driver

---

## File Access Examples

### Reading SID Factory II Driver Source
```python
# Access Driver 11 assembly source
driver11_source = "C:/Users/mit/Downloads/sidfactory2-master/sidfactory2-master/source/drivers/driver11/"

# Read main driver file
Read driver11_source + "driver11.asm"
```

### Browsing VICE SID Emulation
```python
# Access VICE SID source
vice_sid = "C:/Users/mit/Downloads/vice-3.9/src/sid/"

# Read main SID implementation
Read vice_sid + "sid.c"
```

### Exploring RetroDebugger
```python
# Access RetroDebugger source
retro_debugger = "C:/Users/mit/Downloads/RetroDebugger-master/src/"

# Read SID monitoring code
Read retro_debugger + "SID/CViewC64StateSID.cpp"
```

---

## Build Tools and Dependencies

### SID Factory II Build Requirements

Check the repository for:
- Build scripts (Makefile, build.bat, etc.)
- Required assembler (KickAssembler, ACME, CA65)
- Dependencies and libraries

### VICE Build Requirements

VICE requires:
- C compiler (GCC, MSVC)
- Various libraries (SDL, etc.)
- See `vice-3.9/README` for details

---

## Search Patterns

### Finding Specific Code

When searching these repositories, use these patterns:

**SID Factory II**:
- Driver code: `source/drivers/**/*.asm`
- Converters: `source/converters/Converter*.cpp`
- Format handlers: `source/formats/**/*.cpp`

**VICE**:
- SID emulation: `src/sid/**/*.c`
- Monitor: `src/monitor/**/*.c`
- File format: `src/fileio/**/*.c`

**RetroDebugger**:
- SID viewer: `src/SID/**/*.cpp`
- Debugger core: `src/Debugger/**/*.cpp`

**SID-Depacker**:
- Depackers: `src/**/*.cpp`
- Packer definitions: `packers/**/*`

**sidtool**:
- Library code: `lib/sidtool/**/*.rb`
- Executables: `bin/*`
- Tests: `spec/**/*.rb`

---

## Version Information

| Repository | Version/Date | Source |
|------------|-------------|--------|
| RetroDebugger | master branch | Downloaded snapshot |
| SID-Depacker | Current | Downloaded snapshot |
| SID Factory II | master branch | Downloaded snapshot |
| sidtool | master branch | Downloaded snapshot |
| VICE | 3.9 | Official release |

**Note**: These are local snapshots. Check original repositories for updates.

---

## Best Practices

### When Exploring External Repos

1. **Start with documentation** - Look for README, INSTALL, DEVELOPERS files
2. **Find build files** - Makefile, CMakeLists.txt, build scripts
3. **Identify key source files** - Main entry points, core modules
4. **Cross-reference with SIDM2 docs** - Connect external code to project needs

### When Creating Custom Driver

1. **Read SID Factory II driver source thoroughly**
2. **Compare with Laxity player (`learnings/21g5.txt`)**
3. **Identify commonalities and differences**
4. **Design hybrid approach**
5. **Test incrementally**

---

## Troubleshooting

### If Claude Code Can't Access External Repos

1. Verify paths are correct in `.claude/settings.local.json`
2. Check Windows path format (double backslashes: `C:\\Users\\...`)
3. Ensure directories exist
4. Restart Claude Code session if needed

### If Build Instructions Needed

- Check each repository's README
- Look for INSTALL or BUILD files
- Search for Makefile or build.bat scripts

---

## Related Documentation

**In Main Project**:
- `sourcerepository.md` - Internal source code inventory
- `docs/TOOLS_REFERENCE.md` - External tools documentation
- `tools/RETRODEBUGGER_ANALYSIS.md` - RetroDebugger analysis
- `CLAUDE.md` - Project quick reference

**External**:
- Each repository's own documentation
- SID Factory II user manual: `learnings/user_manual.pdf`

---

## Summary

You now have access to **five critical C64 development repositories**:

1. ✅ **RetroDebugger** - Real-time debugging and SID monitoring
2. ✅ **SID-Depacker** - Packing/unpacking reference
3. ✅ **SID Factory II** - **Complete editor source (CRITICAL for custom driver)**
4. ✅ **sidtool** - SID file analysis and manipulation tools
5. ✅ **VICE** - Reference C64/SID emulation

**Most Important**: The **SID Factory II source code** contains the complete assembly source for all drivers. This is essential for creating a custom Laxity driver.

**Next Action**: Analyze `sidfactory2-master/source/drivers/` to understand driver architecture and begin custom Laxity driver implementation.

---

**Created**: 2025-12-13
**Last Updated**: 2025-12-13
