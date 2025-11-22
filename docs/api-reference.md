# API Reference

## Core Classes

### SIDParser

Parses SID files and loads data into memory model.

```python
from sid_to_sf2 import SIDParser

parser = SIDParser(filepath)
```

#### Constructor

| Parameter | Type | Description |
|-----------|------|-------------|
| `filepath` | str | Path to SID file |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `data` | bytes | Raw file data |
| `header` | PSIDHeader | Parsed header info |
| `load_addr` | int | Memory load address |
| `init_addr` | int | Init routine address |
| `play_addr` | int | Play routine address |
| `name` | str | Song name |
| `author` | str | Author name |
| `copyright` | str | Copyright info |

#### Methods

##### `parse_header()`
Parses PSID/RSID header from file data.

**Returns:** `PSIDHeader` namedtuple

##### `get_music_data()`
Returns music data section (after header).

**Returns:** `bytes`

---

### PSIDHeader

Named tuple containing SID header fields.

```python
PSIDHeader(
    magic,          # b'PSID' or b'RSID'
    version,        # 1, 2, 3, or 4
    data_offset,    # Offset to music data
    load_addr,      # C64 load address
    init_addr,      # Init routine address
    play_addr,      # Play routine address
    songs,          # Number of songs
    start_song,     # Default song number
    speed,          # Speed flags
    name,           # Song name (32 chars)
    author,         # Author name (32 chars)
    copyright,      # Copyright (32 chars)
    flags,          # v2+ flags
    start_page,     # v2+ start page
    page_length,    # v2+ page length
)
```

---

### LaxityPlayerAnalyzer

Extracts music data from Laxity NewPlayer format.

```python
from sid_to_sf2 import LaxityPlayerAnalyzer

analyzer = LaxityPlayerAnalyzer(memory, load_addr)
data = analyzer.extract_music_data()
```

#### Constructor

| Parameter | Type | Description |
|-----------|------|-------------|
| `memory` | bytearray | 64KB memory image |
| `load_addr` | int | Base load address |

#### Methods

##### `extract_music_data()`
Extracts all music data from player.

**Returns:** `ExtractedData` dict with keys:
- `instruments` - List of instrument dicts
- `wave_table` - List of (duration, waveform) tuples
- `pulse_table` - List of (duration, value) tuples
- `filter_table` - List of (duration, value) tuples
- `sequences` - List of sequence byte lists
- `commands` - List of command names
- `song_order` - Song order table

##### `find_instrument_table()`
Locates instrument table in memory.

**Returns:** `int` - Address of instrument table, or `None`

##### `find_wave_table()`
Locates wave table in memory.

**Returns:** `tuple` - (address, entries) or `None`

##### `find_pulse_table()`
Locates pulse table in memory.

**Returns:** `tuple` - (address, entries) or `None`

##### `find_filter_table()`
Locates filter table in memory.

**Returns:** `tuple` - (address, entries) or `None`

---

### SF2Writer

Writes extracted data to SF2 format.

```python
from sid_to_sf2 import SF2Writer

writer = SF2Writer(driver_type='driver11')
writer.write(extracted_data, output_path)
```

#### Constructor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `driver_type` | str | 'driver11' | Target driver type |
| `template_path` | str | None | Custom template path |

#### Methods

##### `write(extracted_data, output_path)`
Writes SF2 file from extracted data.

| Parameter | Type | Description |
|-----------|------|-------------|
| `extracted_data` | dict | Data from analyzer |
| `output_path` | str | Output file path |

**Returns:** `bool` - Success status

##### `load_template()`
Loads SF2 template file.

**Returns:** `bytes` - Template data

##### `inject_data(template, data)`
Injects extracted data into template.

**Returns:** `bytes` - Modified template

---

### ExtractedData

Dictionary structure returned by analyzers:

```python
{
    'instruments': [
        {
            'attack': 0,
            'decay': 9,
            'sustain': 15,
            'release': 0,
            'wave_ptr': 0,
            'pulse_ptr': 0,
            'filter_ptr': 0,
            'pulse_width': 2048,
            'vibrato': 0,
            'name': 'Instrument 01'
        },
        # ... more instruments
    ],
    'wave_table': [
        (1, 0x41),   # duration=1, waveform=pulse
        (0, 0x40),   # duration=0, waveform=pulse (gate off)
        # ...
    ],
    'pulse_table': [
        (1, 0x800),  # duration=1, value=2048
        # ...
    ],
    'filter_table': [
        (1, 0x400),  # duration=1, cutoff=1024
        # ...
    ],
    'sequences': [
        [0x3C, 0x40, 0x43, 0xFF],  # C-4, E-4, G-4, end
        # ...
    ],
    'commands': [
        'Slide Up',
        'Slide Down',
        'Vibrato',
        # ...
    ],
    'song_order': [0, 1, 2, 0, 1, 2],  # Pattern order
}
```

