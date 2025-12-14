# SID-Depacker Directory Inventory

**Location**: `C:\Users\mit\Downloads\SID-Depacker`
**Date**: 2025-12-14
**Purpose**: Comprehensive catalog of all SID music tools, source code, and resources

---

## File Type Summary (788 files total)

| Extension | Count | Type | Can Be... |
|-----------|-------|------|-----------|
| `.np20` | 250 | NewPlayer v20 source music files | Converted to SID/SF2 |
| `.sid` | 63 | SID music files (PSID/RSID format) | Played, analyzed, disassembled |
| `.txt` | 44 | Documentation | Read |
| `.h` | 34 | C/C++ header files | Compiled |
| `.cpp` | 33 | C++ source code | Compiled |
| `.d64` | 24 | C64 disk images (170KB) | Unpacked, mounted in emulator |
| `.zip` | 22 | Compressed archives | Extracted |
| `.vcxproj` | 21 | Visual Studio project files | Build configuration |
| `.filters` | 21 | Visual Studio filter files | Build configuration |
| `.seq` | 18 | Sequence data files | Analyzed |
| `.prg` | 15 | C64 program files | Disassembled, executed on C64/emulator |
| `.exe` | 13 | Windows executables | Executed |
| `.py` | 7 | Python scripts | Executed with Python |
| `.asm` | 7 | Assembly source code | Assembled with 64tass/KickAss |
| `.png` | 5 | Image files | Viewed |
| `.htm` | 4 | HTML documentation | Viewed in browser |
| `.s` | 3 | Assembly source code | Assembled |
| `.c` | 3 | C source code | Compiled |
| `.sln` | 3 | Visual Studio solution files | Build configuration |
| `.bat` | 3 | Batch scripts | Executed on Windows |
| `.sng` | 1 | GoatTracker song file | Converted to SID |
| `.d81` | 1 | C64 disk image (800KB) | Unpacked, mounted in emulator |

---

## 1. Windows Tools (Executables)

### SID Conversion & Analysis Tools

| Tool | Path | Purpose | Input → Output |
|------|------|---------|----------------|
| **psid64.exe** | `psid64-1.3-win64/` | SID to PRG converter | `.sid` → `.prg` (playable on C64) |
| **sid2sng.exe** | Root | SID to GoatTracker converter | `.sid` → `.sng` |
| **SID2MIDIw.exe** | `s2mwr17_release8_unrestricted/` | SID to MIDI converter (v1.7) | `.sid` → `.mid` |
| **h2g.v1.2.exe** | `h2g.v1.2 (1)/` | Hubbard to GoatTracker converter | `.sid` → `.sng` |

### SID Decompilers & Disassemblers

| Tool | Path | Purpose | Capabilities |
|------|------|---------|--------------|
| **SIDdecompiler.exe** | `SIDdecompiler_0.8-Win_x64/x64/` | SID decompiler (v0.8) | Decompiles SID to assembly source |
| **SIDcompare.exe** | `SIDdecompiler_0.8-Win_x64/x64/` | SID comparison tool | Compares two SID files |
| **sasm.exe** | `SIDdecompiler_0.8-Win_x64/x64/` | 6502 assembler | Assembles `.asm` → `.prg` |

### Disk Image Tools

| Tool | Path | Purpose | Capabilities |
|------|------|---------|--------------|
| **DirMasterSetup.exe** | `DirMaster_v3.1.5-STYLE/` | D64/D81 disk image manager | View, extract, create C64 disk images |

### Testing Tools (from SIDdecompiler)

| Tool | Path | Purpose |
|------|------|---------|
| **64tass.exe** | `SIDdecompiler-master/test/` | 64tass assembler |
| **p2s.exe** | `SIDdecompiler-master/test/` | PRG to SID converter |
| **siddump.exe** | `SIDdecompiler-master/test/` | SID register dump tool |
| **sidreloc.exe** | `SIDdecompiler-master/test/` | SID relocator |

