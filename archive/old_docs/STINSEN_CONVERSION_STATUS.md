# Stinsen Conversion Status

**Source**: `SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid`
**Target**: SF2 Driver 11 format
**Date**: 2025-12-08

## Conversion Progress

### ✅ COMPLETED TABLES

#### 1. Pulse Table
- **Status**: ✅ Complete
- **Location**: SF2-packed offset varies
- **Format**: Driver 11 format (4 bytes per entry)
- **Notes**: Successfully extracted and validated

#### 2. Wave Table
- **Status**: ✅ Complete
- **Location**: SF2-packed offset varies
- **Format**: (waveform, note_offset) pairs
- **Notes**: Successfully extracted and validated

#### 3. Filter Table
- **Status**: ✅ Complete
- **Location**: SF2-packed offset varies
- **Format**: 4-byte filter sweep entries
- **Notes**: Successfully extracted and validated

#### 4. Instruments Table
- **Status**: ✅ Complete
- **Location**: SF2-packed offset varies
- **Format**: Column-major, 6 bytes per instrument
- **Notes**: Successfully extracted and validated

#### 5. Arpeggio Table
- **Status**: ✅ Complete
- **Location**: SF2-packed offset varies
- **Format**: Semitone offset patterns
- **Notes**: Successfully extracted and validated

#### 6. Commands Table
- **Status**: ✅ Complete
- **Location**: SF2-packed offset varies
- **Format**: 3-byte command entries
- **Notes**: Successfully extracted and validated

#### 7. Tempo Table
- **Status**: ✅ Complete
- **Location**: SF2-packed ends at 0x0A9A
- **Format**: Speed values with 7F wrap marker
- **Notes**: Successfully extracted and validated

### 🔄 IN PROGRESS

#### 8. Order List (Song List)
- **Status**: 🔄 Partially working
- **Source locations**:
  - Voice 0: 0x0AEE
  - Voice 1: 0x0B1A
  - Voice 2: 0x0B31
- **Target addresses**: $242A, $252A, $262A
- **Format tested**:
  - ✅ Compact format with 256-byte blocks - LOADS but wrong row numbering
  - ✅ Expanded XXYY format - LOADS but wrong row numbering
  - ❌ Row-major format - CRASHES editor
- **Data validation**: ✅ Content is correct
  - Voice 0: 0E 0F 0F 0F 0F 11 01...
  - Voice 1: 00 12 06 06 06 07...
  - Voice 2: 0A 0A 0B 0C 0A 10...
- **Issue**: Row numbering displays byte offsets instead of sequence row numbers
- **Files created**:
  - `convert_orderlist_to_driver11.py` - Extracts compact format
  - `inject_orderlists_original_format.py` - Injects with 256-byte blocks
  - `expand_orderlist_to_fixed_rows.py` - Creates expanded XXYY format
  - `inject_orderlists_row_major.py` - Creates row-major format (crashes)
- **Output files**:
  - `output/orderlist_voice{0,1,2}_driver11.bin` - Extracted compact orderlists
  - `output/Stinsens_Last_Night_of_89_WITH_ORDERLISTS_256BYTE_BLOCKS.sf2` - Compact format
  - `output/Stinsens_Last_Night_of_89_WITH_ORDERLISTS_EXPANDED.sf2` - Expanded format

#### 9. Tracks/Sequences
- **Status**: ✅ Extracted and injected (CORRECTED)
- **Source locations** (split pointer format at $1A1C-$1A21):
  - Track 1 (Voice 0): $1A70-$1A9B (43 bytes)
  - Track 2 (Voice 1): $1A9B-$1AB3 (24 bytes)
  - Track 3 (Voice 2): $1AB3-$1AEE (59 bytes)
  - **Total**: 126 bytes (NOT 670 bytes as previously thought)
- **Pointer format**: Split format (low bytes at $1A1C-$1A1E, high bytes at $1A1F-$1A21)
- **Format**: 3 bytes per entry [Instrument] [Command] [Note]
- **Notes**: Three separate contiguous track blocks, stacked in SF2
- **Files created**:
  - `extract_sequences_correct.py` - Correct extraction using pointers
  - `inject_sequences_correct.py` - Inject corrected sequences
- **Output files**:
  - `output/track{1,2,3}_sequences.bin` - Individual track extractions
  - `output/sequences_combined_correct.bin` - Combined 126 bytes
  - `output/Stinsens_Last_Night_of_89_WITH_SEQUENCES_CORRECT.sf2` - SF2 with correct sequences
- **Next step**: Test in SID Factory II to verify row numbering fix

### ❌ NOT STARTED

#### 10. HR Table (Hard Restart)
- **Status**: ❌ Not started
- **Location**: Unknown in SF2-packed
- **Format**: (AD, SR) pairs per instrument
- **Default values**: 0F 00 (fast attack, immediate decay)
- **Note**: Prevents SID's "ADSR bug"

#### 11. INIT Table
- **Status**: ❌ Not started
- **Location**: Unknown in SF2-packed
- **Format**: (tempo_row, volume) pair
- **Note**: Song initialization parameters

## Key Findings

### Orderlist Format Discovery

1. **Compact Format**:
   - Format: `TT [SS SS SS...]` where TT=transpose marker, SS=sequence numbers
   - Transpose markers (A0, A2, AC, etc.) only included when changing
   - End markers: 0xFF (loop) or 0xFE (end)

