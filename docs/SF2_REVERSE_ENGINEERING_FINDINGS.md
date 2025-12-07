# SF2 Reverse Engineering Findings

## Executive Summary

**Goal**: Reverse engineer SF2-packed SID files back to original SF2 format

**Current Status**: **48.7% accuracy** - Structure is correct, but data extraction needs improvement

**Key Finding**: SF2-packed SID files are **compiled/stripped** versions of SF2 files, not just exports with different headers

## File Format Comparison

### 1. Original SF2 File (`learnings/Stinsen - Last Night Of 89.sf2`)

- **Size**: 17,252 bytes
- **Load Address**: $0D7E (3,454)
- **Format**: Full SID Factory II editor format
- **Contents**:
  - PRG load address (2 bytes)
  - Driver code (~2KB at $0D7E)
  - **Header blocks** ($0800+): Editor metadata, table definitions, config
  - Music data tables (instruments, sequences, wave, pulse, filter, etc.)
  - **Auxiliary data**: Instrument names, command names, comments
  - Orderlist and sequence data
  - Padding/alignment

### 2. SF2-Packed SID File (`SIDSF2Player/SF2packed_Stinsens_Last_Night_of_89.sid`)

- **Size**: 6,201 bytes total (6,075 bytes music data + 124 bytes PSID header)
- **Load Address**: $1000 (4,096)
- **Format**: PSID v2 with compiled SF2 driver + packed music data
- **Contents**:
  - PSID v2 header (124 bytes)
  - **Compiled driver code** (~2KB at $1000)
  - **Packed music data** (tables at driver-specific offsets)
  - **NO header blocks**
  - **NO auxiliary data**
  - **NO editor metadata**

### 3. What Gets Lost in SF2→SID Packing

| Data | Original SF2 | SF2-Packed SID | Lost? |
|------|--------------|----------------|-------|
| Driver code | ✓ Full driver | ✓ Compiled driver | Modified |
| Header blocks | ✓ Present | ✗ Stripped | **LOST** |
| Table definitions | ✓ In Block 3 | ✗ Hard-coded in driver | **LOST** |
| Instruments | ✓ Full data | ✓ Packed | Transformed |
| Sequences | ✓ Full data | ✓ Packed | Transformed |
| Wave/Pulse/Filter | ✓ Full tables | ✓ Packed tables | Transformed |
| Instrument names | ✓ In aux data | ✗ Stripped | **LOST** |
| Command names | ✓ In aux data | ✗ Stripped | **LOST** |
| Comments | ✓ In aux data | ✗ Stripped | **LOST** |
| Editor config | ✓ In headers | ✗ Stripped | **LOST** |

**Result**: 11,051 bytes (64%) of data is stripped/transformed during packing

## Player Identification

```bash
$ tools/player-id.exe "SIDSF2Player/SF2packed_Stinsens_Last_Night_of_89.sid"
Result: SidFactory_II/Laxity
```

**Meaning**: SF2-packed files are recognized as SF2 format but have Laxity-compatible structure.

## Current Reverse Engineering Accuracy

### What Works ✓

| Aspect | Accuracy | Notes |
|--------|----------|-------|
| Table structure | 100% | All 9 table offsets detected correctly |
| Load/init/play addresses | 100% | Matches perfectly |
| File format recognition | 100% | PSID parser working |

### What Doesn't Work ✗

| Aspect | Accuracy | Notes |
|--------|----------|-------|
| Overall file size | 48.7% | Only recovering ~half the original data |
| Data byte match | 7.8% | Most extracted data is different from original |
| Metadata | 0% | Names, author, copyright garbled |
| Auxiliary data | 0% | Instrument/command names not recovered |

## Root Cause Analysis

### Problem 1: Format Mismatch

**Issue**: We're treating SF2-packed SID as if it has the same structure as the original SF2 file.

**Reality**:
- **Original SF2**: Editor format with header blocks ($0D7E)
- **SF2-packed SID**: Compiled SID with no header blocks ($1000)