---

## 2. Python Scripts

| Script | Path | Purpose | Input → Output |
|--------|------|---------|----------------|
| **sid2prg.py** | Root & `SIDdisk/` | SID to PRG converter | `.sid` → `.prg` |

---

## 3. C64 Native Tools (PRG files)

### Editors (Run on C64 or Emulator)

| Tool | Path | Version | Purpose |
|------|------|---------|---------|
| **Future Composer v5.0** | Root | v5.0 (1992) | Music editor by Warrior |
| **hmt-sidhacker25.prg** | `Sidhacker25/` | v2.5 | SID tracker by Hermit |
| **jch-ed docs-deek.prg** | Root | - | JCH editor documentation |

### Utilities

| Tool | Path | Purpose |
|------|------|---------|
| **tt.prg** | `SIDdisk/` | Test tune |
| **un.prg** | `SIDdisk/` | Utility (unknown) |
| **unentire.prg** | `SIDdisk/` | Utility (unknown) |

---

## 4. Disk Images (D64/D81 - Can Be Unpacked)

### Player/Editor Disks

| Disk Image | Path | Contents | Purpose |
|------------|------|----------|---------|
| **21.g5_Final.d64** | `NewPlayer v21.G5 Final/` | NewPlayer v21.G5 Final | Laxity player (final version) |
| **21.g5_Demos_Final.d64** | `NewPlayer v21.G5 Final/` | Demo tunes | Example music for NP21 |
| **NP-PACK5.5.d64** | `NewPlayer v21.G5 Final/` | Packer tool | Packs NP21 music |
| **Laxity Editor.d64** | Root | Laxity editor | Music editor by Laxity |
| **JCH 3.1+NP22-25.d64** | Root | JCH editor + NewPlayer v22-25 | JCH tools collection |
| **JCHEDIT.D64** | Root | JCH editor | JCH music editor |
| **JCH-TOOLS.D64** | `JCH-TOOLS/` | JCH tools | JCH utility collection |
| **Hermit-SIDhack25.d64** | `Sidhacker25/` | SIDhacker v2.5 | SID tracker |

### Depackers & Converters

| Disk Image | Path | Purpose |
|------------|------|---------|
| **DMC_5_Depack.d64** | Root | DMC v5 depacker |
| **JCH_Depaker.d64** | `JCH_Depaker/` | JCH depacker |
| **jch-depack-v2.0-the-syndrom.d64** | Root & `jch-depack-v2.0-the-syndrom/` | JCH depacker v2.0 by The Syndrom |
| **raw_jch_format_to_sdi_converter_v01_shape.d64** | `raw_jch_format_to_sdi_converter_v01_shape/` | JCH to SDI converter by Shape |

### Future Composer

| Disk Image | Path | Version |
|------------|------|---------|
| **FCOMPV3.d64** | Root | Future Composer v3 |
| **FutureComposer40-SUPERSOFT.d64** | Root | Future Composer v4.0 by Supersoft |
| **futurecomposer + acid demo.D64** | Root | Future Composer + demo |

### Other Tools

| Disk Image | Path | Purpose |
|------------|------|---------|
| **newplayer_tools.d64** | `crescent-newplayer_tools/` | NewPlayer tools by Crescent |
| **PLAYIT64_V0_9_MYD_2014.d64** | `PLAYIT64_V0_9_MYD_2014/` | PlayIt64 v0.9 player |
| **PLAYIT64_V0_9_MYD_2014.d81** | `PLAYIT64_V0_9_MYD_2014/` | PlayIt64 v0.9 (extended disk) |
| **sidsjhc.d64** | `SIDdisk/` | SID collection |

---

## 5. Source Code

### C/C++ Source Code (SIDdecompiler v0.8 - Master)

**Location**: `SIDdecompiler-master/SIDdecompiler-master/src/`

#### Core Libraries

