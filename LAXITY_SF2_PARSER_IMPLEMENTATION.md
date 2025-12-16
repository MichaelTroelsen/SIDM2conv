# Laxity SF2 Sequence Parser Implementation

**Date**: 2025-12-16
**Status**: IMPLEMENTATION PLAN
**Goal**: Fix sequence parsing to read from correct file offset

---

## Problem Analysis

Current implementation reads from wrong file offset:
- **Current behavior**: Reads from 0x1662 (offset table + padding)
- **Expected behavior**: Should read from 0x1772 (actual sequence data)
- **Result**: 0xE1 padding bytes appear as notes instead of proper note values

### File Structure (Laxity SF2)

```
File Offset    Content                    Size      Purpose
-----------    -------                    ----      -------
0x1662-0x1664  24 25 26                   3 bytes   Header/offset pointers
0x1665-0x1710  E1 E1 E1... (repeated)     175 bytes Padding/filler
0x1711-0x1771  27 28 29...a6              97 bytes  Index table (128 sequential entries)
0x1772+        a0 0e 0f... (valid data)   variable  ACTUAL SEQUENCE DATA
```

### Key Markers

- **0xA0 markers**: Indicate instrument selection OR sequence start
- **0x7F marker**: Sequence terminator
- **0xE1 bytes**: Padding (should be skipped)
- **Valid control bytes**: 0xC0-0xFF (command), 0xA0-0xBF (instrument), 0x80-0x9F (duration)

---

## Implementation Strategy

### Step 1: Detect Offset Table Structure

Look for pattern:
1. Start with 3 bytes (offset pointers)
2. Followed by many 0xE1 bytes (175 minimum)
3. Then index table with ascending bytes
4. Then 0xA0 marker indicating real sequence data

### Step 2: Skip to Real Data

Once offset table detected:
1. Skip 3-byte header
2. Skip all 0xE1 padding (up to 175 bytes)
3. Skip index table (sequential bytes)
4. Start parsing from first 0xA0 marker

### Step 3: Parse Sequences

Use existing `unpack_sequence()` function but:
1. Start from correct offset (0x1772)
2. Let 0x7F terminator signal end of sequence
3. Skip padding between sequences (0x00 bytes)
4. Stop when hitting invalid data or end of file

### Step 4: Handle 0xA0 Markers

- First 0xA0 in packed data = instrument selection
- Subsequent 0xA0s in same sequence = instrument changes
- 0xA0 at start of new sequence = new instrument start

---

## Detection Algorithm

```python
def _detect_laxity_offset_table(data: bytes, start_offset: int = 0x1600) -> Optional[int]:
    """
    Detect Laxity offset table structure.

    Returns: File offset of real sequence data (0x1772-equivalent) if found
    """

    # Look for start of offset table
    for offset in range(start_offset, min(len(data), 0x1800)):
        # Pattern: 3 bytes + many 0xE1 bytes + index table + 0xA0 marker

        # Check for 3-byte header followed by 0xE1 padding
        if offset + 180 >= len(data):
            continue

        # Look for 0xE1 padding block (at least 150 bytes)
        padding_start = offset + 3
        e1_count = 0
        for i in range(padding_start, min(padding_start + 200, len(data))):
            if data[i] == 0xE1:
                e1_count += 1
            else:
                break

        if e1_count < 150:  # Need substantial padding block
            continue

        # After padding, expect index table (sequential ascending bytes)
        index_start = padding_start + e1_count
        is_index_table = True
        if index_start + 32 < len(data):
            for i in range(index_start, min(index_start + 32, len(data))):
                # Index table should have bytes that generally increase or repeat
                # Skip strict validation - just look for reasonable pattern
                pass

        # Real data should start with 0xA0 marker after index table
        data_start = index_start + 128  # Approximate index table size
        if data_start < len(data) and (data[data_start] == 0xA0 or
                                       0x01 <= data[data_start] <= 0x7E):
            # Found it!
            return data_start

    return None
```

---

## Implementation in sf2_viewer_core.py

### New Method: `_parse_packed_sequences_laxity_sf2()`

