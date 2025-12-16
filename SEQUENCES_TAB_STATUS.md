# SF2 Viewer - Sequences Tab Status Report

**Date**: 2025-12-16
**Status**: DISPLAY FORMAT IMPROVED - Data Parsing Issue Identified
**Version**: 2.2.0

---

## Summary

The Sequences tab display format has been significantly improved to show **3 parallel tracks** in proper SID Factory II editor layout. However, the underlying **sequence data parsing has issues** that need further investigation.

---

## Improvements Made

### 1. SequenceEntry Class Enhancement
- Added `instrument` field to store full instrument byte (0x80, 0x90, 0xA0-0xBF)
- Added `instrument_display()` method for proper SID Factory II formatting
- Added `command_display()` method for command byte formatting
- Updated `note_name()` to handle gate off (---), sustain (+++), and note names

### 2. Unpacker Function Fix
- Modified `unpack_sequence()` to preserve full byte values
- Properly initializes instrument/command to 0x80 (no change)
- Generates sustain events (0x7E) for duration values

### 3. Parser Updates
- Updated `_parse_packed_sequences()` to store instrument in SequenceEntry
- Improved `_find_packed_sequences()` to skip 0xE1 pointer blocks
- Added fallback for traditional format sequences

### 4. GUI Display Format - **NEW 3-TRACK PARALLEL LAYOUT**

**Current Display**:
```
      Track 1              Track 2              Track 3
Step  In Cmd Note         In Cmd Note         In Cmd Note
----  ---- --- --------  ---- --- --------  ---- --- --------
0000  --  --       C-3  --  --      C#-3  --  --       D-3
0001  01  21      0xE1  --  --       +++  01  21      0xE1
0002  --  --       +++  01  21      0xE1  --  --       +++
...
```

**Features**:
- ✅ 3 parallel track display (matches SID Factory II editor)
- ✅ Clear track headers and column labels
- ✅ Proper spacing and alignment
- ✅ Shows Instrument (In), Command (Cmd), and Note for each track
- ✅ Proper formatting: "--" for no change, values in hex, notes as names

---

## Current Issues

### 1. **Data Quality Problem - 0xE1 Bytes**

**Issue**: Notes showing as `0xE1` instead of valid note values

**Root Cause**:
- File offset detection may be incorrect
- The Laxity packed format might store data differently than expected
- Data after 0x7F end marker contains sequential bytes (0x80, 0x81, 0x82...) suggesting wrong offset

**Evidence**:
- Sequence 0: Has valid notes (C-3, C#-3, D-3) followed by invalid 0xE1 bytes
- Sequence 1: Contains note values like 0x81, 0x83 (outside valid 0x01-0x7E range)
- Raw file data shows: `24 25 26 [E1 E1 E1...] 7F 80 81 82 83...`

### 2. **File Structure Understanding**

**Current Understanding**:
- 2 sequences found in Laxity file
- Each sequence divides perfectly by 3 (243 = 81×3, 918 = 306×3)
- Suggests 3 parallel tracks stored as interleaved entries

**Missing Information**:
- Exact Laxity packed sequence format specification
- How 0xE1 bytes should be interpreted (pointer table? metadata?)
- Why data after 0x7F contains sequential bytes instead of next sequence

---

## Next Steps to Fix Data Parsing

### Option 1: Review Laxity Driver Documentation
- Look for formal specification of Laxity packed sequence format
- Check if format differs from standard SID Factory II format
- Verify file offset calculations

### Option 2: Reverse Engineer from Working Data
- Use SID Factory II editor as reference
- Load the same file and analyze what it displays
- Compare byte-by-byte with our parser output

### Option 3: Investigate File Structure
- Check if 0xE1 bytes are metadata/pointers
- Verify sequence boundaries (0x7F markers)
- Look for sequence size hints in file headers

---

## Files Modified

1. **sf2_viewer_core.py**:
   - SequenceEntry class (added instrument field, display methods)
   - unpack_sequence() function (preserve full byte values)
   - _parse_packed_sequences() (store instrument data)
   - _find_packed_sequences() (skip 0xE1 pointer blocks)

2. **sf2_viewer_gui.py**:
   - on_sequence_selected() (new 3-track parallel display format)
   - Added proper spacing and alignment
   - Added track headers and column labels

---

## Test Results

### Display Format
- ✅ 3 parallel tracks displayed side-by-side
- ✅ Clear column headers and spacing
- ✅ Proper alignment and readability

### Data Quality
- ⚠️ 0xE1 bytes appearing in note fields (should not happen)
- ⚠️ Some note values > 0x7F (invalid per SF2 spec)
- ⚠️ Does not match reference SID Factory II output

---

## Verification Checklist

- [x] Display format shows 3 parallel tracks
- [x] Column headers are clear and readable
- [x] Spacing matches user expectations (improved from previous version)
- [x] Note names display correctly (where data is valid)
- [ ] Data matches SID Factory II editor (DATA PARSING ISSUE)
- [ ] No invalid byte values in note fields (DATA PARSING ISSUE)
- [ ] 0xE1 bytes properly handled or eliminated (UNKNOWN)

---

## User Feedback Summary

The user indicated:
1. **Display Format**: Needed 3 parallel track layout ✅ FIXED
2. **Spacing/Alignment**: Needed better formatting ✅ IMPROVED
3. **Data Quality**: "The data still do not match the data from the editor" ⚠️ **REQUIRES INVESTIGATION**

User recommendation: "Look at the source code from the SID Factory editor to see how it loads"

---

## Recommendations

**Immediate**:
- Investigate Laxity packed sequence format specification
- Review file offset calculation in _find_packed_sequences()
- Check if 0xE1 bytes are valid or indicate parsing error

**Follow-up**:
- Compare our output byte-by-byte with SID Factory II editor
- Verify sequence boundaries and structure
- Test with additional Laxity test files

**Documentation**:
- Create Laxity format specification document
- Document any deviations from standard SF2 format
- Include examples of properly parsed sequences

---

**Status**: DISPLAY FORMAT COMPLETE - Awaiting data parsing fixes

Generated: 2025-12-16
Last Updated: Claude Code Assistant