---

## Utility Functions

### extract_from_siddump()

Runs siddump.exe and parses output.

```python
from sid_to_sf2 import extract_from_siddump

result = extract_from_siddump(sid_path)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `sid_path` | str | Path to SID file |

**Returns:** `dict` or `None` - Parsed siddump data

---

### find_instrument_table()

Finds instrument table address using heuristics.

```python
from sid_to_sf2 import find_instrument_table

addr = find_instrument_table(data, load_addr)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | bytes | Memory data |
| `load_addr` | int | Base address |

**Returns:** `int` or `None` - Table address

---

### find_and_extract_wave_table()

Finds and extracts wave table data.

```python
from sid_to_sf2 import find_and_extract_wave_table

addr, entries = find_and_extract_wave_table(data, load_addr)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | bytes | Memory data |
| `load_addr` | int | Base address |

**Returns:** `tuple` - (address, list of entries) or `(None, [])`

---

### find_and_extract_pulse_table()

Finds and extracts pulse table data.

```python
from sid_to_sf2 import find_and_extract_pulse_table

addr, entries = find_and_extract_pulse_table(data, load_addr)
```

**Returns:** `tuple` - (address, list of entries) or `(None, [])`

---

### find_and_extract_filter_table()

Finds and extracts filter table data.

```python
from sid_to_sf2 import find_and_extract_filter_table

addr, entries = find_and_extract_filter_table(data, load_addr)
```

**Returns:** `tuple` - (address, list of entries) or `(None, [])`

---

### extract_all_laxity_tables()

Extracts all tables from Laxity player in one call.

```python
from sid_to_sf2 import extract_all_laxity_tables

tables = extract_all_laxity_tables(data, load_addr)
```

**Returns:** `dict` with keys:
- `instruments`
- `wave_table`
- `pulse_table`
- `filter_table`

---

## Command Line Interface

### sid_to_sf2.py

```bash
python sid_to_sf2.py <input.sid> <output.sf2> [options]
```

#### Arguments

| Argument | Description |
|----------|-------------|
| `input.sid` | Input SID file path |
| `output.sf2` | Output SF2 file path |

#### Options

| Option | Description |
|--------|-------------|
| `-d, --driver` | Driver type (driver11, np20) |
| `-t, --template` | Custom template path |
| `-v, --verbose` | Verbose output |

#### Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | Input file not found |
| 2 | Parse error |
| 3 | Extraction error |
| 4 | Write error |

---

### convert_all.py

```bash
python convert_all.py [options]
```

#### Options

| Option | Description |
|--------|-------------|
| `-i, --input` | Input directory (default: SID/) |
| `-o, --output` | Output directory (default: SF2/) |
| `-f, --force` | Overwrite existing files |

---

## Constants

### Memory Addresses

```python
# SID chip registers
SID_BASE = 0xD400

# Typical Laxity player locations
PLAYER_CODE = 0x1000
MUSIC_DATA = 0x1800
SEQUENCE_DATA = 0x2000
```

### Table Sizes

```python
MAX_INSTRUMENTS = 32
MAX_WAVE_ENTRIES = 128
MAX_PULSE_ENTRIES = 128
MAX_FILTER_ENTRIES = 128
MAX_SEQUENCES = 128
```

### Control Bytes

```python
TABLE_END = 0x7F
TABLE_LOOP = 0x7E
SEQUENCE_END = 0xFF
```

### Waveforms

```python
WAVEFORM_TRIANGLE = 0x10
WAVEFORM_SAWTOOTH = 0x20
WAVEFORM_PULSE = 0x40
WAVEFORM_NOISE = 0x80
WAVEFORM_GATE = 0x01
```

---

## Error Handling

### Exceptions

Currently using generic exceptions. Planned custom exceptions:

```python
class SIDError(Exception):
    """Base exception for SID operations"""
    pass

class SIDParseError(SIDError):
    """Error parsing SID file"""
    pass

class TableExtractionError(SIDError):
    """Error extracting table data"""
    pass

class SF2WriteError(SIDError):
    """Error writing SF2 file"""
    pass
```

### Return Values

Functions return `None` on failure. Check return values:

```python
result = find_instrument_table(data, load_addr)
if result is None:
    print("Could not find instrument table")
    return

addr = result
# Continue processing
```
