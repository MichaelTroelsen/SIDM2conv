# Laxity SF2 Driver Research

**Purpose**: Document research findings for creating a custom Laxity NewPlayer v21 driver for SID Factory II

**Date**: 2025-12-12
**Version**: 1.0

---

## Executive Summary

Creating a custom Laxity-specific SF2 driver would enable direct conversion of Laxity NewPlayer v21 SID files to SF2 format without format translation, potentially achieving 70-90% accuracy vs current 1-8%.

**Challenge**: SF2 driver source code is not publicly available - only compiled .prg binaries exist.

**Solution Strategy**: Extract Laxity player code from existing SID files and package it as an SF2 driver.

---

## SF2 Driver Architecture

### Driver Structure

SF2 drivers are C64 PRG files containing:

```
┌─────────────────────────────────────┐
│  Load Address (2 bytes)             │  $0D7E (standard)
├─────────────────────────────────────┤
│  Driver Code (~2KB 6502 assembly)   │  $0D7E-$15xx
│  - Init routine (JSR entry)         │
│  - Play routine (JSR entry)         │
│  - Table lookup code                │
│  - SID register write routines      │
│  - Effect handlers (vibrato, etc.)  │
├─────────────────────────────────────┤
│  Header Blocks (configuration)      │  $0800+
│  - Block 1: Descriptor              │
│  - Block 2: Common addresses        │
│  - Block 3: Table definitions       │
│  - Block 4-9: Metadata              │
│  - Block 255: End marker            │
├─────────────────────────────────────┤
│  Music Data Tables                  │  $0900+
│  - Sequences/Order lists            │
│  - Instruments                      │
│  - Wave table                       │
│  - Pulse table                      │
│  - Filter table                     │
│  - Arpeggio table                   │
│  - HR (Hard Restart) table          │
│  - Tempo table                      │
│  - Init table                       │
└─────────────────────────────────────┘
```

### Driver Entry Points

**Init Routine**:
- Called once to set up the music
- Initializes SID chip
- Sets up table pointers
- Loads first song

**Play Routine**:
- Called every frame (50Hz PAL / 60Hz NTSC)
- Updates sequences
- Processes commands
- Runs table programs
- Writes SID registers

### Table Offset System

Each driver has fixed table offsets (example - Driver 11):

```python
LOAD_ADDRESS = 0x0D7E

# Table offsets (relative to load address)
SEQUENCE_TABLE_OFFSET = 0x0903  # Absolute: $0D7E + $0903 = $1681
INSTRUMENT_TABLE_OFFSET = 0x0A03  # Absolute: $0D7E + $0A03 = $1781
WAVE_TABLE_OFFSET = 0x0B03      # Absolute: $0D7E + $0B03 = $1881
PULSE_TABLE_OFFSET = 0x0D03     # Absolute: $0D7E + $0D03 = $1A81
FILTER_TABLE_OFFSET = 0x0F03    # Absolute: $0D7E + $0F03 = $1C81
```

**Key Insight**: Different drivers use different offsets!

| Driver | Inst | Pulse | Filter |
|--------|------|-------|--------|
| Driver 11 | $0A03 | $0D03 | $0F03 |
| NP20 | $0F4D | $0E4D | $0D4D |
| **Laxity** | **TBD** | **TBD** | **TBD** |

---

## Laxity NewPlayer v21 Structure

### Memory Layout

Based on STINSENS_PLAYER_DISASSEMBLY.md and analysis:

```
Address Range   Content
-------------   -------
$1000-$10A0     Init routine
$10A1-$19FF     Play routine and player code
$1900-$1A1E     Orderlist pointers
$1A1E-$1A3A     Filter table
$1A3B-$1A6A     Pulse table
$1A6B-$1ACB     Instruments
$1ACB+          Wave tables
```

### Player Entry Points

```asm
; Init routine
LAXITY_INIT = $1000
; Input: A = song number (usually $00)
; Modifies: All registers
; Returns: Nothing

; Play routine
LAXITY_PLAY = $10A1
; Input: None
; Modifies: All registers
; Returns: Nothing
```

### Table Formats

**Instruments** (8 bytes per entry):
```
Byte 0: AD (Attack/Decay)
Byte 1: SR (Sustain/Release)
Byte 2: Flags
Byte 3: Pulse pointer (lo)
Byte 4: Pulse pointer (hi)
Byte 5: Filter pointer (lo)
Byte 6: Filter pointer (hi)
Byte 7: Wave pointer
```

**Wave Table** (2 bytes per entry):
```
Byte 0: Note offset
Byte 1: Waveform
```

