# SIDM2 Architecture

Complete architecture documentation for the SID to SF2 converter system.

## System Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Laxity SID │────>│ SID to SF2   │────>│   SF2 File  │
│  (Original) │     │  Converter   │     │  (Editable) │
└─────────────┘     └──────────────┘     └─────────────┘
                            │                     │
                            v                     v
                    ┌──────────────┐     ┌─────────────┐
                    │  Validation  │     │  SF2 to SID │
                    │    System    │     │    Packer   │
                    └──────────────┘     └─────────────┘
                                                 │
                                                 v
                                         ┌─────────────┐
                                         │ Packed SID  │
                                         │ (Playable)  │
                                         └─────────────┘
```

---

## Conversion Flow

### 1. Parse SID Header (PSID v2)

Extract metadata and entry points:

```
Offset  Field
------  -----
0x00    Magic bytes: 'PSID' or 'RSID'
0x04    Version (0x0002)
0x06    Data offset (usually 0x007C = 124 bytes)
0x08    Load address (0x0000 = read from data)
0x0A    Init address
0x0C    Play address
0x0E    Number of songs
0x10    Start song
0x16    Title (32 bytes, null-terminated)
0x36    Author (32 bytes, null-terminated)
0x56    Copyright (32 bytes, null-terminated)
```

### 2. Identify Player Type

Use `player-id.exe` to detect player format:
- Laxity NewPlayer v21 (supported)
- GoatTracker (not supported)
- JCH (not supported)
- etc.

### 3. Load SID Data into 64KB Memory Model

```python
memory = bytearray(65536)  # 64KB C64 memory
load_addr = get_load_address(sid_data)
memory[load_addr:load_addr+len(sid_data)] = sid_data
```

### 4. Extract Tables

Extract music data structures from player code:
- Instruments (ADSR + table pointers)
- Wave table (waveform + note offset pairs)
- Pulse table (PWM programs)
- Filter table (filter sweeps)
- Commands (effect parameters)

See [Table Extraction Strategy](#table-extraction-strategy) below.

### 5. Extract Sequences (Hybrid Approach v1.3)

**Static Extraction**:
- Parse sequence pointer table
- Extract note/instrument/command data

**Runtime Extraction** (NEW in v1.3):
- Run siddump to capture actual played sequences
- Detect repeating patterns
- Convert to SF2 format with proper gate markers

### 6. Load SF2 Template for Target Driver

Load pre-built SF2 file with driver code:
- Driver 11 (default, full features)
- NP20 (NewPlayer-compatible)

Templates contain:
- Complete driver code (~2KB 6502 assembly)
- Empty table placeholders
- Correct header structure

### 7. Inject Extracted Data into Template

Write tables at known offsets:

```python
# Driver 11 offsets
SEQUENCE_TABLE_OFFSET = 0x0903
INSTRUMENT_TABLE_OFFSET = 0x0A03
WAVE_TABLE_OFFSET = 0x0B03
PULSE_TABLE_OFFSET = 0x0D03
FILTER_TABLE_OFFSET = 0x0F03
```

### 8. Write Output .sf2 File

Write complete SF2 file with:
- PSID v2 header
- Driver code
- Music data tables
- Sequences and orderlists

---

## Table Extraction Strategy

### Challenge

Music data structures in SID files don't have fixed addresses - they vary by song.

### Solution

Multi-stage heuristic search:

#### Stage 1: Search for Pointer Patterns

Look for pointer tables in player code:
```
Example: Instrument pointer table
  Address   Bytes
  -------   -----
  $19A0:    0D 1A    ; Pointer to instrument 0 ($1A0D)
  $19A2:    15 1A    ; Pointer to instrument 1 ($1A15)
  $19A4:    1D 1A    ; Pointer to instrument 2 ($1A1D)
  ...
```

#### Stage 2: Score Candidates

Apply validity heuristics:
- Pointers must be ascending
- Pointers must point to valid memory regions
- Data at pointers must match expected format
- Must contain end marker (0x7F) within reasonable distance

#### Stage 3: Extract Entries

Follow pointers and extract until end marker:
```python
def extract_table(memory, start_ptr, entry_size):
    entries = []
    ptr = start_ptr
    while True:
        entry = memory[ptr:ptr+entry_size]
        if entry[0] == 0x7F:  # End marker
            break
        entries.append(entry)
        ptr += entry_size
    return entries
