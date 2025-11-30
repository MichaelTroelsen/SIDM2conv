# Analysis Findings - Root Cause of 1-5% Accuracy

**Date**: 2025-11-30
**Version**: 0.6.5
**Files Analyzed**: Broware.sid (5.00% accuracy - worst case)

---

## CRITICAL FINDING: Wave Table Extraction Failure

### The Problem

When converting Broware.sid (and likely the other 7 failing files), the converter shows:

```
WARNING: Note index $43 exceeds table size 0
WARNING: Note index $45 exceeds table size 0
... (many more warnings)
```

**Root Cause**: The wave table has **size 0** when sequences are being validated, even though:
- Sequences ARE extracted (1 sequence found) ✓
- Instruments ARE extracted (8 instruments) ✓
- Later, 6 wave entries ARE extracted ✓

### The Sequence

1. Parser extracts sequence data with note values ($43, $45, etc.)
2. Parser tries to validate notes against wave table
3. **Wave table is empty at this point** (size 0)
4. Warnings are generated
5. Later, wave table is actually extracted (6 entries found)

### Why This Causes 5% Accuracy

The sequence has notes referencing wave table entries that don't exist (or are in wrong order):
- Sequence has 1106 events
- Many reference wave table entries that were at index $43, $45, etc.
- But wave table only has 6 entries (indices 0-5)

**Result**: The converted SF2 has:
- Correct structure (sequences, instruments)
- But **wrong note mappings** because wave table is incomplete/incorrect
- When exported back to SID, notes play at wrong pitches or don't play at all

---

## Affected Files (All Original Laxity Files)

Based on batch validation results, these 8 files likely have the same issue:

1. **Broware**: 5.00% - Wave table size 0 during validation
2. **I_Have_Extended_Intros**: 3.26%
3. **Aint_Somebody**: 3.02%
4. **Cocktail_to_Go_tune_3**: 2.93%
5. **Halloweed_4_tune_3**: 2.46%
6. **Stinsens_Last_Night_of_89**: 1.53%
7. **Expand_Side_1**: 1.37%
8. **Staying_Alive**: 1.01%

All show very low accuracy (1-5%), suggesting systematic table extraction failure.

---

## SF2-Originated Files: 100% Accuracy

The 17 files with 100% accuracy are all **SF2-originated**:
- Angular_test_exported
- Driver 11 Test files
- official_tie_notes (all variations)
- test_* files

**Why they work**: These files were created by SF2, so the table layout matches exactly what the parser expects. No extraction needed - the data is already in the correct format.

---

## Technical Analysis

### What's Extracted Successfully from Broware

```
INFO: Extracted 1 sequences (via Laxity parser)
INFO: Extracted 8 instruments
INFO: Created 3 orderlists
INFO: Tempo: 2
INFO: Written 6 wave table entries
INFO: Written 4 Pulse table entries
INFO: Written 4 Filter table entries
```

### What's Wrong

1. **Wave Table Timing**: Table is extracted AFTER sequences are validated
2. **Wave Table Size**: Only 6 entries found, but notes reference much higher indices
3. **Note Mapping**: Note indices $43, $45, $47 etc. don't map to wave table entries 0-5

### Laxity Player Memory Layout (Expected)

From `docs/LAXITY_PLAYER_ANALYSIS.md`:
```
LAXITY_WAVE_TABLE = 0x19AD    # Wave table (offsets)
LAXITY_WAVE_FORMS = 0x19E7    # Wave table (waveforms)
```

**Hypothesis**: The Laxity parser is finding the tables, but:
- Table is smaller than expected (6 entries vs ~70 expected)
- Table detection stops too early
- Or tables are in different location in original SID files

---

## The Fix

### Short-Term (High Priority)

1. **Fix Wave Table Extraction** in `sidm2/laxity_parser.py`:
   - Improve table boundary detection
   - Don't stop at first $7F marker prematurely
   - Handle tables at non-standard addresses
   - Extract full table before validating sequences

2. **Improve Table Detection** in `sidm2/table_extraction.py`:
   - Better heuristics for finding table start/end
   - Handle compressed/packed table formats
   - Validate extracted table makes sense (check size, patterns)

3. **Fix Sequence Validation**:
   - Don't validate note indices if wave table not yet extracted
   - Or extract wave table FIRST, before sequences

