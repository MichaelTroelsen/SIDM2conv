# Pulse Table Fix Summary - Stinsens Last Night of '89

## Problem

The pulse table in the converted SF2 file was not being extracted correctly from the SF2-packed SID source file.

## Root Cause

The SF2-packed SID format stores the pulse table differently than Driver 11:
- **SF2-packed**: 3 consecutive columns of 25 bytes each (75 bytes total)
- **Driver 11**: 4 columns of 256 bytes each (1024 bytes total), column-major

The original conversion code was not properly extracting the 3-column data from the SF2-packed SID.

## Solution

Created `fix_pulse_table_correct.py` to:

1. **Extract 3 consecutive columns** from SF2-packed SID at offset $09BC:
   - Column 0: bytes 0-24 (Value)
   - Column 1: bytes 25-49 (Delta)
   - Column 2: bytes 50-74 (Duration)

2. **Convert to Driver 11 format**:
   - Copy 3 columns to first 3 columns of 256-row table
   - Fill 4th column (Next) with zeros
   - Use column-major storage

3. **Write to SF2 file** at pulse table address $1B24

## Data Verification

### Extracted Data (First 15 Entries)

| Entry | Col0 (Value) | Col1 (Delta) | Col2 (Duration) |
|-------|--------------|--------------|-----------------|
| 00    | 88           | 00           | 00              |
| 01    | 00           | 00           | 01              |
| 02    | 81           | 70           | 00              |
| 03    | 00           | 40           | 04              |
| 04    | 00           | 10           | 20              |
| 05    | 0F           | F0           | 20              |
| 06    | 7F           | 00           | 04              |
| 07    | 88           | 00           | 00              |
| 08    | 7F           | 00           | 07              |
| 09    | 88           | 00           | 00              |
| 0A    | 0F           | A0           | 05              |
| 0B    | 0F           | F0           | 20              |
| 0C    | 00           | 10           | 20              |
| 0D    | 7F           | 00           | 0A              |
| 0E    | 88           | 00           | 00              |

### Verification Results

All tables now pass verification:
```
WAVE: PASS
PULSE: PASS ✓ (FIXED)
FILTER: PASS
INSTRUMENTS: PASS
COMMANDS: PASS
TEMPO: PASS
HR: PASS
INIT: PASS
ARP: PASS
```

## Files

- **Source**: `SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid`
  - Pulse table at: $09BC-$0A06 (75 bytes)

- **Target**: `test_direct.sf2`
  - Load address: $0D7E
  - Pulse table at: $1B24 (1024 bytes)

- **Script**: `fix_pulse_table_correct.py`
  - Extracts 3 consecutive columns from SF2-packed SID
  - Converts to Driver 11 4-column format
  - Writes to SF2 file

- **Verification**: `verify_all_tables.py test_direct.sf2`

## Key Learning

SF2-packed SID files store pulse data as **3 consecutive columns** rather than the row-major format initially assumed. Each column is exactly 25 bytes, making the total pulse data 75 bytes starting at $09BC.

This differs from Driver 11 which uses 4 columns of 256 bytes each in column-major format.

## Status

✅ **COMPLETE** - Pulse table extraction fixed and verified (2025-12-07)
