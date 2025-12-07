# Wave Table Packing Format

## Overview

The Wave Table in SID Factory II uses **column-major storage** - a form of Structure-of-Arrays (SoA) packing that separates note offsets and waveforms into two contiguous blocks.

**Based on**: SF2 source code analysis and format reverse engineering

---

## Format Comparison

### Editor Display Format (UI)
```
Entry | Waveform | Note
------|----------|-----
  00  |    21    |  80
  01  |    21    |  80
  02  |    41    |  00
  03    |    7F    |  02   (loop marker)
  04  |    51    |  C0
  ...
```

### Packed Format (In Memory/File)
```
Address: $1914-$1953 (64 bytes total)

Bytes 0x00-0x1F (32 bytes): Note Offsets
  80 80 00 02 C0 A1 9A 00 07 C4 AC C0 BC 0C C0 00 ...

Bytes 0x20-0x3F (32 bytes): Waveforms
  21 21 41 7F 51 41 41 41 7F 81 41 80 80 7F 81 01 ...
```

---

## Storage Layout

### Column-Major (2 columns × 32 rows)

The Wave table stores data in **column-major** order:
- **Column 0** (Note offsets): All 32 note offset bytes
- **Column 1** (Waveforms): All 32 waveform bytes

**Memory Layout**:
```
$1914-$1933: Note offsets [0-31]
$1934-$1953: Waveforms [0-31]
```

### Why Column-Major?

This layout optimizes for:
1. **Sequential access** - Player can read all notes or all waveforms linearly
2. **Cache efficiency** - Related data grouped together
3. **Compression** - Patterns in note offsets or waveforms easier to identify

---

## Packing Algorithm

### From Editor to Packed Format

```python
def pack_wave_table(entries: list) -> bytes:
    """
    Pack Wave table entries to column-major format.

    Args:
        entries: List of (waveform, note) tuples

    Returns:
        64 bytes: [all notes] + [all waveforms]
    """
    notes = []
    waveforms = []

    for waveform, note in entries:
        notes.append(note)
        waveforms.append(waveform)

    # Column-major: all notes first, then all waveforms
    return bytes(notes) + bytes(waveforms)
```

**Example**:
```
Input (editor format):
  [(0x21, 0x80), (0x21, 0x80), (0x41, 0x00), ...]

Output (packed format):
  [0x80, 0x80, 0x00, ...] + [0x21, 0x21, 0x41, ...]
  ^-- notes (32 bytes)     ^-- waveforms (32 bytes)
```

---

## Unpacking Algorithm

### From Packed Format to Editor

```python
def unpack_wave_table(packed_data: bytes) -> list:
    """
    Unpack Wave table from column-major format.

    Args:
        packed_data: 64 bytes in column-major format

    Returns:
        List of (waveform, note) tuples
    """
    notes = packed_data[0:32]      # First 32 bytes
    waveforms = packed_data[32:64]  # Next 32 bytes

    entries = []
    for i in range(32):
        entries.append((waveforms[i], notes[i]))

    return entries
```

**Example**:
```
Input (packed format):
  Bytes 00-1F: 80 80 00 02 C0 ... (notes)
  Bytes 20-3F: 21 21 41 7F 51 ... (waveforms)

Output (editor format):
  [(0x21, 0x80), (0x21, 0x80), (0x41, 0x00), (0x7F, 0x02), (0x51, 0xC0), ...]
```

---

## Table Definition

From SF2 header Block 3 (Driver Tables):

```cpp
TableDefinition {
    m_Type = 0x00               // Generic table
    m_ID = 2                    // Wave table
    m_Name = "Wave"
    m_DataLayout = 1            // ColumnMajor
    m_Address = 0x1914          // Start address
    m_ColumnCount = 2           // 2 columns (note, waveform)
    m_RowCount = 32             // 32 entries
}
```

---

## Byte Values

### Note Offset Column
- `0x00`: No offset (use base note)
- `0x01-0x5F`: Positive offset (+1 to +95 semitones)
- `0x7E`: Gate on marker
- `0x7F`: Loop marker
- `0x80`: Special note offset (recalculate frequency)
- `0xA0+`: Negative offset / transpose values

### Waveform Column
- **Bits 0-3**: Waveform type
  - `0x01` = Triangle
  - `0x02` = Sawtooth
  - `0x04` = Pulse
  - `0x08` = Noise
- **Bit 4**: Gate bit
- **Bits 5-7**: Additional control flags
- **Special values**:
  - `0x7E` = Gate on (sustain)
  - `0x7F` = Loop marker
  - `0x80` = Gate off (---)

---

## Implementation Example

### Reading from SF2-packed SID

```python
def read_wave_table(memory: bytes, base_addr: int) -> list:
    """
    Read Wave table from packed SID memory.

    Args:
        memory: 64KB C64 memory
        base_addr: Wave table start address (e.g., 0x1914)

    Returns:
        List of (waveform, note) entries
    """
    # Extract 64 bytes
    packed_data = memory[base_addr:base_addr+64]

    # Unpack column-major format
    notes = packed_data[0:32]
    waveforms = packed_data[32:64]

    entries = []
    for i in range(32):
        waveform = waveforms[i]
        note = notes[i]
        entries.append((waveform, note))

    return entries
```

### Writing to SF2 format

```python
def write_wave_table(memory: bytearray, base_addr: int, entries: list):
    """
    Write Wave table to SF2 format memory.

    Args:
        memory: 64KB C64 memory (bytearray)
        base_addr: Wave table start address
        entries: List of (waveform, note) tuples
    """
    # Pad to 32 entries
    while len(entries) < 32:
        entries.append((0x00, 0x00))

    # Separate into columns
    notes = []
    waveforms = []
    for waveform, note in entries[:32]:
        notes.append(note)
        waveforms.append(waveform)

    # Write column-major: notes first, then waveforms
    for i, note in enumerate(notes):
        memory[base_addr + i] = note

    for i, waveform in enumerate(waveforms):
        memory[base_addr + 32 + i] = waveform
```

---

## Comparison with Other Tables

### Storage Formats by Table

| Table      | Layout       | Columns | Rows | Notes |
|------------|--------------|---------|------|-------|
| Wave       | Column-Major | 2       | 32   | Note + Waveform |
| Pulse      | Row-Major    | 4       | 16   | Value, Delta, Duration, Next |
| Filter     | Row-Major    | 3       | 16   | Value, Delta, Duration |
| Arpeggio   | Row-Major    | 4       | 16   | 4 note offsets |
| Instruments| Column-Major | 6       | 32   | Driver 11 only |
| Commands   | Row-Major    | 3       | 64   | Type, Param1, Param2 |

---

## References

- [SF2 Format Specification](SF2_FORMAT_SPEC.md)
- [SF2 Source Analysis](SF2_SOURCE_ANALYSIS.md)
- [Driver Reference](DRIVER_REFERENCE.md)
- Wave table packing demo: `wave_table_packing_demo.py`

---

## Key Takeaways

1. ✅ **Wave table uses column-major storage** (all notes, then all waveforms)
2. ✅ **Editor displays pairs** (waveform, note) but packs as columns
3. ✅ **Total size is always 64 bytes** (32 notes + 32 waveforms)
4. ✅ **Access pattern**: `packed[i]` = note[i], `packed[32+i]` = waveform[i]
5. ✅ **Round-trip verified**: Pack → Unpack → Pack produces identical data
