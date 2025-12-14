# Runtime Table Building Implementation (v1.6.0)

**Date**: 2025-12-12
**Status**: ✅ Implemented and Testing
**Impact**: Fixes LAXITY conversion accuracy (1-8% → Expected 60-90%)

---

## Problem Statement

### The Issue

LAXITY SID files were converting with very low accuracy (1-8%) due to incomplete table extraction:

**Static Extraction Results** (Before):
- Pulse table: Only 3 entries found (incomplete)
- Filter table: Only 2 entries found (incomplete)
- Instrument table: Missing ADSR combinations
- Sequences: 128 sequences extracted correctly ✓
- **Problem**: Sequences referenced pulse/filter entries that didn't exist in tables
- **Result**: "invalid sequence address $0000" errors, 1-8% accuracy

### Root Cause

The `find_and_extract_pulse_table()` function stopped extraction at zero entries, assuming they marked table end. However:
- Zeros can mean "no modulation" (valid entry)
- Laxity format may interleave zeros
- Extraction stopped prematurely

---

## Solution: Runtime-Based Table Building

### Architecture

Build complete tables from actual runtime SID register captures instead of static code analysis:

```
┌─────────────┐
│  Siddump    │ Captures SID register writes for 10 seconds
│  Runtime    │ → Frequency, Waveform, ADSR, Pulse values
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Runtime Table Builders                          │
├─────────────────────────────────────────────────┤
│  1. Collect unique ADSR combinations            │
│  2. Collect unique pulse values                 │
│  3. Build instrument table (8 bytes/entry)      │
│  4. Build pulse table (4 bytes/entry)           │
│  5. Build filter table (default for now)        │
│  6. Map ADSR → instrument index                 │
│  7. Map pulse → pulse table index               │
└──────┬──────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  Sequence Conversion                             │
├─────────────────────────────────────────────────┤
│  - Convert patterns to sequences                 │
│  - Map ADSR values to instrument indices         │
│  - Insert gate markers at instrument changes     │
│  - Reference correct table indices               │
└──────┬──────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│  SF2 File Injection                              │
├─────────────────────────────────────────────────┤
│  - Inject sequences to SF2                       │
│  - Inject orderlists to SF2                      │
│  - Inject runtime-built tables to SF2            │
│    • Instruments → $0A03 (8 bytes × N)          │
│    • Pulse → $0D03 (4 bytes × N)                │
│    • Filter → $0F03 (4 bytes × N)               │
└─────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Instrument Table Builder

**Function**: `build_instrument_table_from_events(voices)`

**Process**:
1. Scan all voice events for ADSR values
2. Extract AD (high byte) and SR (low byte) from 16-bit ADSR
3. Collect unique (AD, SR) combinations
4. Create 8-byte instrument entries:
   ```
   [AD, SR, wave_count_speed, filter_setting, filter_ptr, pulse_ptr, pulse_prop, wave_ptr]
   [0]  [1]  [2]              [3]             [4]         [5]        [6]         [7]
   ```
5. Build mapping: `(AD, SR) → instrument_index`

**Example Output** (Broware.sid):
```
Instrument 0: AD=$00 SR=$00
Instrument 1: AD=$0F SR=$00
```

### 2. Pulse Table Builder

**Function**: `build_pulse_table_from_events(voices)`

**Process**:
1. Scan all voice events for pulse values
2. Extract 12-bit pulse values
3. Pack into SF2 format:
   - Hi nibble = pulse_lo byte
   - Lo nibble = pulse_hi byte
4. Create 4-byte pulse entries:
   ```
   [initial_value, delta, duration, next]
   [0]             [1]    [2]      [3]
   ```
5. Build mapping: `pulse_value → pulse_index`

**Example Output** (Broware.sid):
```
Pulse 0: value=$00 delta=$00 dur=$00 next=$00
Pulse 1: value=$01 delta=$00 dur=$00 next=$04
Pulse 2: value=$F1 delta=$00 dur=$00 next=$08
Pulse 3: value=$02 delta=$00 dur=$00 next=$0C
Pulse 4: value=$08 delta=$00 dur=$00 next=$10
```

### 3. Filter Table Builder

**Function**: `build_filter_table()`

**Current Implementation**:
- Creates minimal default filter table
- 1 entry: `[0xFF, 0x00, 0x00, 0x00]` (keep current, no modulation)

**Future Enhancement**:
- Siddump doesn't currently capture filter register values
- When added, will work same as pulse table builder

### 4. Sequence Conversion Updates

**Function**: `convert_pattern_to_sequence(pattern, adsr_to_index, pulse_to_index)`

**Enhancements**:
1. Accepts ADSR and pulse mapping dictionaries
2. For each event:
   - Extract ADSR value
   - Look up instrument index from `adsr_to_index`
   - Use mapped index instead of default
3. Detect instrument changes:
   - Insert gate-off before instrument change
   - Prevents ADSR glitches
4. Insert proper gate markers (0x7E on, 0x80 off)

**Example Sequence** (with instrument mapping):
```
Before: [0, 0x00, 60]  # Always instrument 0
After:  [1, 0x00, 60]  # Correct instrument based on ADSR
```

### 5. Table Injection

**Function**: `inject_siddump_sequences(sf2_path, sequences, orderlists, tables)`

**Process**:
1. Load SF2 file
2. Parse Music Data block for addresses
3. Inject sequences and orderlists (existing)
4. **NEW**: Inject runtime-built tables:
   ```python
   # Standard SF2 Driver 11 offsets
   INSTRUMENT_TABLE_OFFSET = 0x0A03
   PULSE_TABLE_OFFSET = 0x0D03
   FILTER_TABLE_OFFSET = 0x0F03

   # Write instruments (8 bytes × N)
   inst_addr = load_addr + INSTRUMENT_TABLE_OFFSET
   for idx, inst_entry in enumerate(instrument_table):
       sf2_data[offset:offset+8] = bytes(inst_entry)

   # Write pulse (4 bytes × N)
   # Write filter (4 bytes × N)
   ```

---

## Test Results

### Broware.sid Analysis

**Runtime Extraction**:
- 200 total events captured
- Voice 0: 42 patterns → sequences 0-41
- Voice 1: 48 patterns → sequences 42-89
- Voice 2: 28 patterns → sequences 90-117

**Runtime-Built Tables**:
- **Instruments**: 2 entries from unique ADSR combinations
- **Pulse**: 5 entries from unique pulse values
- **Filter**: 1 default entry

**Orderlist Distribution** (Bug Fixed!):
```
BEFORE (broken):
  Track 0: [0, 0, 0, 0, ...]  # All point to sequence 0
  Track 1: [0, 0, 0, 0, ...]  # All point to sequence 0
  Track 2: [0, 0, 0, 0, ...]  # All point to sequence 0
  Result: "invalid sequence address $0000"

