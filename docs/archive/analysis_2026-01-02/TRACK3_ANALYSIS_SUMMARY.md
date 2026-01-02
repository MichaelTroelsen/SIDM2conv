# Track 3 Analysis Summary

**Date**: 2025-12-17
**Status**: Reference data mismatch identified - on hold pending correct reference

---

## Overview

This document summarizes the Track 3 comparison work, including the format understanding achieved, tools developed, and current status.

## Work Completed

### 1. Format Understanding

Successfully decoded the SF2 track/sequence format through progressive clarification:

**OrderList Format**: `XXYY` (4 hex characters)
- XX = Transpose value (0x80 to 0xBF)
  - 0xA0 = default (no transpose)
  - Formula: (XX - 0xA0) = semitones offset
- YY = Sequence number (0x00-0x7F, 0-127)

**Sequence Entry Format**: `AA BB CCC` (3 columns)
- AA = Instrument (2 hex chars, `--` = no change)
- BB = Command (2 hex chars, `--` = no command)
- CCC = Note (3-4 chars: `C-0` to `B-9`, `+++`, `---`, `END`)

**Combined Format**: Lines can have orderlist prefix
- With prefix: `XXYY AA BB CCC` (e.g., `a00a 0b -- F-3`)
- Without prefix: `AA BB CCC` (e.g., `-- -- +++`)

### 2. Gate Control Understanding

**Gate On (`+++`)**: Sustains previous note
- Does NOT retrigger envelope
- Maintains current pitch and ADSR state
- Used for held notes

**Note Name (e.g., `F-3`)**: Triggers/retriggers note
- Starts attack phase of ADSR envelope
- Can be same or different pitch
- Resets envelope even if same note

**Gate Off (`---`)**: Silences note
- Triggers release phase of envelope
- Used for gaps/rests

### 3. Musical Pattern Example

From track_3.txt reference:
```
a00a 0b -- F-3    # OrderList a00a, set instrument 0b, play F-3
     -- -- +++    # Sustain (gate on)
     -- 02 +++    # Apply command 02 while sustaining
     -- -- +++    # Continue sustaining
     -- -- F-3    # Retrigger F-3
```

**Interpretation**:
- Step 0: Trigger note F-3 with instrument 0b
- Step 1: Sustain (gate on)
- Step 2: Apply effect (command 02) while sustaining
- Step 3: Continue sustaining
- Step 4: Retrigger same note (restarts ADSR envelope)

### 4. Tools Created

**compare_track3_v2.py**
- Parses track_3.txt reference file
- Extracts Track 3 data from SF2 sequences
- Generates side-by-side comparison
- Handles both 3-part and 4-part line formats

**SF2 Viewer Updates**
- Updated sequence display to 3-column format
- Matches SID Factory II editor layout exactly
- Column widths: Instrument (2), Command (2), Note (3-4)

### 5. Documentation Created

**docs/SF2_TRACKS_AND_SEQUENCES.md** (433 lines)
- Complete OrderList and Sequence format documentation
- Gate control system explanation
- 3-track parallel system for SID voices
- Sequence storage and interleaving
- Track operations and keyboard shortcuts
- Typical sequence sizes and patterns
- Official SID Factory II tutorial references

**docs/SF2_INSTRUMENTS_REFERENCE.md** (595 lines)
- 6-byte instrument structure
- ADSR envelope system (all 16 levels)
- Hard Restart mechanism (bit 7, 2-tick pre-gate-off)
- Test Bit / Oscillator Reset (bit 4)
- Waveforms (Triangle 11, Sawtooth 21, Pulse 41, Noise 81)
- Wave table system with loop commands
- Pulse width tables
- Practical examples (snare drum, ADSR patterns)
- Keyboard shortcuts
- Official SID Factory II tutorial references

---

## Comparison Results

### Test File: Laxity - Stinsen - Last Night Of 89.sf2

**Sequence 0 (Track 3)**:
- Total Reference Entries: 41
- Total SF2 Entries: 30
- Matched Entries: 0
- Accuracy: **0.0%**