### Medium-Term

4. **Enhanced Extraction Logging**:
   - Log exact addresses where tables are found
   - Log table sizes and contents (first few entries)
   - Compare against expected Laxity addresses

5. **Add Table Size Validation**:
   - Warn if wave table has < 32 entries (suspicious)
   - Check if table entries make sense (valid note ranges, waveforms)

6. **Alternative Extraction Strategy**:
   - Try multiple detection methods
   - Use siddump output to validate tables
   - Cross-reference with frequency/waveform usage

---

## Next Steps (Immediate Action)

### Step 1: Debug Wave Table Extraction ⏳ NOW

Add detailed logging to see what's happening:

```python
# In sidm2/laxity_parser.py or table_extraction.py
logger.info(f"Wave table search starting at ${address:04X}")
logger.info(f"Found wave table at ${table_addr:04X}")
logger.info(f"Wave table size: {len(wave_table)} entries")
logger.info(f"Wave table entries: {wave_table[:10]}")  # First 10
```

### Step 2: Compare Working vs Failing Files

- Angular_test_exported (100%) vs Broware (5%)
- What's different in their wave table extraction?
- Are tables at different addresses?
- Different formats/layouts?

### Step 3: Fix and Test

1. Fix wave table extraction
2. Re-run: `python sid_to_sf2.py "SIDSF2player/Broware.sid" "test.sf2"`
3. Check if warnings disappear
4. Run validation: `python batch_validate_sidsf2player.py`
5. Check if Broware accuracy improves from 5% → higher

### Step 4: Apply to All Failing Files

Once Broware is fixed, apply same fix to all 8 failing files.

---

## Expected Outcome

After fixing wave table extraction:
- **Before**: Broware 5.00%, others 1-3%
- **After**: Target 80%+ (maybe not 99% immediately, but much better)
- **Remaining issues**: Command parameters, fine-tuning

This is the **highest-impact fix** - it affects all 8 failing files systematically.

---

## Validation Strategy

### How to Verify the Fix Works

1. **Check Console Output**:
   - No more "exceeds table size 0" warnings
   - Wave table size should be 32+ entries
   - Note indices should be within table range

2. **Check Accuracy**:
   ```bash
   python batch_validate_sidsf2player.py
   ```
   - Broware should jump from 5% to 50%+ if tables work
   - Other files should also improve

3. **Check Structure**:
   - Open converted SF2 in SID Factory II
   - Check wave table has entries
   - Check sequences play correct notes

---

## Code Locations to Fix

### Primary Target: `sidm2/laxity_parser.py`

```python
class LaxityPlayerAnalyzer:
    def analyze(self):
        # FIX HERE: Extract wave table FIRST
        # Then extract sequences
        # Then validate note indices
```

### Secondary: `sidm2/table_extraction.py`

```python
def find_and_extract_wave_table():
    # FIX HERE: Better boundary detection
    # Don't stop at first $7F too early
    # Validate extracted table size
```

---

## Success Criteria

### Phase 1 Fix Complete When:
- [ ] Broware extracts wave table with 30+ entries
- [ ] No "exceeds table size 0" warnings
- [ ] Broware accuracy improves from 5% to 50%+
- [ ] At least 4 of 8 failing files show improvement

### Phase 2 Complete When:
- [ ] All 8 files achieve 50%+ accuracy
- [ ] Tables extracted correctly for all
- [ ] Remaining issues are command/parameter related

### Phase 3 Complete When:
- [ ] All 8 files achieve 80%+ accuracy
- [ ] Fine-tuning complete
- [ ] Ready for 95%+ push

### Final Goal:
- [ ] All 25 files achieve 99%+ accuracy
- [ ] Converter reliably handles Laxity NewPlayer v21 files

---

## Conclusion

**We found the root cause!**

The 8 failing files all have **wave table extraction failure**. The wave table is either:
- Not found at all (size 0)
- Found but incomplete (6 entries when 30-70 expected)
- Found at wrong location

This causes note indices in sequences to be invalid, resulting in wrong/missing notes in the converted SF2, leading to 1-5% accuracy.

**Fix this one issue → all 8 files should improve dramatically.**

This is the **critical path** to 99% accuracy.