**Pulse Table** (4 bytes per entry):
```
Byte 0: Pulse hi
Byte 1: Pulse lo
Byte 2: Speed
Byte 3: Next index (Y*4)
```

**Filter Table** (4 bytes per entry):
```
Byte 0: Cutoff hi
Byte 1: Cutoff lo
Byte 2: Resonance
Byte 3: Next index
```

---

## Driver Source Code Availability

### Investigation Results

**GitHub Repository** (https://github.com/Chordian/sidfactory2):
- Contains 20 compiled .prg driver files
- **No assembly source code** (.asm files) found
- DEVELOPMENT.md has no driver development documentation
- Drivers created by Laxity and JCH (not open source)

**Local Resources**:
- `G5/drivers/` - Same compiled .prg files
- `learnings/` - Driver .prg files, notes files
- No driver source code found

**Conclusion**: SF2 driver source code is **proprietary** and not publicly available.

---

## Approach Options

### Option A: Reverse Engineer Existing Driver

**Method**:
1. Disassemble Driver 11 binary
2. Understand code structure
3. Replace table reading code with Laxity format
4. Reassemble and test

**Pros**:
- Builds on proven driver code
- Inherits SF2 features (commands, effects)

**Cons**:
- Complex reverse engineering task
- May violate original authors' intent
- Difficult to maintain/modify

**Estimated Effort**: 2-4 weeks

### Option B: Extract and Wrap Laxity Player

**Method**:
1. Extract Laxity player code ($1000-$19FF) from SID file
2. Create thin wrapper to expose init/play entry points
3. Define table offsets matching Laxity memory layout
4. Package as SF2 driver

**Pros**:
- Uses proven Laxity player code directly
- High fidelity to original format
- Simpler than full reverse engineering

**Cons**:
- No SF2 commands/effects (pure Laxity player)
- Table editing may not work correctly
- May require memory relocation

**Estimated Effort**: 1-2 weeks

### Option C: Build Minimal Custom Driver

**Method**:
1. Write minimal 6502 driver from scratch
2. Implement only essential features (play notes, ADSR)
3. Read Laxity table format directly
4. Focus on playback accuracy, not editing

**Pros**:
- Full control over implementation
- Clean codebase
- Can optimize for Laxity format

**Cons**:
- Requires significant 6502 assembly expertise
- Missing SF2 commands/effects initially
- Extensive testing required

**Estimated Effort**: 3-6 weeks

---

## Recommended Approach: Option B (Extract and Wrap)

### Phase 1: Extract Laxity Player

**Tasks**:
1. Load Laxity SID file into memory
2. Extract player code ($1000-$19FF, ~2.5KB)
3. Identify all data table references
4. Document self-modifying code locations

**Tools**:
- Python script to extract binary code
- SIDwinder disassembly for analysis
- Memory dump comparison

### Phase 2: Create SF2 Driver Wrapper

**Tasks**:
1. Create PRG file with load address $0D7E
2. Copy Laxity player code
3. Add init/play entry point wrappers
4. Define table offset constants

**Code Structure**:
```asm
; SF2 Driver - Laxity NewPlayer v21 Wrapper
; Load address: $0D7E

.org $0D7E

; Entry points for SF2
sf2_init:
    jmp laxity_init    ; Jump to Laxity init

sf2_play:
    jmp laxity_play    ; Jump to Laxity play

; Laxity player code (relocated)
laxity_init:
    ; ... extracted code ...

laxity_play:
    ; ... extracted code ...
```

### Phase 3: Define Table Layout

**Create SF2 header blocks**:
- Block 1: Driver descriptor
- Block 2: Entry point addresses
- Block 3: Table definitions with Laxity offsets

**Table mapping**:
```python
# Laxity native addresses (at load $1000)
LAXITY_INSTRUMENTS = 0x1A6B
LAXITY_PULSE = 0x1A3B
LAXITY_FILTER = 0x1A1E
LAXITY_WAVE = 0x1ACB

# Calculate offsets from SF2 load address $0D7E
# Assuming player code relocated to $0D7E
SF2_INSTRUMENT_OFFSET = LAXITY_INSTRUMENTS - 0x1000 + (0x0D7E - 0x0D7E)
# This requires careful address calculation!
```

### Phase 4: Handle Relocation

**Challenge**: Laxity code expects to run at $1000, but SF2 loads at $0D7E.

**Solutions**:

**A. Minimal Relocation**:
- Keep player at $1000 (original address)
- SF2 wrapper at $0D7E just jumps to $1000
- Requires non-overlapping memory

**B. Full Relocation**:
- Relocate all code and data references
- Use SIDwinder `-relocate` functionality
- More complex but cleaner

### Phase 5: Create Conversion Script

**Modify `sid_to_sf2.py`**:
```python
def convert_to_laxity_driver(sid_path, output_path):
    # 1. Load Laxity SID
    # 2. Extract tables using existing code
    # 3. Load Laxity driver template (new!)
    # 4. Inject tables at Laxity-specific offsets
    # 5. Write SF2 file
```

### Phase 6: Testing and Validation

**Test cases**:
1. Load SF2 file in SID Factory II editor
2. Verify playback matches original
3. Export back to SID
4. Compare accuracy with siddump

**Success criteria**:
- SF2 loads without errors
- Playback matches original (70-90% accuracy)
- Can edit basic tables (instruments, wave)

---

## Technical Challenges

### Challenge 1: Memory Relocation

**Problem**: Laxity code has hardcoded addresses

**Solution**: Either:
- Use SIDwinder's relocate feature
- Manually patch address references
- Keep player at original address

### Challenge 2: Self-Modifying Code

**Problem**: Laxity may modify its own code at runtime

**Solution**:
- Identify all SMC locations via disassembly
- Ensure relocated code updates correct addresses
- Test thoroughly with siddump comparison

### Challenge 3: Zero Page Usage

**Problem**: Laxity uses specific zero-page addresses

**Solution**:
- Document Laxity's zero-page map
- Check for conflicts with SF2 editor
- May need to relocate ZP vars (complex!)

### Challenge 4: SF2 Header Blocks

**Problem**: No documentation for creating header blocks

**Solution**:
- Analyze existing driver headers with hex editor
- Copy structure from Driver 11
- Modify table offset fields

### Challenge 5: Table Editing

**Problem**: SF2 editor may not understand Laxity table format

**Solution**:
- Initial version: playback only
- Phase 2: Add table editing support
- May require editor modifications (not feasible)

---

## Next Steps

1. ✅ **Research SF2 driver structure** - COMPLETED
2. **Analyze existing driver binaries** - IN PROGRESS
   - Hex dump Driver 11 header
   - Map header block structure
   - Identify init/play addresses
3. **Extract Laxity player code**
   - Choose reference SID file
   - Extract code region $1000-$19FF
   - Disassemble with SIDwinder
4. **Create minimal driver wrapper**
   - Write init/play entry points
   - Set up table pointers
   - Build PRG file
5. **Test basic playback**
   - Load in SF2 editor
   - Verify sound output
   - Check for crashes
6. **Implement full conversion pipeline**
   - Modify `sid_to_sf2.py`
   - Add Laxity driver option
   - Test with all 18 files

---

## References

### Documentation
- `docs/ARCHITECTURE.md` - System architecture
- `docs/reference/SF2_FORMAT_SPEC.md` - SF2 file format
- `docs/reference/DRIVER_REFERENCE.md` - Driver feature comparison
- `docs/reference/STINSENS_PLAYER_DISASSEMBLY.md` - Laxity player analysis
- `learnings/21.g5_Final.txt` - Laxity NewPlayer v21 instructions
- `learnings/notes_driver11.txt` - Driver 11 table formats

### Tools
- `tools/SIDwinder.exe` - Disassembly, relocation, trace
- `tools/siddump.exe` - Register dump validation
- `tools/player-id.exe` - Player type detection

### Source Code
- GitHub: https://github.com/Chordian/sidfactory2 (no driver source)
- SID Factory II blog: https://blog.chordian.net/sf2/
- CSDb: https://csdb.dk/release/?id=213369

### Previous Research
- `LAXITY_NP20_RESEARCH_REPORT.md` - Format compatibility analysis
- `KNOWLEDGE_CONSOLIDATION_NP20_RESEARCH.md` - Strategic learnings

---

## Appendix A: Driver File Analysis

### Driver 11 Binary Structure

```
Offset    Content (hex)                       Description
--------  ----------------------------------  -----------
$0000-01  7E 0D                              Load address: $0D7E
$0002-03  37 13                              Unknown header
$0004-05  01 29                              Unknown
$0006-10  ...                                Driver metadata
$0011-1F  "11.00.00 - T" "S"                Driver version string
$0020-...  [binary code]                     Driver 6502 code
```

### Header Block Structure (TBD)

Need to analyze with hex editor to understand:
- Block size encoding
- Block ID markers
- Table offset fields
- Entry point addresses

---

## Status

**Current Phase**: Research and Analysis
**Next Milestone**: Extract and analyze Driver 11 header structure
**Blockers**: None identified
**Risk Level**: Medium (driver source code unavailability)

**Success Probability**:
- Playback only: 80%
- Full editing support: 40%
- Achieving 70-90% accuracy: 70%
