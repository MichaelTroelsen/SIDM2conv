# Architecture Documentation

## System Overview

The SID to SF2 converter transforms Commodore 64 SID music files into SID Factory II format, enabling editing and remixing of classic chiptunes.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  SID File   │ ──► │  Converter   │ ──► │  SF2 File   │
│  (Input)    │     │   Pipeline   │     │  (Output)   │
└─────────────┘     └──────────────┘     └─────────────┘
```

## Conversion Pipeline

### Stage 1: SID Parsing

```python
SIDParser(filepath)
```

1. Read binary SID file
2. Parse PSID/RSID header (124 bytes)
3. Extract metadata (name, author, copyright)
4. Identify load address and data offset
5. Load music data into memory model

**Key Classes:**
- `PSIDHeader` - Header data structure
- `SIDParser` - File parsing and memory loading

### Stage 2: Player Identification

```bash
tools/player-id.exe input.sid
```

1. Run external player identification tool
2. Parse output for player type
3. Select appropriate extraction strategy
4. Currently only Laxity NewPlayer v21 supported

### Stage 3: Music Data Extraction

```python
LaxityPlayerAnalyzer(memory, load_addr)
```

1. Locate player code entry points
2. Find pointer tables for:
   - Instrument definitions
   - Wave table data
   - Pulse table data
   - Filter table data
   - Sequence/pattern data
3. Extract and validate table contents
4. Build internal representation

**Extraction Flow:**
```
Memory Image
    │
    ├─► find_instrument_table() ──► Instrument data
    │
    ├─► find_and_extract_wave_table() ──► Wave table
    │
    ├─► find_and_extract_pulse_table() ──► Pulse table
    │
    ├─► find_and_extract_filter_table() ──► Filter table
    │
    └─► extract_sequences() ──► Pattern data
```

### Stage 4: SF2 Generation

```python
SF2Writer(driver_type, template_path)
```

1. Load appropriate driver template
2. Inject extracted data at correct offsets
3. Convert instrument formats if needed
4. Write output file

**Template Structure:**
```
SF2 Template
├── Driver code (unchanged)
├── Sequence table ──► Inject patterns
├── Instrument table ──► Inject instruments
├── Wave table ──► Inject wave data
├── Pulse table ──► Inject pulse data
└── Filter table ──► Inject filter data
```

## Memory Model

The converter uses a 64KB memory model matching the C64 architecture:

```
$0000-$00FF: Zero page
$0100-$01FF: Stack
$0200-$0FFF: System/BASIC
$1000-$BFFF: Typical SID data location
$C000-$CFFF: Upper memory
$D000-$DFFF: I/O (SID at $D400-$D41C)
$E000-$FFFF: Kernal ROM
```

SID files typically load at `$1000` and contain:
- Player code
- Music data tables
- Sequence/pattern data

## Data Structures

### Instrument Format (Laxity)

8 bytes per instrument:
```
Byte 0: Attack/Decay
Byte 1: Sustain/Release
Byte 2: Wave table pointer
Byte 3: Pulse table pointer
Byte 4: Filter table pointer
Byte 5: Pulse width low
Byte 6: Pulse width high / flags
Byte 7: Vibrato settings
```

### Wave Table Entry

2 bytes per entry:
```
Byte 0: Duration/control
Byte 1: Waveform/note offset
```

Control values:
- `$00-$7E`: Duration in frames
- `$7F`: End of table
- `$7E`: Loop marker

### Sequence Format

Variable length patterns:
```
$00-$5F: Note values (C-0 to B-7)
$60-$7F: Note with duration
$80-$BF: Rest/tie commands
$C0-$CF: Commands (slide, portamento, etc.)
$FF: End of sequence
```

## Table Finding Algorithm

### Instrument Table Detection

1. Search for pointer patterns in player code
2. Score candidates based on:
   - Valid ADSR values (bits 0-15)
   - Reasonable table pointers
   - Consistent entry spacing
3. Select highest-scoring candidate
4. Extract until invalid entry

```python
def find_instrument_table():
    candidates = []
    for addr in search_range:
        score = 0
        score += validate_adsr(data[addr:addr+2])
        score += validate_pointers(data[addr+2:addr+5])
        if score >= threshold:
            candidates.append((addr, score))
    return best_candidate(candidates)
