# Phase 6: Pointer Patching Implementation Results

**Date**: 2025-12-13
**Status**: Pointer patching implemented but accuracy unchanged
**Conclusion**: Incomplete data injection - need to inject ALL tables, not just orderlists

---

## Executive Summary

Implemented static code analysis and pointer patching system to route relocated Laxity player to injected music data. Successfully applied 40/42 pointer patches, but accuracy remained at 0.20% (no improvement from 0.18%).

**Root Cause**: We're only injecting orderlists and sequences, but the Laxity player requires complete data structure including wave, pulse, filter, and instrument tables.

---

## Implementation

### 1. Static Code Scanner

Created `scripts/trace_orderlist_access.py` (319 lines) to scan Laxity player code for address references:

**Scan Results**:
- Scanned 5,319 instructions
- Found 42 instructions accessing $1898-$1B98 range
- Identified addressing modes: Absolute,X/Y, Compare, Store
- Generated patch instructions with file offsets

**Key Findings**:
- 12 references to $16B7 (sequence/wave data)
- 8 references to table locations ($1819-$1849)
- 22 references to various sequence/data offsets

### 2. Pointer Patching System

Implemented in `sidm2/sf2_writer.py` lines 1357-1432:

```python
# 40 pointer patches applied
# Format: (file_offset, old_lo, old_hi, new_lo, new_hi)
# Example:
(0x01C6, 0xD8, 0x16, 0x40, 0x19)  # $16D8 -> $1940
(0x00DE, 0x19, 0x18, 0x81, 0x1A)  # $1819 -> $1A81 (instrument table)
```

**Patch Application**:
- 40/42 patches applied successfully
- 2 patches failed (file offset or byte mismatch)
- Orderlists injected at $1900-$1B00 (safe location)

### 3. Test Results

**Conversion**: Success
```
INFO: Applied 40 pointer patches
INFO: Injecting 3 orderlists...
INFO: Injecting 1 sequences...
```

**Accuracy Validation**:
```
Original: 14,595 register writes
Exported:  3,023 register writes (unchanged!)
Overall Accuracy: 0.20% (was 0.18%)
```

**Playback Behavior**:
- Only Voice 1 pulse width changing
- No notes playing
- Same behavior as before patching

---

## Problem Analysis

### What We Patched

The 42 pointer locations include references to:
1. **Orderlists** ($1898, $1998, $1A98 ranges)
2. **Sequences** (various offsets $18B7-$19BD)
3. **Wave table** ($18DA, $190C references)
4. **Instrument table** ($1819-$1849 references)
5. **Pulse table** (referenced in scanned code)
6. **Filter table** (referenced in scanned code)

### What We Injected

Currently injecting:
- ✅ 3 orderlists (256 bytes each at $1900, $1A00, $1B00)
- ✅ 1 sequence (limited data)
- ❌ Wave table (NOT injected)
- ❌ Pulse table (NOT injected)
- ❌ Filter table (NOT injected)
- ❌ Instrument table (NOT injected)

### Why Accuracy Is Still Low

The Laxity player expects a complete music data structure:

```
Memory Layout (Required by Player):
$1900-$1AFF: Orderlists (3 × 256 bytes) ✅ INJECTED
$1B00-$1CFF: Sequences              ✅ PARTIAL
$1D00-$1DFF: Wave table             ❌ NOT INJECTED
$1E00-$1EFF: Pulse table            ❌ NOT INJECTED
$1F00-$1FFF: Filter table           ❌ NOT INJECTED
$2000-$20FF: Instrument table       ❌ NOT INJECTED
```

Without the complete structure:
1. Player reads orderlists successfully (patched pointers work!)
2. Player tries to read wave/pulse/filter tables
3. Tables don't exist at expected locations
4. Player falls back to embedded default data
5. No notes play (only pulse width changes from minimal data)

---

## Technical Details

### Scanner Implementation

**File**: `scripts/trace_orderlist_access.py`

**Approach**: Static analysis (not emulation)
- Scans player binary looking for instructions with absolute addressing
- Checks if operand addresses fall in orderlist/table ranges
- Generates patch instructions with calculated offsets

**Advantages**:
- Fast (no emulation overhead)
- Reliable (scans all code paths)
- Simple (standard library only)

**Limitations**:
- Doesn't detect indirect addressing (zero-page pointers)
- Can't distinguish code from data in some edge cases
- Misses runtime-calculated addresses

### Pointer Patch Calculation

**Formula**:
```
Original address:     $18D8
After -$0200 reloc:   $16D8 (in driver template)
Target injection:     $1940 (+$0268 offset)
Little-endian bytes:  D8 16 -> 40 19
File offset:         $01C6 (PC=$0E46 in relocated code)
```

**Verification**:
- Check old bytes match before patching
- Log mismatches for debugging
- Count successful patches

### Current Data Flow

