# Sequence Investigation Summary

## Current Understanding (Updated)

### Memory Map Discovery

From `STINSENS_PLAYER_DISASSEMBLY.md` line 15:
```
| $199F-$19A5   | Sequence pointers (3 voices × 2 bytes) |
```

These are **RUNTIME pointers** - the current position for each voice, NOT the 39 sequence locations!

### Architecture Hypothesis

**Theory**: The Laxity player doesn't have 39 separate sequence blocks. Instead:

1. **Orderlists** at $1A70, $1A9B, $1AB3 contain the FULL TRACK DATA
2. Each orderlist IS a continuous sequence of 3-byte entries
3. Sequence "numbers" (0x00-0x26) might be:
   - Position offsets within the orderlist
   - OR inline note values, not indices
4. $199F-$19A5 stores current read position for each voice

### Key Code Section

```asm
$107F  BD 1C 1A      LDA    $1A1C,X        ; Load orderlist BASE pointer low
$1084  BD 1F 1A      LDA    $1A1F,X        ; Load orderlist BASE pointer high
$1087  85 FD         STA    $FD            ; Store in $FC/$FD

$1089  BC 92 17      LDY    $1792,X        ; Y = current position WITHIN orderlist
$108C  B1 FC         LDA    ($FC),Y        ; Read byte from orderlist[Y]
```

This reads from: **orderlist_base + current_offset**

The $1792+X locations store the current read offset for each voice within their orderlist.

### What This Means

**There are NO 39 separate sequences!**

The "orderlists" at $1A70, $1A9B, $1AB3 ARE the sequence data. Each voice has ONE long sequence (orderlist) that contains all the music for that voice.

The numbers we saw (0x0E, 0x0F, etc.) are likely:
- **Option A**: Direct note values or instrument numbers
- **Option B**: Offsets/commands within the current voice's data stream

### Next Step

Extract the FULL data from each of the three "orderlists" as the complete sequences for each voice:

1. Voice 0: Start at $1A70 (file 0x0AEE), read until end marker
2. Voice 1: Start at $1A9B (file 0x0B19), read until end marker
3. Voice 2: Start at $1AB3 (file 0x0B31), read until end marker

These ARE the sequences we need!

## Files to Create

1. `extract_three_voice_sequences.py` - Extract full sequence data for all 3 voices
2. Test extraction by checking lengths and patterns
3. Inject into Driver 11 SF2 format

## Previous Misconceptions

- ❌ Thought there were 39 separate sequence blocks
- ❌ Thought orderlists just contained sequence NUMBER references
- ❌ Searched for a 39-entry pointer table that doesn't exist

## Correct Understanding

- ✅ There are 3 voice tracks (orderlists)
- ✅ Each voice has ONE continuous sequence
- ✅ Orderlists at $1A70, $1A9B, $1AB3 ARE the full sequence data
- ✅ $199F-$19A5 are runtime read pointers, not sequence lookup table

## Resolution

The confusion came from expecting a GoatTracker-style format (sequences + orderlists) when Laxity uses a simpler format (just 3 voice tracks).

**Next action**: Extract the three voice sequences and inject into SF2.
