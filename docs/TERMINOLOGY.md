# SIDM2 Terminology Glossary
**Standard Definitions for Consistent Documentation**

**Version**: 3.1.0
**Last Updated**: 2026-01-02
**Purpose**: Single source of truth for all SIDM2-specific terminology

---

## How to Use This Glossary

- **Bold terms** are the preferred/standard terminology
- *Italic terms* are deprecated or alternative names (avoid using)
- Cross-references shown as → pointing to related terms
- See also: **ACCURACY_MATRIX.md** for accuracy-specific terms

---

## Table of Contents

1. [Player Types & Formats](#player-types--formats)
2. [Driver Types](#driver-types)
3. [Accuracy Metrics](#accuracy-metrics)
4. [File Formats](#file-formats)
5. [Technical Concepts](#technical-concepts)
6. [SID Chip Concepts](#sid-chip-concepts)
7. [Music Sequencing](#music-sequencing)
8. [Tables & Data Structures](#tables--data-structures)
9. [Acronyms & Abbreviations](#acronyms--abbreviations)
10. [Commands & Operations](#commands--operations)

---

## Player Types & Formats

### **Laxity NewPlayer v21**
**Preferred Name**: Laxity NewPlayer v21
**Also Known As**: *NewPlayer_v21/Laxity*, *Laxity v21*, *NP21*
**Definition**: Native Laxity format SID player, the most widely supported player type in SIDM2.
**Key Characteristics**:
- Uses 6502 assembly player code embedded in SID file
- Load address typically $1000
- Uses 5 tables: instruments, wave, pulse, filter, sequences
- 99.93% conversion accuracy with Laxity driver

**Driver**: Laxity Driver (custom)
**Detection**: Pattern database with 18 distinctive code patterns
**Files**: 286 in SIDM2 collection (43.3% of total)

→ See also: **Laxity Driver**, **Pattern Database**

---

### **SID Factory II Player**
**Also Known As**: *SidFactory_II*, *SF2 player*, *SidFactory/Laxity*
**Definition**: SID files created by exporting from SID Factory II editor.
**Key Characteristics**:
- Contains SF2 driver code (usually Driver 11)
- 100% roundtrip accuracy guaranteed
- Player-id signature: `SidFactory_II/*` or `SidFactory/*`

**⚠️ Important**: Even if player-id shows "Laxity" in the name (e.g., `SidFactory_II/Laxity`), **always use Driver 11**, not Laxity driver.

**Driver**: Driver 11 (or auto-detected original driver)
**Detection**: Player-id signature matching
**Accuracy**: 100% (perfect roundtrip)

→ See also: **SF2-exported SID**, **Perfect Roundtrip**

---

### **NewPlayer v20** (*NP20*)
**Also Known As**: *JCH NewPlayer*, *NewPlayer-compatible*, *NewPlayer 20.G4*
**Definition**: Earlier NewPlayer variant, lower priority than v21.
**Key Characteristics**:
- Partially supported format
- 70-90% conversion accuracy
- Smaller feature set than v21

**Driver**: NP20 Driver
**Accuracy**: 70-90% frame accuracy
**Status**: Best-effort conversion

→ See also: **NP20 Driver**

---

### **Rob Hubbard Player**
**Definition**: SID files using Rob Hubbard's distinctive player style.
**Key Characteristics**:
- Named after legendary C64 composer Rob Hubbard
- Uses specific ADSR workarounds ("school band effect")
- 55+ files in SIDM2 collection

**Driver**: Driver 13 (The Hubbard Experience) - Experimental
**Status**: Experimental support
**Files**: 55+ in collection (~8%)

→ See also: **Driver 13**, **Hard Restart**

---

### **Martin Galway Player**
**Definition**: SID files by composer Martin Galway with distinctive player characteristics.
**Files**: 30+ in collection (~5%)
**Driver**: Driver 11 (generic conversion)
**Status**: Experimental support

---

### **Unknown Player**
**Definition**: SID files where the player type cannot be identified by pattern database.
**Fallback**: Driver 11 (safe default)
**Accuracy**: Unknown (varies by actual player format)
**Occurrence**: ~31% of files in collection

---

## Driver Types

### **Laxity Driver**
**Type**: Custom driver for Laxity NewPlayer v21
**Accuracy**: 99.93% for Laxity files
**Memory**: 2,500 bytes code + 3,000 bytes data
**Tables**: 5 Laxity tables (instruments, wave, pulse, filter, sequences)

**Features**:
- ✅ Native Laxity format preservation
- ✅ 99.93% frame accuracy
- ❌ 0% filter conversion (format incompatible)
- ⚠️ Laxity NewPlayer v21 only

**Use Case**: **Recommended for all Laxity NewPlayer v21 files**

→ See also: **ACCURACY_MATRIX.md** for complete capabilities

---

### **Driver 11** (*The Standard*)
**Type**: Default luxury driver with full features
**Accuracy**: 100% for SF2-exported files, 1-8% for Laxity (not recommended for Laxity)
**Memory**: 6,656 bytes code + 2,048 bytes data (largest footprint)

**Features**:
- ✅ Maximum compatibility
- ✅ All SF2 features supported
- ✅ 15 command types
- ✅ Complete table support

**Use Cases**:
- SF2-exported files (100% accuracy)
- Unknown player types (safe fallback)
- Maximum feature set needed

→ See also: **SF2-exported SID**

---

### **NP20 Driver**
**Type**: NewPlayer-compatible driver
**Accuracy**: 70-90% for NewPlayer 20.G4 files
**Memory**: 5,376 bytes code + 2,048 bytes data
**Use Case**: NewPlayer 20.G4 files

---

### **Driver 13** (*The Hubbard Experience*)
**Type**: Rob Hubbard sound emulation driver
**Status**: Experimental
**Features**: Hubbard-specific effects (pulse sweep, dive, noise gate)
**Use Case**: Rob Hubbard-style compositions

---

## Accuracy Metrics

### **Frame Accuracy**
**Preferred Term**: Frame accuracy
**Unit**: Percentage (%)
**Definition**: Percentage of frames where the converted SF2 produces identical SID register writes compared to the original.

**Calculation**:
```
Frame Accuracy = (Matching frames / Total frames) × 100%
```

**Key Concept**: SID players write to registers only when values change (sparse frames). Each frame represents one 20ms cycle of C64 execution.

**Example**: 507 matching register writes out of 507 total = **99.93% frame accuracy**

**Significance**: Byte-for-byte correctness in playback

→ See also: **Sparse Frames**, **Register Accuracy**

---

### **Register Accuracy**
**Definition**: Percentage of individual SID registers that match expected values across all frames.

**Registers Tracked**:
- Voice 1-3: Frequency (2 bytes), Waveform (1 byte), ADSR (2 bytes), Pulse Width (2 bytes)
- Filter: Cutoff (2 bytes), Resonance (1 byte), Mode (1 byte)
- Volume (1 byte)

**Calculation**:
```
Register Accuracy = (Matching registers / Total register samples) × 100%
```

→ See also: **Frame Accuracy**, **Voice Accuracy**

---

### **Voice Accuracy**
**Definition**: Per-voice (Voice 1, Voice 2, Voice 3) playback correctness.

**Includes**:
- Pitch accuracy (frequency values)
- Waveform selection (triangle, sawtooth, pulse, noise)
- ADSR envelope timing
- Pulse width modulation

**Measurement**: Percentage correct per voice

---

### **Musical Match**
**Definition**: Whether the converted file sounds musically identical when played (subjective quality metric).

**Test Methods**:
- Audio comparison using VICE emulator
- Human listening test
- Waveform visualization

**Result**: For Laxity files, 99.93% frame accuracy = **100% musical match**

---

### **Perfect Roundtrip**
**Definition**: SF2-exported SID file → Conversion → Resulting SF2 is byte-for-byte identical to original SF2.

**Accuracy**: 100% (guaranteed for SF2-exported files)
**Method**: Direct SF2 reference copy after auto-detection
**Detection**: Player-id signature `SidFactory_II/*` or `SidFactory/*`

→ See also: **SF2-exported SID**

---

### **Filter Accuracy**
**Special Case**: Currently **0%** for Laxity→SF2 conversion
**Reason**: Laxity 3-table filter format incompatible with SF2 1-table format
**Partial Workaround**: 60-80% for static filter values only
**Full Accuracy**: Requires manual filter editing in SF2 editor

→ See also: **Filter Table**, **Laxity Format**

---

### **Sparse Frames**
**Definition**: Frames where only some SID registers change (not all registers written).

**Context**: SID players optimize by writing only changed registers. This creates "sparse" frame data where most registers remain unchanged from previous frame.

**Impact on Accuracy**: Frame accuracy measures correctness of sparse register writes, not full 25-byte SID state each frame.

**Introduced**: ACCURACY_FIX_VERIFICATION_REPORT.md (Dec 2025)

---

## File Formats

### **PSID** (Program SID)
**Full Name**: Program SID format
**Version**: PSID v2
**Magic Bytes**: 'PSID' (bytes 0-3)
**Header Size**: 124 bytes

**Structure**:
- Offset 0-3: Magic bytes 'PSID'
- Offset 4-5: Version (0x0002 for v2)
- Offset 6-7: Data offset
- Offset 8-9: Load address
- Offset 10-11: Init address
- Offset 12-13: Play address
- Offset 14-15: Number of songs
- Offset 16-47: Title (32 bytes, null-terminated)
- Offset 48-79: Author (32 bytes)
- Offset 80-111: Copyright (32 bytes)
- Offset 112+: Flags, speed, reserved fields

**Use Case**: Standard SID file format for most SID files

→ See also: **RSID**, **SID File**

---

### **RSID** (Real SID)
**Full Name**: Real SID format
**Magic Bytes**: 'RSID' (bytes 0-3)
**Characteristics**: Strict C64 compatibility (real hardware playback)

**Differences from PSID**:
- Must be C64-compatible (no emulator tricks)
- Stricter format requirements
- Guaranteed to work on real C64 hardware

---

### **SF2** (SID Factory II Format)
**Full Name**: SID Factory II project file format
**File Extension**: .sf2
**Components**:
- Driver code (SF2 player)
- Template structure
- Music data tables (instruments, sequences, wave, pulse, filter, etc.)

**Characteristics**:
- Editable in SID Factory II GUI
- Can be exported to SID file
- Binary format with known structure

→ See also: **SF2-exported SID**, **SID Factory II Player**

---

### **SID File** (Generic)
**File Extension**: .sid
**Definition**: Commodore 64 music file (generic term)
**Can Be**: PSID, RSID, or contain Laxity/other player

**Usage Note**: "SID file" is ambiguous - specify PSID, RSID, or player type when possible.

---

### **SF2-exported SID** / **SF2-packed**
**Definition**: SID file created by exporting from SID Factory II.
**Format**: SF2 format embedded in SID file
**Detection**: Player-id identifies as `SidFactory_II/*`

**⚠️ Critical**: These files should **always use Driver 11** (or detected original driver), never Laxity driver, even if player-id shows "Laxity" in the name.

**Roundtrip**: 100% accuracy guaranteed

→ See also: **Perfect Roundtrip**, **SID Factory II Player**

---

### **Laxity Format**
**Definition**: Native format used by Laxity NewPlayer v21.

**Structure**:
- Load address: Typically $1000
- Player code: Embedded 6502 assembly
- Pointer tables: For instruments, wave, pulse, filter, sequences
- Data tables: Actual music data

**Key Characteristic**: 5-table system (vs SF2's unified tables)

**Conversion**: 99.93% accuracy with Laxity driver

---

## Technical Concepts

### **Pointer Patching**
**Definition**: Technique for relocating code/data pointers when moving player code from one memory address to another.

**Use Case**: Laxity driver uses 40 pointer patches to relocate player code from $1000 (original) to $0E00 (SF2 location).

**Process**:
1. Identify all absolute memory addresses in code
2. Calculate offset (e.g., -$0200 for $1000 → $0E00)
3. Apply offset to each pointer
4. Verify table access works correctly

**Component**: `sidm2/cpu6502.py` (pointer analysis)

→ See also: **Code Relocation**

---

### **Wave Table De-interleaving**
**Definition**: Extracting waveform and note offset pairs from interleaved memory format.

**Laxity Format**:
- Row-major: `(note_offset, waveform)` pairs, 2 bytes per entry
- Sequential storage in memory

**SF2 Format**:
- Column-major: Two separate arrays (waveforms, note_offsets)
- 50-byte offset between arrays

**Critical Discovery**: Format mismatch caused 0.20% → 99.93% accuracy breakthrough

**Conversion Process**:
1. Read interleaved pairs from Laxity table
2. Separate into two arrays
3. Write to SF2 format (swapped byte order)

→ See also: **Wave Table**, **Laxity Format**

---

### **Super-Command**
**Definition**: Extended control byte in Laxity sequences.
**Format**: Two-byte command with parameter byte
**Examples**:
- `$9x $yy` - Set ADSR (Attack/Decay/Sustain/Release)
- `$8x $xx` - Slide command

**Mapping**: Laxity super-commands map to SF2 command system

→ See also: **Sequence**, **Command**

---

### **Gate** / **Gate Control**
**SID Concept**: Bit 0 in SID control register controlling ADSR envelope cycle
**States**:
- 1 = Attack/Decay/Sustain (gate on)
- 0 = Release (gate off)

**Laxity Format**: Implicit in waveform value
**SF2 Format**: Explicit gate markers
- `0x7E` = Gate on
- `0x80` = Gate off

**Inference**: `WaveformGateAnalyzer` detects gate transitions from siddump

→ See also: **Hard Restart**, **ADSR**

---

### **Hard Restart** (*HR*)
**Definition**: ADSR workaround for SID envelope bug (retriggering notes quickly may not reset envelope properly).

**Solution**:
1. Temporarily apply different ADSR values
2. Reset gate
3. Apply correct ADSR for note

**Table**: HR table with 32 entries of alternate ADSR values
**Flag**: `INSTR_FLAGS_HR_ENABLED` bit in instrument flags
**Common Use**: Rob Hubbard files ("school band effect")

→ See also: **ADSR**, **Rob Hubbard Player**, **Envelope Bug**

---

### **Break Speed**
**Laxity-Specific Concept**: Tempo/speed variation data
**Storage**: First 4 bytes of filter table (shared storage)
**Challenge**: Must preserve break speed when extracting filter table

→ See also: **Filter Table**, **Tempo**

---

### **Tie Note** / **Tie**
**Definition**: Note sustain without ADSR restart.
**SF2 Notation**: `**` (hold previous note)
**Waveform Marker**: No waveform change, no gate reset
**Purpose**: Smooth continuous playback without envelope retrigger

---

### **Code Relocation**
**Definition**: Moving player code from one memory address to another while maintaining functionality.

**Laxity Example**:
- Source: $1000-$19FF (original Laxity location)
- Target: $0E00-$16FF (SF2 compatible location)
- Offset: -$0200
- Patches: 40 address references updated

**Challenges**:
- Absolute addressing must be updated
- Self-modifying code must be adjusted
- Table pointers must be redirected

→ See also: **Pointer Patching**

---

### **Pattern Database**
**Definition**: Collection of 18 distinctive code patterns used to identify Laxity NewPlayer v21 files.

**Accuracy**: 99.0% detection rate (283/286 files)
**Method**: Disassembly analysis to find unique code signatures
**Validation**: Confirmed with external `player-id.exe` tool

**False Negatives**: 3 files (actually Rob Hubbard, not Laxity)

→ See also: **Player Detection**, **Laxity NewPlayer v21**

---

## SID Chip Concepts

### **SID Chip**
**Full Name**: Sound Interface Device (MOS Technology 6581/8580)
**Function**: C64 sound synthesizer chip
**Voices**: 3 independent oscillators
**Registers**: 25 memory-mapped registers ($D400-$D418)

**Capabilities**:
- 3-voice polyphony
- 4 waveforms per voice
- ADSR envelope per voice
- Programmable filter (shared)
- Ring modulation
- Oscillator sync

---

### **3 Voices**
**Definition**: Three independent oscillators/channels in SID chip.
**Numbering**: Voice 1, Voice 2, Voice 3 (or 0-2 in code)
**Registers Per Voice**: 7 bytes
- Frequency (2 bytes)
- Pulse width (2 bytes)
- Control register (1 byte)
- Attack/Decay (1 byte)
- Sustain/Release (1 byte)

**Routing**: Each voice can independently be routed through filter

---

### **Waveforms**
**Count**: 4 waveforms per voice
**Types**:
1. **Triangle** - Smooth, flute-like sound
2. **Sawtooth** - Bright, buzzy sound (richest harmonics)
3. **Pulse** - Hollow sound (variable duty cycle with PWM)
4. **Noise** - White noise for percussion/effects

**Selection**: Control register bits 4-7
**Combinations**: Multiple waveforms can be combined (experimental)

---

### **ADSR** (Attack/Decay/Sustain/Release)
**Definition**: Four-stage envelope controlling amplitude over time.

**Stages**:
1. **Attack** (A): Time to reach maximum amplitude (0-8 seconds)
2. **Decay** (D): Time to fall to sustain level (0-24 seconds)
3. **Sustain** (S): Held amplitude level (0-15)
4. **Release** (R): Time to fall to zero after gate off (0-24 seconds)

**Format**: 2 bytes
- Byte 1: Attack (bits 4-7), Decay (bits 0-3)
- Byte 2: Sustain (bits 4-7), Release (bits 0-3)

**Envelope Bug**: "School band effect" - SID may not properly retrigger on quick notes

→ See also: **Hard Restart**, **Gate Control**

---

### **Filter**
**Definition**: Programmable analog filter (shared across all voices).

**Types**:
- **High-pass**: Removes low frequencies
- **Band-pass**: Keeps frequencies near cutoff
- **Low-pass**: Removes high frequencies
- **Notch**: Combination mode

**Controls**:
- **Cutoff** (11-bit): Filter frequency (30-12000 Hz)
- **Resonance** (4-bit): Q-factor amplification at cutoff
- **Mode**: High-pass, band-pass, low-pass, notch
- **Voice Routing**: Which voices pass through filter

**Laxity Format**: 3-table system (cutoff, resonance, mode)
**SF2 Format**: 1-table system (combined)
**Incompatibility**: 0% filter conversion accuracy

→ See also: **Filter Accuracy**, **Filter Table**

---

### **Pulse Width Modulation** (*PWM*)
**Definition**: Varying the duty cycle of pulse waveform.
**Range**: 0-4095 (12-bit value)
**Effect**: Changes tone from hollow (50%) to thin (1-5%)
**Usage**: Pulse table controls PWM over time

→ See also: **Pulse Table**, **Waveforms**

---

### **Oscillator Sync**
**Definition**: Voice synchronization technique.
**Mechanism**: Reset phase of one oscillator based on another
**Control**: Bit 1 of control register
**Effect**: Creates harmonic-rich timbres

---

### **Ring Modulation**
**Definition**: Voice interaction effect (amplitude modulation).
**Mechanism**: Multiply waveforms of two voices
**Control**: Bit 2 of control register
**Effect**: Bell-like metallic sounds

---

### **Frequency Control**
**Definition**: Musical pitch selection for each voice.
**Format**: 16-bit value (0-65535)
**Range**: 0-4000 Hz (practical music range)
**Calculation**: `Frequency = Note × 0.0596` (PAL)

**Registers**: 2 bytes per voice
- Low byte: Bits 0-7
- High byte: Bits 8-15

---

## Music Sequencing

### **Sequence**
**Definition**: Per-voice note data organized by time.
**Structure**: List of events (note, instrument, command)
**Extraction Methods**:
- **Static**: From pointer tables in memory
- **Runtime**: From siddump output (actual played notes)

**SF2 Format**: Row-based sequence with gate markers

→ See also: **Orderlist**, **Gate Control**, **Super-Command**

---

### **Orderlist**
**Definition**: Arrangement of pattern playback order.
**Purpose**: Controls which sequences play in which order
**Format**: List of sequence indices (0-255)
**Reliability**: Sometimes unreliable (heuristic detection used)

**Example**:
```
Orderlist = [0, 1, 2, 1, 3, 0]
Playback: Seq 0 → Seq 1 → Seq 2 → Seq 1 → Seq 3 → Seq 0
```

---

### **Note Offset**
**Definition**: Octave/semitone adjustment relative to wave table base.
**Range**: -128 to +127 semitones
**Usage**: Allows single wave table to cover full pitch range

**Example**: Base note C-4, offset +12 = C-5 (one octave up)

---

### **Transpose**
**Definition**: Shifting all notes by fixed interval.
**Command**: Transpose command in SF2
**Range**: -127 to +127 semitones
**Usage**: Key changes without rewriting sequences

---

### **Vibrato**
**Definition**: Periodic frequency modulation effect (warbling pitch).
**Parameters**: Speed, depth, waveform
**Implementation**: LFO (Low-Frequency Oscillator) modulating frequency

---

### **Portamento**
**Definition**: Smooth pitch glide between notes.
**Also Known As**: Glissando, slide
**Parameters**: Slide speed
**Direction**: Up or down based on target note

---

### **Arpeggio**
**Definition**: Rapid note sequence patterns (broken chords).
**Table**: Arpeggio table with note offset sequences
**Common Pattern**: Major chord (0, +4, +7 semitones)

**Example**: C major arpeggio = C, E, G (repeat)

---

### **Tempo**
**Definition**: Playback speed.
**Units**: BPM (Beats Per Minute) or frame rate
**Typical Range**: 100-180 BPM
**Control**: Tempo table or init parameter

→ See also: **Break Speed**

---

## Tables & Data Structures

### **Instrument Table**
**Definition**: Timbre/sound definitions with ADSR parameters.
**Structure**: 6-8 bytes per entry
- Attack/Decay (1 byte)
- Sustain/Release (1 byte)
- Waveform (1 byte)
- Pulse pointer (2 bytes)
- Filter pointer (2 bytes)
- Flags (1 byte)

**Max Entries**: 32 (SF2 standard)

→ See also: **ADSR**, **Instrument**

---

### **Wave Table**
**Definition**: Waveform selection and note offset pairs.

**Laxity Format**:
- Structure: `(note_offset, waveform)` pairs
- Size: 2 bytes per entry
- Layout: Row-major interleaved

**SF2 Format**:
- Structure: Two separate arrays
- Size: 128 entries max
- Layout: Column-major (2 bytes/entry)

**Critical**: Byte order swap during conversion

→ See also: **Wave Table De-interleaving**, **Waveforms**

---

### **Pulse Table**
**Definition**: Pulse width modulation sequences.
**Structure**: 4 bytes per entry
- Pulse width value (2 bytes)
- Delay/timing (1 byte)
- Control byte (1 byte)

**Max Entries**: 64 (SF2 standard)
**Purpose**: Animate pulse waveform duty cycle over time

→ See also: **Pulse Width Modulation**

---

### **Filter Table**
**Laxity Format** (3-table system):
- Table 1: Cutoff values
- Table 2: Resonance values
- Table 3: Mode/routing
- **Plus**: First 4 bytes = Break speed data

**SF2 Format** (1-table system):
- Combined: Cutoff + Resonance + Mode (4 bytes/entry)
- Max Entries: 32

**Incompatibility**: 0% conversion accuracy (manual editing required)

→ See also: **Filter**, **Filter Accuracy**, **Break Speed**

---

### **Arpeggio Table**
**Definition**: Note offset sequences for arpeggio patterns.
**Structure**: Sequence of relative semitone offsets
**Max Length**: Varies by implementation

**Example**: [0, 4, 7, 0] = Major chord pattern

→ See also: **Arpeggio**

---

## Acronyms & Abbreviations

### **File Format Acronyms**
- **SF2** = SID Factory II format
- **SID** = Sound Interface Device / SID file
- **PSID** = Program SID format (v2)
- **RSID** = Real SID format

### **Audio/Hardware Acronyms**
- **C64** = Commodore 64 computer
- **6502** = CPU processor family
- **6510** = Enhanced 6502 variant (actual C64 CPU)
- **PAL** = Phase Alternating Line (European, 50 Hz)
- **NTSC** = National Television System Committee (US, 60 Hz)
- **ADSR** = Attack/Decay/Sustain/Release
- **HR** = Hard Restart (envelope workaround)
- **PWM** = Pulse Width Modulation
- **LFO** = Low-Frequency Oscillator

### **File Type Acronyms**
- **WAV** = Waveform audio file
- **MIDI** = Musical Instrument Digital Interface
- **CSV** = Comma-Separated Values
- **JSON** = JavaScript Object Notation

### **Tool Acronyms**
- **VICE** = Versatile Commodore Emulator
- **VSID** = VICE's SID player module
- **SID2WAV** = SID to WAV rendering tool
- **NP** / **NP20** / **NP21** = NewPlayer version

### **UI/Development Acronyms**
- **GUI** = Graphical User Interface
- **CLI** = Command-Line Interface
- **API** = Application Programming Interface
- **CI/CD** = Continuous Integration/Continuous Deployment

### **Project-Specific Acronyms**
- **SIDM2** = SID to SID Factory II (this project)
- **JCH** = Tracker format variant
- **ReSID** = SID chip emulation library

---

## Commands & Operations

### **Command** (SF2 Context)
**Definition**: Control byte in SF2 sequence affecting playback.
**Types**: 15 command types in Driver 11
- Note on/off
- Slide up/down
- Vibrato
- Portamento
- Arpeggio
- Volume change
- Transpose
- Gate control
- Filter control
- Pulse control

→ See also: **Super-Command**, **Sequence**

---

### **Conversion** / **Convert**
**Definition**: Process of transforming SID file to SF2 format.
**Tool**: `sid_to_sf2.py` or `sid-to-sf2.bat`
**Steps**:
1. Parse SID file (PSID header + data)
2. Detect player type (pattern database)
3. Select driver (auto or manual)
4. Extract tables (instruments, sequences, wave, pulse, filter)
5. Convert formats (Laxity → SF2)
6. Generate SF2 file

**Accuracy**: Depends on player type and driver selection

→ See also: **ACCURACY_MATRIX.md**

---

### **Roundtrip** / **Roundtrip Test**
**Definition**: SID → SF2 → SID conversion to test fidelity.
**Purpose**: Validate 100% accuracy for SF2-exported files
**Test**: `test-roundtrip.bat` or `test_roundtrip.py`

**Expected Result**:
- SF2-exported files: 100% perfect match
- Laxity files: 99.93% frame accuracy

→ See also: **Perfect Roundtrip**

---

### **Validation**
**Two Meanings**:

**1. Accuracy Validation**: Testing conversion quality
- Frame comparison
- Register accuracy checking
- Audio comparison
- Musical quality assessment

**2. Format Validation**: Verifying file format correctness
- PSID header validation
- SF2 structure validation
- Table integrity checking

**Tool**: `validate_sid_accuracy.py` (accuracy), `sf2_validator.py` (format)

---

### **Trace** / **Tracing**
**Definition**: Recording SID register writes frame-by-frame during playback.
**Tools**:
- **siddump**: C++ external tool (original)
- **SIDwinder**: Python tool (SIDM2 implementation)

**Output**: Frame-by-frame register write log
**Usage**: Accuracy validation, debugging, analysis

→ See also: **Frame Accuracy**, **SIDwinder**

---

### **Extraction**
**Two Types**:

**1. Static Extraction**: Scanning SID file memory for tables
- Pattern matching
- Pointer following
- Heuristic detection

**2. Runtime Extraction**: Analyzing siddump trace output
- Observing actual register writes
- Inferring table values from playback
- Gate inference from waveform changes

→ See also: **Table Extraction**, **siddump**

---

## Terms to Avoid (Deprecated)

### Deprecated Terminology

| Deprecated Term | Use Instead | Reason |
|-----------------|-------------|--------|
| *"NewPlayer_v21"* | **Laxity NewPlayer v21** | Ambiguous |
| *"NP21"* | **Laxity NewPlayer v21** | Unclear abbreviation |
| *"SidFactory_II/Laxity"* | **SF2-exported SID** | Confusing (implies Laxity driver) |
| *"Packed SID"* | **SF2-exported SID** | Ambiguous term |
| *"Frame match"* | **Frame accuracy** | Inconsistent with other accuracy terms |
| *"Register match"* | **Register accuracy** | Inconsistent |
| *"Table"* (alone) | **Specify table type** | Too generic |
| *"Player"* (alone) | **Player type** or **Driver** | Ambiguous |

---

## Cross-References

### Related Documentation
- **ACCURACY_MATRIX.md** - Complete accuracy data for all conversion paths
- **LAXITY_DRIVER_TECHNICAL_REFERENCE.md** - Deep technical details on Laxity driver
- **DRIVER_REFERENCE.md** - All SF2 driver specifications
- **SF2_FORMAT_SPEC.md** - Complete SF2 binary format
- **COMPONENTS_REFERENCE.md** - Python module API reference
- **ARCHITECTURE.md** - System architecture and data flow

---

## Maintenance & Updates

**How to Update This Glossary**:
1. When adding new terms, follow existing format (Definition, Key characteristics, cross-references)
2. When term usage changes, mark old term as deprecated
3. Update version number and "Last Updated" date
4. Verify all cross-references still valid

**Review Schedule**: Update with each minor version (v3.2, v3.3, etc.)

---

**Document Status**: ✅ Complete & Current
**Maintained By**: SIDM2 Development Team
**Last Verification**: 2026-01-02
**Next Review**: v3.2.0 release

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
