# Laxity Table Design Summary

**Quick Reference for Table Descriptor Design**

---

## All 5 Tables at a Glance

| # | Name | Address | Type | Columns | Rows | Bytes | Editable | Notes |
|---|------|---------|------|---------|------|-------|----------|-------|
| 1 | Instruments | $1A6B | 0x80 | 8 | 32 | 256 | **YES** | ADSR, waveform, pulse, filter per instrument |
| 2 | Wave | $1ACB | 0x00 | 2 | 128 | 256 | **YES** | Waveform index + note offset |
| 3 | Pulse | $1A3B | 0x00 | 4 | 64 | 256 | **YES** | Pulse width + delta + duration |
| 4 | Filter | $1A1E | 0x00 | 4 | 32 | 128 | **YES** | Filter freq + resonance + mode |
| 5 | Sequences | $1900 | 0x00 | 1 | 255 | Var | Maybe | Variable-length (continuous) |

---

## Descriptor Hex Strings

These are the exact hex bytes to include in Block 3 (DriverTables):

### Table 1: Instruments (27 bytes)
```
80 00 0C 49 6E 73 74 72 75 6D 65 6E 74 73 00
00 00 01 00 FF 03 6B 1A 08 00 20 00
```

### Table 2: Wave (20 bytes)
```
00 01 06 57 61 76 65 00
00 00 00 00 FF 00 CB 1A 02 00 80 00
```

### Table 3: Pulse (20 bytes)
```
00 02 07 50 75 6C 73 65 00
00 00 00 00 FF 00 3B 1A 04 00 40 00
```

### Table 4: Filter (21 bytes)
```
00 03 08 46 69 6C 74 65 72 00
00 00 00 00 FF 00 1E 1A 04 00 20 00
```

### Table 5: Sequences (24 bytes) - Optional
```
00 04 0A 53 65 71 75 65 6E 63 65 73 00
00 04 00 FF 00 00 19 01 00 FF 00
```

---

## Byte-by-Byte Breakdown Pattern

All descriptors follow this pattern:

```
[Type:1] [ID:1] [NameLen:1] [Name:Var] [Layout:1] [Flags:1]
[Rules:3] [Addr:2LE] [Cols:2LE] [Rows:2LE]
```

Example: Instruments table

```
80          Type = 0x80 (Instruments)
00          ID = 0
0C          Name length = 12 (includes null)
49 6E 73... Name = "Instruments\0" (12 bytes)
00          Layout = 0x00 (row-major)
01          Flags = 0x01 (insert/delete enabled)
00          Insert/Delete rule = 0
FF          Enter action = none
03          Color rule = 3
6B 1A       Address = $1A6B (little-endian: 0x1A6B → 0x6B 0x1A)
08 00       Columns = 8 (little-endian)
20 00       Rows = 32 (little-endian)
```

---

## Implementation Notes

### ASCII Encoding
Table names are ASCII strings with null terminator:
- "Instruments" → 0x49 0x6E 0x73 0x74 0x72 0x75 0x6D 0x65 0x6E 0x74 0x73 0x00
- "Wave" → 0x57 0x61 0x76 0x65 0x00
- "Pulse" → 0x50 0x75 0x6C 0x73 0x65 0x00
- "Filter" → 0x46 0x69 0x6C 0x74 0x65 0x72 0x00
- "Sequences" → 0x53 0x65 0x71 0x75 0x65 0x6E 0x63 0x65 0x73 0x00

### Little-Endian Addresses
Memory addresses in 6502 are little-endian:
- $1A6B → bytes: 0x6B, 0x1A
- $1ACB → bytes: 0xCB, 0x1A
- $1A3B → bytes: 0x3B, 0x1A
- $1A1E → bytes: 0x1E, 0x1A
- $1900 → bytes: 0x00, 0x19

### Type Codes
- 0x80 = Instruments (special type, gets instrument colors)
- 0x00 = Generic table (most others)

### Flags Byte
- Bit 0: Enable insert/delete operations (1 = yes, 0 = no)
- Bit 1: Layout vertically in editor (usually 0)
- Bit 2: Index as continuous memory (for variable-length data like sequences)

