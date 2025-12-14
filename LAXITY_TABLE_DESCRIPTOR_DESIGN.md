# Laxity Table Descriptor Design Specification

**Status**: Design Phase
**Date**: 2025-12-14
**Purpose**: Exact specifications for SF2 header table descriptors

---

## Design Principles

1. **Native Format**: Tables remain in Laxity format, no conversion
2. **Editor Compatibility**: Structures match SF2 editor expectations
3. **Editability**: All tables should be viewable, instruments/wave/pulse/filter editable
4. **Integrity**: No data corruption when editing
5. **Clarity**: Column/row structure clearly represents actual data

---

## Table 1: Instruments Table

### Overview
- **Memory Address**: $1A6B
- **Entries**: 32 instruments
- **Bytes per Entry**: 8 bytes
- **Total Size**: 256 bytes
- **Type**: 0x80 (Instruments - special in SF2)
- **Data Layout**: Row-major

### Laxity Instrument Format (8 bytes each)
```
Byte 0: ADSR Attack rate
Byte 1: ADSR Decay rate
Byte 2: ADSR Sustain level
Byte 3: ADSR Release rate
Byte 4: Waveform bits [7:0] (triangle, pulse, noise, sawtooth)
Byte 5: Pulse width high byte
Byte 6: Pulse width low byte
Byte 7: Filter type / routing
```

### SF2 Descriptor Design

**Block 3 Data** (Table Descriptor):
```
Offset  Value  Description
------  -----  -----------
0x00    0x80   Type = Instruments (special table type)
0x01    0x00   ID = 0 (first table)
0x02    0x0C   Name length = 12 bytes (including null)
0x03    'I'    Name start: "Instruments\0"
0x03-0x0E  ...
0x0F    0x00   Data Layout = Row-major
0x10    0x01   Flags: bit 0 = Insert/Delete enabled, others = 0
0x11    0x00   Insert/Delete Rule ID = 0 (standard)
0x12    0xFF   Enter Action Rule ID = 0xFF (none)
0x13    0x03   Color Rule ID = 3 (standard instruments color)
0x14-0x15  0x6B 0x1A   Address = $1A6B (little-endian: 0x1A6B)
0x16-0x17  0x08 0x00   Columns = 8 (bytes per instrument)
0x18-0x19  0x20 0x00   Rows = 32 (number of instruments)
```

**Byte-by-byte**:
```
80 00 0C 49 6E 73 74 72 75 6D 65 6E 74 73 00 00 00 01 00 FF 03 6B 1A 08 00 20 00
```

**Breakdown**:
- `80`: Type = Instruments
- `00`: ID = 0
- `0C`: Name = 12 bytes
- `49 6E 73 74 72 75 6D 65 6E 74 73 00`: "Instruments\0"
- `00`: Row-major layout
- `01`: Insert/Delete enabled
- `00 FF 03`: Rules
- `6B 1A`: Address $1A6B (little-endian)
- `08 00`: 8 columns
- `20 00`: 32 rows

**Size**: 27 bytes

---

## Table 2: Wave Table

### Overview
- **Memory Address**: $1ACB
- **Entries**: 128 waveform lookups
- **Bytes per Entry**: 2 bytes
- **Total Size**: 256 bytes
- **Type**: 0x00 (Generic)
- **Data Layout**: Row-major

### Laxity Wave Format (2 bytes each)
```
Byte 0: Waveform index (0-255)
Byte 1: Note offset (semitones, signed -128 to +127)
```

### SF2 Descriptor Design

```
Offset  Value  Description
------  -----  -----------
0x00    0x00   Type = Generic
0x01    0x01   ID = 1 (second table)
0x02    0x06   Name length = 6 bytes (including null)
0x03    'W'    Name start: "Wave\0" (5 chars + null)
0x03-0x07  ...
0x08    0x00   Data Layout = Row-major
0x09    0x00   Flags: bit 0 = Insert/Delete disabled
0x0A    0x00   Insert/Delete Rule ID = 0
0x0B    0xFF   Enter Action Rule ID = 0xFF (none)
0x0C    0x00   Color Rule ID = 0
0x0D-0x0E  0xCB 0x1A   Address = $1ACB (little-endian)
0x0F-0x10  0x02 0x00   Columns = 2 (2 bytes per entry)
0x11-0x12  0x80 0x00   Rows = 128 (128 entries)
```

**Byte-by-byte**:
```
00 01 06 57 61 76 65 00 00 00 00 00 FF 00 CB 1A 02 00 80 00
```

**Size**: 20 bytes

---

## Table 3: Pulse Table

### Overview
- **Memory Address**: $1A3B
- **Entries**: 64 pulse width entries
- **Bytes per Entry**: 4 bytes
- **Total Size**: 256 bytes
- **Type**: 0x00 (Generic)
- **Data Layout**: Row-major