```

### Wave Table Detection

1. Find JSR/JMP patterns to table handlers
2. Extract pointer references
3. Validate waveform bytes
4. Verify note offset ranges
5. Check for proper terminators

## SF2 File Format

### Header (64 bytes)
```
Offset  Size  Description
$0000   4     Magic "SF2\x00"
$0004   2     Version
$0006   32    Song name
$0026   32    Author name
$0046   2     Driver type
...
```

### Data Sections
```
$0903   Sequence table (variable)
$0A03   Instrument table (32 × 8 bytes)
$0B03   Wave table (128 × 2 bytes)
$0D03   Pulse table (128 × 2 bytes)
$0F03   Filter table (128 × 2 bytes)
```

## Driver Types

### Driver 11 (Standard)
- 8-byte instrument format
- Full table support
- Compatible with most Laxity files

### NP20 (NewPlayer 2.0)
- Extended instrument format
- Additional command support
- Larger table sizes

## Error Handling Strategy

### Current Implementation
- Generic exception catching
- Print warnings to stdout
- Return None on failure
- Continue processing

### Recommended Approach
```python
class SIDParseError(Exception): pass
class TableExtractionError(Exception): pass
class SF2WriteError(Exception): pass

try:
    data = extract_table()
except TableExtractionError as e:
    logger.error(f"Table extraction failed: {e}")
    raise
```

## Performance Considerations

### Memory Usage
- 64KB per analyzer instance
- Multiple instances during batch conversion
- No explicit cleanup between files

### CPU Bottlenecks
- Nested loops in table search (O(n²) to O(n³))
- Full memory scans for pattern matching
- No caching of common lookups

### Optimization Opportunities
1. Index common byte patterns
2. Cache table locations
3. Parallel file processing
4. Memory pooling for batch jobs

## Extension Points

### Adding New Player Support

1. Create player analyzer class:
```python
class NewPlayerAnalyzer:
    def __init__(self, memory, load_addr):
        self.memory = memory
        self.load_addr = load_addr

    def extract_music_data(self):
        # Player-specific extraction
        pass
```

2. Register in player detection:
```python
PLAYER_ANALYZERS = {
    'laxity': LaxityPlayerAnalyzer,
    'goattracker': GoatTrackerAnalyzer,
    'newplayer': NewPlayerAnalyzer,
}
```

3. Implement table extraction methods

### Adding New Output Formats

1. Create writer class:
```python
class MIDIWriter:
    def __init__(self, extracted_data):
        self.data = extracted_data

    def write(self, output_path):
        # Convert to MIDI format
        pass
```

2. Register in output handlers

## Testing Architecture

### Unit Tests (`test_converter.py`)
- SID parsing tests
- Table extraction tests
- Format validation tests

### Integration Tests
- End-to-end conversion
- Batch processing
- Error recovery

### Test Data
- Minimal valid SID files
- Edge case files
- Known-good conversions

## Future Architecture Goals

### Modularization
```
sidm2/
├── __init__.py
├── parsers/
│   ├── sid_parser.py
│   └── laxity_parser.py
├── extractors/
│   ├── instrument.py
│   ├── wave_table.py
│   ├── pulse_table.py
│   └── filter_table.py
├── writers/
│   └── sf2_writer.py
├── constants.py
└── exceptions.py
```

### Plugin System
- Dynamic player loading
- Custom extraction strategies
- Multiple output formats

### Configuration
- YAML/JSON config files
- Environment variable overrides
- Command-line options
