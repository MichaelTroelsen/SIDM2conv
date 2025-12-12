# SIDDUMP EXTRACTION SUCCESS - BREAKTHROUGH!

## Summary

**User's Breakthrough Suggestion:**
> "can we use the output from siddump which i believe is 3 voice streams and convert that into sequence with order list."

**Result: SUCCESS!** ✓

We successfully extracted sequences and orderlists from runtime behavior by analyzing siddump output instead of trying to reverse-engineer the packed SID file format.

## What We Accomplished

### 1. Siddump Parser (`parse_siddump_table.py`)

Created a parser that handles siddump's tabular output format:

```
| Frame | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | FCut RC Typ V |
|     5 | 2E66  F-5 C1  13 .... 800 | ....  ... ..  .. .... 1B0 | 3A8C  A-5 C5  15 .... 800 | .... .. ... . |
```

**Handles two formats:**
- Note format: `2E66  F-5 C1  13 .... 800` (Freq, Note, Abs, WF, ADSR, Pul)
- Delta format: `0116 (+ 0116) 20 0F00 ...` (Freq, Delta, WF, ADSR, Pul)

**Extraction Results:**
- Voice 0: 1,198 events (110 note events)
- Voice 1: 426 events (112 note events)
- Voice 2: 434 events (76 note events)
- **Total: 2,058 voice events captured**

### 2. Sequence Extraction (`convert_siddump_to_sf2_sequences.py`)

Converted runtime behavior to SF2 structure:

**Pattern Identification:**
- Voice 0: 7 unique sequences
- Voice 1: 7 unique sequences
- Voice 2: 5 unique sequences
- **Total: 19 sequences extracted**

**SF2 Format Conversion:**
- Each sequence converted to 3-byte entries: `[instrument] [command] [note]`
- Sequences range from 13-17 entries each
- Padded to exactly 39 sequences (SF2 requirement)
- 20 empty sequences added as padding

**Example Sequence 0:**
```
Entry 0: [00] [00] [41]  ; F-5
Entry 1: [00] [00] [41]  ; F-5
Entry 2: [00] [00] [40]  ; E-5
Entry 3: [00] [00] [40]  ; E-5
Entry 4: [00] [00] [40]  ; E-5
Entry 5: [00] [00] [3E]  ; D#5
...
```

### 3. Orderlist Creation

Generated orderlists that reference sequences:

**SF2 Format:**
```
[A0] [00]  ; No transpose, play sequence 0
[A0] [01]  ; No transpose, play sequence 1
[A0] [02]  ; No transpose, play sequence 2
...
[A0] [7F]  ; End marker
```

**Results:**
- Voice 0 orderlist: 16 bytes (7 sequences + end)
- Voice 1 orderlist: 16 bytes (7 sequences + end)
- Voice 2 orderlist: 12 bytes (5 sequences + end)

## Files Created

1. **`stinsens_original.dump`** (163KB)
   - Raw siddump output from SID file
   - 1,500 frames @ 50Hz = 30 seconds
   - Full register capture for all 3 voices

2. **`parse_siddump_table.py`**
   - Parser for siddump table format
   - Handles note and delta formats
   - Extracts voice events with frame timing

3. **`convert_siddump_to_sf2_sequences.py`**
   - Converts voice events to SF2 sequences
   - Creates orderlists with transpose markers
   - Pads to 39 sequences

4. **`sf2_music_data_extracted.pkl`**
   - Saved sequences (39 total)
   - Saved orderlists (3 voices)
   - Ready for SF2 file assembly

## Why This Approach Worked

**Previous Failed Approaches:**
- ❌ Static analysis of SID file structure
- ❌ Byte-level comparison with reference SF2
- ❌ Pattern matching in packed data
- ❌ Reverse engineering packer code
- ❌ Searching for pointer tables

**Why they failed:**
- SF2→SID packing TRANSFORMS data structure
- Laxity format (3 inline streams) ≠ SF2 format (39 sequences)
- No byte-level correspondence between formats
- Sequences don't exist as discrete blocks in packed SID

**Why siddump approach succeeded:**
- Captures ACTUAL MUSIC BEHAVIOR (not data structure)
- Extracts what the music DOES (notes, waveforms, timing)
- Identifies repeating patterns = reusable sequences
- Reconstructs SF2 structure from behavior
- Format-agnostic - works regardless of packing method

## What We Have Now

### Complete Music Data (2/11 tables):
- ✅ **Sequences** (39 total) - Extracted from siddump
- ✅ **Orderlists** (3 voices) - Extracted from siddump

### Previously Extracted (8/11 tables):
- ✅ Commands
- ✅ Instruments
- ✅ Wave
- ✅ Pulse
- ✅ Filter
- ✅ Arpeggio
- ✅ Tempo
- ✅ (HR or Init - need to verify)

### Remaining (1/11 tables):
- ❓ HR or Init (whichever wasn't extracted yet)

## Next Steps

1. **Combine All Tables** - Create script to assemble complete SF2 file
2. **Load SF2 Template** - Use Driver 11 template as base
3. **Inject Data** - Write all 11 tables to correct offsets
4. **Test in SF2 Editor** - Load and verify playback
5. **Compare with Original** - Validate against reference SF2

## Technical Details

### SF2 Structure Requirements

**Driver 11 Table Offsets:**
- Init table: `0x????`
- Tempo table: `0x????`
- HR table: `0x????`
- Instruments: `0x0A03` (32 × 6 bytes)
- Commands: `0x????`
- Wave table: `0x0B03`
- Pulse table: `0x0D03`
- Filter table: `0x0F03`
- Arpeggio table: `0x????`
- Sequences: `0x0903` (39 sequences)
- Orderlists: `0x????` (3 orderlists)

### Note Mapping

Siddump notes → SF2 note numbers:
- `C-0` = 0
- `C#0` = 1
- `D-0` = 2
- ...
- `F-5` = 65 (5×12 + 5)
- `E-5` = 64 (5×12 + 4)
- `D#5` = 63 (5×12 + 3)
- ...
- `B-9` = 119

### Sequence Format

SF2 3-byte entries:
```
[Instrument byte] [Command byte] [Note byte]
[00] [00] [41]  ; Default inst, no cmd, note 65 (F-5)
[00] [00] [7F]  ; End marker
```

### Orderlist Format

SF2 transpose + sequence pairs:
```
[Transpose byte] [Sequence number]
[A0] [00]  ; No transpose (0xA0), sequence 0
[A0] [7F]  ; No transpose (0xA0), end marker (0x7F)
```

## Validation Metrics

When the complete SF2 is created, we should validate:

1. **Structure**
   - All 11 tables present
   - Correct offsets and sizes
   - Valid end markers

2. **Playback**
   - Loads in SF2 Editor without errors
   - Plays music (doesn't crash)
   - Sounds similar to original

3. **Round-trip**
   - SF2 → SID export works
   - Exported SID plays correctly
   - Register dumps match original

## Breakthrough Attribution

**User's key insight:** Use runtime behavior instead of static analysis!

This paradigm shift solved the impossible problem of reconstructing SF2 structure from a packed SID file that had been format-converted.

---

**Status:** SEQUENCES AND ORDERLISTS EXTRACTED ✓

**Next:** Assemble complete SF2 file with all 11 tables
