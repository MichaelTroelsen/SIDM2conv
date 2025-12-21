# LAXITY Conversion Accuracy Analysis

## Session Date: 2025-12-12

## Executive Summary

Player detection has been fixed (no more 0% accuracy files), but LAXITY conversions produce low accuracy (1-8%) due to incomplete table extraction. The root cause is a mismatch between statically extracted tables (incomplete) and runtime-extracted sequences (complete).

## Problem Statement

After fixing player detection in commit `617de7e`, all 18 files now process successfully, but accuracy distribution reveals a critical issue:

- **100% accuracy**: 7 files (REFERENCE/TEMPLATE methods)
- **88.32%**: 1 file (Tie Notes test)
- **1-8%**: 10 files (LAXITY method)

Files that were previously at 0% are now converting with LAXITY method but achieving only 1-8% accuracy.

## Root Cause Analysis

### The Hybrid Conversion Pipeline

The current pipeline uses a **hybrid approach**:

1. **Step 1**: Static table extraction (sid_to_sf2.py + LaxityPlayerAnalyzer)
   - Extracts: Instruments, Wave table, Pulse table, Filter table, Commands
   - For Aint_Somebody: Found only **3 pulse entries**, **2 filter entries**, **33 wave entries**

2. **Step 1.5**: Runtime sequence extraction (siddump_extractor)
   - Captures SID register writes for 10 seconds
   - Extracts: **128 sequences** with correct note/timing data
   - **Replaces** the 2 statically-extracted sequences with 128 runtime sequences

3. **Result**: **Table/Sequence Mismatch**
   - Sequences reference pulse/filter entries that don't exist in incomplete tables
   - Example: Sequence uses pulse setting #15, but only 3 pulse entries exist
   - Accuracy: 3.01%

### Why Static Extraction Finds Incomplete Tables

The `find_and_extract_pulse_table()` function (table_extraction.py:687-876) stops extraction when it hits an all-zero entry:

```python
# Line 868
if val == 0 and cnt == 0 and dur == 0 and nxt == 0 and i > 0:
    break
```

This assumes zero entries mark table end, but:
- Zeros can mean "no modulation" (valid entry)
- Laxity format may interleave zeros
- Extraction stops prematurely (only 3 entries found when more exist)

### Comparison: REFERENCE vs LAXITY

**REFERENCE Method (Driver 11 tests - 100% accuracy):**
- Has original SF2 file as template
- Extracts from **known addresses** in SF2-packed structure
- Tables: 50 wave, **25 pulse**, **26 filter** entries
- Sequences match tables perfectly

**LAXITY Method (Aint_Somebody - 3% accuracy):**
- No reference file
- Must detect tables from Laxity player code
- Tables: 33 wave, **3 pulse**, **2 filter** entries (incomplete!)
- 128 runtime sequences don't match incomplete tables

## Evidence

### Aint_Somebody.sid Conversion Results

**Static Extraction (LaxityPlayerAnalyzer):**
```
Extracted 2 sequences, 8 instruments, 64 commands
Found 33 wave entries at $190C
Written 3 Pulse table entries
Written 2 Filter table entries
Validation warnings: 5 instrument filter_ptr errors
```

**Runtime Extraction (siddump):**
```
Parsed 281 total events
Voice 0: 41 patterns, Voice 1: 46 patterns, Voice 2: 41 patterns
Extracted 256 sequences total
Orderlists reference sequences: [0..127] (128 sequences)
```

**Final Result:**
- File size: 38,474 bytes (expanded from 8,127 bytes to fit sequences)
- Accuracy: **3.01%**

## The Missing Piece

### What siddump_extractor Does

The runtime extractor **already captures** pulse/filter values:

```python
# sidm2/siddump_extractor.py:101-107
pulse_str = parts[wave_idx + 2]
if pulse_str != "...":
    pulse = int(pulse_str, 16)
```

Each captured event includes:
- Frequency (note)
- Waveform
- ADSR envelope
- **Pulse width value** ✓
- (Filter is captured but not stored in events)

### What It Doesn't Do

siddump_extractor does NOT:
1. Build pulse/filter **tables** from captured values
2. Create reusable table entries
3. Map sequence events to table indices

Instead, it uses pulse values directly in sequences, but the SF2 format expects:
- Sequences reference **table indices**
- Tables contain the actual pulse/filter data

## Proposed Solution

### Option 1: Runtime-Based Table Building (Recommended)

Enhance siddump_extractor to build tables from captured runtime data:

1. **Collect unique pulse/filter values** during extraction
2. **Build tables** from these values:
   - Deduplicate values
   - Create table entries
   - Assign indices
3. **Update sequences** to reference table indices instead of raw values
4. **Replace incomplete static tables** with runtime-built tables

**Advantages:**
- Tables match actual music data
- No reliance on static code analysis
- Should achieve high accuracy (80-100%)

**Challenges:**
- Must understand SF2 pulse/filter format
- May create large tables if many unique values
- Need to handle table size limits (256 entries)

### Option 2: Fix Static Extraction

Improve `find_and_extract_pulse_table()` to:
- Not stop at zero entries
- Use better heuristics for table boundaries
- Follow chain links (byte 3 = next entry)

**Advantages:**
- Smaller code change
- Preserves original table structure

**Challenges:**
- Still relies on detecting correct addresses
- May not work for all Laxity variants
- Harder to get right

### Option 3: Hybrid Approach

Use runtime data to **validate and extend** static extraction:
1. Extract tables statically (may be incomplete)
2. Capture runtime values
3. Add missing entries to tables
4. Verify sequences can reference all needed values

**Advantages:**
- Best of both worlds
- Preserves original structure where possible
- Fills gaps with runtime data

**Challenges:**
- Most complex implementation
- Need to merge static + runtime data correctly

## Recommendation

**Implement Option 1: Runtime-Based Table Building**

This approach:
1. Uses proven runtime data (siddump already works)
2. Eliminates dependency on static code analysis
3. Should work for all Laxity variants
4. Expected accuracy: 70-90% (matching baseline performance)

## Next Steps

1. Design runtime table builder architecture
2. Implement pulse table building from siddump data
3. Implement filter table building from siddump data
4. Test with Aint_Somebody.sid (target: >50% accuracy)
5. Run full pipeline (target: average >65% accuracy)
6. Refine and iterate based on results

## Baseline Comparison

| Metric | Baseline (v1.4.1) | Current (v1.5.1) | Target (v1.6.0) |
|--------|-------------------|------------------|-----------------|
| Avg Accuracy | 71.0% | 45.39% | >65% |
| Files at 100% | 6/18 | 7/18 | 8+/18 |
| Files at 0% | 4/18 | 0/18 | 0/18 ✓ |
| Conversion Success | 14/18 | 18/18 ✓ | 18/18 |

## Files Analyzed

**LAXITY conversions (low accuracy):**
1. Aint_Somebody.sid: 3.01%
2. Broware.sid: 4.99%
3. Cocktail_to_Go_tune_3.sid: 2.90%
4. Expand_Side_1.sid: 1.33%
5. Halloweed_4_tune_3.sid: 2.45%
6. I_Have_Extended_Intros.sid: 8.18%
7. SF2packed_new1_Stiensens_last_night_of_89.sid: 1.59%
8. SF2packed_Stinsens_Last_Night_of_89.sid: 1.59%
9. Staying_Alive.sid: 1.00%
10. Stinsens_Last_Night_of_89.sid: 1.59%

All suffer from the same root cause: incomplete tables from static extraction.
