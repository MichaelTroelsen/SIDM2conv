# Root Cause Analysis - WAV Rendering Failures

**Date**: 2025-12-14
**Status**: ROOT CAUSE IDENTIFIED ✅
**Issue**: 6/18 files timeout during WAV rendering, 12/18 produce silent output

---

## The Problem

When SF2 files (like Broware.sf2) are exported to PSID format and then rendered to WAV:
- Entry stubs are patched with correct addresses (Phase 2 fixed this)
- BUT pointer relocation finds ZERO addresses to relocate in the code
- Result: Pointers never get updated, player code references wrong addresses, produces no audio or hangs

---

## Root Cause Discovered

### The File Format Mismatch

**Broware.sf2 is NOT raw driver code** - it's an **SF2-formatted project file** with internal block structure.

#### SF2 File Format:
```
Offset 0-1:   PRG load address (little-endian)
Offset 2-3:   SF2 magic ID: 0x1337
Offset 4+:    Block descriptors:
              - Block type (1 byte)
              - Block size (2 bytes, little-endian)
              - Block data (N bytes)
              - Block types: 0x01, 0x02, 0x03, 0x04, 0x05, 0xFF (end)
```

**Example from Broware.sf2:**
```
File offset 0-1:   7e 0d  (0x0D7E = load address)
File offset 2-3:   37 13  (0x1337 = SF2 magic ID)
File offset 4-?:   Block descriptors describing:
                   - Driver code
                   - SF2 tables (instruments, waves, pulses, filters)
                   - Music data (sequences with 0x7F end markers)
                   - DriverCommon structure
```

#### Memory Layout After Loading:
```
Address $0D7E-$0FFF:  PRG header + SF2 block descriptors + metadata
                      (text: "Laxity NewPlayer v21 SF2", "Instruments", "Wave", etc.)

Address $1000-$1040:  FIRST BLOCK DATA (appears to be code, but contains non-valid opcodes!)
                      Bytes: a7 41 a2 18 a7 48 a4 80 11 00 a1 83 0f ...

Analysis:
- 0xA7 is not a valid 6502 opcode
- 0x7F is SF2 sequence END MARKER, not code
- This is MUSIC DATA from the SF2 block, not driver code!
```

### Why fetch_driver_code() Breaks

The `fetch_driver_code()` method in sf2_packer.py:

1. **Assumes** the file contains raw driver code at fixed addresses:
   - 0x1000-0x1040: Code section
   - 0x1040: Instruments table start
   - 0x1100: Commands table start
   - etc.

2. **In reality** for SF2 files, those addresses contain:
   - SF2 block descriptors
   - Music data (sequences)
   - Metadata

3. **Result**: Extracts garbage bytes as "code"

4. **Consequence**: scan_relocatable_addresses() finds ZERO valid 6502 instructions
   - Can't identify any relocatable pointers
   - NO pointer relocation happens
   - Player code still has broken pointers

### Evidence

**Debug script output (debug_sf2_loading.py):**
```
SF2 file: Broware.sf2
  File size: 13,008 bytes
  Load address: $0D7E
  Data size: 13,006 bytes

Memory layout:
  SF2 data byte 0 (offset 2 in file) maps to memory address $0D7E
  SF2 data byte 642 maps to memory address $1000
  This is file offset 644

First 32 bytes at $1000:
  a7 41 a2 18 a7 48 a4 80 11 00 a1 83 0f 81 00 a6 3c a7 43 a2 18 a7 48 a4 83 18 7f a1 83 1c a6 81

Analysis of pattern:
  0xA7: Not a valid 6502 opcode (INSTRUCTION_SIZES[0xA7] = 0 = unknown)
  0x7F: SF2 sequence end marker at offset 26 in this region
  Pattern: A7 41 / A7 48 / A7 43 / A7 45 (repeating 0xA7 with data)
  This looks like SF2 music data, not code!
```

**Structure analysis (analyze_broware_structure.py):**
```
First 642 bytes contain:
  - "Laxity NewPlayer v21 SF2" (SF2 file identifier)
  - "Instruments", "Wave", "Pulse" (table names)
  - Binary data (likely SF2 block descriptors)

This is NOT driver code - it's SF2 METADATA!
```

