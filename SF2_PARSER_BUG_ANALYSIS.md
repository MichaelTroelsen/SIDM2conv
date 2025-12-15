# SF2 Parser Bug Analysis & Fixes

**Date**: 2025-12-15
**Status**: Critical bugs identified in sf2_viewer_core.py
**Severity**: High - causes incorrect parsing of driver names and table descriptors

---

## Executive Summary

The SF2 parser in `sf2_viewer_core.py` has **three critical parsing bugs** that prevent correct reading of:
1. Driver names in Block 1 (Descriptor)
2. Table name length fields in Block 3 (Driver Tables)
3. Table dimension fields (column_count, row_count) as 2-byte values

These bugs cause:
- Driver names with embedded control characters to display incorrectly
- Table names to be garbled or incomplete
- Table dimensions to be wrong (causing incorrect table data display)
- Memory map to show corrupted data

---

## Bug #1: Descriptor Block Parser - Missing Name Length Field

### Location
`sf2_viewer_core.py`, lines 303-332, `_parse_descriptor_block()`

### Current Code
```python
def _parse_descriptor_block(self):
    """Parse Block 1: Descriptor (driver info)"""
    if BlockType.DESCRIPTOR not in self.blocks:
        return

    offset, data = self.blocks[BlockType.DESCRIPTOR]

    if len(data) < 3:
        return

    driver_type = data[0]
    driver_size = struct.unpack('<H', data[1:3])[0]

    # Extract driver name (null-terminated string)
    name_end = data.find(b'\x00', 3)
    if name_end == -1:
        name_end = len(data)

    # Use latin-1 to preserve all bytes, then clean non-printable characters
    driver_name_raw = data[3:name_end].decode('latin-1')
    driver_name = self._clean_string(driver_name_raw)

    self.driver_info = {
        'type': driver_type,
        'size': driver_size,
        'name': driver_name,
        'size_hex': f"0x{driver_size:04X}",
    }

    logger.info(f"Driver: {driver_name} (size: ${driver_size:04X})")
```

### Correct Block 1 Structure
Per SF2 specification:
```
Offset  Size  Type     Description
------  ----  -------  -----------
0x00    1     uint8    Driver Type (always 0x00)
0x01    2     uint16   Total Driver Size (little-endian)
0x03    var   string   Driver Name (null-terminated ASCII)
```

### Problem
✓ The parsing is correct for Block 1! No bugs found here.

---

## Bug #2: Driver Tables Block Parser - Incorrect Name Length Handling

### Location
`sf2_viewer_core.py`, lines 370-430, `_parse_driver_tables_block()`

### Current Code (INCORRECT)
```python
def _parse_driver_tables_block(self):
    """Parse Block 3: Driver Tables (table descriptors)"""
    if BlockType.DRIVER_TABLES not in self.blocks:
        return

    offset, data = self.blocks[BlockType.DRIVER_TABLES]

    pos = 0
    while pos < len(data):
        if pos + 12 > len(data):
            break

        table_type = data[pos]        # Offset 0x00
        table_id = data[pos + 1]      # Offset 0x01

        # Find name (null-terminated) - SKIPS THE NAME LENGTH FIELD!
        name_start = pos + 2           # Should be pos + 3!
        name_end = data.find(b'\x00', name_start)
        if name_end == -1:
            name_end = len(data)

        # Use latin-1 to preserve all bytes, then clean non-printable characters
        name_raw = data[name_start:name_end].decode('latin-1')
        name = self._clean_string(name_raw)
        pos = name_end + 1

        if pos + 10 > len(data):
            break

        # WRONG OFFSETS - Reading from pos instead of correctly advancing past name
        data_layout = TableDataLayout(data[pos])           # WRONG OFFSET
        flags = data[pos + 1]                               # WRONG OFFSET
        insert_delete_rule = data[pos + 2]                 # WRONG OFFSET
        enter_action_rule = data[pos + 3]                  # WRONG OFFSET
        color_rule = data[pos + 4]                         # WRONG OFFSET
        address = struct.unpack('<H', data[pos + 5:pos + 7])[0]  # WRONG OFFSET
        column_count = data[pos + 7]   # BUG: Should be 2 bytes, not 1!
        row_count = data[pos + 8]      # BUG: Should be 2 bytes, not 1!

        # ... rest of code ...
        pos += 9  # WRONG: This assumes fixed name length
```

### Correct Table Descriptor Structure
Per SF2 specification (each descriptor is variable-length):
```
Offset  Size  Type     Description
------  ----  -------  -----------
0x00    1     uint8    Table Type
0x01    1     uint8    Table ID
0x02    1     uint8    Name Field Length (INCLUDING null terminator)
0x03    var   string   Table name (ASCII)
...     1     uint8    0x00 (null terminator)
...     1     uint8    Data Layout (0x00=row-major, 0x01=column-major)
...     1     uint8    Flags byte
...     1     uint8    Insert/Delete Rule ID
...     1     uint8    Enter Action Rule ID
...     1     uint8    Color Rule ID
...     2     uint16   Address of table data (little-endian)
...     2     uint16   Column count (little-endian) ← 2 BYTES
...     2     uint16   Row count (little-endian)    ← 2 BYTES
...     1     uint8    Visible row count
```