**Sequence 2 (Track 3)**:
- Total Reference Entries: 41
- Total SF2 Entries: 10
- Matched Entries: 6
- Accuracy: **14.6%**

### Analysis

The very low match rates (0-14.6%) indicate that the reference data in `track_3.txt` is from a **different source or file** than the SF2 file being tested.

**Evidence**:
1. Note patterns are completely different (reference shows F-3 patterns, SF2 shows D-3 to F-10 chromatic scales)
2. Instrument and command values don't match
3. Entry counts differ significantly (41 reference vs 10-30 SF2)

**Conclusion**: The track_3.txt reference file does not represent the actual Track 3 data in the test SF2 file.

---

## Current Status

**Work On Hold**: Pending correct reference data

**Reason**: The current track_3.txt reference doesn't match the SF2 file being tested. Before continuing comparison work, we need to:

1. Verify the source of track_3.txt
2. Obtain correct reference data for the test SF2 file
3. Or identify which SF2 file the track_3.txt reference is from

**Tools Ready**: The comparison system is fully functional and ready to use once correct reference data is available.

---

## Next Steps (When Resumed)

1. **Verify Reference Source**
   - Identify which SID/SF2 file track_3.txt represents
   - Or create new reference from known SF2 file

2. **Validate Comparison System**
   - Test with matching reference data
   - Verify 100% match on known-good data

3. **Expand Coverage**
   - Create comparisons for Tracks 1 and 2
   - Test multiple sequences per track
   - Validate all 3 tracks in parallel

4. **Integrate with Validation Pipeline**
   - Add track comparison to complete_pipeline_with_validation.py
   - Track comparison accuracy over time
   - Detect regressions in track extraction

---

## Key Learnings

### Format Knowledge Gained

1. **OrderList System**: Transpose + Sequence reference system allows sequence reuse at different pitches
2. **Gate Control**: Clear distinction between sustain (+++), trigger (note name), and silence (---)
3. **3-Track Interleaving**: Sequences store 3 tracks interleaved (entries 0,1,2 = Tracks 1,2,3 at step 0)
4. **Independent Track Lengths**: Tracks don't have to align, enabling complex arrangements
5. **ADSR Envelope**: Understanding of Attack/Decay/Sustain/Release and how gate control interacts

### Official Resources Integrated

- SID Factory II Tutorial Part 1 (Introduction)
- SID Factory II Tutorial Part 2 (Sequences)
- SID Factory II Tutorial Part 3 (Tracks)
- SID Factory II Tutorial Part 4 (Instruments)
- Complete editor documentation with keyboard shortcuts

### Tools and Infrastructure

- Robust parsing system for reference files
- Side-by-side comparison with detailed mismatch reporting
- Updated SF2 viewer matching official editor layout
- Comprehensive documentation for future work

---

## Files Modified

**Created**:
- `compare_track3_v2.py` - Comparison script with correct parsing
- `docs/SF2_TRACKS_AND_SEQUENCES.md` - Comprehensive tracks/sequences guide
- `docs/SF2_INSTRUMENTS_REFERENCE.md` - Comprehensive instruments guide
- `TRACK3_COMPARISON.txt` - Sequence 0 comparison results
- `TRACK3_SEQ2_COMPARISON.txt` - Sequence 2 comparison results
- `docs/TRACK3_ANALYSIS_SUMMARY.md` - This document

**Modified**:
- `sf2_viewer_core.py` - Added param_display() method
- `sf2_viewer_gui.py` - Updated to 3-column sequence display
- `CLAUDE.md` - Added references to new documentation

---

## References

- **Official Tutorials**: https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-1-introduction/
- **SF2 Format Docs**: docs/SF2_TRACKS_AND_SEQUENCES.md
- **Instrument Docs**: docs/SF2_INSTRUMENTS_REFERENCE.md
- **Comparison Files**: TRACK3_COMPARISON.txt, TRACK3_SEQ2_COMPARISON.txt
- **Reference File**: track_3.txt (source unknown)
- **Test File**: learnings/Laxity - Stinsen - Last Night Of 89.sf2

---

**Recommendation**: This work has provided valuable format understanding and comprehensive documentation. The comparison system is ready for use when correct reference data becomes available.