```

### Table-Specific Strategies

#### Wave Table
- Format: (waveform, note_offset) pairs
- End: 0x7F marker or 0x7E loop
- Scoring: Valid waveforms (0x00-0x81), reasonable note offsets (0x00-0x80)

#### Pulse Table
- Format: 4 bytes (pulse_hi, pulse_lo, speed, next_index)
- End: 0x7F in next_index
- Scoring: Valid pulse values (0x000-0xFFF), reasonable speeds

#### Filter Table
- Format: 4 bytes (cutoff_hi, cutoff_lo, resonance, next_index)
- End: 0x7F in next_index
- Scoring: Valid cutoff (0x000-0x7FF), valid resonance (0x00-0xFF)

#### Instrument Table
- Format: 8 bytes (ADSR + table indices)
- End: 0x7F in first byte
- Scoring: Valid ADSR values, valid table indices

---

## SF2 Template-Based Approach

### Why Templates?

SF2 files are driver-dependent with complex interdependencies:
- Driver code: ~2KB of 6502 assembly
- Header blocks: Intricate pointer relationships
- Table offsets: Must align exactly with driver expectations

Building from scratch is error-prone. Templates provide battle-tested foundations.

### Template Structure

```
┌─────────────────────────────────────────┐
│         PSID v2 Header (124 bytes)      │
├─────────────────────────────────────────┤
│      Driver Code (~2KB 6502 assembly)   │
│  - Init routine                         │
│  - Play routine                         │
│  - Table lookup code                    │
│  - SID register write routines          │
├─────────────────────────────────────────┤
│          Music Data Tables              │
│  - Sequences (per-voice note data)      │
│  - Orderlists (pattern arrangements)    │
│  - Instruments (ADSR + pointers)        │
│  - Wave table (waveforms)               │
│  - Pulse table (PWM programs)           │
│  - Filter table (filter sweeps)         │
│  - Arp table (chord patterns)           │
│  - HR table (hard restart ADSR)         │
│  - Tempo table (speed values)           │
│  - Init table (song initialization)     │
└─────────────────────────────────────────┘
```

### Injection Process

1. **Load template** - Read pre-built SF2 file
2. **Clear tables** - Zero out table regions
3. **Write data** - Inject extracted tables at known offsets
4. **Update pointers** - Adjust sequence/orderlist pointers
5. **Validate** - Check table boundaries and references

### Template Variants

| Driver | Features | Use Case |
|--------|----------|----------|
| Driver 11 | Full features, separate tables | Default (luxury driver) |
| NP20 | NewPlayer-compatible layout | Laxity format preservation |
| Driver 12 | Minimal features | Size-constrained projects |
| Driver 13 | Rob Hubbard emulation | Specific sound emulation |

---

## Key Format Differences (Laxity vs SF2)

### Wave Table Byte Order

**Laxity NewPlayer**:
```
Byte 0: Note offset
Byte 1: Waveform
```

**SID Factory II**:
```
Byte 0: Waveform
Byte 1: Note offset
```

**Conversion**: Swap byte order during extraction.

### Pulse Table Indexing

**Laxity NewPlayer**:
```
; Y register pre-multiplied by 4
LDA pulse_table,Y
```

**SID Factory II**:
```
; Direct index, driver multiplies by 4
LDA pulse_table,X
```

**Conversion**: Divide Laxity indices by 4.

### Gate Handling

**Laxity NewPlayer**:
- Implicit gate control via waveform values
- Gate on: waveform |= 0x01
- Gate off: waveform &= 0xFE

**SID Factory II**:
- Explicit gate markers in sequences
- `0x7E` (+++): Gate on
- `0x80` (---): Gate off
- No marker (--): Hold current gate state

**Conversion**: Detect gate transitions and insert explicit markers.

---

## Gate System

### SF2 Gate Notation

```
+++ = Gate on (trigger attack)
--- = Gate off (trigger release)
**  = Tie note (no envelope restart)
--  = No change (hold current state)
```

### Gate Byte Values

```python
GATE_ON = 0x7E      # +++
GATE_OFF = 0x80     # ---
NO_CHANGE = 0x80    # -- (context-dependent)
END_MARKER = 0x7F   # End of sequence
```

### Example Sequence

```
Note  Gate   Meaning
----  ----   -------
C-4   +++    Play C-4, gate on (attack)
---   ---    Gate off (release)
E-4   +++    Play E-4, gate on (attack)
---   ---    Gate off (release)
G-4   +++    Play G-4, gate on (attack)
G-4   **     Hold G-4, no envelope restart (tie)
---   ---    Gate off (release)
7F    -      End marker
```

### Why Explicit Gates?

Provides precise envelope control:
- Independent control of attack/release timing
- Supports advanced articulation (staccato, legato)
- Different from GoatTracker/CheeseCutter implicit systems

Trade-off: Requires more rows per note (~2-4 rows typical).

---

## Hard Restart (HR)

### Problem: ADSR Bug

SID chip's ADSR envelope generator has a bug (Martin Galway's "school band effect"):
- When retriggering quickly, envelope may not reset properly
- Results in notes with wrong attack/decay characteristics
- Sounds like "wheezing" or "gasping"

### Solution: Hard Restart

Driver implements HR to stabilize envelope:

1. **2 frames before next note**: Gate off
2. **Apply HR table ADSR**: Temporary ADSR values (default: `$0F $00`)
   - Attack: Fast (0x0F)
   - Decay: Immediate (0x00)
   - Sustain: 0
   - Release: 0
3. **Next note triggers**: Envelope is now stabilized

### HR Table Format

```
HR Table Entry (2 bytes):
  Byte 0: AD (Attack/Decay)    - Default: 0x0F (fast attack, immediate decay)
  Byte 1: SR (Sustain/Release) - Default: 0x00 (no sustain/release)
