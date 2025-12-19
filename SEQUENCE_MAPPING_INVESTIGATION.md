# Sequence Mapping Investigation - Critical Findings

## Problem Summary

User's track_3.txt reference file (from SID Factory II editor, sequence 0x0A, Track 3) does NOT match any sequence in the SF2 Viewer.

## Key Findings

### 1. Sequence Pointer Table Issue

**Location**: File offset 0x16D2
**Problem**: Points to INVALID data (all zeros)

```
Seq 00-08: mem=0xE1E1 (padding/invalid)
Seq 09:    mem=0x27E1, file=0x1A65
Seq 10:    mem=0x2928, file=0x1BAC ← POINTS TO ALL ZEROS!
Seq 11:    mem=0x2B2A, file=0x1DAE
```

**Verification**: File offset 0x1BAC contains 200+ bytes of zeros (no valid sequence data)

### 2. Parser Sequence Numbering

The SF2 Viewer parser uses **scan-based indexing**:
- Scans file for 0x7F terminators
- Assigns indices 0, 1, 2, ... in **scan order**
- **NOT** based on the sequence pointer table

**Result**: Parser sequence indices DO NOT match SID Factory II sequence numbers!

### 3. Sequence Length Comparison

| Parser Index | Total Entries | Track 3 Steps | Notes |
|--------------|---------------|---------------|-------|
| 0 | 91 | 30 | Too short |
| 1 | 32 | 10 | Too short |
| 6 | 128 | 42 | **Closest match** to reference (41 steps) |
| 10 | 32 | 10 | Too short |

**Reference**: 41 steps for Track 3

### 4. Sequence 6 Comparison Results

Tested parser sequence 6 vs reference:
- **Match rate**: 42.9% (18/42 steps)
- **Problem**: Data is completely different

**Examples**:
- Step 0: Extracted shows `-- -- +++`, reference shows `0b -- F-3`
- Step 2: Extracted shows `02 -- C-2`, reference shows `-- 02 +++`

### 5. Unpacking Format Investigation

**Raw bytes at 0x2665** (23 bytes): `AB 81 29 C2 7E 29 83 35 29 81 29 C2 7E 29 29 35 D2 7E 83 29 81 2D 7F`

**Tested interpretations**:
1. ✗ **Packed format** (current unpacker): Creates wrong data
2. ✗ **Unpacked 3-byte format**: Also produces wrong data

## Critical Questions

### Q1: Sequence Number Mismatch
**SID Factory II shows "a00a"** (OrderList: transpose=0xA0, sequence=0x0A)
**But which sequence index** in the parser corresponds to SID Factory II's sequence 0x0A?

### Q2: Sequence Storage Location
- Pointer table at 0x16D2 is invalid (points to zeros)
- Where is the ACTUAL sequence 0x0A data stored?
- How does SID Factory II find it?

### Q3: Unpacking Algorithm
- Current unpacker produces completely different data
- Is the unpacking algorithm wrong?
- Or are we unpacking the wrong sequence?

## Possible Explanations

### Option A: Wrong Sequence
The parser's sequence numbering doesn't match SID Factory II's numbering. Sequence 0x0A in SID Factory II might be:
- Parser sequence 6 (has 42 steps)
- Or some other sequence we haven't found yet

### Option B: Multiple Sequence Tables
The file might have:
- One sequence table for the Laxity player (not used by SF2 editor)
- Another sequence table for SF2 editor display
- The parser is finding one, SID Factory II uses the other

### Option C: Unpacking Bug
The `unpack_sequence()` function has a fundamental bug that:
- Misinterprets the packed byte format
- Produces wrong instrument/command/note assignments
- Creates wrong track interleaving

## Recommended Next Steps

### Step 1: Find ALL Sequences in File
Scan ENTIRE file for all potential sequence data to build a complete index.

### Step 2: Match by Length
Find sequences with 41-42 Track 3 steps and compare ALL of them with the reference.

### Step 3: Study SID Factory II Source Code
Check how SID Factory II:
- Reads sequence numbers from files
- Maps OrderList entries to sequence data
- Unpacks/displays sequence data

### Step 4: Check for Laxity-Specific Format
Verify if Laxity SF2 files use a different:
- Sequence table format
- Unpacking algorithm
- Track interleaving method

## Files for Review

- **File**: `learnings/Laxity - Stinsen - Last Night Of 89.sf2`
- **Reference**: `track_3.txt` (41 steps, from SID Factory II editor, sequence 0x0A, Track 3)
- **Parser code**: `sf2_viewer_core.py::unpack_sequence()` (lines 240-337)
- **Sequence parser**: `sf2_viewer_core.py::_parse_packed_sequences_laxity_sf2()` (lines 938-1022)

## Status

- ✅ Found sequence pointer table (but contains invalid data)
- ✅ Parser finds 22 sequences via file scanning
- ✅ Identified sequence length mismatch (seq 6 has 42 steps)
- ❌ Cannot identify which parser sequence = SID Factory II sequence 0x0A
- ❌ Sequence data doesn't match reference (42.9% match rate)
- ❌ Unpacking algorithm produces wrong results

**Blocker**: Need to determine correct mapping between SID Factory II sequence numbers and parser sequence indices.
