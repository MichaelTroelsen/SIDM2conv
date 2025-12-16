# Laxity SF2 Sequence Format Discovery

**Date**: 2025-12-16
**Status**: CRITICAL FINDING - FORMAT MISMATCH IDENTIFIED
**Impact**: Explains why data is wrong

---

## Discovery

When examining the raw bytes of the Laxity SF2 file (`Laxity - Stinsen - Last Night Of 89.sf2`), we found that the sequence data structure is **NOT** where our code assumed it was!

### What We Found

**File Offset 0x1662** (where we thought sequences started):
```
24 25 26 E1 E1 E1 E1 E1 E1 ... (many E1 bytes) ... 27 28 29 2a ...
```

- `0x24, 0x25, 0x26` = appear to be note values (C-3, C#-3, D-3)
- `0xE1` repeated many times = **PADDING/FILLER** (not valid command bytes)
- This looks like an **offset table or header**, not sequence data!

**File Offset 0x1772** (where real sequence data appears to start):
```
03 A0 13 14 13 15 0E 11 01 05 01 04 AC 02 1B A0 13 14 13 15 1C 1C 1C 1C AC 02 1F 20 FF ...
```

- These ARE valid control bytes! (0xA0+, 0x01-0x7F, etc.)
- This looks like **ACTUAL sequence data** in the packed format!

---

## Problem Analysis

1. **Wrong Offset**: Our code finds packed sequences at offset 0x1662, but this appears to be a **pointer table or header**, not the actual sequence data
2. **Padding Issue**: The repeated 0xE1 bytes confused the parser
3. **Offset Table**: Bytes `24 25 26` followed by 0xE1 padding might be:
   - Pointer table entries (each pointing to actual sequence data)
   - Or an offset header
   - Or track information

---

## What Needs to Happen

The unpacking algorithm needs to:

1. **Skip the header/offset table** at 0x1662
2. **Find where real sequence data starts** (appears to be around 0x1772)
3. **Parse the actual sequence bytes** that contain valid control codes

The actual sequence format appears to be valid (with bytes like 0xA0, 0x03, 0x13, etc.), but our code is trying to parse from the wrong starting offset!

---

## Root Cause

When `_find_packed_sequences()` finds the packed sequences at offset 0x1662 with length 220 bytes, it's finding:
- An offset/header table (0x1662-0x1700)
- Then the real sequence data (0x1772+)

But our `_parse_packed_sequences()` method tries to parse FROM 0x1662, which includes the header/padding!

---

## Next Steps

1. **Examine offset table structure**: What do `24 25 26 E1...` represent?
2. **Find proper sequence boundaries**: Where does each sequence actually start and end?
3. **Skip header correctly**: Modify parsing to skip the offset table and read actual data
4. **Update unpack logic**: May need to handle Laxity-specific format

The good news: The **actual sequence data exists and appears to be in valid format**. We just need to parse from the right offset!

---

**Critical Realization**: The issue is not that the format is wrong, but that we're reading from the wrong location in the file. The 0xE1 "mystery bytes" were never supposed to be parsed as sequence data - they're just padding!