```

### Instrument Flags

Bit 0 of instrument flags byte enables HR:
```python
INSTR_FLAGS_HR_ENABLED = 0x01

# Most instruments should enable HR
instrument_flags = 0x01  # HR enabled
```

### When to Use HR

**Enable for**:
- Fast note retriggering
- Percussive sounds
- Staccato articulation

**Disable for**:
- Slow, sustained notes
- Legato passages
- When ADSR bug is not audible

---

## Laxity Super Command Mappings

Commands in Laxity player must be mapped to SF2 command system.

### Command Mapping Table

| Laxity Command | SF2 Command | Parameters | Notes |
|----------------|-------------|------------|-------|
| `$0x yy` | T0 slide | Direct | Slide up by yy |
| `$2x yy` | T0 slide | Direct | Slide down by yy |
| `$60 xy` | T1 vibrato | x→XX, y→YY | Vibrato depth/speed |
| `$8x xx` | T2 portamento | Direct | Slide to target note |
| `$9x yy` | T9 set ADSR | Direct | Persistent ADSR change |
| `$ax yy` | T8 local ADSR | Direct | ADSR until next note |
| `$e0 xx` | Td tempo | Direct | Speed change |
| `$f0 xx` | Te volume | Direct | Master volume |

### SF2 Command Format

```
Command Table Entry (3 bytes):
  Byte 0: Command type (0x00-0x0F)
  Byte 1: Parameter 1
  Byte 2: Parameter 2
```

### Command Types

```python
# Command byte values (from SF2 source)
CMD_SLIDE = 0x00
CMD_VIBRATO = 0x01
CMD_PORTAMENTO = 0x02
CMD_ARPEGGIO = 0x03
CMD_FRET = 0x04
CMD_ADSR_NOTE = 0x08
CMD_ADSR_PERSIST = 0x09
CMD_INDEX_FILTER = 0x0A
CMD_INDEX_WAVE = 0x0B
CMD_INDEX_PULSE = 0x0C      # Driver 11.02+
CMD_TEMPO = 0x0D            # Driver 11.02+
CMD_VOLUME = 0x0E           # Driver 11.02+
CMD_DEMO_FLAG = 0x0F
```

---

## Special Wave Table Cases

### $80 Note Offset (Hubbard Slide)

**Purpose**: Recalculate frequency without overwriting current waveform.

**Behavior**:
```
Base note:    C-4 (MIDI 60)
Transpose:    +7 (orderlist)
Note offset:  $80

Result: Frequency = freq_table[60 + 7]
        Waveform unchanged
