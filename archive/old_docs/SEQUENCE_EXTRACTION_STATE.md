# Sequence Extraction State - 2025-12-08

## Current Status: BLOCKED - Need RetroDebugger Investigation

The sequence extraction from SF2-packed Stinsen SID file is **incorrect**. We have attempted multiple static analysis approaches, all unsuccessful. Dynamic analysis with RetroDebugger is required to find the correct memory addresses.

## What We Know (Confirmed)

### File Information
- **Source File**: `SID/Stinsens_Last_Night_of_89.sid`
- **Size**: 6,201 bytes
- **Load Address**: $1000
- **Init Address**: $1000
- **Play Address**: $1006
- **PSID Header**: 0x7E bytes

### Successfully Extracted Tables (8/11)

1. ✅ **Pulse Table** - Extracted and validated
2. ✅ **Wave Table** - Extracted and validated
3. ✅ **Filter Table** - Extracted and validated
4. ✅ **Instruments Table** - Extracted and validated
5. ✅ **Arpeggio Table** - Extracted and validated
6. ✅ **Commands Table** - Extracted and validated
7. ✅ **Tempo Table** - Extracted and validated
8. ✅ **Orderlists** - Extracted and validated
   - Voice 0: File 0x0AEE (Memory $1AEE)
   - Voice 1: File 0x0B1A (Memory $1B1A)
   - Voice 2: File 0x0B31 (Memory $1B31)

### Orderlist Analysis (Confirmed Correct)

**Voice 0 uses sequences**: 01, 02, 03, 04, 05, 0E, 0F, 11, 13, 14, 15, 1B, 1C, 1F, 20 (15 sequences)

**Voice 1 uses sequences**: 00, 06, 07, 12, 16, 17, 18, 1D, 21, 25 (10 sequences)

**Voice 2 uses sequences**: 08, 09, 0A, 0B, 0C, 0D, 10, 19, 1A, 1E, 22, 23, 24, 26 (14 sequences)

**Total**: 39 unique sequence numbers (0x00-0x26)

## What We Need (MISSING)

### Critical Missing Data

1. ❌ **Sequence Pointer Table Location**
   - Maps sequence numbers (0x00-0x26) to memory addresses
   - Format unknown (direct pointers? split format? offsets?)
   - Location unknown

2. ❌ **Actual Sequence Data Locations**
   - Where sequence 0x00 starts
   - Where sequence 0x01 starts
   - etc. for all 39 sequences

3. ❌ **HR (Hard Restart) Table** - Not yet extracted
4. ❌ **INIT Table** - Not yet extracted

## Failed Extraction Attempts

### Attempt 1: Using Disassembly Pointers ($1A1C-$1A21)

**Method**: Found code in disassembly at lines 160-162 showing:
```asm
$107F  BD 1C 1A      LDA    $1A1C,X
$1084  BD 1F 1A      LDA    $1A1F,X
```

**Assumption**: These are sequence pointers in split format

**Result**: ❌ **INCORRECT**
- Extracted pointers: $1A70, $1A9B, $1AB3
- Extracted 126 bytes total (43 + 24 + 59)
- Data at these addresses does NOT match correct sequence data
- **User confirmed**: "the track and sequence are not correct. the data pointers are wrong"

**Files Created**:
- `extract_sequences_correct.py` - Uses wrong pointers
- `inject_sequences_correct.py` - Injects wrong data
- `output/track{1,2,3}_sequences.bin` - Wrong extractions
- `output/sequences_combined_correct.bin` - Wrong combined data

### Attempt 2: Pattern Matching with Reference SF2

**Method**: Extract sequences from reference SF2 file, search for matches in SID file

**Result**: ❌ **NO MATCHES FOUND**
- Reference SF2 sequence data doesn't exist in SF2-packed SID file
- Confirms SF2-packed format stores sequences differently

**Files Created**:
- `find_sequences_by_comparison.py`

