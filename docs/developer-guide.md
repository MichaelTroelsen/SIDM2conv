# Developer Guide

## Getting Started

### Prerequisites

- Python 3.x
- Windows (for siddump.exe and player-id.exe tools)
- SID Factory II templates in `G5/` directory

### Project Setup

```bash
git clone <repository>
cd SIDM2

# Verify tools are present
dir tools\siddump.exe
dir tools\player-id.exe

# Run tests
python -m pytest test_converter.py -v
```

## Development Workflow

### Converting a Single File

```bash
# Basic conversion
python sid_to_sf2.py SID/song.sid SF2/song.sf2

# View extraction details
type SF2\song_info.txt
```

### Debugging Extraction Issues

1. **Generate dump file:**
```bash
tools\siddump.exe SID\problem.sid > SF2\problem.dump
```

2. **Check player identification:**
```bash
tools\player-id.exe SID\problem.sid
```

3. **Review extraction log:**
```bash
python sid_to_sf2.py SID\problem.sid SF2\problem.sf2 -v
```

4. **Examine memory addresses in dump**

### Running Tests

```bash
# All tests
python -m pytest -v

# Specific test file
python -m pytest test_converter.py -v

# Single test
python -m pytest test_converter.py::test_sid_parser -v

# With coverage
python -m pytest --cov=sid_to_sf2 --cov-report=html
```

## Code Structure

### Main Modules

| File | Purpose | Lines |
|------|---------|-------|
| `sid_to_sf2.py` | Core converter | 3600 |
| `convert_all.py` | Batch processing | 526 |
| `laxity_parser.py` | Dedicated Laxity parser | 371 |

### Test Files

| File | Purpose |
|------|---------|
| `test_converter.py` | Unit tests |
| `test_sf2_format.py` | Format validation |

### Analysis Tools (Development)

These are development/debug tools with overlapping functionality:

- `analyze_laxity*.py` - Various analysis scripts
- `extract_*.py` - Extraction experiments
- `laxity_*_extractor.py` - Extractor variations

## Key Algorithms

### Instrument Table Finding

The instrument table finder uses a scoring system:

```python
def find_instrument_table(data, load_addr):
    candidates = []

    for addr in range(load_addr, len(data) - 8):
        score = 0

        # Check ADSR values (bytes 0-1)
        ad = data[addr]
        sr = data[addr + 1]
        if is_valid_adsr(ad, sr):
            score += 2

        # Check table pointers (bytes 2-4)
        wave_ptr = data[addr + 2]
        pulse_ptr = data[addr + 3]
        filter_ptr = data[addr + 4]
        if all_pointers_valid(wave_ptr, pulse_ptr, filter_ptr):
            score += 3

        # Check pulse width (bytes 5-6)
        pw = data[addr + 5] | (data[addr + 6] << 8)
        if 0 < pw < 4096:
            score += 1

        if score >= 6:  # Threshold
            candidates.append((addr, score))

    return best_candidate(candidates)
```

**Scoring Thresholds:**
- `6+`: Likely instrument table
- `4-5`: Possible, needs validation
- `<4`: Unlikely

### Wave Table Extraction

Wave tables contain waveform commands:

```python
def extract_wave_table(data, addr):
    entries = []
    i = 0

    while i < MAX_ENTRIES:
        duration = data[addr + i*2]
        waveform = data[addr + i*2 + 1]

        if duration == 0x7F:  # End marker
            break
        if duration == 0x7E:  # Loop marker
            entries.append(('loop', waveform))
            break

        entries.append((duration, waveform))
        i += 1

    return entries
```

### Sequence Parsing

Sequences contain note and command data:

```python
def parse_sequence(data):
    events = []
    i = 0

    while i < len(data):
        byte = data[i]

        if byte == 0xFF:  # End
            break
        elif byte < 0x60:  # Note
            events.append(('note', byte))
        elif byte < 0x80:  # Note with duration
            events.append(('note', byte & 0x1F, byte >> 5))
        elif byte < 0xC0:  # Rest/tie
            events.append(('rest', byte & 0x3F))
        else:  # Command (0xC0-0xCF)
            cmd = byte - 0xC0
            param = data[i + 1] if needs_param(cmd) else None
            events.append(('cmd', cmd, param))
            if param:
                i += 1

        i += 1

    return events
```

## Adding New Features

### Adding a New Player Format

1. **Create analyzer class:**

```python
# In new file: goattracker_analyzer.py

class GoatTrackerAnalyzer:
    def __init__(self, memory, load_addr):
        self.memory = memory
        self.load_addr = load_addr

    def extract_music_data(self):
        return {
            'instruments': self._extract_instruments(),
            'wave_table': self._extract_wave_table(),
            'pulse_table': self._extract_pulse_table(),
            'filter_table': self._extract_filter_table(),
            'sequences': self._extract_sequences(),
            'commands': self._get_command_names(),
            'song_order': self._extract_song_order(),
        }

    def _extract_instruments(self):
        # GoatTracker-specific extraction
        pass
```

2. **Register in main converter:**

```python
# In sid_to_sf2.py

PLAYER_ANALYZERS = {
    'Laxity NewPlayer': LaxityPlayerAnalyzer,
    'GoatTracker': GoatTrackerAnalyzer,
}

def get_analyzer(player_type, memory, load_addr):
    analyzer_class = PLAYER_ANALYZERS.get(player_type)
    if analyzer_class:
        return analyzer_class(memory, load_addr)
    return None
```

3. **Add player detection:**

```python
def detect_player(sid_path):
    result = run_player_id(sid_path)
    for name in PLAYER_ANALYZERS.keys():
        if name in result:
            return name
    return None
```