```

**Use case**: "Hubbard slide" effect - smooth frequency transitions while maintaining waveform.

### Vibrato/Slide Limitation

**Rule**: Vibrato and slide effects only apply to wave entries with `note_offset = $00`.

**Reason**: Non-zero offsets recalculate frequency each frame, overriding vibrato/slide.

**Example**:
```
Wave Entry        Vibrato Applied?
-----------       ----------------
$11 $00          YES (note_offset = 0)
$11 $05          NO  (note_offset != 0)
$11 $80          NO  (special case)
```

---

## Speed/Break Speed System

### Normal Speed

Standard tempo system:
```
Tempo Table:
  Row 0: Speed value (frames per row)
  Row 1: Speed value
  ...
  Row N: 0x7F (end marker) + wrap_row
```

### Break Speed (Laxity-specific)

Special speed lookup triggered by speed values `$00` and `$01`:

**Mechanism**:
1. Speed `$00` or `$01` encountered
2. Driver reads **first 4 bytes of filter table**
3. Cycles through these 4 values
4. Wraps automatically

**Example**:
```
Filter Table (first 4 bytes):
  $06, $06, $06, $05

Break speed sequence:
  Frame 0-5:   Speed 6 (6 frames/row)
  Frame 6-11:  Speed 6
  Frame 12-17: Speed 6
  Frame 18-22: Speed 5
  Frame 23:    Wrap to speed 6
```

**Wrap Marker**: `$00` in break speed table = wrap to start.

**Conversion Challenge**: Must preserve break speed data when extracting filter table.

---

## Complete Pipeline Architecture

### The 12 Pipeline Steps

#### Step 1: SID → SF2 Conversion
- Smart file type detection (SF2-packed vs Laxity)
- Conversion method selection (REFERENCE/TEMPLATE/LAXITY)
- Table extraction and sequence generation

#### Step 1.5: Siddump Sequence Extraction (NEW v1.3)
- Runtime analysis using siddump
- Pattern detection in actual played sequences
- Injection of runtime sequences into SF2
- Hybrid approach for improved accuracy

#### Step 2: SF2 → SID Packing
- Uses `sidm2/sf2_packer.py`
- Generates PSID v2 header
- Performs pointer relocation
- Creates playable SID file

#### Step 3: Siddump Generation
- Runs `tools/siddump.exe` on both original and exported
- Captures 30 seconds of register writes
- Pipe-delimited output format
- Used for validation comparison

#### Step 4: WAV Rendering
- Runs `tools/SID2WAV.EXE` on both files
- 30-second, 16-bit audio
- Enables audio quality comparison
- Human-audible validation

#### Step 5: Hexdump Generation
- Creates xxd-format hexdumps
- Byte-level comparison capability
- Debug binary differences
- Identifies specific relocation issues

#### Step 6: SIDwinder Trace
- ⚠️ Requires rebuilt SIDwinder.exe
- Frame-by-frame register trace
- Text format: `FRAME N: D400:$xx,...`
- Currently generates empty files

#### Step 7: Info.txt Reports
- Comprehensive conversion metadata
- Address mappings
- Table sizes and locations
- Validation warnings
- Accuracy metrics

#### Step 8: Annotated Disassembly
- Python-based disassembly
- Annotated with addresses
- Human-readable format
- Always succeeds

#### Step 9: SIDwinder Disassembly
- Professional disassembly using SIDwinder
- KickAssembler-compatible
- ⚠️ Fails on exported SIDs due to packer bug
- Works correctly on original SIDs

#### Step 10: Validation Check
- Verifies all 16 required files generated (11 New + 5 Original)
- Reports: COMPLETE (all files) or PARTIAL (some missing)
- Identifies missing files
- Generates summary statistics

#### Step 11: MIDI Comparison (NEW v1.2)
- Exports SID to MIDI using Python MIDI emulator
- Generates `{filename}_python.mid`
- Creates comparison report `{filename}_midi_comparison.txt`
- 100.66% overall accuracy (3 perfect matches)
- See `docs/analysis/MIDI_VALIDATION_COMPLETE.md` for complete validation results

#### Step 12: Final Summary
- Displays pipeline completion status
- Reports total file count
- Shows any warnings or errors

### Output Structure

```
output/SIDSF2player_Complete_Pipeline/
└── {filename}/
    ├── Original/
    │   ├── {filename}_original.dump         # Siddump capture
    │   ├── {filename}_original.wav          # Audio
    │   ├── {filename}_original.hex          # Hexdump
    │   ├── {filename}_original.txt          # SIDwinder trace
    │   └── {filename}_original_sidwinder.asm # SIDwinder disassembly
    └── New/
        ├── {filename}.sf2                       # SF2 file
        ├── {filename}_exported.sid              # Packed SID
        ├── {filename}_exported.dump             # Siddump capture
        ├── {filename}_exported.wav              # Audio
        ├── {filename}_exported.hex              # Hexdump
        ├── {filename}_exported.txt              # SIDwinder trace
        ├── {filename}_exported_disassembly.md   # Python disasm
        ├── {filename}_exported_sidwinder.asm    # SIDwinder disasm
        ├── {filename}_python.mid                # Python MIDI export (NEW v1.2)
        ├── {filename}_midi_comparison.txt       # MIDI validation (NEW v1.2)
        └── info.txt                             # Comprehensive report