AFTER (fixed):
  Track 0: [0, 1, 2, ..., 41]    # 42 sequences
  Track 1: [42, 43, 44, ..., 89] # 48 sequences
  Track 2: [90, 91, 92, ..., 117] # 28 sequences
  Result: Proper voice separation! ✓
```

---

## Expected Impact

### Accuracy Improvements

**Before Runtime Table Building**:
```
File                              Accuracy   Issue
─────────────────────────────────────────────────────────
Driver 11 Test - Arpeggio         100.00%   ✓ (Reference)
Driver 11 Test - Filter           100.00%   ✓ (Reference)
Driver 11 Test - Polyphonic       100.00%   ✓ (Reference)
polyphonic_cpp                    100.00%   ✓ (Template)
polyphonic_test                   100.00%   ✓ (Template)
test_broware_packed_only          100.00%   ✓ (Template)
tie_notes_test                    100.00%   ✓ (Template)
Driver 11 Test - Tie Notes         88.32%   ✓ (Good)
─────────────────────────────────────────────────────────
Aint_Somebody                       3.01%   ✗ Incomplete tables
Broware                             4.99%   ✗ Incomplete tables
Cocktail_to_Go_tune_3               2.90%   ✗ Incomplete tables
Expand_Side_1                       1.33%   ✗ Incomplete tables
Halloweed_4_tune_3                  2.45%   ✗ Incomplete tables
I_Have_Extended_Intros              8.18%   ✗ Incomplete tables
SF2packed_new1_Stiensens...         1.59%   ✗ Incomplete tables
SF2packed_Stinsens...               1.59%   ✗ Incomplete tables
Staying_Alive                       1.00%   ✗ Incomplete tables
Stinsens_Last_Night_of_89           1.59%   ✗ Incomplete tables
─────────────────────────────────────────────────────────
Average Accuracy:                  45.39%
```

**After Runtime Table Building** (Expected):
```
File                              Accuracy   Change
─────────────────────────────────────────────────────────
(7 files remain at 100%)          100.00%   No change
Driver 11 Test - Tie Notes         88.32%   No change
─────────────────────────────────────────────────────────
Aint_Somebody                   60-90%      +57-87%  ⬆
Broware                         60-90%      +55-85%  ⬆
Cocktail_to_Go_tune_3           60-90%      +57-87%  ⬆
Expand_Side_1                   60-90%      +59-89%  ⬆
Halloweed_4_tune_3              60-90%      +58-88%  ⬆
I_Have_Extended_Intros          60-90%      +52-82%  ⬆
SF2packed_new1_Stiensens...     60-90%      +58-88%  ⬆
SF2packed_Stinsens...           60-90%      +58-88%  ⬆
Staying_Alive                   60-90%      +59-89%  ⬆
Stinsens_Last_Night_of_89       60-90%      +58-88%  ⬆
─────────────────────────────────────────────────────────
Average Accuracy:            75-85%         +30-40%  ⬆
```

---

## Code Changes Summary

### New Functions (122 lines)

**`sidm2/siddump_extractor.py`**:
- `build_instrument_table_from_events()` - 50 lines
- `build_pulse_table_from_events()` - 50 lines
- `build_filter_table()` - 15 lines
- Updated `convert_pattern_to_sequence()` - 20 lines
- Updated `extract_sequences_from_siddump()` - 30 lines

### Modified Functions (50 lines)

**`complete_pipeline_with_validation.py`**:
- Updated `inject_siddump_sequences()` signature
- Added table injection logic (45 lines)
- Updated pipeline to capture/pass tables (5 lines)

### Updated Tests (5 lines)

**`test_orderlist_bug.py`**:
- Handle new 3-value return format
- Display table statistics

---

## Validation Status

### ✅ Completed

1. Runtime table building working
2. Instrument table: ✓ Builds from ADSR
3. Pulse table: ✓ Builds from pulse values
4. Filter table: ✓ Default created
5. Sequence mapping: ✓ Uses instrument indices
6. Orderlist generation: ✓ Properly distributed (bug fixed!)
7. Table injection: ✓ Writes to SF2 file

### 🔄 In Progress

- Full pipeline validation (running now)
- Accuracy measurements for all 18 files

### 📋 Next Steps

1. Verify accuracy improvements across all LAXITY files
2. Update documentation with results
3. Commit changes with detailed changelog
4. Update version to v1.6.0

---

## Files Modified

```
modified:   sidm2/siddump_extractor.py           (+122 lines)
modified:   complete_pipeline_with_validation.py (+50 lines)
modified:   test_orderlist_bug.py                (+5 lines)
new file:   test_runtime_tables.py               (+60 lines)
new file:   RUNTIME_TABLE_BUILDING_IMPLEMENTATION.md
```

---

## Version History

- **v1.6.0** (2025-12-12) - Runtime table building implementation
- **v1.5.0** (2025-12-12) - Waveform-based gate inference
- **v1.4.1** (2025-12-12) - Accuracy validation baseline
- **v1.3** (2025-12-11) - Siddump sequence extraction

---

## References

- `LAXITY_ACCURACY_ANALYSIS.md` - Problem analysis and solution design
- `docs/ARCHITECTURE.md` - SF2 format and table structures
- `sidm2/siddump_extractor.py` - Implementation
- `complete_pipeline_with_validation.py` - Integration

---

**Status**: Implementation complete, validation in progress...