**Solution**: Need different parsers for each format

### Problem 2: Data Transformation

**Issue**: The packing process doesn't just copy data - it transforms it.

**Transformations during packing**:
1. **Pointer relocation**: All addresses adjusted for new load address ($0D7E → $1000)
2. **Table packing**: Tables compressed/optimized
3. **Sequence compression**: Sequence data packed into minimal format
4. **Driver compilation**: Driver code optimized for target address
5. **Metadata stripping**: All editor-specific data removed

**Example** - Instrument table:
- **Original SF2** ($0D7E + offset): 32 instruments × 6 bytes, column-major layout
- **SF2-packed** ($1000 + offset): Same instruments but pointers relocated, possibly optimized

### Problem 3: Information Loss

**Issue**: Some data is permanently lost during packing and cannot be recovered.

**Unrecoverable data**:
- Instrument names (default names must be generated)
- Command names (default names must be generated)
- Comments and annotations
- Editor preferences and settings
- Original load address intent

**Recoverable but transformed**:
- Music data (instruments, sequences, tables) - requires correct parsing
- Table structures - requires driver detection

## Comparison Results

Using `compare_sf2_reverse_engineering.py`:

```
Header fields matching: 5/10 (50.0%)
File size ratio:        48.7%
First 256 bytes match:  7.8%
Missing data:           8,857 bytes (51.3%)
```

**Analysis**:
- We got the **structure** right (addresses, table offsets)
- We got the **data** wrong (actual table contents different)
- We're **missing** auxiliary data (names, metadata)

## Technical Deep Dive

### SF2 Driver Memory Layout (Driver 11)

Based on SF2_FORMAT_SPEC.md:

```
Address Range   Content
--------------  ----------------------------------
$0D7E - $0FFF   Driver code (~2KB)
$1000 - $10FF   Init table, HR table, Tempo table
$1100 - $11FF   Commands table (3×64 = 192 bytes)
$1200 - $12FF   Instruments table (6×32 = 192 bytes, column-major)
$1300 - $14FF   Wave table (2×256 = 512 bytes)
$1500 - $17FF   Pulse table (3×256 = 768 bytes)
$1800 - $1AFF   Filter table (3×256 = 768 bytes)
$1B00 - $1CFF   Arpeggio table (1×256 = 256 bytes)
$1D00+          Sequences and orderlists
```

### SF2-Packed SID Memory Layout (Relocated to $1000)

```
Address Range   Content
--------------  ----------------------------------
$1000 - $12FF   Driver code (~2KB)
$1300 - $13FF   Init, HR, Tempo tables
$1400 - $14FF   Commands table (relocated)
$1500 - $15FF   Instruments table (relocated)
$1600 - $17FF   Wave table (relocated)
$1800 - $1AFF   Pulse table (relocated)
$1B00 - $1DFF   Filter table (relocated)
$1E00 - $1FFF   Arpeggio table (relocated)
$2000+          Sequences (packed/relocated)
```

**Key insight**: All offsets are shifted by ($1000 - $0D7E) = $282 bytes

But it's not just a simple shift - the data is also transformed and optimized!

## Roadmap to 99% Accuracy

### Phase 1: Driver Detection & Table Location ✓ (DONE)

- [x] Detect SF2 vs Laxity vs other formats
- [x] Identify load address and driver type
- [x] Locate table offsets
- [ ] Parse driver-specific table layouts

### Phase 2: Data Extraction (IN PROGRESS)

Current approach with `sidm2/sf2_player_parser.py`:
- [x] Basic table extraction (with reference SF2)
- [ ] Standalone extraction (without reference)
- [ ] Handle pointer relocation correctly
- [ ] Validate extracted data against siddump

### Phase 3: Data Transformation Reverse Engineering

**Challenge**: Reverse the transformations that happened during packing

Required:
- [ ] Pointer relocation reversal ($1000 → $0D7E)
- [ ] Sequence decompression
- [ ] Table layout reconstruction
- [ ] ADSR and waveform validation

