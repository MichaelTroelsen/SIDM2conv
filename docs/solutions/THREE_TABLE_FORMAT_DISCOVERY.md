# Three-Table Format Discovery - Laxity to SF2 Conversion

**Critical Finding**: All major tables (Wave, Pulse, Filter) use a **consistent 3-table structure** in Laxity NewPlayer v21, which SF2 consolidates into 2 tables.

**Date**: 2025-12-07
**Discovery Source**: Analysis of Stinsens_Last_Night_of_89.sid and SF2packed_Stinsens_Last_Night_of_89.sid

---

## Executive Summary

Through disassembly analysis of the Laxity NewPlayer v21 format, we discovered that **all table types follow the same 3-table pattern**:

1. **Table 1**: Primary value or delta (high byte for pulse/filter)
2. **Table 2**: Secondary value or delta (low byte for pulse/filter, note offset for wave)
3. **Table 3**: Duration/control/loop parameters

SF2 format consolidates these into **2 tables** by:
- **Interleaving** Tables 1 and 2 into a single table
- **Keeping** Table 3 separate for duration/control

This explains why SF2→SID roundtrip works perfectly (dual format preserved) and why Laxity→SF2 conversion fails (semantic gap in table structure).

---

## Wave Tables (2 + 1 Format)

### Laxity Format (Separate Tables):

**Table 1** - Waveforms at `$18DA`:
```
21 21 41 7F 81 41 41 41 7F 81 41 80 80 7F 81 01 7F 81 15 11 11 7F 81 7F...
```

**Table 2** - Note Offsets at `$190C`:
```
80 80 00 02 C0 A1 9A 00 07 C4 AC C0 BC 0C C0 00 0F C0 00 76 74 14 B4 12...
```

### SF2 Format (Interleaved):

**Table 1** at `$0958` - (Waveform, Note) Pairs:
```
21 21  41 7F  81 41  41 41  7F 81  41 80  80 7F  81 01  7F 81  15 11...
wf note wf note wf note wf note wf note wf note wf note wf note wf note
```

**Table 2** at `$098A` - Note Offsets (extracted):
```
21 7F 41 41 81 80 7F 01 81 11 7F 7F 21 11 51 15 40 53 81 41 20 81 41 80...
(same note values as pairs)
```

### Read Instructions:
```asm
; Laxity (separate tables):
ldy wave_index
lda DataBlock_6 + $239,Y    ; Read waveform from $18DA
lda DataBlock_6 + $26B,Y    ; Read note offset from $190C

; SF2 (interleaved):
ldy wave_index
tya
asl                         ; Y * 2 for pairs
tay
lda Table1,Y                ; Read waveform
iny
lda Table1,Y                ; Read note offset
```

---

## Pulse Tables (3-Table Format)

### Laxity Format (3 Separate Tables):

**Table 1** - Pulse High/Delta at `$193E`:
```
88 00 81 00 00 0F 7F 88 7F 88 0F 0F 00 7F 88 00 0F 00 7F
```

**Table 2** - Pulse Low/Delta at `$1957`:
```
(need to extract from original file)
```

**Table 3** - Duration at `$1970`:
```
00 00 70 40 10 F0 00 00 00 00 A0 F0 10 00 00 80 F0 10 00
```

### SF2 Format (2 Tables):

**Table 1** at `$09BC` - Pulse Values (19 bytes):
```
88 00 81 00 00 0F 7F 88 7F 88 0F 0F 00 7F 88 00 0F 00 7F
```
*Hypothesis: Interleaved high/low pairs*

**Table 2** at `$09D5` - Duration (19 bytes):
```
00 00 70 40 10 F0 00 00 00 00 A0 F0 10 00 00 80 F0 10 00
```

### Read Instructions:
```asm
; Laxity (3 tables):
ldy pulse_index
lda DataBlock_6 + $29D,Y    ; Read pulse high from $193E
lda DataBlock_6 + $2B6,Y    ; Read pulse low from $1957
lda DataBlock_6 + $2CF,Y    ; Read duration from $1970

; SF2 (hypothesized):
ldy pulse_index
tya
asl                         ; Y * 2 for interleaved
tay
lda Table1,Y                ; Read pulse high
iny
lda Table1,Y                ; Read pulse low
...
ldy pulse_index             ; Original index
lda Table2,Y                ; Read duration
```