4. **Write tests:**

```python
def test_goattracker_extraction():
    memory = create_test_goattracker_data()
    analyzer = GoatTrackerAnalyzer(memory, 0x1000)
    data = analyzer.extract_music_data()
    assert len(data['instruments']) > 0
```

### Adding New Output Format

1. **Create writer class:**

```python
# In new file: midi_writer.py

class MIDIWriter:
    def __init__(self):
        self.tempo = 120
        self.ppq = 480

    def write(self, extracted_data, output_path):
        midi = self._create_midi()

        for i, seq in enumerate(extracted_data['sequences']):
            track = self._create_track(seq)
            midi.tracks.append(track)

        midi.save(output_path)
        return True

    def _create_track(self, sequence):
        # Convert sequence to MIDI events
        pass
```

2. **Integrate with CLI:**

```python
# In sid_to_sf2.py

OUTPUT_FORMATS = {
    'sf2': SF2Writer,
    'mid': MIDIWriter,
}

def main():
    # ...
    format = args.format or 'sf2'
    writer_class = OUTPUT_FORMATS[format]
    writer = writer_class()
    writer.write(data, output_path)
```

### Adding New Table Type

1. **Create extraction function:**

```python
def find_and_extract_arp_table(data, load_addr):
    # Search for arpeggio table pattern
    for addr in search_range:
        if is_arp_table_candidate(data, addr):
            entries = extract_arp_entries(data, addr)
            if validate_arp_entries(entries):
                return addr, entries
    return None, []
```

2. **Add to analyzer:**

```python
class LaxityPlayerAnalyzer:
    def extract_music_data(self):
        return {
            # ... existing tables
            'arp_table': self._extract_arp_table(),
        }

    def _extract_arp_table(self):
        addr, entries = find_and_extract_arp_table(
            self.memory, self.load_addr
        )
        return entries
```

3. **Update SF2 writer:**

```python
class SF2Writer:
    def _inject_arp_table(self, template, entries):
        offset = ARP_TABLE_OFFSET
        for i, entry in enumerate(entries):
            template[offset + i*2] = entry[0]
            template[offset + i*2 + 1] = entry[1]
        return template
```

## Debugging Tips

### Memory Inspection

```python
def dump_memory_region(memory, start, length):
    """Print hex dump of memory region"""
    for i in range(0, length, 16):
        addr = start + i
        hex_str = ' '.join(f'{memory[addr+j]:02X}'
                          for j in range(min(16, length-i)))
        print(f'${addr:04X}: {hex_str}')
```

### Table Validation

```python
def validate_instrument(instr):
    """Check if instrument data is valid"""
    issues = []

    if instr['attack'] > 15:
        issues.append(f"Invalid attack: {instr['attack']}")
    if instr['wave_ptr'] > 127:
        issues.append(f"Invalid wave ptr: {instr['wave_ptr']}")

    return issues
```

### Tracing Extraction

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def find_instrument_table(data, load_addr):
    logger.debug(f"Searching from ${load_addr:04X}")

    for addr in search_range:
        score = calculate_score(data, addr)
        if score >= 4:
            logger.debug(f"Candidate at ${addr:04X}, score={score}")
```

## Common Issues

### "Could not find instrument table"

**Causes:**
- Unknown player format
- Corrupted SID file
- Non-standard memory layout

**Solutions:**
1. Verify player type with `player-id.exe`
2. Check SID file with `siddump.exe`
3. Lower scoring threshold (may cause false positives)

### "Invalid wave table entries"

**Causes:**
- Wrong table address
- Different table format
- Encrypted/packed data

**Solutions:**
1. Examine memory dump manually
2. Look for different byte patterns
3. Check if data is compressed

### "Output sounds wrong"

**Causes:**
- Incorrect instrument mapping
- Missing table data
- Wrong driver template

**Solutions:**
1. Compare input/output in SID Factory II
2. Check `_info.txt` for extraction details
3. Try different driver type

## Performance Optimization

### Profiling

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Run conversion
convert_file(input_path, output_path)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Memory Optimization

```python
# Avoid creating multiple memory copies
memory = bytearray(65536)  # Reuse this

# Clear between conversions
def clear_memory(memory):
    for i in range(len(memory)):
        memory[i] = 0
```

### Batch Processing

```python
from concurrent.futures import ProcessPoolExecutor

def batch_convert(files, max_workers=4):
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(convert_file, f): f
                   for f in files}
        for future in as_completed(futures):
            result = future.result()
            print(f"Completed: {futures[future]}")
```

## Code Style

### Naming Conventions

- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

### Documentation

```python
def find_instrument_table(data, load_addr):
    """
    Find instrument table in memory.

    Searches for patterns characteristic of Laxity instrument
    tables and scores candidates based on validity.

    Args:
        data: Memory image as bytes
        load_addr: Base address of SID data

    Returns:
        Address of instrument table, or None if not found

    Example:
        >>> addr = find_instrument_table(memory, 0x1000)
        >>> if addr:
        ...     print(f"Found at ${addr:04X}")
    """
```

### Error Handling

```python
# Good: Specific exception with context
try:
    data = read_sid_file(path)
except FileNotFoundError:
    logger.error(f"SID file not found: {path}")
    raise
except PermissionError:
    logger.error(f"Cannot read SID file: {path}")
    raise

# Bad: Bare except
try:
    data = read_sid_file(path)
except:
    print("Error reading file")
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-player`
3. Write tests for new functionality
4. Ensure all tests pass: `python -m pytest`
5. Submit pull request

See `CONTRIBUTING.md` for detailed guidelines.
