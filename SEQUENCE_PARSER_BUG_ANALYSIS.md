# Sequence Parser Bug Analysis

## Problem Statement

**User Issue**: SF2 Viewer shows different Track 3 data than SID Factory II editor

- **SID Factory II shows**: "a00a 0b -- F-3", "-- -- +++", etc. (correct)
- **SF2 Viewer shows**: Chromatic scales (D-3, F-3, G#-3, B-3...) (wrong)
- **File**: `learnings/Laxity - Stinsen - Last Night Of 89.sf2`

## Root Cause Identified

**Parser only finds 3 sequences but OrderList references 11 sequences!**

- **OrderList uses**: Sequences 0, 1, 2, 3, 4, 5, 6, 11, 12, 14, 15 (11 unique)
- **Parser found**: Only sequences 0, 1, 2
- **Missing**: Sequences 3, 4, 5, 6, 11, 12, 14, 15

## Key Findings

### 1. User's Screenshot is from SID Factory II Editor

The screenshot showing "a00a 0b -- F-3" is from **SID Factory II editor**, not the SF2 Viewer. The "a00a" likely means sequence 0x0A (10 decimal).

### 2. Found the Actual Data Pattern

Searched for instrument 0xAB (packed format for instrument 0x0B) + note 0x29 (F-3):

```
Found at file offset 0x2465:
  AB 81 29 C2 7E 29
  |  |  |  |  |  |
  |  |  |  |  |  +-- F-3 again
  |  |  |  |  +-- 0x7E = "+++" (gate on)
  |  |  |  +-- Command 0xC2
  |  |  +-- F-3 note
  |  +-- Command 0x81
  +-- Instrument 0x0B
```

This matches the pattern "0b -- F-3" followed by "-- -- +++"!

### 3. Sequence Pointer Table Location

Found potential pointer table at offset **0x16D2** with 16 entries:
- Sequences 0-8: 0xE1E1 (padding)
- Sequence 9: mem=0x27E1, file=0x1A63
- Sequence 10: mem=0x2928, file=0x1BAA
- Sequence 11: mem=0x2B2A, file=0x1DAC
- Etc.

**BUT**: Sequence 10's pointer (0x1BAA) contains all zeros, not the "AB 81 29" pattern at 0x2465!

### 4. Current Parser Method is Broken

`sf2_viewer_core.py::_parse_packed_sequences_laxity_sf2()`:
- Does **linear sequential scan** from offset ~0x1772
- Finds first few sequences that happen to be stored sequentially
- Stops after finding 3 sequences
- **Ignores the sequence pointer table completely!**

## Next Steps to Fix

### Step 1: Find Correct Sequence Pointer Table

The pointer table at 0x16D2 might not be the correct one, or there might be multiple pointer tables (one for OrderList, one for actual sequences). Need to:

1. Check SID Factory II source code for how it reads sequence pointers
2. Examine file structure more carefully around 0x1600-0x1800
3. Look for index table that maps OrderList sequence indices to pointer table offsets

### Step 2: Implement Proper Sequence Parser

Replace linear scan with:
```python
def _parse_sequences_using_pointer_table():
    1. Find sequence pointer table offset (from MusicData block or fixed location)
    2. Read N pointers (16 or 32) from table
    3. For each non-padding pointer:
       - Convert memory address to file offset
       - Read sequence data from that offset
       - Unpack using existing unpack_sequence()
       - Store in sequences dict with correct index
    4. Return complete sequences dict
```

### Step 3: Handle Multiple Sequence Formats

SID Factory II might support:
- **Packed sequences** (current format with 0xA0-0xFF bytes)
- **Unpacked sequences** (3-byte entries: inst, cmd, note)
- **Hybrid formats** (Laxity driver specific)

Need to detect format and parse accordingly.

### Step 4: Verify Against SID Factory II Display

Once parser is fixed:
1. Open file in both SID Factory II and SF2 Viewer
2. Compare Track 3 for each sequence
3. Verify match for sequence 0x0A specifically
4. Run comparison test: `python compare_track3_flexible.py ...`

## Files to Update

1. **sf2_viewer_core.py**:
   - Fix `_parse_packed_sequences_laxity_sf2()`
   - Add `_find_sequence_pointer_table()`
   - Add `_parse_sequence_from_pointer()`

2. **test_track3_comparison.py**:
   - Update to handle sequence 0x0A
   - Add validation for all 11 sequences from OrderList

3. **Documentation**:
   - Document sequence pointer table format
   - Update SF2_FORMAT_SPEC.md with findings

## References

- **File**: `learnings/Laxity - Stinsen - Last Night Of 89.sf2`
- **MusicData block**: Offset 0x015F, contains addresses
- **Potential pointer table**: Offset 0x16D2
- **Sequence 0x0A data**: File offset 0x2465
- **User's track_3.txt**: Reference for expected Track 3 output

## Questions to Answer

1. Why does pointer table at 0x16D2 point to 0x1BAA (zeros) instead of 0x2465 (actual data)?
2. Are there multiple pointer tables?
3. Is there an index table that maps OrderList indices to pointer table offsets?
4. How does SID Factory II determine which sequence to display?
5. What does "a00a" really mean in the GUI display?

## Status

- **Bug identified**: ✅ Parser finds only 3/11 sequences
- **Data pattern found**: ✅ Sequence 0x0A at offset 0x2465
- **Pointer table found**: ⚠️ Points to wrong location
- **Fix implemented**: ❌ Not yet
- **Verified**: ❌ Not yet

**Next action**: Study SID Factory II source code to understand exact sequence pointer table format and parsing algorithm.
