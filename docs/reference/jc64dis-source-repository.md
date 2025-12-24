# JC64dis Source Code Repository

*Complete Java source code for the JC64 Commodore 64 emulator and JC64dis disassembler*

---

## Overview

**Repository**: https://github.com/ice00/jc64
**License**: GPL-2.0
**Language**: Java (98.5%)
**Status**: Active development (442+ commits)
**Latest Release**: JC64dis 3.0 (April 21, 2025)

The jc64 repository contains the complete Java source code for:
1. **JC64** - Cycle-accurate Commodore 64 emulator
2. **JC64dis** - Advanced 6502 disassembler with GUI (the component relevant to SIDM2)

This repository complements the compiled binary distribution we have locally at `C:\Users\mit\Downloads\jc64dis-win64\`.

---

## JC64dis Disassembler Component

### Two Versions Available

#### 1. Legacy JC64dis (Beta 2003)
**Class**: `sw_emulator.software.FileDasm`
**Interface**: Command-line
**Status**: Original implementation

**Capabilities**:
- Processes PRG, SID, and MUS file formats
- Generates disassembly output files
- No graphical interface

#### 2. Next-Generation JC64dis (Current)
**Class**: `sw_emulator.swing.main.JC64dis`
**Interface**: Graphical User Interface
**Status**: Enhanced with 3-panel iterative workflow

**Capabilities**:
- Three-panel iterative refinement interface
- Produces human-readable source code
- Advanced disassembly analysis
- 330+ configuration options (from manual)
- Supports 7 M6502 assemblers including Kick Assembler

### Supported File Formats

JC64dis can disassemble:
- **PRG** - Commodore 64 program files
- **SID** - SID music files (CRITICAL for SIDM2)
- **MUS** - Music files
- **CRT** - Cartridge files
- **VSF** - VICE snapshot files
- **AY** - Amstrad/ZX Spectrum music
- **NSF** - NES Sound Format
- **SAP** - Atari SAP format

### Technical Specifications

From the 488-page manual (`jc64dis.pdf`):
- **Code Size**: 101,000+ lines of Java
- **Version**: 2.9 (in manual), 3.0 (latest GitHub release)
- **First Release**: 2003 (by Ice Team)
- **Supported CPUs**: M6502, Z80, Intel 8048
- **Configuration Options**: 330+

---

## Relevance to SIDM2 Project

### Direct Applications

1. **SID File Analysis**
   - JC64dis can disassemble SID files to reveal player code structure
   - Critical for understanding Laxity NewPlayer v21 and other SID formats
   - Complements our existing analysis in `learnings/21g5.txt`

2. **6502 Disassembly Reference**
   - Java implementation provides cross-platform alternative
   - Could be integrated into SIDM2 pipeline for automated analysis
   - Reference for understanding player initialization and playback routines

3. **Converter Architecture Reference**
   - Source code shows how to handle multiple music file formats
   - Architecture patterns for format detection and conversion
   - GUI design patterns for music file tools

### Integration Possibilities

**Current SIDM2 Pipeline**:
```
SID File → Laxity Parser → SF2 Converter → SF2 File
```

**With JC64dis Integration**:
```
SID File → JC64dis Analysis → Enhanced Parser → SF2 Converter → SF2 File
                ↓
        Automated Player Detection
        Code Structure Analysis
        Data Extraction Hints
```

---

## Repository Structure

```
jc64/
├── src/                              # Java source code (PRIMARY)
│   └── sw_emulator/                 # Main package
│       ├── software/                # Legacy tools
│       │   └── FileDasm.java       # Legacy disassembler
│       ├── swing/                   # GUI components
│       │   └── main/
│       │       └── JC64dis.java    # Modern disassembler GUI
│       ├── cpu/                     # CPU emulation (6502, Z80, etc.)
│       ├── hardware/                # C64 hardware emulation
│       └── util/                    # Utility classes
│
├── bin/                              # Compiled class files
├── lib/                              # External dependencies
├── data/                             # Resource files (ROMs, etc.)
├── nbproject/                        # NetBeans IDE project files
├── history/                          # Version history
│
├── build.xml                         # Apache Ant build script
├── yjp-build.xml                     # YourKit profiler build
├── README.md                         # Project documentation
├── AUTHORS                           # Contributors
├── BUGS                              # Known issues
├── TODO                              # Development roadmap
└── COPYING                           # GPL-2.0 license
```

---

## Key Source Files for SIDM2

### Critical Files to Examine

1. **JC64dis GUI Disassembler**
   ```
   src/sw_emulator/swing/main/JC64dis.java
   ```
   - Modern disassembler with 3-panel interface
   - SID file format handling
   - Configuration management (330+ options)

2. **Legacy Command-Line Disassembler**
   ```
   src/sw_emulator/software/FileDasm.java
   ```
   - Original implementation
   - Simpler architecture for reference
   - Command-line interface patterns

3. **CPU Emulation**
   ```
   src/sw_emulator/cpu/
   ```
   - 6502 CPU emulation (basis for our cpu6502_emulator.py)
   - Instruction set reference
   - Cycle-accurate timing

4. **File Format Handlers**
   ```
   src/sw_emulator/ (various file loader classes)
   ```
   - SID file parsing
   - PRG file handling
   - Format detection logic

---

## Building from Source

### Prerequisites

- **Java Development Kit (JDK)** - Java 8 or later
- **Apache Ant** - Build automation tool
- **NetBeans** (optional) - IDE with project files included

### Build Commands

```bash
# Clone repository
git clone https://github.com/ice00/jc64.git
cd jc64

