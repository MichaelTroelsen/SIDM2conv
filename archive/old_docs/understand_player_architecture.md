# Understanding the Laxity Player Architecture

## Problem Statement

We're trying to extract sequences from "Stinsen's Last Night of 89" which uses the Laxity NewPlayer v21 format. The challenge is understanding how the player accesses sequence data.

## What We Know

### 1. Orderlist Pointers (Confirmed)

From disassembly at $107F/$1084:
```asm
$107F  BD 1C 1A      LDA    $1A1C,X        ; Load orderlist pointer low byte
$1084  BD 1F 1A      LDA    $1A1F,X        ; Load orderlist pointer high byte
```

The bytes at $1A1C-$1A21 are: `70 9B B3 1A 1A 1A`

Split format decode:
- Voice 0: $1A70 (file 0x0AEE)
- Voice 1: $1A9B (file 0x0B19)
- Voice 2: $1AB3 (file 0x0B31)

### 2. What's in the "Orderlists"

Analyzing the data at these three addresses shows:
- Transpose markers ($A0+)
- Sequence numbers (0x00-0x26 / 0-38 decimal)
- Loop markers (0xFF)

For example, Voice 0 orderlist ($1A70):
```
A0 0E 0F 0F 0F 0F 11 01 05 01 04...
```

Breaking this down:
- `A0` = Transpose +0
- `0E` = Sequence 14
- `0F` = Sequence 15
- `0F` = Sequence 15
- etc.

From smart analysis, Voice 0 uses sequences: [1, 2, 3, 4, 5, 14, 15, 17, 19, 20, 21, 27, 28, 31, 32]

This MATCHES the bytes we see: 0x0E (14), 0x0F (15), etc.

### 3. Missing Link: Sequence Lookup

**QUESTION**: When the player reads sequence number 0x0E (14) from the orderlist, how does it find the actual sequence data (3-byte entries of instrument/command/note)?

**HYPOTHESIS**:
1. There must be a sequence pointer table mapping 0-38 → addresses
2. OR sequences are stored sequentially and indexed by number × fixed size
3. OR we're misunderstanding the format entirely

## Key Code Section to Understand

```asm
$1089  BC 92 17      LDY    $1792,X        ; Y = current position in orderlist
$108C  B1 FC         LDA    ($FC),Y        ; Read from orderlist at position Y
$108E  10 09         BPL    $1099          ; If bit 7 clear, it's a note
$1090  38            SEC                   ; Bit 7 set = transpose value
$1091  E9 A0         SBC    #$A0           ; Subtract $A0 to get signed transpose
```

This reads from ($FC/$FD)+Y, which is:
- **$FC/$FD** = Orderlist pointer ($1A70, $1A9B, or $1AB3)
- **Y** = Position within orderlist

So it reads DIRECTLY from the orderlist. The bytes it reads are either:
- Transpose markers ($A0+)
- OR sequence numbers

But then what? The code at $108E checks bit 7. If clear, it treats it as "a note". But we know these are sequence NUMBERS (0x0E, 0x0F), not actual note values!

## Possible Explanations

### Theory 1: Two-Level Indexing
The player:
1. Reads sequence number from orderlist
2. Uses that as an index into another pointer table
3. Jumps to that sequence's data
4. Reads 3-byte entries from there

### Theory 2: Hybrid Format
The orderlists contain BOTH:
- Sequence numbers for repeated patterns
- AND inline sequence data for short patterns

### Theory 3: We're Reading Wrong Address
Maybe the pointers at $1A1C aren't for orderlists at all, but for something else?

## Next Steps

1. **Trace through more disassembly** - Find where sequence numbers are used
2. **Look for sequence pointer table** - 39 entries, probably near orderlists
3. **Check if $179B (instrument) relates to sequences** - Line 202 reads from $179B
4. **Use RetroDebugger** - Set breakpoints and watch actual execution

## Files Created

- `analyze_sequences_smart.py` - Found orderlists use 39 unique sequences
- `check_sequence_pointers.py` - Confirmed pointers point to orderlists
- `analyze_orderlist_as_sequences.py` - Shows orderlist contains sequence numbers
- `find_sequence_pointer_table.py` - No standard pointer table found

## Current Status

**STUCK**: We can identify orderlists and see they reference 39 sequences (0-38), but we cannot find where the actual sequence data (3-byte entries) is stored.

**NEED**: Dynamic analysis (RetroDebugger) or deeper disassembly understanding to see how sequence numbers map to sequence data addresses.
