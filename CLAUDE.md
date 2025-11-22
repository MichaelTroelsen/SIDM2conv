# CLAUDE.md - Project Guide for AI Assistants

## Project Overview

SID to SF2 Converter - Converts Commodore 64 SID music files to SID Factory II (.sf2) format for editing and remixing.

## Quick Start

```bash
# Convert single file
python sid_to_sf2.py SID/input.sid SF2/output.sf2

# Batch convert all SID files
python convert_all.py
```

## Project Structure

```
SIDM2/
├── sid_to_sf2.py          # Main converter (3600 lines - monolithic)
├── convert_all.py         # Batch conversion script
├── test_converter.py      # Unit tests (34 tests)
├── test_sf2_format.py     # Format validation tests
├── laxity_parser.py       # Dedicated Laxity player parser
├── SID/                   # Input SID files
├── SF2/                   # Output SF2 files + dumps
├── tools/                 # External tools (siddump.exe, player-id.exe)
└── G5/                    # Driver templates
```

## Key Components

### Main Converter (`sid_to_sf2.py`)
- `SIDParser` class - Parses PSID/RSID headers
- `LaxityPlayerAnalyzer` class - Extracts music data from Laxity player
- `SF2Writer` class - Writes SF2 format using templates
- Table extraction functions for wave, pulse, filter tables

### External Tools
- `tools/siddump.exe` - Dumps SID register writes
- `tools/player-id.exe` - Identifies SID player type

## Supported Formats

**Input**: Laxity NewPlayer v21 SID files only
**Output**: SID Factory II .sf2 format (Driver 11 or NP20)

## Running Tests

```bash
python test_converter.py
python test_sf2_format.py
```

## CI/CD Rules

**IMPORTANT: Always follow these rules when making changes:**

### 1. Always Run Tests
Before committing any code changes, you MUST:
- Run `python test_converter.py` and ensure all tests pass
- Run `python test_sf2_format.py` for format validation tests
- If tests fail, fix the issues before committing

### 2. Always Update Documentation
When making code changes, you MUST update relevant documentation:
- Update `README.md` if adding/changing features or CLI options
- Update `CLAUDE.md` if changing project structure or conventions
- Update `docs/` files if changing architecture or API
- Keep version numbers in sync across files
- Update improvement status in README when completing items

## Common Tasks

### Adding a new SID file
1. Place .sid file in `SID/` directory
2. Run `python sid_to_sf2.py SID/file.sid SF2/file.sf2`
3. Check `SF2/file_info.txt` for extraction details

### Debugging extraction issues
1. Run `tools/siddump.exe SID/file.sid > SF2/file.dump`
2. Check dump for register patterns
3. Review `SF2/file_info.txt` for table addresses

## Known Limitations

- Only supports Laxity NewPlayer v21
- Single subtune per file (multi-song SIDs not supported)
- Init, Arp, HR tables use defaults (not extracted)
- Command parameters not fully extracted

## Code Conventions

- Memory addresses as hex: `0x1000`, `0x1AF3`
- Table sizes: typically 32, 64, or 128 entries
- Control bytes: `0x7F` (end), `0x7E` (loop)
- Waveforms: `0x01` (triangle), `0x10` (triangle+gate), `0x11` (pulse), etc.

## Important Constants

```python
# SF2 structure offsets
SEQUENCE_TABLE_OFFSET = 0x0903
INSTRUMENT_TABLE_OFFSET = 0x0A03
WAVE_TABLE_OFFSET = 0x0B03
PULSE_TABLE_OFFSET = 0x0D03
FILTER_TABLE_OFFSET = 0x0F03

# Laxity player markers
LAXITY_INIT_PATTERN = [0xA9, 0x00, 0x8D]  # LDA #$00, STA
```

## Architecture Notes

### Conversion Flow
1. Parse SID header (PSID v2)
2. Identify player type via player-id.exe
3. Load SID data into 64KB memory model
4. Extract tables (instruments, wave, pulse, filter)
5. Extract sequences from pattern data
6. Load SF2 template for target driver
7. Inject extracted data into template
8. Write output .sf2 file

### Table Extraction Strategy
- Search for pointer patterns in player code
- Score candidates based on validity heuristics
- Extract entries until end marker (0x7F/0x7E)

## Improvement Opportunities

See README.md for full improvement list with status tracking.

### Completed ✅
- Modularize `sid_to_sf2.py` into separate files (sidm2 package)
- Consolidate duplicate analysis scripts
- Extract magic numbers to constants
- Add comprehensive documentation

### In Progress 🔄
- Add proper logging instead of print statements
- Add type hints to all public functions
- Error handling in critical extraction functions

### Pending
- Test coverage for edge cases
- Configuration system for SF2 generation
- Support for additional player formats

## Dependencies

- Python 3.x
- No external Python packages required
- Windows tools: siddump.exe, player-id.exe

## File Format References

- `README.md` - Comprehensive format documentation
- `CONTRIBUTING.md` - Contribution guidelines
- SID Factory II manual for .sf2 format details