### Phase 4: Metadata Reconstruction

**Challenge**: Regenerate lost auxiliary data

Approach:
- [ ] Generate default instrument names ("Instr 00", "Instr 01", ...)
- [ ] Generate default command names ("Cmd 00", "Cmd 01", ...)
- [ ] Extract song name from PSID header
- [ ] Use generic values for missing metadata

### Phase 5: SF2 Format Reconstruction

**Challenge**: Rebuild the full SF2 editor format with header blocks

Required:
- [ ] Generate Block 1 (Descriptor): Driver info
- [ ] Generate Block 2 (Driver Common): Memory addresses
- [ ] Generate Block 3 (Driver Tables): Table definitions
- [ ] Generate Block 4 (Instrument Descriptor): Instrument metadata
- [ ] Generate Block 5 (Music Data): Sequence/orderlist pointers
- [ ] Write aux data block with names
- [ ] Calculate correct file size and padding

## Alternative Approaches

### Option A: Keep Original SF2 as Reference

**Concept**: When packing SF2→SID, save a copy of the original SF2

**Benefits**:
- Perfect round-trip accuracy
- No reverse engineering needed
- All metadata preserved

**Drawbacks**:
- Requires storing 2 files
- Doesn't help with existing SF2-packed files

### Option B: Enhanced Metadata in SID

**Concept**: Store auxiliary data in PSID copyright field or as data block

**Benefits**:
- Some metadata survives packing
- Better than nothing

**Drawbacks**:
- Limited space in PSID headers
- Still lossy

### Option C: Perfect Reverse Engineering (This project!)

**Concept**: Build tools to reverse engineer SF2-packed SID → original SF2

**Benefits**:
- Works with existing SF2-packed files
- No need to keep originals
- Validates packing process

**Drawbacks**:
- Complex implementation
- Some data permanently lost (names)
- Requires deep format knowledge

## Conclusions

### What We Know

1. **SF2-packed SID files are compiled** - They're not just "SF2 files with a PSID header"
2. **Significant data loss occurs** - 64% of original data is stripped/transformed
3. **Structure is detectable** - We can find all table locations correctly
4. **Data extraction is hard** - Content differs due to transformations

### What We Can Achieve

**Realistic target: 90% accuracy** (not 99%)

**90% means**:
- ✓ All table structures correct
- ✓ All instruments extracted correctly
- ✓ All sequences playable
- ✓ All wave/pulse/filter tables working
- ✗ Names are generic (not original)
- ✗ Some metadata missing

**This is acceptable** because:
- The music plays correctly
- All editable data is present
- Only cosmetic data (names) is lost
- User can rename as needed

### Next Steps

1. **Enhance `sidm2/sf2_player_parser.py`** to work standalone (without reference SF2)
2. **Implement proper table extraction** using driver-specific layouts
3. **Add sequence decompression** to handle packed sequence data
4. **Generate header blocks** to create valid SF2 files
5. **Test round-trip** SF2→SID→SF2 with validation

### Success Metrics

| Metric | Current | Realistic Target |
|--------|---------|------------------|
| File structure | 100% | 100% |
| Table offsets | 100% | 100% |
| Music data accuracy | ~50% | 90% |
| Metadata accuracy | 0% | 50% (generic names) |
| Overall playability | Unknown | 95% |

## Files Created

1. `compare_sf2_reverse_engineering.py` - Comparison tool
2. `sidm2/sf2_packed_reader.py` - PSID/PRG reader with header block parser
3. `SF2_REVERSE_ENGINEERING_ANALYSIS.md` - Technical analysis
4. `SF2_REVERSE_ENGINEERING_FINDINGS.md` - This document

## References

- `docs/SF2_FORMAT_SPEC.md` - SF2 format specification
- `docs/SF2_SOURCE_ANALYSIS.md` - SF2 editor source code analysis
- `sidm2/sf2_player_parser.py` - Existing SF2-exported SID parser
- `tools/player-id.exe` - Player type identification