---

## What Should Happen

The SF2Packer should:

1. **Detect SF2 format** by checking for:
   - PRG load address in bytes 0-1
   - SF2 magic ID (0x1337) in bytes 2-3

2. **Parse SF2 blocks** using SF2Reader class (already exists):
   ```python
   if file_has_sf2_marker:
       reader = SF2Reader(sf2_data, load_address)
       # Properly extract driver code, tables, music data
   else:
       # Use traditional fixed-address extraction for raw driver files
   ```

3. **Extract correctly:**
   - Driver code from BLOCK_DRIVER_CODE or BLOCK_DRIVER_TABLES
   - Music data from BLOCK_MUSIC_DATA
   - Instruments from BLOCK_INSTRUMENT_DESC
   - Tables (Wave, Pulse, Filter) from appropriate blocks

4. **Relocate only code**, not SF2 metadata

---

## Current Code Issues

### sf2_packer.py - fetch_driver_code() method (lines 238-318)

**Current behavior:**
```python
def fetch_driver_code(self):
    driver_start = 0x1000

    # Hardcoded data table addresses - assumes raw driver file!
    data_tables = [
        (0x1040, 0x0C0, "Instruments"),
        (0x1100, 0x0E0, "Commands"),
        (0x11E0, 0x200, "Wave"),
        (0x13E0, 0x300, "Pulse"),
        (0x16E0, 0x300, "Filter"),
    ]
```

**Problem:**
- Works ONLY for raw driver PRG files
- Breaks completely for SF2-formatted files
- No check for SF2 format markers
- No use of SF2Reader class

### sf2_packer.py - process_driver_code() method (lines 391-494)

**Result of broken extraction:**
- Tries to relocate SF2 metadata and music data
- scan_relocatable_addresses() finds ZERO valid instructions
- Pointer relocation doesn't happen
- Player code remains broken

---

## Impact Summary

| Issue | Root Cause | Impact |
|-------|-----------|--------|
| 0 relocations found | Reading SF2 blocks instead of code | Pointers never updated |
| Silent audio (12/18 files) | Pointers broken → wrong memory refs | No SID register writes |
| Timeouts (6/18 files) | Broken code → infinite loops | Process hangs |
| Phase 2 fix ineffective | Entry stubs correct, but other pointers wrong | No improvement in results |

---

## Solution Strategy

**Two-pronged approach:**

### Option A: SF2-Aware SF2Packer (Recommended)
Modify sf2_packer.py to:
1. Detect SF2 format files
2. Use SF2Reader to properly parse the structure
3. Extract driver code, music data, and tables from correct blocks
4. Apply pointer relocation only to actual code

**Pros:**
- Proper handling of SF2 format
- Works with current conversion pipeline
- Handles both raw driver and SF2 files

**Cons:**
- Requires significant rewrite of fetch_driver_code()
- Need to understand complete SF2 block format

### Option B: Pre-process SF2 Files
Before passing to SF2Packer:
1. Parse SF2 structure using SF2Reader
2. Extract driver code and music data
3. Reconstruct as raw driver PRG format
4. Pass to existing SF2Packer

**Pros:**
- Minimal changes to SF2Packer
- Separates concerns

**Cons:**
- Extra processing step
- Need wrapper logic

---

## Files That Need Changes

- **sf2_packer.py**: fetch_driver_code() and process_driver_code() methods
- **sf2_reader.py**: Already has SF2 parsing (extend if needed)

---

## Verification

Once fixed, should see:
- All 18 files generate valid WAV files
- WAV files contain actual audio (not silent)
- No timeout issues
- scan_relocatable_addresses() finds significant number of pointer relocations

---

## Related Files

- `debug_sf2_loading.py` - Shows SF2 structure being loaded
- `analyze_broware_structure.py` - Analyzes file structure byte-by-byte
- `sidm2/sf2_reader.py` - Proper SF2 format parser (already exists)
- `sidm2/sf2_writer.py` - SF2 file creator (for reference)
- `PHASE2_COMPLETION_REPORT.md` - Phase 2 entry stub fix (necessary but insufficient)

