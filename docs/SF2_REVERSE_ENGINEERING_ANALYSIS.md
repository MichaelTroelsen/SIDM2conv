# SF2 Reverse Engineering Analysis

## Overview

This document analyzes the accuracy of reverse engineering SF2 files from SF2-packed SID files.

**Test case**: Stinsen's Last Night of '89
- Original SF2: `learnings/Stinsen - Last Night Of 89.sf2` (17,252 bytes)
- Exported SID: `SIDSF2Player/SF2packed_Stinsens_Last_Night_of_89.sid` (6,075 bytes)
- Reverse-engineered SF2: `output/Stinsens_SF2Packed/New/Stinsens_SF2Packed_d11.sf2` (8,395 bytes)

## Current Accuracy: 48.7%

### What's Working ✓

| Aspect | Status |
|--------|--------|
| **Table Structure** | 100% accurate - All 9 tables found at correct offsets |
| Load Address | ✓ $0744 (matches) |
| Init Address | ✓ $1209 (matches) |
| Play Address | ✓ $1605 (matches) |
| Commands Table | ✓ $1100 offset correct |
| Instruments Table | ✓ $1040 offset correct |
| Wave Table | ✓ $11E0 offset correct |
| Pulse Table | ✓ $13E0 offset correct |
| Filter Table | ✓ $16E0 offset correct |
| Arpeggio Table | ✓ $19E0 offset correct |
| Tempo Table | ✓ $1AE0 offset correct |
| HR Table | ✓ $0F40 offset correct |
| Init Table | ✓ $0F20 offset correct |

### What's Missing ✗

| Issue | Impact |
|-------|--------|
| **File Size** | 51.3% smaller (8,857 bytes missing) |
| **Data Accuracy** | Only 7.8% of first 256 bytes match |
| **Metadata** | Name, author, copyright garbled |
| **Sequences** | Not extracted from packed format |
| **Auxiliary Data** | Instrument names, command names missing |

## Root Cause Analysis

### Problem: Format Mismatch

Our converter treats SF2-packed SID files as **Laxity format**, but they are actually **SF2 packed format**:

| Aspect | Laxity Format | SF2 Packed Format |
|--------|---------------|-------------------|
| Player code | ~2KB player at $1000 | Compact driver at load address |
| Table layout | Fixed offsets | Driver-specific offsets |
| Sequences | Uncompressed in memory | Packed/compressed |
| Tables | Direct data | Compiled/optimized |

### Current Converter Behavior

1. **Reads SF2-packed SID** → Treats as Laxity
2. **Searches for Laxity patterns** → Finds wrong data
3. **Extracts using Laxity logic** → Gets corrupted tables
4. **Writes to SF2 template** → Creates new file with wrong data

### What We Need

A **specialized SF2-packed SID parser** that:
1. Recognizes SF2 packed format (identifies driver type)
2. Locates packed tables using SF2 driver structure
3. Extracts sequences from compressed format
4. Preserves auxiliary data (names, metadata)
5. Reconstructs original SF2 file

## Technical Details

### SF2 Packed Format Structure

When SF2 exports to SID, it:
1. Loads appropriate driver (11, 12, 13, etc.)
2. Packs music data into driver tables
3. Compresses sequences
4. Relocates pointers for target address
5. Strips auxiliary data (names stored separately)

### Reverse Engineering Requirements

To achieve 99%+ accuracy, we need to:

#### 1. Driver Detection
```python
def detect_sf2_driver(sid_data, load_addr):
    """Detect which SF2 driver was used."""
    # Check for driver ID marker at $1337 offset
    # Identify driver version (11, 12, 13, 14, 15, 16, NP20)
    # Return driver configuration
```

#### 2. Table Extraction
```python
def extract_sf2_tables(sid_data, driver_config):
    """Extract tables using driver-specific layout."""
    # Use DriverInfo structure from SF2 source
    # Read table definitions (type, layout, address, dimensions)
    # Extract raw table data
```