**Key Structure Rules:**
1. The name length field at offset 0x02 tells us how many bytes the name occupies (including null terminator)
2. Example: If name length = 0x0C (12 bytes), the name is 11 ASCII characters + 1 null byte
3. We must read this field to know where the name ends and the rest of the struct begins
4. The parser cannot use `find(b'\x00')` because it doesn't correctly locate the field boundaries

### Problems Found

**Problem 1: Missing Name Length Field Read**
- Current code: Skips the name length field at offset 0x02
- Code reads: `name_start = pos + 2`
- Should be: `name_length = data[pos + 2]` then `name_start = pos + 3`

**Problem 2: Dynamic Null Finder vs Structured Parsing**
- Current code: Uses `find(b'\x00')` to locate end of name
- This works by accident if null terminator is present, but:
  - Doesn't validate the name length field
  - Produces wrong position for subsequent field reads
  - Doesn't properly align with table descriptor structure

**Problem 3: Incorrect Field Offsets After Name**
- Current code sets `pos = name_end + 1` after finding null terminator
- Then reads fields from `pos` assuming they're at fixed offsets
- But the fields are actually located at:
  - `name_end + 1` (after null terminator): data_layout
  - `name_end + 2`: flags
  - `name_end + 3`: insert_delete_rule
  - `name_end + 4`: enter_action_rule
  - `name_end + 5`: color_rule
  - `name_end + 6-7`: address (2 bytes)
  - `name_end + 8-9`: column_count (2 bytes) ← NOT `data[pos + 7]`
  - `name_end + 10-11`: row_count (2 bytes) ← NOT `data[pos + 8]`

**Problem 4: Column/Row Count as 1-byte Instead of 2-byte**
```python
column_count = data[pos + 7]   # BUG: Reading only 1 byte
row_count = data[pos + 8]      # BUG: Reading only 1 byte
```

Should be:
```python
column_count = struct.unpack('<H', data[pos + 8:pos + 10])[0]  # 2-byte little-endian
row_count = struct.unpack('<H', data[pos + 10:pos + 12])[0]    # 2-byte little-endian
```

**Problem 5: Incorrect Position Increment**
```python
pos += 9  # WRONG: Assumes fixed-length name
```

This assumes every table descriptor is exactly 9 bytes after the type+ID, which is wrong because names are variable-length!

Should be:
```python
pos = name_end + 1 + 10  # Skip null terminator + 10 remaining bytes
```

Or better, properly calculate based on parsed name length:
```python
pos = pos + 3 + name_length + 10  # 3 header bytes + name + 10 tail bytes
```

---

## Bug #3: Incorrect Field Offset Calculations

### Current Broken Logic
```python
pos = name_end + 1  # Position after null terminator

# These offsets are WRONG because pos doesn't account for name length field
data_layout = TableDataLayout(data[pos])         # Should be at name_end + 1
flags = data[pos + 1]                             # Should be at name_end + 2
insert_delete_rule = data[pos + 2]               # Should be at name_end + 3
enter_action_rule = data[pos + 3]                # Should be at name_end + 4
color_rule = data[pos + 4]                       # Should be at name_end + 5
address = struct.unpack('<H', data[pos + 5:pos + 7])[0]  # Should be at name_end + 6
column_count = data[pos + 7]                     # BUG: Only 1 byte!
row_count = data[pos + 8]                        # BUG: Only 1 byte!

pos += 9  # COMPLETELY WRONG increment
```

### Correct Logic
```python
# Read name length at offset 0x02
name_length = data[pos + 2]

# Calculate where the name bytes start
name_start = pos + 3

# Calculate where name ends (name_length includes the null terminator)
name_end = name_start + name_length - 1

# Read name bytes (excluding null terminator)
name_bytes = data[name_start:name_end]
name_raw = name_bytes.decode('ascii')  # ASCII per spec, not latin-1
name = self._clean_string(name_raw)

# Now parse remaining fields starting after the null terminator
field_start = name_start + name_length

# Read all remaining fields
data_layout = TableDataLayout(data[field_start + 0])
flags = data[field_start + 1]
insert_delete_rule = data[field_start + 2]
enter_action_rule = data[field_start + 3]
color_rule = data[field_start + 4]
address = struct.unpack('<H', data[field_start + 5:field_start + 7])[0]
column_count = struct.unpack('<H', data[field_start + 7:field_start + 9])[0]  # 2 BYTES
row_count = struct.unpack('<H', data[field_start + 9:field_start + 11])[0]    # 2 BYTES
visible_rows = data[field_start + 11]

# Move to next descriptor
pos = field_start + 12
```

