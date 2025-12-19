# Track 3 Unpacker Fix - Summary

## Problem Solved

**Issue**: SF2 Viewer unpacker was carrying over instrument and command values across multiple events, causing incorrect display.

**Example Before Fix**:
```
Entry 0: inst=0B, cmd=--, note=F-3  ✓ (correct)
Entry 1: inst=--, cmd=--, note=+++  ✓ (correct)
Entry 2: inst=0B, cmd=02, note=+++  ✗ (wrong - should be: --, 02, +++)
Entry 3: inst=--, cmd=--, note=+++  ✓ (correct)
```

**Fix Applied** (sf2_viewer_core.py:326-329):
```python
# Reset instrument and command after using them
# They should only appear on the step where they're set, then revert to "no change" (0x80)
current_instrument = 0x80
current_command = 0x80
```

**Result After Fix**:
```
Entry 0: inst=0B, cmd=--, note=F-3  ✓
Entry 1: inst=--, cmd=--, note=+++  ✓
Entry 2: inst=--, cmd=02, note=+++  ✓ (now correct!)
Entry 3: inst=--, cmd=--, note=+++  ✓
```

## Remaining Issue

**Core Problem**: Parser sequence numbering doesn't match SID Factory II sequence numbering.

### What We Know

1. **Sequence Pointer Table is Invalid**:
   - Located at file offset 0x16D2
   - Sequence 10 pointer → file offset 0x1BAC (contains all zeros)
   - Table is not being used by SF2 file

2. **Parser Uses Scan-Based Indexing**:
   - Scans file for 0x7F terminators
   - Assigns indices 0, 1, 2, ... in scan order
   - Found 22 sequences total
   - **NOT** based on official sequence numbers

3. **Best Match Results**:
   - Reference: 41 steps (from SID Factory II, sequence 0x0A, Track 3)
   - Parser sequence 6: 42 steps, 42.9% match rate
   - Parser sequence 21: 42 steps, 42.9% match rate
   - Parser sequence 10: 10 steps, 14.6% match rate

4. **Data Mismatch**:
   Even sequence 6 (best match) shows completely different data:
   ```
   Extracted Step 0: -- -- +++     Reference Step 0: 0b -- F-3
   Extracted Step 2: 02 -- C-2     Reference Step 2: -- 02 +++
   Extracted Step 4: 01 -- F-1     Reference Step 4: -- -- F-3
   ```

### Hypothesis

**The file stores sequences in a different order than SID Factory II expects!**

Possible explanations:
1. **Multiple sequence tables**: File has both Laxity-native table and SF2 table
2. **Different numbering scheme**: SID Factory II uses a different mapping
3. **OrderList indirection**: Sequence 0x0A in OrderList doesn't directly map to file sequence 10
4. **Separate track storage**: Tracks might be stored separately, not interleaved

## Next Steps

### Option 1: Decode OrderList Structure
- Parse OrderList to understand how it maps to sequences
- Check if "a00a" references a different sequence table
- Verify OrderList format for Laxity SF2 files

### Option 2: Check SID Factory II Source Code
- Review how SF2 editor reads Laxity files
- Check sequence numbering/indexing logic
- Understand OrderList → sequence mapping

### Option 3: Test All Sequences Against Reference
- Extract Track 3 from ALL 22 sequences
- Compare each against full reference (not just first 10 steps)
- Find sequence with highest match across all 41 steps

### Option 4: Examine User's SF2 Viewer Screenshot
- User showed screenshot of SF2 Viewer displaying sequence 0x0A correctly
- Check which parser sequence index corresponds to what user saw
- Verify the mapping in SF2 Viewer GUI

## Files Modified

- **sf2_viewer_core.py** (lines 326-329): Added instrument/command reset after each event

## Files Created

- **test_sequence_format.py**: Test script for sequence display
- **SEQUENCE_MAPPING_INVESTIGATION.md**: Detailed analysis of sequence mapping issue
- **TRACK3_FIX_SUMMARY.md**: This file

## Test Results

### Before Fix
- Sequence 10: 14.6% match (10 steps vs 41 reference)
- Sequence 6: 42.9% match (42 steps vs 41 reference)
- Instruments and commands carried over incorrectly

### After Fix
- Sequence 10: 14.6% match (still wrong sequence)
- Sequence 6: 42.9% match (still different data)
- Instruments and commands now display correctly

**Conclusion**: Fix improved display accuracy, but sequence mapping issue remains unsolved.

## Status

- ✅ **FIXED**: Unpacker instrument/command carryover bug
- ✅ **VERIFIED**: Fix works correctly for sequence display
- ❌ **UNSOLVED**: Sequence numbering mismatch between parser and SID Factory II
- ❌ **BLOCKED**: Cannot verify Track 3 matches until correct sequence is identified

## Recommendations

1. **Immediate**: Parse OrderList structure to understand sequence mapping
2. **Short-term**: Check SID Factory II source for Laxity file handling
3. **Long-term**: Implement proper sequence table detection for all SF2 file types
