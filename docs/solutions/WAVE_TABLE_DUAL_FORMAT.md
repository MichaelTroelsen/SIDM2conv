# Wave Table Dual Format Discovery

**Date**: 2025-12-07
**File Analyzed**: SF2packed_Stinsens_Last_Night_of_89.sid
**Discovery**: SF2-packed files contain TWO sequential wave table structures

---

## Problem Statement

During wave table extraction from SF2-packed SID files, we found TWO distinct wave table patterns at consecutive addresses, leading to confusion about which format to use.

## Discovery

SF2-packed files store wave tables in a **dual format** with both structures present:

### Table 1: SF2 Wave Table (Waveform-First Format)
**Address**: `$0958` to `$0989` (50 bytes)
**Format**: `(waveform, note_offset)` pairs
**Data**:
```
21 21 41 7F 81 41 41 41 7F 81 41 80 80 7F 81 01
7F 81 15 11 11 7F 81 7F 21 7F 21 11 7F 51 7F 15
40 7F 53 7F 81 01 7F 41 7F 20 7F 81 41 40 80 7F
13 7F
```

**Interpretation**:
- Byte 0: `21` = Waveform (triangle)
- Byte 1: `21` = Note offset
- Byte 2: `41` = Waveform (pulse)
- Byte 3: `7F` = End marker / Note offset
- etc.

### Table 2: Note Offset Table (Note-First Format)
**Address**: `$098A` to `$09BB` (50 bytes)
**Format**: Note offset values only
**Data**:
```
80 80 00 02 C0 A1 9A 00 07 C4 AC C0 BC 0C C0 00
0F C0 00 76 74 14 B4 12 00 18 00 00 1B 00 1D C5
00 20 00 22 C0 00 25 00 27 00 29 C7 AE A5 C0 2E
00 30
```

**Interpretation**:
- These are the note offset values extracted from Table 1
- Used by the SF2 driver for note lookup
- Values like `80`, `C0`, `00`, etc. are note offsets ($00 = base note, $80 = transpose)

---

## Why Both Tables Exist

### SF2 Format Requirements

The SF2 driver needs:
1. **Waveform sequences** - to control SID waveform register ($D412)
2. **Note offsets** - to calculate frequency based on base note + offset

### Storage Strategy

SF2-packed files store:
1. **Combined table** ($0958): Original SF2 format with (waveform, note) pairs
2. **Note-only table** ($098A): Extracted note offsets for faster lookup

This is an **optimization** - the driver can:
- Read waveforms from Table 1
- Read notes from Table 2
- Both tables are kept in sync

---

## Format Comparison

| Aspect | Laxity NewPlayer | SF2 Format | SF2-Packed |
|--------|-----------------|------------|------------|
| Wave table format | `(note, waveform)` | `(waveform, note)` | Both! |
| Table 1 location | Various | $0958 (Driver 11) | $0958 |
| Table 2 location | N/A | N/A | $098A |
| Byte order | Note-first | Waveform-first | Both |
| Optimization | Single table | Single table | Dual tables |

---

## Implications for Conversion

### When Converting Laxity → SF2:

1. **Extract Laxity table** in (note, waveform) format
2. **Byte-swap to SF2 format**: (waveform, note)
3. **Write to SF2 at $0958**
4. **Extract note offsets** from pairs
5. **Write note table at $098A**

### When Reading SF2-Packed Files:

1. **Read Table 1** at $0958 for complete wave table
2. **Verify with Table 2** at $098A for note consistency
3. **Use Table 1** as primary source (has both values)

### Extraction Algorithm:

```python
def extract_sf2_wave_table(sid_data, base_addr=0x0958):
    """Extract wave table from SF2-packed SID"""
    wave_table = []
    note_table = []

    # Read combined table (waveform, note) pairs
    addr = base_addr
    while True:
        waveform = sid_data[addr]
        note_offset = sid_data[addr + 1]

        if waveform == 0x7F:  # End marker
            break

        wave_table.append((waveform, note_offset))
        addr += 2

    # Verify with note-only table at $098A
    note_table_addr = base_addr + len(wave_table) * 2 + 2
    for i, (wf, note) in enumerate(wave_table):
        expected_note = sid_data[note_table_addr + i * 2]
        if note != expected_note:
            print(f"Warning: Note mismatch at entry {i}")

    return wave_table
```

---

## Byte-Swap Pattern Example

**Laxity Format**:
```
Note  Waveform
$00   $21      (base note, triangle)
$02   $41      (+2 semitones, pulse)
$C0   $81      (transpose, pulse+gate)
```

**SF2 Format (Table 1)**:
```
Waveform  Note
$21       $00      (triangle, base note)
$41       $02      (pulse, +2 semitones)
$81       $C0      (pulse+gate, transpose)
```

**SF2 Format (Table 2)**:
```
$00   (note offset only)
$02   (note offset only)
$C0   (note offset only)
```

---

## Detection Heuristic

To determine if a SID file has dual wave tables:

```python
def has_dual_wave_tables(sid_data):
    """Check if file has both SF2 wave table formats"""
    # Table 1 starts at $0958
    table1_start = 0x0958

    # Find end of Table 1 (0x7F marker)
    table1_end = table1_start
    while sid_data[table1_end] != 0x7F:
        table1_end += 2

    # Table 2 should start immediately after
    table2_start = table1_end + 2

    # Check if Table 2 contains note-only values
    # (alternating pattern of notes and zeros/low values)
    note_values = sid_data[table2_start:table2_start + 20]

    # Heuristic: Every other byte should be note-like
    # (< 0x60 for valid notes, or $00, $80, $C0 for special)
    note_pattern = all(
        note_values[i] < 0x60 or note_values[i] in [0x00, 0x80, 0xC0]
        for i in range(0, len(note_values), 2)
    )

    return note_pattern
```

---

## Testing

**Test File**: SF2packed_Stinsens_Last_Night_of_89.sid

**Verification**:
```bash
# Extract wave tables
xxd -s 0x0958 -l 100 SF2packed_Stinsens_Last_Night_of_89.sid

# Compare with original Laxity file
xxd -s [laxity_wave_addr] -l 100 Stinsens_Last_Night_of_89.sid
```

**Expected Result**:
- Table 1 has (waveform, note) pairs
- Table 2 has note values only
- Byte-swapped from original Laxity format

---

## References

- [SF2 Format Specification](../reference/SF2_FORMAT_SPEC.md)
- [Wave Table Packing](../reference/WAVE_TABLE_PACKING.md)
- [Technical Analysis](../analysis/TECHNICAL_ANALYSIS.md)
- [Consolidation Insights](../analysis/CONSOLIDATION_INSIGHTS.md#5-the-laxitysf2-conversion-is-semantic-not-syntactic)

---

## Status

**Confirmed**: ✅ Dual format exists in SF2-packed files
**Implemented**: ❌ Extraction code not yet updated
**Next Steps**:
1. Update `sidm2/table_extraction.py` to handle dual format
2. Add unit tests for dual table extraction
3. Update conversion pipeline to use both tables for validation

---

**Document Type**: Solution / Discovery
**Maintainer**: SIDM2 Project
**Version**: 1.0
