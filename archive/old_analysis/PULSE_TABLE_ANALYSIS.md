# Pulse Table Extraction Analysis - Stinsens Last Night of '89

## Summary

The pulse table extraction from `SF2packed_Stinsens_Last_Night_of_89.sid` is **INCORRECT**. The reference SF2 file shows the pulse table should be completely empty (all zeros), but the converted SF2 has 3 non-zero entries.

## Files Analyzed

1. **Original SF2-packed SID**: `SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid`
   - Load address: $1000
   - Pulse table claimed at: $09BC-$09D4 (25 bytes)

2. **Reference SF2** (correct version): `learnings/Stinsen - Last Night Of 89.sf2`
   - Load address: $0D7E
   - Pulse table at: $1B24
   - **All entries: 00 00 00 00** (no pulse modulation used)

3. **Converted SF2** (extracted): `output/Pipeline_Single/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2`
   - Load address: $0D7E
   - Pulse table at: $1B24
   - **INCORRECT entries**: 80, 06, 0F in first 3 positions

## Pulse Table Comparison

### Reference SF2 (Correct)
```Entry 00-0F: All zeros (00 00 00 00)
```

### Converted SF2 (Incorrect)
```
Entry 00: 80 00 00 00  (12-bit value: $080)Entry 01: 06 00 00 00  (12-bit value: $006)Entry 02: 0F 00 00 00  (12-bit value: $00F)Entry 03-0F: All zeros
```

## Raw Data from SF2-packed SID at $09BC

```
$09BC: 88 00 81 00 00 0F 7F 88 7F 88 0F 0F 00 7F 88 00
$09CC: 0F 00 7F 86 00 0F 00 0F 7F
```

If parsed as 3-column row-major (3 bytes per entry):
```
Entry 00: 88 00 81
Entry 01: 00 00 0F
Entry 02: 7F 88 7F
Entry 03: 88 0F 0F
Entry 04: 00 7F 88
Entry 05: 00 0F 00
Entry 06: 7F 86 00
Entry 07: 0F 00 0F
```

## Issues Identified

1. **Wrong Extraction**: The converted SF2 has values (80, 06, 0F) that don't match the reference (all zeros)

2. **Format Mismatch**: The user's image showed the SF2-packed SID has 3-column pulse data, but:
   - User showed entries 00-0F (16 entries)
   - File offset $09BC-$09D4 is only 25 bytes (8 entries at 3 bytes each)
   - This suggests either:
     - Wrong offset provided
     - Wrong table identified
     - Different table format than assumed

3. **Incorrect Interpretation**: The data at $09BC may not be pulse table data at all, or the SF2-packed format stores pulse data differently than expected

## Conclusion

**The pulse table should be completely empty for this song.** The reference SF2 confirms that Stinsens Last Night of '89 does not use pulse modulation effects. The extraction process is incorrectly identifying some other data as pulse table entries.

## Recommended Fix

The pulse table extraction code should be modified to:
1. Correctly identify when pulse modulation is not used (all zeros in reference)
2. Either extract from the correct offset in SF2-packed SIDs, or
3. Recognize that not all songs have pulse data and default to empty tables

For now, the pulse table should be manually set to all zeros to match the reference SF2 file.