```

### File Type Detection

**SF2-packed SID files**:
```python
load_addr == 0x1000 and
init_addr == 0x1000 and
play_addr == 0x1003
```

**Laxity format SID files**:
```python
load_addr >= 0xA000 or
has_laxity_init_pattern(memory)
```

### Conversion Method Selection

**REFERENCE** (100% accuracy):
- Requires original SF2 file as template
- Extracts tables using known offsets
- Perfect table reproduction

**TEMPLATE** (variable accuracy):
- Uses generic SF2 template
- Heuristic table extraction
- Quality depends on extraction success

**LAXITY** (format-specific):
- Parses original Laxity NewPlayer format
- Specialized extraction for Laxity structures
- Handles Laxity-specific quirks

### Validation System

Checks for 16 required files:
- 5 in Original/ (.dump, .wav, .hex, .txt, .asm)
- 11 in New/ (.sf2, .sid, .dump, .wav, .hex, .txt, .md, .asm, .mid, .txt, info.txt)

**Status**:
- **COMPLETE**: All 16 files present
- **PARTIAL**: Some files missing (reports which ones)

### Known Limitations

**SIDwinder Disassembly of Exported SIDs** (Step 9):
- **Impact**: 17/18 exported SIDs fail disassembly
- **Error**: "Execution at $0000"
- **Root Cause**: Pointer relocation bug in `sidm2/sf2_packer.py`
- **Scope**: Only affects SIDwinder's strict CPU emulation
- **Workaround**: Files play correctly in VICE, SID2WAV, siddump
- **Status**: Known limitation, under investigation

**SIDwinder Trace** (Step 6):
- **Impact**: Empty trace files
- **Root Cause**: Three bugs in SIDwinder source
- **Status**: ✅ Bugs fixed in source code
- ⚠️ Requires rebuild of SIDwinder.exe to activate

---

## SF2 Driver Reference

### Driver 11 (Default)

The "luxury" driver with full features.

#### Tables

| Table | Purpose | Format | Size |
|-------|---------|--------|------|
| Init | Song initialization | `tempo_row volume` | 2 bytes |
| Tempo | Speed values | `speed ... 7F wrap_row` | Variable |
| HR | Hard restart ADSR | `AD SR` | 32 × 2 bytes |
| Instruments | ADSR + pointers | 6 bytes column-major | 32 × 6 bytes |
| Commands | Effect parameters | 3 bytes | 32 × 3 bytes |
| Wave | Waveform sequences | `waveform note_offset` | Variable |
| Pulse | PWM programs | `hi lo speed next` | Variable |
| Filter | Filter sweeps | `hi lo res next` | Variable |
| Arp | Chord patterns | Semitone offsets | Variable |

#### Memory Layout

```
$1000-$1FFF: Driver code (~2KB)
$0903:       Sequence table
$0A03:       Instrument table
$0B03:       Wave table
$0D03:       Pulse table
$0F03:       Filter table
```

#### Features

- 12-bit pulse width control
- 12-bit filter cutoff control
- Hard restart support
- Full command system
- Column-major instrument table

### Other Drivers

**Driver 12**: Extremely simple, minimal features
**Driver 13**: Rob Hubbard sound emulation
**Driver 15/16**: Tiny drivers for size-constrained projects

---

## Module Architecture

### Conversion Pipeline (`sidm2/conversion_pipeline.py`)

**Purpose**: Core business logic for SID to SF2 conversion, separated from CLI interface for testability.

**Key Functions**:

1. **`detect_player_type(filepath: str) -> str`**
   - Detects SID player type using player-id.exe
   - Returns: "NewPlayer_v21/Laxity", "SidFactory_II", "Unknown", etc.

2. **`analyze_sid_file(filepath, config, sf2_reference_path) -> ExtractedData`**
   - Parses SID file and analyzes player structure
   - Returns ExtractedData namedtuple with header and C64 data

3. **`convert_laxity_to_sf2(input_path, output_path, config) -> bool`**
   - Converts Laxity NewPlayer v21 SID using custom driver
   - Achieves 99.93% accuracy
   - Returns True on success

4. **`convert_galway_to_sf2(input_path, output_path, config) -> bool`**
   - Converts Martin Galway SID files
   - Uses table extraction and injection
   - Returns True on success

5. **`convert_sid_to_sf2(input_path, output_path, driver_type, config, ...)`**
   - Main conversion function with automatic driver selection
   - Supports all driver types (laxity, driver11, np20, galway)
   - Raises sidm2_errors on failure

6. **`convert_sid_to_both_drivers(input_path, output_dir, config) -> Dict`**
   - Converts using both driver11 and Laxity for comparison
   - Returns dictionary with conversion results

7. **`print_success_summary(input_path, output_path, driver_selection, validation_result, quiet)`**
   - Formats and prints conversion success message
   - Includes driver selection info and validation results

**Availability Flags** (12 total):
- `LAXITY_CONVERTER_AVAILABLE`
- `GALWAY_CONVERTER_AVAILABLE`
- `SIDWINDER_INTEGRATION_AVAILABLE`
- `DISASSEMBLER_INTEGRATION_AVAILABLE`
- `AUDIO_EXPORT_INTEGRATION_AVAILABLE`
- `MEMMAP_ANALYZER_AVAILABLE`
- `PATTERN_RECOGNIZER_AVAILABLE`
- `SUBROUTINE_TRACER_AVAILABLE`
- `REPORT_GENERATOR_AVAILABLE`
- `OUTPUT_ORGANIZER_AVAILABLE`
- `SIDDUMP_INTEGRATION_AVAILABLE`
- `ACCURACY_INTEGRATION_AVAILABLE`

**Module Exports** (`__all__`): All 7 functions + all 12 availability flags

**Test Coverage**: 65.89% (299/445 statements covered, 34/34 tests passing)
- Statement coverage: 299/445 (65.89%)
- Branch coverage: 90/112 (80.36%)
- Test pass rate: 34/34 (100%)
- Exceeds 50% target by 31.8%
- Coverage improvement: +6.11% from previous 59.78%

**Usage**:
```python
from sidm2.conversion_pipeline import (
    detect_player_type,
    convert_sid_to_sf2,
    LAXITY_CONVERTER_AVAILABLE,
)