**libsasm** - 6502 Assembler Library
- `Assembler.cpp/h` - Main assembler
- `OpcodeDefs.cpp/h` - 6502 opcode definitions
- `Parser.cpp/h` - Assembly parser
- `Tokenizer.cpp/h` - Lexical analysis
- `Label.cpp/h` - Label management
- `Section.cpp/h` - Code sections
- `Output.cpp/h` - Code generation
- `Assertion.cpp/h` - Assertion support
- `Util.cpp/h` - Utilities

**libsasmdisasm** - 6502 Disassembler Library
- `Disassembler.cpp/h` - Main disassembler

**libsasmemu** - 6502 Emulator Library
- `C64MachineState.cpp/h` - C64 state management
- `cpu.c/h` - 6502 CPU emulator
- `DebugEvaluators.cpp/h` - Debug support
- `EmulatedC64.cpp/h` - Full C64 emulation
- `Instruction.cpp/h` - Instruction execution
- `MemoryAccess.cpp/h` - Memory management
- `MemoryIO.cpp/h` - I/O operations
- `SidCall.cpp/h` - SID register tracking
- `TrackedMemory.cpp/h` - Memory tracking

**libsidsid** - SID File Library
- `PSIDData.cpp/h` - PSID/RSID file handling
- `SIDData.cpp/h` - SID data structures

**HueUtil** - Utility Library
- `HueUtilString.cpp/h` - String utilities
- `RegExp.cpp/h` - Regular expressions
- `ProgramOption.h` - Command-line options

#### Applications

**SIDdecompiler** - Main decompiler tool
- Location: `SIDdecompiler-master/src/SIDdecompiler/`
- Purpose: Decompiles SID files to assembly source
- Components: C64-specific analysis, pattern detection, optimization

**SIDcompare** - SID comparison tool
- Location: `SIDdecompiler-master/src/SIDcompare/`
- Purpose: Compares two SID files for differences

**sasm** - Assembler
- Location: `SIDdecompiler-master/src/sasm/`
- Purpose: Assembles 6502 assembly to binary

**Total C/C++ Files**: ~60+ source files

### Assembly Source Code

**NewPlayer Packers** (Crescent NewPlayer Tools)
- `np_v14.g0_packer.s` - NewPlayer v14 (G0 format) packer
- `np_v17.g1_packer.s` - NewPlayer v17 (G1 format) packer
- `np_v20.g4_packer.s` - NewPlayer v20 (G4 format) packer

**JCH Source** (SRC_JCH_Glover)
- `21.g4 full .src.prg` - NewPlayer v21 G4 source
- `21.g5spd3up.src.prg` - NewPlayer v21 G5 speed-up source
- `21g4.seq` - Sequence data
- `21g5.seq` - Sequence data
- `21g4.txt` - Documentation
- `21g5.txt` - Documentation

**SIDhacker Source**
- `dazzler.prg` - Dazzler source (in `Sidhacker25/Sources/`)

---

## 6. Music Files

### SID Files (63 files)

**Test SID Files** (h2g.v1.2 directory)
- `Bump_Set_Spike.sid`
- `Commando.sid`
- `Crazy_Comets.sid`

**Reference SID Files**
- `Unboxed_Ending_8580.sid` - Test file (DRAX/Laxity)
- `tt.sid` - Test tune
- `un.sid` - Test tune

**SIDdecompiler Test SIDs** (21.g5 demos)
- `21.g5_clean.prg` - Clean NewPlayer v21
- `21.g5_demo_1.prg` - Demo 1
- `21.g5_demo_2.prg` - Demo 2
- `21.g5_demo_3.prg` - Demo 3
- `Green_Beret_c000_c012.prg` - Green Beret music
- `Ocean_Loader_3.prg` - Ocean loader music

### NewPlayer v20 Source Files (250 .np20 files)

**Location**: `NP20_Source_Tunes_v1/NP20/DRAX/`