#### 3. Sequence Decompression
```python
def decompress_sequences(sequence_data):
    """Decompress packed sequence data."""
    # Parse packed format
    # Reconstruct event structure (instrument, command, note)
    # Handle compression markers
```

#### 4. Auxiliary Data Recovery
```python
def reconstruct_aux_data(table_data):
    """Reconstruct instrument/command names."""
    # Generate default names if not stored
    # Match SF2 naming conventions
```

## Comparison Results

### Header Comparison

| Field | Original | Reverse-Eng | Match |
|-------|----------|-------------|-------|
| name | "00 - T S   (  - T S   (" | "w             A" | NO |
| author | "w             A" | "" | NO |
| copyright | "C   @       C  D @ I" | "" | NO |
| load_addr | $0744 | $0744 | YES |
| init_addr | $1209 | $1209 | YES |
| play_addr | $1605 | $1605 | YES |
| songs | 4640 | 4640 | YES |
| start_song | 12593 | 12593 | YES |
| data_size | 17,134 | 8,277 | NO |
| total_size | 17,252 | 8,395 | NO |

### Size Analysis

- **Original size**: 17,252 bytes
- **Reverse-eng size**: 8,395 bytes
- **Missing**: 8,857 bytes (51.3%)

### First 256 Bytes Match

- **Matching bytes**: 20/256 (7.8%)
- **Issue**: Most data is different, suggesting we're creating new data instead of extracting original

## Roadmap to 99% Accuracy

### Phase 1: SF2 Format Detection (Week 1)
- [ ] Implement driver detection
- [ ] Parse driver configuration
- [ ] Identify table locations
- [ ] Extract table metadata

### Phase 2: Direct Table Extraction (Week 2)
- [ ] Read tables using driver layout
- [ ] Validate table sizes and dimensions
- [ ] Handle row-major vs column-major
- [ ] Extract all 9 table types

### Phase 3: Sequence Reconstruction (Week 3)
- [ ] Parse packed sequence format
- [ ] Decompress sequence data
- [ ] Reconstruct event stream
- [ ] Handle orderlists

### Phase 4: Auxiliary Data (Week 4)
- [ ] Extract/generate instrument names
- [ ] Extract/generate command names
- [ ] Reconstruct metadata
- [ ] Validate against original

### Phase 5: Integration & Testing
- [ ] Create SF2PlayerParser class
- [ ] Integrate with sid_to_sf2.py
- [ ] Test with all SF2-packed files
- [ ] Validate round-trip accuracy

## Implementation Strategy

### Option A: Use Existing SF2PlayerParser

We already have `sidm2/sf2_player_parser.py` (389 lines) which:
- Parses SF2-exported SID files
- Pattern-based table extraction
- Tested with 15 SIDSF2player files
- **Current status**: Works with matching SF2 reference

**Enhancement needed**:
- Make it work without reference SF2
- Add heuristic extraction mode
- Improve table detection accuracy

### Option B: Create New SF2ReverseEngineer Module

Build dedicated reverse engineering tool:
- Focused on SF2→SID→SF2 round-trip
- Uses SF2 source code patterns
- Direct memory structure analysis
- 99% accuracy target

## Next Steps

1. **Enhance SF2PlayerParser** for standalone operation
2. **Create test suite** comparing original vs reverse-engineered
3. **Implement driver detection** to identify SF2 vs Laxity format
4. **Extract tables directly** from packed SID using driver layout
5. **Validate accuracy** on all test cases

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| File size accuracy | 48.7% | 95%+ |
| Data byte match | 7.8% | 99%+ |
| Table structure | 100% | 100% |
| Metadata recovery | 0% | 90%+ |
| Sequence accuracy | Low | 99%+ |

## Conclusion

**Current state**: We can identify the correct structure but extract wrong data (48.7% accurate).

**Root cause**: Treating SF2-packed format as Laxity format.

**Solution**: Build specialized SF2-packed SID parser using driver detection and direct table extraction.

**Effort estimate**: 4 weeks for 99% accuracy.

**Priority**: HIGH - This enables true SF2→SID→SF2 round-trip validation.