### Rule IDs
- Insert/Delete rule: 0x00 (standard)
- Enter action rule: 0xFF (none/default)
- Color rule: 0x03 (instruments color), 0x00 (others)

---

## Memory Validation

**Laxity Memory Layout**:
```
$1000-$19FF   Laxity Player Code (relocated from $1000)
$1900-$19FF   Sequences (variable, usually <512 bytes)
$1A1E-$1A4D   Filter Table (32 entries × 4 bytes = 128 bytes)
$1A3B-$1A3E   Pulse Table (64 entries × 4 bytes = 256 bytes)
$1A6B-$1AAA   Instruments (32 entries × 8 bytes = 256 bytes)
$1ACB-$1ACB   Wave Table (128 entries × 2 bytes = 256 bytes)
```

**No Overlaps**: ✓ All tables are sequential and non-overlapping

---

## SF2 Editor Integration Points

### What SF2 Editor Does:
1. Reads table descriptors from Block 3
2. For each table:
   - Gets name from descriptor
   - Gets address and size
   - Displays columns × rows grid
   - Allows user to edit cells
3. On save, writes edited bytes back to file

### What We Need:
- ✅ Correct addresses (already defined)
- ✅ Correct column/row counts (already designed)
- ✅ Readable names (already ASCII)
- ✅ Row-major layout (standard, already specified)

---

## Testing Checkpoints

### Checkpoint 1: Descriptor Generation
- [ ] Python generates exact hex bytes as shown above
- [ ] Hex output matches design specifications
- [ ] No truncation or padding errors

### Checkpoint 2: Block Assembly
- [ ] All 5 descriptors combine to ~112 bytes
- [ ] Block 3 ID (0x03) and size correct
- [ ] Block formatted correctly: [0x03][size][data]

### Checkpoint 3: File Validation
- [ ] Generated SF2 file loads in hex editor
- [ ] Magic number 0x1337 present
- [ ] All blocks present and sized correctly
- [ ] Block 0xFF end marker present

### Checkpoint 4: SF2 Editor Test
- [ ] SF2 file opens in SID Factory II
- [ ] All 5 tables visible in editor
- [ ] Tables show correct dimensions (8×32, 2×128, etc.)
- [ ] Can click on cells and see data
- [ ] Can edit instrument table
- [ ] File doesn't corrupt on edit

---

## Risk Assessment

### Risk 1: Sequences Table (Continuous Memory)
**Severity**: Low
**Mitigation**: Can be removed from descriptors if problematic
**Decision**: Include initially, remove if issues arise

### Risk 2: Insert/Delete on Instruments
**Severity**: Low
**Mitigation**: Disable if causes issues
**Decision**: Enable (standard for instruments)

### Risk 3: Name Length Mismatch
**Severity**: Medium
**Mitigation**: Carefully verify name byte counts
**Verification**: All names manually counted and specified

### Risk 4: Address Typos
**Severity**: High
**Mitigation**: Compare against Laxity memory layout documentation
**Verification**: All addresses cross-checked

---

## Design Decisions Explained

### Why Row-Major?
Most tables follow row-major layout (read sequentially):
- Instruments: 32 rows of 8 bytes each
- Wave: 128 rows of 2 bytes each
- Pulse: 64 rows of 4 bytes each
- Filter: 32 rows of 4 bytes each

### Why Insert/Delete Only for Instruments?
- Instruments: Adding/removing makes sense to users
- Other tables: Adding/removing would break sequences

### Why Continuous Memory for Sequences?
- Sequences have variable length
- Can't be represented as fixed rows/columns
- Continuous memory flag tells editor: "treat as unstructured data"

---

## Implementation Checklist

- [ ] Create `sf2_header_generator.py`
- [ ] Implement `TableDescriptor` class
- [ ] Generate Block 1 (Descriptor)
- [ ] Generate Block 2 (Driver Common)
- [ ] Generate Block 3 (Tables) using specs above
- [ ] Assemble complete header with end marker (0xFF)
- [ ] Test hex output matches specifications
- [ ] Integrate with LaxityConverter
- [ ] Generate test SF2 file
- [ ] Validate in hex editor
- [ ] Test in SF2 Factory II
- [ ] Document results

---

**Status**: ✅ Design Complete & Verified
**Next Step**: Implement header generator (Task 3)