**Collection**: 250+ editable music files by DRAX in NewPlayer v20 format
- Covers, originals, game music remixes
- Examples: "24th Amaranth Grand Prix", "Aliens", "Baby Elephant", "Billie Jean", etc.
- **Can be converted**: `.np20` → `.sid` with appropriate tools

### GoatTracker Files (1 .sng file)

- `International Karate.sng` - Reference file in root

---

## 7. Documentation

### User Manuals

| Document | Path | Purpose |
|----------|------|---------|
| **JCH_C64_Editor_docs.docx** | Root | JCH editor documentation (4.5 MB) |
| **NP22-25 docs.doc** | Root | NewPlayer v22-25 documentation |
| **Futurecomposer Instructions.txt** | Root | Future Composer manual |

### Readme Files

- `readme.txt` - Various tools (psid64, crescent-newplayer_tools, PLAYIT64)
- `README.TXT` - v-c64ed editor
- `playit64readme.txt` - PlayIt64 instructions

### Tool Documentation

- `changelog.txt`, `news.txt`, `todo.txt` - psid64 project docs
- `HELP.htm`, `OPTIONS.htm`, `README.htm`, `WHATSNEW.htm` - SID2MIDIw docs

### Source Code Documentation

- `ED37_SRC.TXT` - v-c64ed source listing
- `21g4.txt`, `21g5.txt` - NewPlayer source docs

---

## 8. Archives (22 .zip files)

**Location**: `archive/` subdirectory

All tools archived as ZIP files:
- `crescent-newplayer_tools.zip`
- `DirMaster_v3.1.5-STYLE.zip`
- `futurecomposer + acid demo.zip`
- `h2g.v1.2 (1).zip`
- `jch-depack-v2.0-the-syndrom.zip`
- `JCH-TOOLS.zip`, `JCH_Depaker.zip`, `Jch_Tools.zip`
- `NewPlayer v21.G5 Final.zip`
- `NP20_Source_Tunes_v1.zip`
- `PLAYIT64_V0_9_MYD_2014.zip`
- `psid64-1.3-win64.zip`
- `raw_jch_format_to_sdi_converter_v01_shape.zip`
- `s2mwr17_release8_unrestricted.zip`
- `SIDdecompiler-master.zip`, `SIDdecompiler_0.8-Win_x64.zip`
- `siddump108.zip`
- `Sidhacker25.zip`
- `SID_to_WAV_v1.8.zip`
- `SRC_JCH_Glover.zip`
- `v-c64ed.zip`

---

## 9. Build Files & Project Files

**Visual Studio Projects** (21 .vcxproj files)
- SIDdecompiler project files
- Build configurations for Windows compilation

**Batch Scripts** (3 .bat files)
- Build scripts for tools
- Automation scripts

**Shell Scripts** (1 .sh file)
- Linux/Mac build scripts

---

## Processing Capabilities by File Type

### Can Be Unpacked/Extracted

| Type | Tool | Output |
|------|------|--------|
| **D64** | DirMaster, c1541 | Individual PRG/SEQ files |
| **D81** | DirMaster, c1541 | Individual PRG/SEQ files |
| **ZIP** | 7-Zip, WinZip | Extracted files |

### Can Be Disassembled

| Type | Tool | Output |
|------|------|--------|
| **PRG** | SIDdecompiler, SIDwinder, 64tass | 6502 assembly (.asm) |
| **SID** | SIDdecompiler, SIDwinder | 6502 assembly (.asm) |

### Can Be Converted

| From | To | Tool |
|------|-----|------|
| **SID** | PRG | psid64, sid2prg.py |
| **SID** | SNG | sid2sng.exe |
| **SID** | MIDI | SID2MIDIw.exe |
| **SID** | SF2 | sid_to_sf2.py (SIDM2 project) |
| **NP20** | SID | JCH tools, converters |
| **SNG** | SID | GoatTracker export |
| **PRG** | SID | p2s.exe |

### Can Be Analyzed

