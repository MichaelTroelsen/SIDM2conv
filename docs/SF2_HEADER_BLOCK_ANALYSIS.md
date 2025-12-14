# SF2 Header Block Analysis

**Date**: 2025-12-14
**Source**: Reverse-engineered from Driver 11 and NP20 drivers
**Purpose**: Document exact SF2 header format for Laxity driver implementation

---

## Executive Summary

This document provides the definitive SF2 header block format based on analysis of existing production drivers (Driver 11 v00, NP20 v00).

**Key Findings**:
- SF2 files start with magic number 0x1337 (little-endian)
- Header blocks follow immediately after magic number
- Block format: ID (1 byte) + Size (1 byte) + Data (N bytes)
- Block 0xFF marks end of headers
- Table descriptors embedded in Block 3

---

## File Structure

### Overall Layout

```
Offset  Size  Description
------  ----  -----------
$0000   2     PRG Load Address (little-endian)
$0002   2     SF2 Magic: 0x1337 (little-endian)
$0004   var   Header Blocks (ID, Size, Data...)
...     var   Block 0xFF (End marker)
...     var   Driver code
...     var   Music data
```

### Example: Driver 11 v00
```
$0D7E   2     Load Address: 0x7E0D → $0D7E
$0D80   2     Magic: 0x3713 (reversed for little-endian 0x1337)
$0D82   var   Header Blocks...
```

---

## Header Blocks

### Block Structure

**Format**: [ID:1][Size:1][Data:N]

Each block:
1. **Block ID** (1 byte): Type of block
2. **Block Size** (1 byte): Length of data section (NOT including ID and Size bytes)
3. **Data** (N bytes): Block-specific content

### Required Blocks

```
Driver 11 v00:
[0] Block ID=0x01 (Descriptor)  Size=41
[1] Block ID=0x02 (DriverCommon) Size=40
[2] Block ID=0x03 (DriverTables) Size=193
[3] Block ID=0x04 (InstrumentDescriptor) Size=65
[4] Block ID=0x05 (MusicData) Size=18
[5] Block ID=0x06 (ColorRules) Size=20
[6] Block ID=0x07 (InsertDeleteRules) Size=50
[7] Block ID=0x08 (ActionRules) Size=61
[8] Block ID=0x09 (InstrumentDataDescriptor) Size=41
[FF] End marker
```

**Note**: Blocks 6-9 are optional; only 1-5 are required.

---

## Block 1: Descriptor (ID=0x01)

**Size**: Varies (41 bytes in Driver 11)

**Format**:
```
Offset  Size  Type     Description
------  ----  -------  -----------
0x00    1     uint8    Driver Type (always 0x00)
0x01    2     uint16   Total Driver Size (little-endian)
0x03    var   string   Driver Name (null-terminated ASCII)
...     var   string   (continues until 0x00 found)
```

**Driver 11 Example**:
```
00: 00           Driver Type = 0x00
01: 44 07        Driver Size = 0x0744 (1860 bytes)
03: 44 12 09...  Name = "D\x12T S 11.00.00 - T S"
```

**For Laxity Driver**:
- Type: 0x00 (standard)
- Size: ~8200 bytes (Laxity driver + headers)
- Name: "Laxity NewPlayer v21 SF2 Driver" or similar

---

## Block 2: Driver Common (ID=0x02)

**Size**: 40 bytes (standard)

**Format**:
```
Offset  Size  Type     Description
------  ----  -------  -----------
0x00    2     uint16   Init routine address (little-endian)
0x02    2     uint16   Stop routine address (little-endian)
0x04    2     uint16   Play/Update routine address (little-endian)
0x06    2     uint16   SID Channel Offset address
0x08    2     uint16   Driver State address
0x0A    2     uint16   Tick Counter address
0x0C    2     uint16   OrderList Index address
0x0E    2     uint16   Sequence Index address
0x10    2     uint16   Sequence in Use address
0x12    2     uint16   Current Sequence address
0x14    2     uint16   Current Transpose address
0x16    2     uint16   Sequence Event Duration address
0x18    2     uint16   Next Instrument address
0x1A    2     uint16   Next Command address
0x1C    2     uint16   Next Note address
0x1E    2     uint16   Next Note is Tied address
0x20    2     uint16   Tempo Counter address
0x22    2     uint16   Trigger Sync address
0x24    1     uint8    Note Event Trigger Sync Value
0x25    1     uint8    Reserved
0x26    2     uint16   Reserved
```