### Laxity Pulse Format (4 bytes each)
```
Byte 0: Pulse width high byte
Byte 1: Pulse width low byte
Byte 2: Pulse width delta (sweep/modulation)
Byte 3: Duration / flags
```

### SF2 Descriptor Design

```
Offset  Value  Description
------  -----  -----------
0x00    0x00   Type = Generic
0x01    0x02   ID = 2 (third table)
0x02    0x07   Name length = 7 bytes (including null)
0x03    'P'    Name start: "Pulse\0" (6 chars + null)
0x03-0x08  ...
0x09    0x00   Data Layout = Row-major
0x0A    0x00   Flags: Insert/Delete disabled
0x0B    0x00   Insert/Delete Rule ID
0x0C    0xFF   Enter Action Rule ID = 0xFF (none)
0x0D    0x00   Color Rule ID = 0
0x0E-0x0F  0x3B 0x1A   Address = $1A3B (little-endian)
0x10-0x11  0x04 0x00   Columns = 4 (4 bytes per entry)
0x12-0x13  0x40 0x00   Rows = 64 (64 entries)
```

**Byte-by-byte**:
```
00 02 07 50 75 6C 73 65 00 00 00 00 FF 00 3B 1A 04 00 40 00
```

**Size**: 20 bytes

---

## Table 4: Filter Table

### Overview
- **Memory Address**: $1A1E
- **Entries**: 32 filter entries
- **Bytes per Entry**: 4 bytes
- **Total Size**: 128 bytes
- **Type**: 0x00 (Generic)
- **Data Layout**: Row-major

### Laxity Filter Format (4 bytes each)
```
Byte 0: Filter frequency high byte
Byte 1: Filter frequency low byte
Byte 2: Filter resonance / filter type
Byte 3: Filter mode (LP, HP, BP, etc.)
```

### SF2 Descriptor Design

```
Offset  Value  Description
------  -----  -----------
0x00    0x00   Type = Generic
0x01    0x03   ID = 3 (fourth table)
0x02    0x08   Name length = 8 bytes (including null)
0x03    'F'    Name start: "Filter\0" (7 chars + null)
0x03-0x09  ...
0x0A    0x00   Data Layout = Row-major
0x0B    0x00   Flags: Insert/Delete disabled
0x0C    0x00   Insert/Delete Rule ID
0x0D    0xFF   Enter Action Rule ID = 0xFF (none)
0x0E    0x00   Color Rule ID = 0
0x0F-0x10  0x1E 0x1A   Address = $1A1E (little-endian)
0x11-0x12  0x04 0x00   Columns = 4 (4 bytes per entry)
0x13-0x14  0x20 0x00   Rows = 32 (32 entries)
```

**Byte-by-byte**:
```
00 03 08 46 69 6C 74 65 72 00 00 00 00 FF 00 1E 1A 04 00 20 00
```

**Size**: 21 bytes

---

## Table 5: Sequences Table

### Overview
- **Memory Address**: $1900
- **Entries**: 3 sequences (one per voice)
- **Format**: Variable-length sequences
- **Type**: 0x00 (Generic)
- **Challenge**: Variable length - difficult to represent as fixed rows/columns

### Laxity Sequence Format
```
Each sequence:
- Voice index (0-2)
- Sequence data with control bytes:
  - 0x7F: End of sequence
  - 0x7E: Loop marker / gate
  - 0x00-0x7D: Note or command
```

### SF2 Descriptor Design - OPTION A (Continuous Memory)

For variable-length data, use "continuous memory" flag:

```
Offset  Value  Description
------  -----  -----------
0x00    0x00   Type = Generic
0x01    0x04   ID = 4 (fifth table)
0x02    0x0A   Name length = 10 bytes (including null)
0x03    'S'    Name start: "Sequences\0" (9 chars + null)
0x03-0x0B  ...
0x0C    0x00   Data Layout = Row-major
0x0D    0x04   Flags: bit 2 = Index as continuous memory
0x0E    0x00   Insert/Delete Rule ID
0x0F    0xFF   Enter Action Rule ID = 0xFF (none)
0x10    0x00   Color Rule ID = 0
0x11-0x12  0x00 0x19   Address = $1900 (little-endian)
0x13-0x14  0x01 0x00   Columns = 1 (continuous)
0x15-0x16  0xFF 0x00   Rows = 255 (maximum for variable data)
```

**Byte-by-byte**:
```
00 04 0A 53 65 71 75 65 6E 63 65 73 00 00 04 00 FF 00 00 19 01 00 FF 00
```

**Size**: 24 bytes

### Alternative: Don't Include Sequences Table

If sequences are too complex, we can skip including them in the SF2 descriptor. Users can still edit orderlists, and sequences will be reflected automatically.

**Recommendation**: Start with OPTION A (continuous memory). If it doesn't work in the editor, remove sequences table entirely.

---

## Combined Block 3 (DriverTables) Assembly

**All 5 table descriptors combined**:

```
Block ID: 0x03
Block Size: 27 + 20 + 20 + 21 + 24 = 112 bytes

Data (hex):
80 00 0C 49 6E 73 74 72 75 6D 65 6E 74 73 00 00 00 01 00 FF 03 6B 1A 08 00 20 00
00 01 06 57 61 76 65 00 00 00 00 00 FF 00 CB 1A 02 00 80 00
00 02 07 50 75 6C 73 65 00 00 00 00 FF 00 3B 1A 04 00 40 00
00 03 08 46 69 6C 74 65 72 00 00 00 00 FF 00 1E 1A 04 00 20 00
00 04 0A 53 65 71 75 65 6E 63 65 73 00 00 04 00 FF 00 00 19 01 00 FF 00
```

**Verification**:
- [x] All table types valid (0x00 or 0x80)
- [x] All IDs unique (0-4)
- [x] All names null-terminated
- [x] All addresses in valid range ($1900-$1ACB)
- [x] All row/column counts reasonable
- [x] Total size ~112 bytes (reasonable)

---

## Implementation in Python

### Data Structure

```python
class TableDescriptor:
    def __init__(self, name, table_id, address, columns, rows,
                 table_type=0x00, layout=0x00, insert_delete=False):
        self.name = name
        self.table_id = table_id
        self.address = address
        self.columns = columns
        self.rows = rows
        self.table_type = table_type
        self.layout = layout
        self.insert_delete = insert_delete

    def to_bytes(self):
        """Generate SF2 descriptor bytes."""
        data = bytearray()

        # Table type and ID
        data.append(self.table_type)
        data.append(self.table_id)

        # Name with null terminator
        name_bytes = self.name.encode('ascii') + b'\x00'
        data.append(len(name_bytes))
        data.extend(name_bytes)

        # Layout and flags
        data.append(self.layout)
        flags = 0x01 if self.insert_delete else 0x00
        data.append(flags)

        # Rule IDs
        data.append(0x00)  # Insert/Delete rule
        data.append(0xFF)  # Enter action rule
        data.append(0x03 if self.table_type == 0x80 else 0x00)  # Color rule

        # Address (little-endian)
        data.extend(struct.pack('<H', self.address))

        # Columns and rows (little-endian)
        data.extend(struct.pack('<H', self.columns))
        data.extend(struct.pack('<H', self.rows))

        return bytes(data)
```

### Usage

```python
# Define tables
tables = [
    TableDescriptor('Instruments', 0, 0x1A6B, 8, 32,
                   table_type=0x80, insert_delete=True),
    TableDescriptor('Wave', 1, 0x1ACB, 2, 128),
    TableDescriptor('Pulse', 2, 0x1A3B, 4, 64),
    TableDescriptor('Filter', 3, 0x1A1E, 4, 32),
    TableDescriptor('Sequences', 4, 0x1900, 1, 255,
                   layout=0x00),  # Will set continuous flag later
]

# Generate block
block_data = bytearray()
for table in tables:
    block_data.extend(table.to_bytes())

# Create block with ID and size
block = bytearray([0x03, len(block_data)])
block.extend(block_data)
```

---

## Alternative Designs Considered

### Design A: Variable Row Count per Table
- **Pros**: More accurate representation
- **Cons**: Complex, may not work in SF2 editor

### Design B: No Sequences Table
- **Pros**: Simpler, avoids complexity
- **Cons**: Loses editability of sequences

### Design C: Map Sequences as Single Large Table
- **Pros**: Editable in editor
- **Cons**: Hard to understand, may confuse users

**Selected**: Design with Sequences as continuous memory (Option A)

---

## Validation Checklist

- [ ] All table addresses match actual memory layout
- [ ] All table sizes match actual data
- [ ] All names are ASCII, null-terminated, reasonable length
- [ ] Data layout values valid (0x00 or 0x01)
- [ ] Flags correctly set (insert/delete only for instruments)
- [ ] Color rules appropriate (3 for instruments, 0 for others)
- [ ] Total descriptor block < 200 bytes
- [ ] No overlapping table addresses
- [ ] No negative values in unsigned fields
- [ ] All little-endian values correct

---

## Next Steps

1. **Implement Python generator** using these specifications
2. **Generate test headers** and verify structure
3. **Compare with Driver 11** for validation
4. **Test in SF2 editor** with real files
5. **Refine based on editor feedback** if needed

---

## Questions & Decisions

**Q**: Should sequences table be included or skipped?
**A**: Include with continuous memory flag. Can be removed later if problematic.

**Q**: Should we enable insert/delete for Instruments?
**A**: Yes - this is typical for instrument tables. Can be disabled if issues arise.

**Q**: What about ordering of tables?
**A**: Instruments first (type 0x80), then generic tables (type 0x00).

**Q**: Do we need optional blocks (6-9)?
**A**: Not initially. Can be added later if editor needs color/action rules.

---

**Status**: ✅ Design Complete
**Next Action**: Implement Python generator in Task 3