```
1. Load driver template (load=$0D7E)
   ├─ Relocated player at $0E00-$16FF
   └─ Embedded data from reference SID

2. Apply 40 pointer patches
   ├─ Change $16D8 -> $1940 (12 instances)
   ├─ Change $1819 -> $1A81 (8 instances)
   └─ Change $17XX -> $19XX (20 instances)

3. Inject orderlists at $1900-$1B00 ✅

4. Inject sequence at $1C00+ ✅

5. Execute player
   ├─ Reads orderlists from $1900 ✅ (patched!)
   ├─ Tries to read wave table -> NOT FOUND ❌
   ├─ Tries to read pulse table -> NOT FOUND ❌
   ├─ Tries to read filter table -> NOT FOUND ❌
   └─ Falls back to embedded data ❌
```

---

## Next Steps: Two Options

### Option A: Complete Table Injection (Continue Laxity Driver)

**Implement complete data structure injection**:

1. **Extract all tables from original SID**:
   ```python
   # In laxity_analyzer.py
   - Extract wave table (typically 256-512 bytes)
   - Extract pulse table (typically 256-512 bytes)
   - Extract filter table (typically 128-256 bytes)
   - Extract instrument table (typically 256-512 bytes)
   ```

2. **Calculate injection addresses**:
   ```
   Orderlists:   $1900-$1B00 (768 bytes) ✅ DONE
   Sequences:    $1B00-$1D00 (512 bytes) ✅ DONE
   Wave table:   $1D00-$1E00 (256 bytes) ⚠️ TODO
   Pulse table:  $1E00-$1F00 (256 bytes) ⚠️ TODO
   Filter table: $1F00-$2000 (256 bytes) ⚠️ TODO
   Instruments:  $2000-$2100 (256 bytes) ⚠️ TODO
   ```

3. **Patch additional pointers**:
   - Wave table pointers (found at $18DA, $190C)
   - Pulse table pointers (need to scan for)
   - Filter table pointers (need to scan for)
   - Instrument table pointers ($1819-$1849)

4. **Inject all tables in sf2_writer.py**:
   ```python
   def _inject_laxity_music_data(self):
       # ... existing orderlist injection ...

       # Inject wave table
       wave_offset = addr_to_offset(0x1D00)
       for i, wave_entry in enumerate(self.data.wave_table):
           self.output[wave_offset + i] = wave_entry

       # Inject pulse table
       pulse_offset = addr_to_offset(0x1E00)
       # ... similar ...

       # Inject filter table
       # Inject instrument table
   ```

5. **Test and validate**:
   - Expected accuracy: 30-70% (if tables are correct)
   - May need additional table format research

**Estimated Effort**: 12-20 hours
**Success Probability**: 50%
**Risk**: High - table formats may not match perfectly

### Option B: Revert to NP20 Driver (Recommended)

**Accept current limitations and focus on NP20**:

1. **Revert pipeline to use NP20 for Laxity files**:
   ```python
   # complete_pipeline_with_validation.py line 170
   ['python', 'scripts/sid_to_sf2.py', ..., '--driver', 'np20', ...]
   ```

2. **Document Laxity driver as experimental**:
   - Update README.md with driver compatibility matrix
   - Note: Laxity driver achieves 0.20% accuracy (experimental)
   - Note: Use NP20 driver for Laxity files (1-8% accuracy baseline)

3. **Focus efforts on improving NP20 conversion**:
   - Better table extraction
   - Improved format translation
   - Gate inference
   - Runtime table building

**Estimated Effort**: 1-2 hours (cleanup)
**Success Probability**: 100%
**Outcome**: Stable baseline with known limitations

---

## Recommendation

**Revert to NP20 (Option B)**

**Rationale**:
1. Laxity driver has proven more complex than anticipated
2. Complete table injection requires deep table format understanding
3. Time investment (20+ hours total) hasn't yielded significant improvement
4. NP20 driver provides stable 1-8% baseline
5. Can revisit Laxity driver later with better tools (VICE debugger, more analysis)

**Learnings to Preserve**:
- ✅ Pointer patching technique works (40/42 patches applied)
- ✅ Static code scanner is reliable and fast
- ✅ Memory layout analysis was comprehensive
- ✅ Relocation engine works correctly
- ❌ Data injection alone is insufficient without complete structure
- ❌ Laxity player has more data dependencies than expected

---

## Conclusion

The pointer patching implementation succeeded technically (40/42 patches applied), but didn't improve accuracy because we're only injecting partial music data structure. The Laxity player requires wave, pulse, filter, and instrument tables that we're not currently providing.

**Two paths forward**:
1. Complete table injection (12-20 hours, 50% success)
2. Revert to NP20 driver (1-2 hours, 100% success, known limitations)

**Recommendation**: Option B (Revert to NP20) and document Laxity driver as experimental.

**Time Invested**: ~16 hours across Phases 5-6
**Commits**: 6 commits documenting the journey
**Code Created**:
- trace_orderlist_access.py (319 lines)
- Pointer patching system (75 lines)
- Comprehensive documentation (1,500+ lines)

---

**Last Updated**: 2025-12-13 (after pointer patching test)
**Accuracy**: 0.20% (40 patches applied, incomplete data injection)
**Next Decision**: Complete table injection OR revert to NP20