2. **Storage Layout**:
   - Driver 11 uses separate 256-byte blocks per voice
   - Memory addresses: $242A, $252A, $262A
   - Pointers at: $2324-$2329 (lo bytes, then hi bytes)

3. **Display Issue**:
   - Content is correct but row numbering shows byte offsets
   - Expected: 0000, 0020, 0040 (sequence row numbers)
   - Actual: 0000, 001c, 0100, 0124 (byte offsets in compact format)
   - May be related to sequence structure, not orderlist

### Format Variations Tested

| Format | Storage | Row Numbering | Editor Result |
|--------|---------|---------------|---------------|
| Compact 256-byte blocks | Column-major | Byte offsets | ✅ Loads, ❌ Wrong rows |
| Expanded XXYY | Column-major | Entry offsets | ✅ Loads, ❌ Wrong rows |
| Row-major 32-byte rows | Row-major | Fixed increments | ❌ Crashes |

### Sequence Extraction Discovery (CORRECTED)

1. **Sequence Pointers** (split format):
   - Location: Memory $1A1C-$1A21 (file offset 0x0A9A-0x0A9F)
   - Format: [low0, low1, low2, high0, high1, high2]
   - Decoded pointers:
     - Voice 0: $1A70 (file offset 0x0AEE)
     - Voice 1: $1A9B (file offset 0x0B19)
     - Voice 2: $1AB3 (file offset 0x0B31)

2. **Track Structure**:
   - **Track 1** (Voice 0): 43 bytes, ends at Voice 1 start
   - **Track 2** (Voice 1): 24 bytes, ends at Voice 2 start
   - **Track 3** (Voice 2): 59 bytes, ends at orderlist start ($1AEE)
   - **Total**: 126 bytes (NOT 670 as previously thought)
   - Format: 3 bytes per entry [Instrument] [Command] [Note]

3. **Key Discovery**:
   - Previous extraction (0x07FC-0x0A9A, 670 bytes) was WRONG
   - That region contained orderlist data, not sequences
   - Actual sequences are pointed to by split pointer table
   - Each voice has separate contiguous sequence block

4. **Integration**:
   - Extracted using `extract_sequences_correct.py`
   - Combined into 126-byte block
   - Saved to `sequences_combined_correct.bin`
   - Injected into SF2 template at file offset 0x19B4
   - Output: `Stinsens_Last_Night_of_89_WITH_SEQUENCES_CORRECT.sf2`

## Next Steps

### Immediate Priority
1. ✅ **Test sequence injection** - Load in SID Factory II and verify row numbering
2. 📋 Extract HR table from SF2-packed
3. 📋 Extract INIT table from SF2-packed
4. 🧪 Test complete conversion with all 11 tables

## File Locations

### Input Files
- `SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid` - Source SF2-packed
- `learnings/Laxity - Stinsen - Last Night Of 89.sf2` - Original reference (17KB)

### Template Files
- `output/Stinsens_Last_Night_of_89_ALL_7_TABLES.sf2` - Base template (8436 bytes)

### Output Files
- `output/Stinsens_Last_Night_of_89_WITH_ORDERLISTS_256BYTE_BLOCKS.sf2` - Compact format (orderlists only)
- `output/Stinsens_Last_Night_of_89_WITH_ORDERLISTS_EXPANDED.sf2` - Expanded XXYY format (orderlists only)
- `output/Stinsens_Last_Night_of_89_WITH_SEQUENCES.sf2` - **Latest with sequences** (8/11 tables)
- `output/orderlist_voice{0,1,2}_driver11.bin` - Extracted compact orderlists
- `output/sequences_extracted.bin` - Extracted sequence table (670 bytes)

### Scripts Created
- `convert_orderlist_to_driver11.py` - Extract compact orderlists
- `expand_orderlist_to_fixed_rows.py` - Create expanded XXYY format
- `extract_and_inject_sequences.py` - **Extract and inject sequence table**

### Experimental Scripts (temp-exp/)
- `analyze_orderlist_location.py` - Locate orderlist patterns
- `decode_orderlist.py` - Parse compact format
- `inject_orderlists_to_sf2.py` - First injection attempt (wrong addresses)
- `inject_orderlists_original_format.py` - Inject with correct Driver 11 addresses
- `inject_orderlists_row_major.py` - Create row-major format (crashes editor)
- `analyze_sequence_structure.py` - Analyze sequence data patterns
- `examine_table_boundaries.py` - Find table boundaries in SID file
- `extract_sequence_table.py` - Validate sequence extraction
- `find_sequence_start.py` - Search for sequence start offset
- `analyze_sf2_sequence_layout.py` - Analyze SF2 sequence layout

## Known Issues

1. **Row Numbering**: Need to test if sequence injection fixes the display issue
2. **HR Table**: Not yet extracted
3. **INIT Table**: Not yet extracted

## Questions Resolved

1. ✅ **Sequence location**: Found at 0x07FC-0x0A9A in SF2-packed file
2. ✅ **Sequence format**: 3 bytes per entry, contiguous stacking, persistence encoding
3. ✅ **Row numbers**: Appear to be byte offsets into sequence table

## Questions Remaining

1. Where are HR and INIT tables in SF2-packed format?
2. Will sequence injection fix the orderlist row numbering display?