# Build with Ant
ant

# Run JC64dis (legacy)
java -cp bin sw_emulator.software.FileDasm <input.sid>

# Run JC64dis (modern GUI)
java -cp bin sw_emulator.swing.main.JC64dis
```

---

## Development History

### Timeline

- **1999-2002**: Original development by Stefano Tognon and Michele Caira
- **2003**: First JC64dis disassembler release (Beta)
- **2025**: JC64dis 3.0 release (April 21)
- **Present**: Active development with 442+ commits

### Attribution

The project builds upon established C64 emulation research:
- **VICE Emulator** - CPU instruction implementation reference
- **Christian Bauer's VIC Article** - VIC II chip documentation
- **64doc** - C64 hardware documentation
- **PAL Timing Specifications** - Video timing reference

---

## Comparison: JC64dis vs Local Binary

| Aspect | GitHub Source | Local Binary |
|--------|---------------|--------------|
| **Version** | 3.0 (latest) | 2.9 (from PDF) |
| **Format** | Java source code | Compiled JAR + EXE |
| **Access** | Full source available | Binary only |
| **Customization** | Fully modifiable | Configuration only |
| **Integration** | Can be embedded | External tool |
| **Platform** | Cross-platform (Java) | Windows x64 |
| **Documentation** | Source + README | 488-page PDF manual |

---

## Integration Strategy for SIDM2

### Phase 1: Analysis (Recommended First Step)

1. **Study SID File Handling**
   - Examine how JC64dis parses SID headers
   - Compare with our `sidm2/sid_file_io.py`
   - Identify improvements or missing features

2. **Understand Player Detection**
   - See how JC64dis identifies different SID players
   - Compare with our `sidm2/player_identifier.py`
   - Potentially enhance our detection logic

3. **Learn Disassembly Algorithms**
   - Study the 3-panel iterative approach
   - Understand code vs. data separation
   - Apply to our Python SIDwinder implementation

### Phase 2: Reference Implementation (Optional)

1. **Cross-Platform Disassembly**
   - Use JC64dis source as reference for Python implementation
   - Replace Windows-only tools with Java-based alternatives
   - Achieve 100% cross-platform pipeline

2. **Enhanced Analysis**
   - Integrate automated disassembly into conversion pipeline
   - Use JC64dis to validate player structure
   - Improve conversion accuracy with better code understanding

### Phase 3: Direct Integration (Advanced)

1. **Java-Python Bridge**
   - Use JPype or Py4J to call JC64dis from Python
   - Embed disassembly functionality in SIDM2 pipeline
   - Automated player analysis during conversion

2. **Source Code Port**
   - Port critical JC64dis algorithms to Python
   - Maintain pure-Python pipeline philosophy
   - Leverage Java implementation as reference

---

## Accessing the Source Code

### Method 1: Clone Repository

```bash
git clone https://github.com/ice00/jc64.git
cd jc64
```

### Method 2: Browse Online

Visit https://github.com/ice00/jc64/tree/master/src

### Method 3: Download ZIP

https://github.com/ice00/jc64/archive/refs/heads/master.zip

---

## Usage Examples

### Example 1: Disassemble Laxity SID File

Using legacy disassembler:
```bash
java -cp bin sw_emulator.software.FileDasm G5/Laxity/Stinsens_Last_Night_of_89.sid
```

Using modern GUI:
```bash
java -cp bin sw_emulator.swing.main.JC64dis
# Then: File → Open → Select SID file → Configure → Disassemble
```

### Example 2: Analyze Player Code Structure

1. Load SID file in JC64dis GUI
2. Use 3-panel iterative approach:
   - **Panel 1**: Initial disassembly
   - **Panel 2**: Code/data separation
   - **Panel 3**: Human-readable source
3. Export to Kick Assembler format
4. Compare with our `learnings/21g5.txt` analysis

### Example 3: Cross-Reference with SIDM2

1. Disassemble SID with JC64dis
2. Compare INIT/PLAY addresses with our parser
3. Validate memory layouts
4. Verify table locations and formats

---

## Known Limitations

From repository documentation:

1. **Development Status**
   - "This program is under construction"
   - No official executable releases to public (must build from source)
   - Active development may introduce breaking changes

2. **Performance Requirements**
   - "You must have a powerful system to run this program"
   - Cycle-accurate emulation is computationally intensive
   - May not be suitable for batch processing

3. **Focus on Accuracy Over Speed**
   - Prioritizes authentic hardware emulation
   - Thread-based multi-core design
   - Experimental VIC II implementation (dot-clock precision)

---

## Resources and Links

### Primary Resources

- **Repository**: https://github.com/ice00/jc64
- **Releases**: https://github.com/ice00/jc64/releases
- **Issues**: https://github.com/ice00/jc64/issues
- **License**: GPL-2.0

### SIDM2 Integration

- **Local Binary**: `C:\Users\mit\Downloads\jc64dis-win64\`
- **Local Manual**: `C:\Users\mit\Downloads\jc64dis-win64\win64\jc64dis.pdf` (488 pages)
- **Our Analysis**: Referenced in `docs/reference/external-repositories.md`

### Related C64 Tools

- **VICE Emulator**: Source in `C:\Users\mit\Downloads\vice-3.9\`
- **RetroDebugger**: Source in `C:\Users\mit\Downloads\RetroDebugger-master\`
- **SID Factory II**: Source in `C:\Users\mit\Downloads\sidfactory2-master\`

---

## Future Possibilities

### Potential Enhancements for SIDM2

1. **Automated Player Detection**
   - Use JC64dis to identify unknown SID players
   - Build database of player signatures
   - Extend beyond Laxity to support more formats

2. **Cross-Platform Independence**
   - Replace all Windows-only tools with Java alternatives
   - Pure Python + Java pipeline (no .exe dependencies)
   - Run SIDM2 on Mac/Linux without Wine

3. **Advanced SID Analysis**
   - Automated extraction of player code patterns
   - Data structure identification
   - Table format detection

4. **Quality Assurance**
   - Validate conversions by comparing disassembly
   - Detect potential conversion errors
   - Ensure code structure preservation

---

## Contributing to JC64

### If You Want to Contribute

1. Fork the repository: https://github.com/ice00/jc64
2. Follow GPL-2.0 license requirements
3. Submit pull requests for improvements
4. Report bugs via GitHub Issues

### Potential Contributions from SIDM2 Experience

1. **Enhanced SID Support**
   - Contribute Laxity NewPlayer v21 disassembly improvements
   - Add SF2 format export capability
   - Improve music file format detection

2. **Documentation**
   - Document SID-specific features
   - Add usage examples for music file analysis
   - Cross-reference with SIDM2 documentation

---

## Comparison with Other Tools

| Tool | Language | Platform | Source Available | SID Support |
|------|----------|----------|------------------|-------------|
| **JC64dis** | Java | Cross-platform | ✅ Yes (GitHub) | ✅ Full |
| **VICE** | C | Cross-platform | ✅ Yes | ✅ Playback |
| **RetroDebugger** | C++ | Windows/Mac | ✅ Yes | ✅ Debug |
| **SIDwinder** | C++ | Windows only | ❌ No | ✅ Trace |
| **siddump** | C | Windows only | ❌ No | ✅ Dump |

**JC64dis Advantage**: Only cross-platform disassembler with full source code available.

---

## Summary

The jc64 GitHub repository provides:

✅ **Complete Java source code** for JC64dis disassembler (101,000+ lines)
✅ **SID file disassembly capability** (critical for SIDM2)
✅ **Cross-platform implementation** (Java-based)
✅ **Active development** (442+ commits, latest release April 2025)
✅ **GPL-2.0 license** (compatible with SIDM2)
✅ **Reference implementation** for 6502 disassembly and SID parsing

**Key Benefit**: Provides complete source code access to complement the compiled binary we already use locally. Enables deep integration, customization, and cross-platform independence for SIDM2.

**Next Step**: Analyze `src/sw_emulator/swing/main/JC64dis.java` and SID file handling code to enhance SIDM2's player detection and analysis capabilities.

---

**Created**: 2025-12-24
**Repository Version**: 3.0 (April 21, 2025)
**Status**: Active development
**Author**: Ice Team
**License**: GPL-2.0