| Type | Tool | Output |
|------|------|--------|
| **SID** | siddump.exe | Register dump (.dump) |
| **SID** | SIDcompare.exe | Comparison report |
| **SID** | player-id.exe | Player format identification |

### Can Be Assembled

| Type | Tool | Output |
|------|------|--------|
| **ASM** | 64tass, sasm | PRG/binary |
| **S** | 64tass | PRG/binary |

### Can Be Played/Edited

| Type | Tool | Platform |
|------|------|----------|
| **SID** | VICE, SIDplay | PC (emulator) |
| **NP20** | JCH editor, Laxity editor | C64/emulator |
| **SNG** | GoatTracker | PC |

---

## Key Tool Collections

### 1. JCH/NewPlayer Ecosystem
- **Editors**: JCH Editor (v3.1), Laxity Editor
- **Players**: NewPlayer v14, v17, v20, v21, v22-25
- **Depackers**: JCH Depacker, jch-depack v2.0
- **Converters**: raw_jch_format_to_sdi_converter
- **Source Files**: 250 NP20 files by DRAX

### 2. Future Composer
- **Versions**: v3, v4, v5
- **Disk Images**: 3 D64 images
- **Format**: Different from JCH/Laxity

### 3. SIDdecompiler Suite
- **Tools**: SIDdecompiler, SIDcompare, sasm
- **Source**: Complete C++ source code (~60 files)
- **Libraries**: Assembler, disassembler, emulator, SID parser
- **Test Suite**: 64tass, p2s, siddump, sidreloc

### 4. Conversion Tools
- **SID→PRG**: psid64, sid2prg.py
- **SID→SNG**: sid2sng, h2g
- **SID→MIDI**: SID2MIDIw

---

## Notable Source Code Availability

### Complete Source Code Available

1. **SIDdecompiler** (C++)
   - Full 6502 emulator
   - Assembler/disassembler
   - SID file parser
   - ~15,000+ lines of C++ code

2. **NewPlayer Packers** (Assembly)
   - v14, v17, v20 packers
   - Source in `.s` format

3. **JCH NewPlayer v21** (Assembly + Sequences)
   - Complete G4/G5 source
   - Sequence data
   - Documentation

### Binary Only (No Source)

- Future Composer
- Most D64 disk tools
- Most conversion utilities

---

## Most Useful Tools for SIDM2 Project

### 1. Analysis & Disassembly
- **SIDdecompiler** - Best for understanding player structure
- **siddump** - Frame-by-frame register analysis
- **SIDwinder** - Professional disassembly (already in SIDM2)

### 2. Reference Music Files
- **250 NP20 source files** - Native NewPlayer v20 format
- **21.g5 demos** - NewPlayer v21 examples

### 3. Conversion Tools
- **psid64** - High-quality SID→PRG conversion
- **sid2sng** - SID→GoatTracker (for format comparison)
- **p2s.exe** - PRG→SID (useful for testing)

### 4. Source Code for Study
- **SIDdecompiler C++ source** - Professional 6502 emulator/assembler
- **NewPlayer packer source** - Understanding packing format
- **JCH v21 source** - Player internals

---

## Integration Opportunities

### For Laxity Driver Enhancement
1. Study NewPlayer v20/v21 source code in detail
2. Compare packing algorithms between versions
3. Analyze 250 NP20 source files for table format patterns

### For NP20 Driver Development
1. Use NP20 source files as test suite
2. Study np_v20.g4_packer.s for format details
3. Reference JCH editor disk images

### For Format Validation
1. Use SIDdecompiler to verify player detection
2. Compare against siddump output for accuracy
3. Cross-reference with 250 NP20 files

---

**Document Status**: Complete inventory (Updated 2025-12-14)
**Total Files**: 788 files
**Total Size**: ~15 MB (excluding archives)
**Key Assets**: 250 NP20 files, SIDdecompiler source, 24 D64 images, 13 Windows tools
**Removed**: SID-Wizard suite (389 files removed)