```python
def _parse_packed_sequences_laxity_sf2(self):
    """
    Parse sequences from Laxity SF2 files.

    Handles offset table structure:
    - Offset table at 0x1662 with 0xE1 padding
    - Index table follows padding
    - Real sequence data starts at 0x1772 with 0xA0 markers
    """

    # Detect where real sequence data starts
    seq_data_offset = self._detect_laxity_offset_table_structure()
    if seq_data_offset is None:
        logger.warning("Could not detect Laxity offset table structure")
        return False

    logger.info(f"Detected Laxity offset table structure, real data at 0x{seq_data_offset:04X}")

    self.sequences = {}
    seq_idx = 0
    offset = seq_data_offset

    # Parse sequences from correct offset
    while offset < len(self.data) and seq_idx < self.MAX_SEQUENCES:
        # Look for 0xA0 marker (instrument selection) indicating sequence start
        # Skip padding bytes (0x00 or other non-data)
        while offset < len(self.data) and self.data[offset] not in [0xA0, 0xC0] and not (0x01 <= self.data[offset] <= 0x7E):
            offset += 1

        if offset >= len(self.data):
            break

        # Extract sequence bytes until 0x7F terminator
        seq_start = offset
        seq_bytes = bytearray()

        while offset < len(self.data):
            byte = self.data[offset]
            seq_bytes.append(byte)
            offset += 1

            if byte == 0x7F:  # End of sequence
                break

        if not seq_bytes or len(seq_bytes) < 5:
            # Too short, skip
            continue

        # Unpack and convert to SequenceEntry format
        events = unpack_sequence(bytes(seq_bytes))
        entries = []
        for event in events:
            entry = SequenceEntry(
                note=event['note'],
                instrument=event['instrument'],
                command=event['command'],
                param1=0,
                param2=0,
                duration=event['duration']
            )
            entries.append(entry)

        if entries:
            self.sequences[seq_idx] = entries
            logger.info(f"Sequence {seq_idx}: {len(entries)} entries")
            seq_idx += 1

        # Stop if parsed enough sequences
        if seq_idx > 1 and offset > seq_data_offset + 1200:
            break

    logger.info(f"Parsed {len(self.sequences)} sequences from Laxity SF2 offset table")
    return len(self.sequences) > 0


def _detect_laxity_offset_table_structure(self) -> Optional[int]:
    """
    Detect Laxity offset table structure in SF2 file.

    Laxity SF2 files contain:
    - Offset table with header (3 bytes)
    - Padding block (0xE1 bytes, ~175 bytes)
    - Index table (sequential entries)
    - Actual sequence data (starts with 0xA0 marker)

    Returns: File offset where real sequence data begins
    """

    # Look for offset table structure starting around 0x1600
    search_start = 0x1600
    search_end = min(len(self.data), 0x1800)

    for table_start in range(search_start, search_end - 200):
        # Look for 0xE1 padding block (at least 150 consecutive 0xE1 bytes)
        padding_start = table_start + 3  # Skip potential 3-byte header
        e1_count = 0

        for i in range(padding_start, min(padding_start + 200, len(self.data))):
            if self.data[i] == 0xE1:
                e1_count += 1
            else:
                break

        if e1_count < 150:
            continue  # Not enough padding

        # After padding, there should be an index table
        # Then real sequence data should start
        index_start = padding_start + e1_count

        # Real data typically starts 128+ bytes after index
        # (allowing for index table of reasonable size)
        data_candidates = []
        for potential_data_start in range(index_start + 100, min(index_start + 150, len(self.data))):
            byte = self.data[potential_data_start]

            # Valid sequence start:
            # - 0xA0-0xBF (instrument marker)
            # - 0x01-0x7E (note value)
            # - Followed by more packed data pattern
            if 0x01 <= byte <= 0x7E or 0xA0 <= byte <= 0xBF:
                # Check if it looks like real sequence data
                # Should have multiple control bytes nearby
                has_packed_pattern = False
                for check in range(potential_data_start + 1, min(potential_data_start + 20, len(self.data))):
                    b = self.data[check]
                    if 0xA0 <= b <= 0xFF or b == 0x7F:  # Packed sequence markers
                        has_packed_pattern = True
                        break

                if has_packed_pattern:
                    data_candidates.append(potential_data_start)

        if data_candidates:
            # Return the first valid candidate (most likely correct)
            return data_candidates[0]

    return None
```

---

## Validation

After implementation, verify:

1. **Offset Detection**: Correctly identifies 0x1772 as data start
2. **Sequence Parsing**: Reads all sequences without 0xE1 bytes as notes
3. **Data Correctness**: Chromatic scale (C-3, C#-3, D-3) displays correctly
4. **Format Match**: Matches SID Factory II reference format
5. **Test File**: Laxity - Stinsen - Last Night Of 89.sf2 should show:
   - 2 sequences found (not more due to 0xE1 padding being parsed)
   - Valid note values (not 0xE1 bytes)
   - Proper 3-track parallel display

---

## Files to Modify

- **sf2_viewer_core.py**:
  - Add `_detect_laxity_offset_table_structure()` method
  - Add `_parse_packed_sequences_laxity_sf2()` method
  - Update `_parse_packed_sequences()` to use new Laxity-specific parser

---

## Integration Points

1. In `_parse_sequences()` method, add check:
   ```python
   # For Laxity driver files, use improved offset table parsing
   if self.is_laxity_driver:
       if self._parse_packed_sequences_laxity_sf2():
           return

   # Fallback to generic packed sequence parsing
   self._parse_packed_sequences()
   ```

2. Update fallback chain to prioritize Laxity-specific parser

---

## Expected Results

### Before Fix
```
Sequence data showing:
- 0xE1 bytes appearing as notes
- Invalid note values
- Wrong display format
```

### After Fix
```
Sequence data showing:
- Proper note values (C-3, C#-3, D-3, etc.)
- Valid duration and instrument bytes
- Correct 3-track parallel display matching SID Factory II
```