player_type = detect_player_type("input.sid")
if LAXITY_CONVERTER_AVAILABLE and player_type == "NewPlayer_v21/Laxity":
    convert_sid_to_sf2("input.sid", "output.sf2", driver_type="laxity")
```

**Related Files**:
- `scripts/sid_to_sf2.py` - Thin CLI wrapper that imports from this module (802 lines)
- `pyscript/test_sid_to_sf2_script.py` - Unit tests (24/24 passing, 100% pass rate)
- `docs/implementation/SID_TO_SF2_REFACTORING_SUMMARY.md` - Refactoring documentation

**History**:
- Created 2025-12-27 via refactoring to separate business logic from CLI script
- Test fixes completed 2025-12-27: 17/24 → 24/24 passing (100% pass rate)
- Coverage improved: 54.15% → 59.78% (+5.63 percentage points)

---

## See Also

- `CLAUDE.md` - Quick reference and workflows
- `docs/TOOLS_REFERENCE.md` - External tools documentation
- `docs/COMPONENTS_REFERENCE.md` - Python modules
- `docs/reference/SF2_FORMAT_SPEC.md` - Complete SF2 format specification
- `docs/reference/CONVERSION_STRATEGY.md` - Laxity to SF2 mapping
- `docs/guides/VALIDATION_GUIDE.md` - Comprehensive validation system guide (v2.0.0)
- `docs/analysis/ACCURACY_ROADMAP.md` - Accuracy improvement plan
- `PIPELINE_EXECUTION_REPORT.md` - Pipeline execution analysis
- `docs/implementation/SID_TO_SF2_REFACTORING_SUMMARY.md` - Conversion pipeline refactoring