**Driver 11 Example**:
```
00-01: 10 03   Init = $1003
02-03: 10 06   Stop = $1006
04-05: C8 16   Play = $16C8
... (rest of addresses)
```

**For Laxity Driver**:
- Init: $0D7E (our wrapper init)
- Stop: $0D84 (our wrapper stop)
- Play: $0D81 (our wrapper play)
- Others: Point to relocated player state locations

---

## Block 3: Driver Tables (ID=0x03)

**Size**: Variable (193 bytes in Driver 11, 174 bytes in NP20)

**Format**: Sequential table descriptors (each ~19-20 bytes)

### Table Descriptor Format

```
Offset  Size  Type     Description
------  ----  -------  -----------
0x00    1     uint8    Table Type:
                         0x00 = Generic table
                         0x80 = Instruments
                         0x81 = Commands
0x01    1     uint8    Table ID (unique per driver)
0x02    1     uint8    Name field length (including null terminator)
0x03    var   string   Table name (null-terminated)
...     1     uint8    Data Layout:
                         0x00 = Row-major (default)
                         0x01 = Column-major
...     1     uint8    Flags (combined):
                         bit 0: Enable insert/delete
                         bit 1: Layout vertically in editor
                         bit 2: Index as continuous memory
...     1     uint8    Insert/Delete Rule ID
...     1     uint8    Enter Action Rule ID
...     1     uint8    Color Rule ID
...     2     uint16   Address of table data (little-endian)
...     2     uint16   Column count (little-endian)
...     2     uint16   Row count (little-endian)
```

**Driver 11 Example** (Instruments table):
```
81 00 0C 43 0F 0D 0D 01 0E 04 13 00 01 00 FF 03 FF 44 18 03
```

Breakdown:
- 81: Type = 0x81 (Instruments)
- 00: ID = 0x00
- 0C: Name length = 12 bytes
- 43 0F 0D 0D 01 0E 04 13: Name data
- 00: Data layout = 0x00 (row-major)
- 01: Flags = 0x01 (insert/delete enabled)
- 00: Insert/Delete rule = 0x00
- FF: Enter action rule = 0xFF (none)
- 03: Color rule = 0x03
- FF 44: Address = $44FF
- 18: Columns = 24 (or similar)
- 03: Rows = 3 (or similar)

### Laxity Tables to Define

1. **Sequences Table**
   - Type: 0x00 (Generic)
   - ID: 0x00
   - Name: "Sequences" (9 bytes)
   - Address: $1900
   - Layout: Custom (may need column-major)
   - Insert/Delete: Maybe disabled (complex structure)

2. **Instruments Table**
   - Type: 0x80 (Instruments)
   - ID: 0x01
   - Name: "Instruments" (11 bytes)
   - Address: $1A6B
   - Columns: 8 (8 bytes per instrument)
   - Rows: 32 (32 instruments)
   - Layout: Row-major
   - Insert/Delete: Enable
   - Fields: ADSR, waveform, pulse width, etc.

3. **Wave Table**
   - Type: 0x00 (Generic)
   - ID: 0x02
   - Name: "Wave" (5 bytes)
   - Address: $1ACB
   - Columns: 2 (waveform index, note offset)
   - Rows: 128 (128 entries)
   - Layout: Row-major
   - Insert/Delete: Maybe disabled

4. **Pulse Table**
   - Type: 0x00 (Generic)
   - ID: 0x03
   - Name: "Pulse" (6 bytes)
   - Address: $1A3B
   - Columns: 4 (4 bytes per entry)
   - Rows: 64 (64 entries)
   - Layout: Row-major

5. **Filter Table**
   - Type: 0x00 (Generic)
   - ID: 0x04
   - Name: "Filter" (7 bytes)
   - Address: $1A1E
   - Columns: 4 (4 bytes per entry)
   - Rows: 32 (32 entries)
   - Layout: Row-major

---

## Block 4: Instrument Descriptor (ID=0x04)

