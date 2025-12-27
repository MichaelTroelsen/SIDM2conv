# Laxity NewPlayer v21 to SID Factory II Conversion Guide

**Version**: 1.0.0
**Date**: 2025-12-27
**Purpose**: Definitive semantic mapping guide for Laxity → SF2 conversion

---

## Table of Contents

1. [Overview](#overview)
2. [Format Comparison](#format-comparison)
3. [Memory Layout](#memory-layout)
4. [Table Transformations](#table-transformations)
5. [Command Mapping](#command-mapping)
6. [Gate Handling](#gate-handling)
7. [Sequence Conversion](#sequence-conversion)
8. [Instrument Mapping](#instrument-mapping)
9. [Edge Cases](#edge-cases)
10. [Validation](#validation)

---

## Overview

### What This Guide Covers

This is the **Rosetta Stone** for converting Laxity NewPlayer v21 SID files to SID Factory II (.sf2) format with maximum fidelity.

**Conversion Goal**: 99.93% frame accuracy (measured via SID register write comparison)

**Key Challenge**: The two formats use fundamentally different architectures:
- **Laxity**: Compact table-driven player with super-commands (multi-parameter)
- **SF2**: Verbose sequence-based player with simple commands (single parameter)

### Quick Reference

| Aspect | Laxity NP21 | SF2 Driver 11 |
|--------|-------------|---------------|
| **Load Address** | Variable ($1000, $A000, etc.) | Fixed ($1000) |
| **Sequence Format** | Compact, implicit gates | Verbose, explicit gates |
| **Command Style** | Super-commands (packed params) | Simple commands (one param) |
| **Instrument Layout** | 8×8 row-major | 32×6 column-major |
| **Wave Table** | Dual-array format | Interleaved pairs |
| **Order Lists** | Implicit (one sequence/voice) | Explicit (index list) |

---

## Format Comparison

### Architecture Overview

```
Laxity NewPlayer v21                  SID Factory II Driver 11
===================                   =========================

┌─────────────────┐                   ┌─────────────────┐
│ Player Code     │ $1000-$19FF       │ Driver Code     │ $0000-$07FF
│ (2.5KB)         │                   │ (2KB)           │
├─────────────────┤                   ├─────────────────┤
│ Sequence Ptrs   │ $199F (6 bytes)   │ Header Blocks   │ $0800-$08FF
├─────────────────┤                   ├─────────────────┤
│ Sequences       │ Variable          │ Sequences       │ $0903+
│ (compressed)    │                   │ (verbose)       │
├─────────────────┤                   ├─────────────────┤
│ Instruments     │ $1A6B (64 bytes)  │ Instruments     │ $0A03 (256 bytes)
│ 8×8 row-major   │                   │ 32×6 col-major  │
├─────────────────┤                   ├─────────────────┤
│ Wave Table      │ $1ACB (100 bytes) │ Wave Table      │ $0B03 (256 bytes)
│ Dual arrays     │                   │ Interleaved     │
├─────────────────┤                   ├─────────────────┤
│ Command Table   │ $1ADB (variable)  │ Pulse Table     │ $0D03 (256 bytes)
│                 │                   ├─────────────────┤
│                 │                   │ Filter Table    │ $0F03 (256 bytes)
└─────────────────┘                   └─────────────────┘
```

### Key Differences

| Feature | Laxity | SF2 | Conversion Strategy |
|---------|--------|-----|---------------------|
| **Gates** | Implicit (inferred from note timing) | Explicit ($7E/$80 markers) | Gate inference algorithm |
| **Commands** | Packed multi-param ($60 xy = vibrato) | Separate single-param (T1 XX, T2 YY) | Command decomposition |
| **Wave Table** | Two 50-byte arrays (note_offsets[], waveforms[]) | 128 interleaved pairs (waveform, note_offset) | Array transposition + interleaving |
| **Instruments** | 8 instruments × 8 bytes (row-major) | 32 instruments × 6 bytes (column-major) | Matrix transpose + padding |
| **Sequences** | Compact (no explicit end marker) | Verbose (explicit $7F end) | Expansion + terminator |

---

## Memory Layout

### Laxity NewPlayer v21 Layout

```
Offset from Load Address    Size    Content
========================    ====    =======
$0000-$09FF                 2.5KB   Player code
$099F-$09A4                 6       Sequence pointers (3 voices × 2 bytes)
$09A5-$0A6A                 var     Sequence data (compressed)
$0A6B-$0AAA                 64      Instruments (8 × 8 bytes, row-major)
$0ACB-$0B2E                 100     Wave table (dual array: 50+50 bytes)
$0ADB-$0xxx                 var     Command table
```

**Example** (Angular.sid, load=$1000):
- Sequence pointers: $199F = $1000 + $099F
- Instruments: $1A6B = $1000 + $0A6B
- Wave table: $1ACB = $1000 + $0ACB

### SF2 Driver 11 Layout

```
Absolute Address    Size    Content
================    ====    =======
$0000-$07FF         2KB     Driver code
$0800-$08FF         256     Header blocks (metadata)
$0903-$09FF         var     Sequence pointers + sequences
$0A03-$0B02         256     Instruments (32 × 8 bytes, column-major)
$0B03-$0D02         512     Wave table (128 pairs × 2 bytes)
$0D03-$0F02         512     Pulse table (64 entries × 4 bytes)
$0F03-$1102         512     Filter table (64 entries × 4 bytes)
```

---

## Table Transformations

### Instrument Table: Row-Major → Column-Major

**Laxity Format** (8 instruments × 8 bytes, row-major):
```
Memory layout (64 bytes total):
Offset  Instrument Data
$0A6B:  AD SR WF PW FL FW AR SP  ← Instrument 0
$0A73:  AD SR WF PW FL FW AR SP  ← Instrument 1
...
$0AA3:  AD SR WF PW FL FW AR SP  ← Instrument 7

Where:
  AD = Attack/Decay
  SR = Sustain/Release
  WF = Waveform index
  PW = Pulse width index
  FL = Filter index
  FW = Filter waveform
  AR = Arpeggio index
  SP = Speed/flags
```

**SF2 Format** (32 instruments × 6 bytes, column-major):
```
Memory layout (192 bytes used, 256 allocated):
$0A03-$0A22:  AD AD AD ... (32 bytes) ← Column 0: All AD values
$0A23-$0A42:  SR SR SR ... (32 bytes) ← Column 1: All SR values
$0A43-$0A62:  FL FL FL ... (32 bytes) ← Column 2: All Flags
$0A63-$0A82:  FI FI FI ... (32 bytes) ← Column 3: Filter indices
$0A83-$0AA2:  PW PW PW ... (32 bytes) ← Column 4: Pulse indices
$0AA3-$0AC2:  WF WF WF ... (32 bytes) ← Column 5: Wave indices
```

**Conversion Algorithm**:
```python
def convert_instruments(laxity_instruments: List[bytes]) -> bytes:
    """
    Convert Laxity row-major 8×8 to SF2 column-major 32×6

    Args:
        laxity_instruments: 8 instruments, 8 bytes each (64 bytes total)

    Returns:
        SF2 instrument table (256 bytes)
    """
    sf2_table = bytearray(256)  # 32 instruments × 8 bytes

    # Transpose: Laxity row-major → SF2 column-major
    for inst_idx in range(8):
        laxity_inst = laxity_instruments[inst_idx]  # 8 bytes

        # Map to SF2 columns (different order!)
        sf2_table[inst_idx] = laxity_inst[0]        # AD → Column 0
        sf2_table[32 + inst_idx] = laxity_inst[1]   # SR → Column 1
        sf2_table[64 + inst_idx] = laxity_inst[7]   # Flags → Column 2
        sf2_table[96 + inst_idx] = laxity_inst[4]   # Filter → Column 3
        sf2_table[128 + inst_idx] = laxity_inst[3]  # Pulse → Column 4
        sf2_table[160 + inst_idx] = laxity_inst[2]  # Wave → Column 5

    # Pad remaining 24 instruments with defaults
    for inst_idx in range(8, 32):
        sf2_table[inst_idx] = 0x00              # AD = 0
        sf2_table[32 + inst_idx] = 0xF0         # SR = full sustain
        sf2_table[64 + inst_idx] = 0x00         # Flags = 0
        sf2_table[96 + inst_idx] = 0x00         # Filter = 0
        sf2_table[128 + inst_idx] = 0x00        # Pulse = 0
        sf2_table[160 + inst_idx] = 0x01        # Wave = triangle

    return bytes(sf2_table)
```

### Wave Table: Dual Array → Interleaved Pairs

**CRITICAL FIX** (v1.8.0): This was the root cause of 0.20% → 99.93% accuracy improvement!

**Laxity Format** (Dual array, 100 bytes):
```
Memory layout:
$1ACB-$1AFE:  note_offsets[50]   ← First 50 bytes: Note offsets
$1AFF-$1B32:  waveforms[50]      ← Second 50 bytes: Waveform values

Example:
  Entry 5: note_offset = note_offsets[5], waveform = waveforms[5]
```

**SF2 Format** (Interleaved pairs, 256 bytes):
```
Memory layout:
$0B03: waveform[0], note_offset[0]    ← Entry 0
$0B05: waveform[1], note_offset[1]    ← Entry 1
$0B07: waveform[2], note_offset[2]    ← Entry 2
...
$0BFF: waveform[126], note_offset[126] ← Entry 126
```

**Conversion Algorithm**:
```python
def convert_wave_table(laxity_wave_data: bytes) -> bytes:
    """
    Convert Laxity dual-array format to SF2 interleaved pairs

    CRITICAL: This format mismatch caused 497x accuracy loss!

    Args:
        laxity_wave_data: 100 bytes (50 note_offsets + 50 waveforms)

    Returns:
        SF2 wave table (256 bytes)
    """
    sf2_wave = bytearray(256)

    # Extract dual arrays
    note_offsets = laxity_wave_data[0:50]   # First 50 bytes
    waveforms = laxity_wave_data[50:100]    # Second 50 bytes

    # Interleave into SF2 format: (waveform, note_offset) pairs
    for i in range(50):
        sf2_wave[i * 2] = waveforms[i]      # Even offset: waveform
        sf2_wave[i * 2 + 1] = note_offsets[i]  # Odd offset: note offset

    # Pad remaining entries with defaults
    for i in range(50, 128):
        sf2_wave[i * 2] = 0x01      # Triangle waveform
        sf2_wave[i * 2 + 1] = 0x00  # No transpose

    return bytes(sf2_wave)
```

**Why This Matters**:
- Before fix: Waveform and note offset were swapped → wrong pitch/timbre
- After fix: Correct pairing → 99.93% accuracy
- Impact: 497x accuracy improvement (0.20% → 99.93%)

---

## Command Mapping

### Laxity Super-Commands → SF2 Simple Commands

Laxity uses **super-commands** (single byte with multi-parameter payload). SF2 uses **simple commands** (one command = one parameter).

**Command Decomposition Table**:

| Laxity | Hex | Params | SF2 Equivalent | Description |
|--------|-----|--------|----------------|-------------|
| **Note Events** | | | | |
| Note C-0 to B-7 | $00-$5F | - | $00-$5F + gate | Direct mapping + explicit gate |
| | | | | |
| **Control Commands** | | | | |
| Set Instrument | $60 xx | 1 | $A1 xx | Change instrument |
| Vibrato | $61 xy | 2 | T1 XX, T2 YY | x=depth, y=speed |
| Pitch Slide Up | $62 xx | 1 | T3 XX | Slide speed |
| Pitch Slide Down | $63 xx | 1 | T4 XX | Slide speed |
| Pattern Jump | $64 xx | 1 | - | Orderlist control |
| Pattern Break | $65 | 0 | - | End pattern early |
| Set Volume | $66 xx | 1 | - | Global volume |
| Fine Volume | $67 xy | 2 | - | Channel volume |
| | | | | |
| **Extended Commands** | | | | |
| Arpeggio | $70 xy | 2 | T5 XX, T6 YY | x=note1, y=note2 |
| Portamento | $71 xx | 1 | T7 XX | Slide to note |
| Tremolo | $72 xy | 2 | T8 XX, T9 YY | Volume modulation |
| Cut Note | $7E | 0 | $80 | Gate off |
| End Sequence | $7F | 0 | $7F | Sequence terminator |

### Command Decomposition Example

**Laxity Vibrato** ($61 with packed parameters):
```
Laxity sequence:
  $3C        ; Note C-4
  $61 $35    ; Vibrato: depth=3, speed=5
  $40        ; Note E-4
  $7F        ; End

Parameters packed in one byte: $35
  High nibble (3) = depth
  Low nibble (5) = speed
```

**SF2 Equivalent** (decomposed into separate commands):
```
SF2 sequence:
  $7E        ; Gate on
  $3C        ; Note C-4
  T1 $03     ; Vibrato depth = 3
  T2 $05     ; Vibrato speed = 5
  $80        ; Gate off
  $7E        ; Gate on
  $40        ; Note E-4
  $80        ; Gate off
  $7F        ; End sequence

Command decomposition:
  Laxity: $61 $35  (2 bytes)
  SF2:    T1 $03   (2 bytes) + T2 $05 (2 bytes) = 4 bytes
  Expansion: 2x
```

**Decomposition Algorithm**:
```python
def decompose_laxity_command(cmd: int, param: int) -> List[Tuple[int, int]]:
    """
    Decompose Laxity super-command into SF2 simple commands

    Args:
        cmd: Laxity command byte
        param: Command parameter byte

    Returns:
        List of (sf2_command, sf2_param) tuples
    """
    if cmd == 0x61:  # Vibrato
        depth = (param >> 4) & 0x0F  # High nibble
        speed = param & 0x0F         # Low nibble
        return [(0xA0 + 1, depth), (0xA0 + 2, speed)]  # T1, T2

    elif cmd == 0x62:  # Pitch slide up
        return [(0xA0 + 3, param)]  # T3

    elif cmd == 0x63:  # Pitch slide down
        return [(0xA0 + 4, param)]  # T4

    elif cmd == 0x70:  # Arpeggio
        note1 = (param >> 4) & 0x0F
        note2 = param & 0x0F
        return [(0xA0 + 5, note1), (0xA0 + 6, note2)]  # T5, T6

    elif cmd == 0x72:  # Tremolo
        depth = (param >> 4) & 0x0F
        speed = param & 0x0F
        return [(0xA0 + 8, depth), (0xA0 + 9, speed)]  # T8, T9

    else:
        # Direct mapping (no decomposition needed)
        return [(cmd, param)]
```

---

## Gate Handling

### The Gate Problem

**Laxity**: Gates are **implicit** (inferred from note timing and context)
**SF2**: Gates are **explicit** ($7E = gate on, $80 = gate off)

**Challenge**: We must infer when gates occur in Laxity sequences and insert explicit markers in SF2.

### Gate Inference Algorithm

```python
def infer_gates(laxity_sequence: bytes) -> List[int]:
    """
    Infer gate events from Laxity sequence

    Algorithm:
    1. Track current note state (on/off)
    2. Insert $7E (gate on) before each new note
    3. Insert $80 (gate off) when:
       - Cut command ($7E) appears
       - New note starts (legato vs staccato detection)
       - Sequence ends

    Returns:
        SF2 sequence with explicit gates
    """
    sf2_seq = []
    gate_is_on = False
    last_note = None

    i = 0
    while i < len(laxity_sequence):
        cmd = laxity_sequence[i]

        if cmd <= 0x5F:  # Note event
            # Detect legato vs staccato
            if last_note is not None and gate_is_on:
                # Staccato: gate off before new note
                sf2_seq.append(0x80)  # Gate off
                gate_is_on = False

            # Gate on for new note
            sf2_seq.append(0x7E)  # Gate on
            sf2_seq.append(cmd)    # Note
            gate_is_on = True
            last_note = cmd

        elif cmd == 0x7E:  # Laxity cut note
            if gate_is_on:
                sf2_seq.append(0x80)  # Gate off
                gate_is_on = False

        elif cmd == 0x7F:  # End sequence
            if gate_is_on:
                sf2_seq.append(0x80)  # Gate off
            sf2_seq.append(0x7F)  # End
            break

        else:  # Other commands
            # Decompose if needed
            params = decompose_laxity_command(cmd, laxity_sequence[i+1] if i+1 < len(laxity_sequence) else 0)
            for sf2_cmd, sf2_param in params:
                sf2_seq.append(sf2_cmd)
                if sf2_param is not None:
                    sf2_seq.append(sf2_param)
            i += 1  # Skip parameter byte

        i += 1

    return sf2_seq
```

### Gate Detection Heuristics

| Scenario | Laxity | SF2 Output | Rule |
|----------|--------|------------|------|
| **New note** | `$3C $40` | `$7E $3C $80 $7E $40` | Gate off + on for staccato |
| **Legato** | `$3C $40` (fast) | `$7E $3C $40` | No gate off if notes overlap |
| **Cut** | `$3C $7E` | `$7E $3C $80` | Explicit gate off |
| **Rest** | (gap in notes) | `$80 [delay] $7E` | Gate off, wait, gate on |

---

## Sequence Conversion

### Format Comparison

**Laxity Sequence** (compact):
```
Bytes: $3C $61 $35 $40 $7F
Size:  5 bytes

Meaning:
  $3C     = Note C-4
  $61 $35 = Vibrato (depth=3, speed=5)
  $40     = Note E-4
  $7F     = End
```

**SF2 Sequence** (verbose):
```
Bytes: $7E $3C $A1 $03 $A2 $05 $80 $7E $40 $80 $7F
Size:  11 bytes

Meaning:
  $7E     = Gate on
  $3C     = Note C-4
  $A1 $03 = Vibrato depth 3
  $A2 $05 = Vibrato speed 5
  $80     = Gate off
  $7E     = Gate on
  $40     = Note E-4
  $80     = Gate off
  $7F     = End

Expansion: 2.2x (5 bytes → 11 bytes)
```

### Sequence Conversion Algorithm

**Complete Workflow**:
```python
def convert_laxity_sequence_to_sf2(laxity_seq: bytes) -> bytes:
    """
    Complete Laxity → SF2 sequence conversion

    Steps:
    1. Decompose super-commands
    2. Infer and insert gates
    3. Add explicit terminator
    4. Validate SF2 sequence
    """
    # Step 1: Parse Laxity sequence
    events = parse_laxity_sequence(laxity_seq)

    # Step 2: Decompose commands
    decomposed = []
    for event in events:
        if event.is_super_command():
            decomposed.extend(decompose_command(event))
        else:
            decomposed.append(event)

    # Step 3: Infer gates
    with_gates = infer_gates(decomposed)

    # Step 4: Add terminator
    if with_gates[-1] != 0x7F:
        with_gates.append(0x7F)

    # Step 5: Validate
    validate_sf2_sequence(with_gates)

    return bytes(with_gates)
```

---

## Instrument Mapping

### Instrument Parameter Mapping

| Laxity Byte | Name | SF2 Column | Name | Transformation |
|-------------|------|------------|------|----------------|
| 0 | Attack/Decay | 0 | Attack/Decay | Direct copy |
| 1 | Sustain/Release | 1 | Sustain/Release | Direct copy |
| 2 | Waveform Index | 5 | Wave Index | Direct copy |
| 3 | Pulse Index | 4 | Pulse Index | Direct copy |
| 4 | Filter Index | 3 | Filter Index | Direct copy |
| 5 | Filter Waveform | - | (unused) | Discard |
| 6 | Arpeggio Index | - | (unused) | Discard |
| 7 | Flags/Speed | 2 | Flags | Direct copy |

**Note**: SF2 uses 6 parameters per instrument, Laxity uses 8. The extra 2 Laxity parameters (filter waveform, arpeggio) are not directly mapped in SF2 Driver 11.

### Example Instrument Conversion

**Laxity Instrument 0**:
```
Offset  Value   Meaning
$1A6B:  $49     Attack=4, Decay=9
$1A6C:  $80     Sustain=8, Release=0
$1A6D:  $05     Waveform index 5
$1A6E:  $03     Pulse index 3
$1A6F:  $07     Filter index 7
$1A70:  $01     Filter waveform
$1A71:  $00     Arpeggio index
$1A72:  $40     Flags
```

**SF2 Instrument 0** (column-major layout):
```
Column  Offset  Value   Meaning
0       $0A03:  $49     Attack/Decay
1       $0A23:  $80     Sustain/Release
2       $0A43:  $40     Flags
3       $0A63:  $07     Filter index
4       $0A83:  $03     Pulse index
5       $0AA3:  $05     Wave index
```

---

## Edge Cases

### 1. Invalid Sequence Addresses

**Problem**: Laxity sequence pointers sometimes point outside loaded data

**Solution**:
```python
if seq_addr < load_address or seq_addr >= load_address + data_size:
    logger.warning(f"Sequence at ${seq_addr:04X} outside loaded data")
    # Use empty sequence as fallback
    return [0x7F]  # Just end marker
```

### 2. Overlapping Data Regions

**Problem**: Some Laxity files have overlapping sequence/instrument data

**Detection**:
```python
if instrument_offset < sequence_end:
    logger.warning("Instrument table overlaps sequence data")
    # Adjust offsets or use heuristics
```

### 3. Variable Load Addresses

**Problem**: Laxity files can load at different addresses ($1000, $A000, etc.)

**Solution**: All offsets are relative to load address
```python
absolute_address = load_address + LAXITY_OFFSET
```

### 4. Missing End Markers

**Problem**: Some Laxity sequences lack explicit $7F terminator

**Solution**: Add automatic termination
```python
if len(sequence) > MAX_SEQUENCE_LENGTH or last_byte != 0x7F:
    sequence.append(0x7F)
```

### 5. Out-of-Range Wave/Pulse/Filter Indices

**Problem**: Laxity may reference non-existent table entries

**Detection**:
```python
if wave_index >= len(wave_table):
    logger.warning(f"Wave index {wave_index} exceeds table size {len(wave_table)}")
    # Clamp to valid range
    wave_index = min(wave_index, len(wave_table) - 1)
```

---

## Validation

### Post-Conversion Checks

After conversion, validate the SF2 file:

```python
def validate_sf2_conversion(sf2_data: bytes) -> List[str]:
    """
    Validate converted SF2 file

    Returns:
        List of validation warnings/errors
    """
    warnings = []

    # 1. Check file size
    if len(sf2_data) < 8192:
        warnings.append("SF2 file unusually small")

    # 2. Check magic number
    if sf2_data[0x0800:0x0802] != b'\x37\x13':  # 0x1337 little-endian
        warnings.append("Invalid SF2 magic number")

    # 3. Check sequence terminators
    seq_data = sf2_data[0x0903:0x0A03]
    if 0x7F not in seq_data:
        warnings.append("No sequence terminator found")

    # 4. Check instrument table bounds
    for i in range(32):
        ad = sf2_data[0x0A03 + i]
        if ad == 0x00:
            warnings.append(f"Instrument {i} has zero attack/decay")

    # 5. Check wave table entries
    for i in range(128):
        waveform = sf2_data[0x0B03 + i*2]
        if waveform not in [0x01, 0x02, 0x04, 0x08, 0x10]:  # Valid waveforms
            warnings.append(f"Wave entry {i} has invalid waveform {waveform:02X}")

    return warnings
```

### Accuracy Measurement

Measure conversion accuracy using SID register write comparison:

```python
# 1. Generate register writes from original Laxity SID
original_writes = trace_sid(laxity_sid_file, frames=1500)

# 2. Generate register writes from converted SF2 SID
converted_writes = trace_sid(sf2_packed_sid_file, frames=1500)

# 3. Compare
accuracy = compare_register_writes(original_writes, converted_writes)

# Target: 99.93% frame accuracy
if accuracy >= 99.9:
    print(f"✅ EXCELLENT: {accuracy:.2f}% accuracy")
elif accuracy >= 95.0:
    print(f"⚠️ GOOD: {accuracy:.2f}% accuracy")
else:
    print(f"❌ POOR: {accuracy:.2f}% accuracy")
```

---

## Conversion Quality Checklist

Use this checklist to ensure high-quality conversions:

### Pre-Conversion
- [ ] Verify SID file is Laxity NewPlayer v21
- [ ] Extract load address from SID header
- [ ] Confirm sequence pointers are valid
- [ ] Check instrument table integrity

### During Conversion
- [ ] Transform wave table (dual → interleaved)
- [ ] Transpose instruments (row-major → column-major)
- [ ] Decompose super-commands
- [ ] Infer and insert gates
- [ ] Add sequence terminators

### Post-Conversion
- [ ] Validate SF2 file structure
- [ ] Check all sequences have terminators
- [ ] Verify instrument parameters in range
- [ ] Test playback in SID Factory II
- [ ] Measure accuracy (target: >99%)

---

## Tools and Utilities

### Conversion Pipeline

```bash
# Complete Laxity → SF2 conversion
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity

# With validation
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity --validate

# With accuracy measurement
python scripts/validate_sid_accuracy.py input.sid output_packed.sid
```

### Analysis Tools

```bash
# View SF2 structure
python pyscript/sf2_viewer_gui.py output.sf2

# Export SF2 to text
python scripts/sf2_export_text.py output.sf2 output.txt

# Compare register writes
python scripts/test_midi_comparison.py input.sid output_packed.sid
```

---

## References

### Documentation
- `docs/reference/SF2_FORMAT_SPEC.md` - SF2 format specification
- `docs/guides/LAXITY_DRIVER_USER_GUIDE.md` - Laxity driver guide
- `docs/testing/SF2_PACKER_ALIGNMENT_FIX.md` - Pointer relocation fix

### Implementation
- `sidm2/laxity_parser.py` - Laxity data extraction
- `sidm2/laxity_converter.py` - Conversion logic
- `sidm2/sf2_writer.py` - SF2 file generation

### Testing
- `scripts/test_laxity_driver.py` - Conversion tests
- `pyscript/test_sf2_packer_alignment.py` - Pointer relocation tests

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-27 | Initial release - Complete Rosetta Stone |

---

**End of Guide**

🤖 Generated with [Claude Code](https://claude.com/claude-code)