### Attempt 3: Scanning for Sequence-Like Patterns

**Method**: Scan entire SID file for 3-byte patterns matching sequence characteristics

**Result**: ❌ **TOO MANY FALSE POSITIVES**
- Found 69 candidate regions
- Most are player code, not actual sequence data
- Cannot determine which is correct without dynamic analysis

**Files Created**:
- `analyze_all_sequence_candidates.py`

### Attempt 4: Siddump Analysis

**Method**: Analyze notes played via siddump, search for frequency values in file

**Result**: ❌ **FREQUENCIES NOT STORED DIRECTLY**
- Notes are converted to frequencies via lookup table
- Cannot trace back to sequence source addresses
- Confirmed notes are playing correctly

**Files Created**:
- `find_sequences_simple.py`

## Tools and Scripts Created

### Analysis Scripts

1. **`extract_sequences_correct.py`** (⚠️ Uses WRONG addresses)
   - Extracts from $1A70, $1A9B, $1AB3
   - Creates track{1,2,3}_sequences.bin
   - **DO NOT USE** - addresses are incorrect

2. **`inject_sequences_correct.py`** (⚠️ Injects WRONG data)
   - Combines wrong extractions
   - Injects into SF2 template
   - **DO NOT USE** - data is incorrect

3. **`find_sequences_by_comparison.py`**
   - Compares reference SF2 with SID file
   - No matches found

4. **`analyze_all_sequence_candidates.py`**
   - Scans file for sequence-like patterns
   - Found 69 candidates (too many)

5. **`find_sequences_simple.py`**
   - Uses siddump output analysis
   - Confirms notes play but can't find source

6. **`trace_sequence_reads.py`** (⚠️ Incomplete)
   - Attempts CPU-level memory read tracking
   - Needs more work

### Documentation

1. **`RETRODEBUGGER_SEQUENCE_INVESTIGATION.md`**
   - Complete guide for using RetroDebugger
   - Step-by-step investigation instructions
   - Template for reporting findings

2. **`temp-exp/RETRODEBUGGER_INVESTIGATION.md`**
   - Earlier investigation guide

3. **`STINSEN_CONVERSION_STATUS.md`** (Updated)
   - Current conversion status (8/11 tables)
   - Documents sequence extraction attempts
   - Tracks what's complete vs pending

## Why Static Analysis Failed

1. **SF2-packed format is non-standard**
   - Stores data differently than regular SF2
   - Pointer structures may be compressed/encoded
   - Not documented anywhere

2. **Multiple pointer indirection**
   - Orderlists reference sequence numbers
   - Sequence numbers index into pointer table
   - Pointer table location unknown

3. **Disassembly ambiguity**
   - Code at $1A1C may not be sequence pointers
   - Could be orderlists, tempo data, or other structures
   - Need runtime execution to verify

## What Dynamic Analysis Will Show

Using RetroDebugger to trace execution will reveal:

1. **When orderlist is read** → See sequence number loaded
2. **How sequence number is used** → Find pointer table lookup
3. **Where pointer table is** → Memory address of table
4. **Where actual sequence data is** → Memory addresses being read during playback

## Next Steps - REQUIRED USER ACTION

### Use RetroDebugger to Find:

```
CRITICAL INFORMATION NEEDED:

1. Sequence pointer table location:
   Memory address: $____
   File offset: 0x____
   Format: [describe]
   First 20 bytes: __ __ __ __ __ __ __ __ __ __ ...

2. Pointer table format:
   [ ] Direct 2-byte pointers (39 × 2 = 78 bytes)
   [ ] Split format (39 low + 39 high = 78 bytes)
   [ ] Offsets from base address
   [ ] Other: ________________

3. Actual sequence start addresses:
   Seq 0x00: Memory $____ File 0x____
   Seq 0x01: Memory $____ File 0x____
   Seq 0x02: Memory $____ File 0x____
   OR
   All sequences in contiguous block at: $____
```