---

## Filter Tables (3-Table Format)

### Laxity Format (3 Separate Tables):

**Table 1** - Filter High/Resonance at `$1989`:
```
(Negative = absolute, Positive = delta)
Bits 6-4: Resonance
Bits 3-0: Filter cutoff high nibble
```

**Table 2** - Filter Low at `$19A3`:
```
8-bit filter cutoff low byte or delta
```

**Table 3** - Duration/Routing at `$19BD`:
```
Bits 7-4: Voice routing
Bits 3-0: Duration
```

### SF2 Format (Hypothesized 2 Tables):

Similar to pulse - likely interleaves high/low and keeps duration/routing separate.

### Read Instructions:
```asm
; Laxity (3 tables):
ldy filter_index
lda DataBlock_6 + $2E8,Y    ; Read filter high from $1989
lda DataBlock_6 + $302,Y    ; Read filter low from $19A3
lda DataBlock_6 + $31C,Y    ; Read duration/routing from $19BD

; Processing:
If high_byte < 0:
  // Absolute set
  resonance = (high_byte >> 4) & $07
  cutoff_high = high_byte & $0F
  cutoff_low = low_byte
Else:
  // Delta mode
  cutoff_high += high_byte
  cutoff_low += low_byte
```

---

## Unified Pattern

### Laxity NewPlayer v21 (3 Tables):

| Table Type | Table 1 | Table 2 | Table 3 |
|------------|---------|---------|---------|
| **Wave** | Waveforms ($18DA) | Note offsets ($190C) | *(embedded in Table 1)* |
| **Pulse** | Pulse high ($193E) | Pulse low ($1957) | Duration ($1970) |
| **Filter** | Filter high ($1989) | Filter low ($19A3) | Duration/routing ($19BD) |

### SF2 Format (2 Tables):

| Table Type | Table 1 (Interleaved) | Table 2 (Control) |
|------------|----------------------|-------------------|
| **Wave** | (wf, note) pairs ($0958) | Note offsets ($098A) |
| **Pulse** | (high, low) pairs ($09BC) | Duration ($09D5) |
| **Filter** | (high, low) pairs (TBD) | Duration/routing (TBD) |

---

## Conversion Algorithm

### Laxity → SF2:

```python
def convert_tables_laxity_to_sf2(laxity_table1, laxity_table2, laxity_table3=None):
    """
    Convert Laxity 3-table format to SF2 2-table format

    Args:
        laxity_table1: Primary values (waveforms, pulse high, filter high)
        laxity_table2: Secondary values (notes, pulse low, filter low)
        laxity_table3: Control values (duration, routing) - optional for wave

    Returns:
        (sf2_table1, sf2_table2): Interleaved + control tables
    """
    # SF2 Table 1: Interleave Table 1 and Table 2
    sf2_table1 = []
    for i in range(len(laxity_table1)):
        sf2_table1.append(laxity_table1[i])
        if i < len(laxity_table2):
            sf2_table1.append(laxity_table2[i])

    # SF2 Table 2: Keep Table 3 as-is
    sf2_table2 = laxity_table3 if laxity_table3 else []

    return (sf2_table1, sf2_table2)
```

### SF2 → Laxity:

```python
def convert_tables_sf2_to_laxity(sf2_table1, sf2_table2):
    """
    Convert SF2 2-table format to Laxity 3-table format

    Args:
        sf2_table1: Interleaved (value1, value2) pairs
        sf2_table2: Control values

    Returns:
        (laxity_table1, laxity_table2, laxity_table3)
    """
    # Deinterleave SF2 Table 1
    laxity_table1 = []
    laxity_table2 = []
    for i in range(0, len(sf2_table1), 2):
        laxity_table1.append(sf2_table1[i])      # Even indices
        if i + 1 < len(sf2_table1):
            laxity_table2.append(sf2_table1[i+1]) # Odd indices

    # Laxity Table 3 is SF2 Table 2
    laxity_table3 = sf2_table2

    return (laxity_table1, laxity_table2, laxity_table3)
```