**Size**: Varies (65 bytes in Driver 11)

**Purpose**: Describes instrument data structure for editor

**Format**: Similar to table descriptors, defines instrument fields

---

## Block 5: Music Data (ID=0x05)

**Size**: Usually small (18 bytes in Driver 11)

**Purpose**: Marks location of music data

**Format**: Contains reference to music data location

---

## Blocks 6-9: Optional (Color, Rules, Action)

**IDs**: 0x06-0x09

**Purpose**: Define visual appearance and behavior rules

- Block 6: Color rules for tables
- Block 7: Insert/delete rules
- Block 8: Action rules (what happens on Enter, etc.)
- Block 9: Instrument data descriptor

---

## Implementation Strategy for Laxity Driver

### Step 1: Create Block 1 (Descriptor)
```python
def create_descriptor_block():
    block = bytearray()
    block.append(0x01)  # Block ID
    # Will add size after content

    driver_type = 0x00
    driver_size = 8192  # Laxity driver size
    name = b"Laxity NewPlayer v21 SF2\x00"

    content = bytearray()
    content.append(driver_type)
    content.extend(struct.pack('<H', driver_size))
    content.extend(name)

    # Add content size before data
    block.append(len(content))
    block.extend(content)
    return block
```

### Step 2: Create Block 2 (Driver Common)
```python
def create_driver_common_block():
    block = bytearray([0x02, 40])  # ID and size (always 40)

    addresses = {
        'init': 0x0D7E,
        'stop': 0x0D84,
        'play': 0x0D81,
        # ... 17 more addresses
    }

    content = bytearray()
    for addr in addresses.values():
        content.extend(struct.pack('<H', addr))

    block.extend(content)
    return block
```

### Step 3: Create Block 3 (Tables)
```python
def create_tables_block():
    tables = [
        create_table_descriptor('Sequences', 0x00, 0x1900, ...),
        create_table_descriptor('Instruments', 0x01, 0x1A6B, 8, 32),
        create_table_descriptor('Wave', 0x02, 0x1ACB, 2, 128),
        create_table_descriptor('Pulse', 0x03, 0x1A3B, 4, 64),
        create_table_descriptor('Filter', 0x04, 0x1A1E, 4, 32),
    ]

    content = bytearray()
    for table in tables:
        content.extend(table)

    block = bytearray([0x03, len(content)])
    block.extend(content)
    return block
```

### Step 4: Assemble Complete Header
```python
def create_sf2_headers():
    headers = bytearray()
    headers.extend(struct.pack('<H', 0x1337))  # Magic
    headers.extend(create_descriptor_block())
    headers.extend(create_driver_common_block())
    headers.extend(create_tables_block())
    headers.extend(create_optional_blocks())
    headers.append(0xFF)  # End marker
    return headers
```

---

## Validation Checklist

- [ ] Magic number 0x1337 present at start
- [ ] Block 1 present with valid driver descriptor
- [ ] Block 2 present with correct address references
- [ ] Block 3 present with all table descriptors
- [ ] All table descriptors have correct addresses
- [ ] All table descriptors have valid name strings
- [ ] Block 0xFF end marker present
- [ ] Total header size < 512 bytes (reserved space)
- [ ] No overlapping table addresses
- [ ] All addresses point to valid memory regions

---

## Known Issues & Workarounds

### Issue 1: Table Name Encoding
**Problem**: Some driver names have special characters that may not be valid ASCII

**Solution**: Filter to printable ASCII only, truncate if too long

### Issue 2: Column/Row Count Ambiguity
**Problem**: Some drivers may specify counts differently than expected

**Solution**: Analyze actual data format, may need to decode sequences specially

### Issue 3: Variable-Length Sequences
**Problem**: Sequence data has variable length, can't be represented as fixed rows/columns

**Solution**: May need to mark as "continuous memory" instead of row/column indexed

---

## References

- **SF2 Editor Source**: See external-repositories.md for SID Factory II source
- **Driver 11 Analysis**: Production driver for reference implementation
- **NP20 Analysis**: Alternative driver for comparison
- **Laxity Documentation**: LAXITY_DRIVER_FINAL_REPORT.md

---

**Status**: Analysis Complete
**Next Step**: Implement header generator based on this specification