### Investigation Process:

1. **Load SID in RetroDebugger**
   - File → Load SID → `SID/Stinsens_Last_Night_of_89.sid`

2. **Set breakpoint on orderlist read**
   - Memory $1AEE (Voice 0 orderlist)
   - Watch when it gets read

3. **Trace sequence number usage**
   - See how the byte read from orderlist is used
   - Follow pointer table lookup
   - Note memory addresses accessed

4. **Record addresses**
   - Where is pointer table?
   - What format is it?
   - Where do sequences start?

## Output Files Status

### Correct Files (Keep)
- `output/Stinsens_Last_Night_of_89_ALL_7_TABLES.sf2` - Base with 7 tables
- `output/Stinsens_Last_Night_of_89_WITH_ORDERLISTS_EXPANDED.sf2` - 8 tables
- `output/orderlist_voice{0,1,2}_driver11.bin` - Correct orderlists

### Incorrect Files (Ignore/Delete)
- `output/track{1,2,3}_sequences.bin` - WRONG extractions
- `output/sequences_combined_correct.bin` - WRONG combined data
- `output/Stinsens_Last_Night_of_89_WITH_SEQUENCES_CORRECT.sf2` - WRONG sequences
- `output/sequences_extracted.bin` - Old WRONG extraction (670 bytes)
- `output/Stinsens_Last_Night_of_89_WITH_SEQUENCES.sf2` - Old WRONG file

## Key Learnings

1. **Split pointer format exists** but $1A1C-$1A21 is NOT it
2. **Orderlists are correct** - extraction and injection working
3. **SF2-packed ≠ regular SF2** - completely different structure
4. **Static analysis insufficient** - need dynamic tracing
5. **Reference SF2 not helpful** - data is transformed in packing

## Conversion Progress

```
┌─────────────────────────────────────────────────────┐
│ Stinsen SID → Driver 11 SF2 Conversion              │
│                                                      │
│ Progress: 8/11 tables (73%)                         │
│                                                      │
│ ✅ Pulse Table                                       │
│ ✅ Wave Table                                        │
│ ✅ Filter Table                                      │
│ ✅ Instruments Table                                 │
│ ✅ Arpeggio Table                                    │
│ ✅ Commands Table                                    │
│ ✅ Tempo Table                                       │
│ ✅ Orderlists                                        │
│ ❌ Sequences ← BLOCKED HERE                         │
│ ❌ HR (Hard Restart) Table                          │
│ ❌ INIT Table                                        │
└─────────────────────────────────────────────────────┘
```

## When We Get Correct Addresses

Once you provide the correct addresses, we can:

1. **Extract sequences correctly**
   - Read pointer table
   - Extract each sequence (0x00-0x26)
   - Validate against orderlist references

2. **Inject into Driver 11**
   - Combine sequences into contiguous block
   - Inject at correct SF2 offset
   - Update pointers

3. **Extract remaining tables**
   - HR table
   - INIT table

4. **Complete conversion**
   - Test in SID Factory II
   - Verify all 11 tables working

## References

- **Disassembly**: `docs/reference/STINSENS_PLAYER_DISASSEMBLY.md`
- **Status Doc**: `STINSEN_CONVERSION_STATUS.md`
- **RetroDebugger Guide**: `RETRODEBUGGER_SEQUENCE_INVESTIGATION.md`
- **Original Reference**: `learnings/Laxity - Stinsen - Last Night Of 89.sf2`

## Contact Point

**Current State**: Waiting for RetroDebugger investigation results

**What we need**: Memory addresses from dynamic analysis

**Files to review**:
- `RETRODEBUGGER_SEQUENCE_INVESTIGATION.md` (investigation guide)
- This file (complete state summary)

---

*Last Updated: 2025-12-08*
*Status: BLOCKED - Awaiting RetroDebugger results*