---

## Impact Analysis

### Symptom: Driver Names with Control Characters
When the driver name contains bytes that look like control characters (0x0F, 0x0C, etc.):
- Current parser: Reads them correctly but displays with [0xNN] notation
- Issue: These are VALID ASCII characters in some encodings, not truly control characters
- Real issue: Should use proper ASCII decoding, not latin-1 with cleaning

### Symptom: Table Names Showing Corrupted Data
The garbled table names like `"[0x0C]C[0x0F][0x0D]..."`:
- This is the name length field (0x0C) being read as part of the name!
- Parser reads from `pos + 2` (name start) but should read name length first
- The "C" is probably the first character of the actual table name
- The [0x0F], [0x0D] are other fields being misinterpreted

### Symptom: Table Dimensions Wrong (0 rows, 0 columns)
- Current code reads 1-byte values for column_count and row_count
- Should read 2-byte little-endian values
- When dimensions are read incorrectly, table display shows empty

### Symptom: Memory Map Contains Non-ASCII Characters
- Driver info display uses the cleaned version with [0xNN] notation
- Actually all bytes are read correctly, just need better display
- The real problem is table descriptors having wrong offsets

---

## Correct Implementation Pattern

### Structured Parsing Function
```python
def read_table_descriptor(self, data: bytes, offset: int) -> Tuple[TableDescriptor, int]:
    """Read one table descriptor and return it with the next offset.

    Args:
        data: Complete block data
        offset: Current position in block

    Returns:
        Tuple of (descriptor, next_offset)
    """
    # Header: Type and ID
    table_type = data[offset + 0]
    table_id = data[offset + 1]

    # Name: Length-prefixed field
    name_length = data[offset + 2]  # Includes null terminator
    name_bytes = data[offset + 3:offset + 3 + name_length - 1]
    table_name = name_bytes.decode('ascii')  # Use ASCII, not latin-1

    # Position after name (including its null terminator)
    field_offset = offset + 3 + name_length

    # Remaining fields at fixed offsets from field_offset
    data_layout = TableDataLayout(data[field_offset + 0])
    flags = data[field_offset + 1]
    insert_delete_rule = data[field_offset + 2]
    enter_action_rule = data[field_offset + 3]
    color_rule = data[field_offset + 4]
    address = struct.unpack('<H', data[field_offset + 5:field_offset + 7])[0]
    column_count = struct.unpack('<H', data[field_offset + 7:field_offset + 9])[0]  # 2 bytes!
    row_count = struct.unpack('<H', data[field_offset + 9:field_offset + 11])[0]    # 2 bytes!
    visible_rows = data[field_offset + 11]

    # Create descriptor
    descriptor = TableDescriptor(
        type=table_type,
        id=table_id,
        name=table_name,  # No cleaning needed if properly parsed
        data_layout=data_layout,
        address=address,
        column_count=column_count,
        row_count=row_count,
        properties=flags,
    )

    # Return descriptor and next offset (12 bytes of fixed fields)
    return descriptor, field_offset + 12
```

---

## Summary of Required Fixes

| Bug | Location | Fix | Impact |
|-----|----------|-----|--------|
| Missing name_length read | Line 383-394 | Read `name_length = data[pos + 2]` | Table names corrupted |
| Wrong name_start offset | Line 386 | Change to `pos + 3` | Name parsing offset |
| Wrong field offsets | Line 399-411 | Calculate from `field_start = pos + 3 + name_length` | Wrong field values |
| 1-byte dimensions | Line 410-411 | Use `struct.unpack('<H', ...)` for both | Table data empty |
| Wrong pos increment | Line 430 | Change to `pos = field_start + 12` | Parser misalignment |
| ASCII vs Latin-1 | Line 392 | Use `'ascii'` not `'latin-1'` | Encoding correctness |

---

## Test Case: Laxity - Stinsen - Last Night Of 89.sf2

Expected results after fix:
```
Table 0: Instruments (dimensions correct, not [0x0C]C...)
Table 1: Commands
Table 2: Arpeggio (or proper identification)
Table 6: Wave
...
All dimensions parsed as 2-byte values
Driver name clean without [0xNN] in valid ASCII range
```

---

## References

- **SF2 Format Spec**: `C:\Users\mit\claude\c64server\SIDM2\docs\SF2_FORMAT_SPEC.md`
- **Header Block Analysis**: `C:\Users\mit\claude\c64server\SIDM2\docs\SF2_HEADER_BLOCK_ANALYSIS.md`
- **Source Code**: `C:\Users\mit\claude\c64server\SIDM2\sf2_viewer_core.py` lines 370-430