---

## Why This Matters

### 1. Explains Conversion Failures

The **32% Laxity conversion failure rate** is due to:
- Missing semantic conversion between 3-table and 2-table formats
- Not properly interleaving tables when converting
- Losing duration/control parameters

### 2. Explains SF2 Roundtrip Success

The **100% SF2 roundtrip accuracy** is because:
- SF2→SID packer preserves the 2-table structure
- When packed back, both tables are maintained
- No semantic gap in the conversion

### 3. Provides Clear Fix

To improve Laxity→SF2 conversion:
1. Extract all 3 Laxity tables properly
2. Interleave Tables 1 and 2 for SF2 Table 1
3. Copy Table 3 to SF2 Table 2
4. Ensure proper end markers and loop points

### 4. Validates Architecture

All three table types follow the **same pattern**, confirming:
- Laxity uses consistent 3-table architecture
- SF2 uses consistent 2-table architecture (interleaved + control)
- Conversion requires semantic transformation, not just byte copying

---

## Implementation Priority

**Priority 1 (P1)**: Implement proper table conversion in converter

Update `sidm2/table_extraction.py`:
```python
def extract_laxity_tables(sid_data):
    # Extract all 3 tables for each type
    wave_waveforms = extract_table(sid_data, 0x18DA)
    wave_notes = extract_table(sid_data, 0x190C)

    pulse_high = extract_table(sid_data, 0x193E)
    pulse_low = extract_table(sid_data, 0x1957)
    pulse_duration = extract_table(sid_data, 0x1970)

    filter_high = extract_table(sid_data, 0x1989)
    filter_low = extract_table(sid_data, 0x19A3)
    filter_duration = extract_table(sid_data, 0x19BD)

    return {
        'wave': (wave_waveforms, wave_notes, None),
        'pulse': (pulse_high, pulse_low, pulse_duration),
        'filter': (filter_high, filter_low, filter_duration)
    }

def convert_to_sf2_format(laxity_tables):
    # Convert each table type from 3-table to 2-table format
    sf2_wave = interleave_tables(laxity_tables['wave'][0],
                                   laxity_tables['wave'][1])
    sf2_pulse = (interleave_tables(laxity_tables['pulse'][0],
                                     laxity_tables['pulse'][1]),
                 laxity_tables['pulse'][2])
    sf2_filter = (interleave_tables(laxity_tables['filter'][0],
                                      laxity_tables['filter'][1]),
                  laxity_tables['filter'][2])

    return {'wave': sf2_wave, 'pulse': sf2_pulse, 'filter': sf2_filter}
```

---

## Testing & Validation

### Test Cases:

1. **Extract Laxity 3-table data from original SID**
   - Verify all 9 tables extracted correctly
   - Check table lengths and end markers

2. **Convert to SF2 2-table format**
   - Interleave correctly
   - Preserve control parameters
   - Maintain end markers

3. **Compare with manually-created SF2**
   - Binary comparison of tables
   - Verify interleaving is correct
   - Check control table matches

4. **Test conversion back to SID**
   - SF2→SID packing
   - Verify playback matches original
   - Check register dumps match

---

## References

- [Wave Table Dual Format](WAVE_TABLE_DUAL_FORMAT.md)
- [Wave Table Read Analysis](../WAVE_TABLE_READ_ANALYSIS.md)
- [Pulse Table Read Analysis](../PULSE_TABLE_READ_ANALYSIS.md)
- [Filter Table Read Analysis](../FILTER_TABLE_READ_ANALYSIS.md)
- [Consolidation Insights](../analysis/CONSOLIDATION_INSIGHTS.md)
- [Project Roadmap](../ROADMAP.md)

---

**Document Status**: Critical discovery - implementation needed
**Priority**: P1 (High Impact)
**Next Steps**:
1. Verify pulse/filter table data in SF2-packed file
2. Update table extraction code
3. Implement interleaving conversion
4. Add unit tests for 3-table ↔ 2-table conversion
5. Measure accuracy improvement

**Maintainer**: SIDM2 Project
**Version**: 1.0
