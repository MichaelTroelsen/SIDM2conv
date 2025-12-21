# Components Reference

Complete reference for all Python modules and scripts in the SIDM2 project.

## Module Overview

### Core Package (`sidm2/`)

| Module | Purpose | Version | Lines |
|--------|---------|---------|-------|
| `sf2_packer.py` | SF2 to SID packer | v0.6.0 | ~800 |
| `cpu6502.py` | 6502 CPU emulator (pointer relocation) | v0.6.0 | ~400 |
| `cpu6502_emulator.py` | Full 6502 emulator with SID capture | v0.6.2 | 1,242 |
| `sid_player.py` | SID file player and analyzer | v0.6.2 | 560 |
| `sf2_player_parser.py` | SF2-exported SID parser | v0.6.2 | 389 |
| `siddump_extractor.py` | Runtime sequence extraction | v1.3 | 438 |
| `gate_inference.py` | Waveform-based gate detection | v1.5.0 | 306 |
| `accuracy.py` | Accuracy calculation module | v1.4.1 | 437 |
| `validation.py` | Validation utilities | v0.6.0 | ~200 |
| `errors.py` | User-friendly error messages | v2.5.0 | 500+ |

### Main Scripts (`scripts/`)

| Script | Purpose | Tests |
|--------|---------|-------|
| `sid_to_sf2.py` | Main SID to SF2 converter | 69 |
| `sf2_to_sid.py` | SF2 to SID exporter | - |
| `convert_all.py` | Batch conversion | - |
| `test_roundtrip.py` | Round-trip validation | - |
| `validate_sid_accuracy.py` | Accuracy validation | - |
| `generate_validation_report.py` | Multi-file validation | - |
| `disassemble_sid.py` | 6502/6510 disassembler | - |
| `extract_addresses.py` | Address extraction | - |

---

## Core Converter (`scripts/sid_to_sf2.py`)

### Overview

Main converter that transforms Laxity NewPlayer v21 SID files to SF2 format.

### Key Classes

#### SIDParser
Parses PSID/RSID headers and extracts metadata.

```python
class SIDParser:
    def parse_header(self, data: bytes) -> dict:
        """Parse PSID v2 header"""
        return {
            'version': int,
            'data_offset': int,
            'load_address': int,
            'init_address': int,
            'play_address': int,
            'songs': int,
            'start_song': int,
            'title': str,
            'author': str,
            'copyright': str
        }
```

#### LaxityPlayerAnalyzer
Extracts music data structures from Laxity player format.

```python
class LaxityPlayerAnalyzer:
    def extract_wave_table(self, memory: bytes, start: int) -> list:
        """Extract wave table (waveform, note offset pairs)"""

    def extract_pulse_table(self, memory: bytes, start: int) -> list:
        """Extract pulse table (4-byte PWM programs)"""

    def extract_filter_table(self, memory: bytes, start: int) -> list:
        """Extract filter table (4-byte filter sweeps)"""

    def extract_instruments(self, memory: bytes, start: int) -> list:
        """Extract instrument definitions (8 bytes each)"""
```

#### SF2Writer
Writes SF2 format files using driver templates.

```python
class SF2Writer:
    def load_template(self, driver: str) -> bytes:
        """Load SF2 driver template (Driver 11, NP20, etc.)"""

    def inject_tables(self, template: bytes, tables: dict) -> bytes:
        """Inject extracted tables at known offsets"""

    def write_sf2(self, path: str, data: bytes):
        """Write final SF2 file"""
```

### Usage

```bash
python scripts/sid_to_sf2.py SID/input.sid output/SongName/New/output.sf2
```

---

## SF2 Packer (`sidm2/sf2_packer.py`)

### Overview

**Version**: v0.6.0
**Purpose**: Pure Python implementation of SF2 to SID packing
**Status**: ✅ Working (with known limitations)

### Features

- Generates VSID-compatible SID files with correct sound playback
- Uses `sidm2/cpu6502.py` for 6502 instruction-level pointer relocation
- Integrated into `convert_all.py` for automatic SID export
- Average output size: ~3,800 bytes (comparable to C++ sf2pack)

### Known Limitation

**Pointer Relocation Bug**:
- Affects 17/18 files in pipeline testing (94%)
- Files play correctly in VICE, SID2WAV, siddump, and other emulators
- Only impacts SIDwinder's strict CPU emulation (disassembly fails with "Execution at $0000")
- Under investigation - see `PIPELINE_EXECUTION_REPORT.md` for details

### API

```python
from sidm2.sf2_packer import SF2Packer

# Create packer instance
packer = SF2Packer()

# Load SF2 file
sf2_data = packer.load_sf2('input.sf2')

# Pack to SID with metadata
sid_data = packer.pack(
    sf2_data,
    title='Song Title',
    author='Author Name',
    copyright='2025'
)

# Write output
with open('output.sid', 'wb') as f:
    f.write(sid_data)
```

### Integration

- Integrated into `scripts/convert_all.py` for batch conversion
- Used in `complete_pipeline_with_validation.py` (Step 2)
- Called by `scripts/sf2_to_sid.py` for single-file export

### See Also

- `PACK_STATUS.md` - Implementation details and test results
- `tools/sf2pack/` - C++ reference implementation

---

## CPU 6502 Emulator (`sidm2/cpu6502_emulator.py`)

### Overview

**Version**: v0.6.2
**Lines**: 1,242
**Purpose**: Full 6502 CPU emulator implementation with SID register capture

### Features

- Complete instruction set with all addressing modes
- SID register write capture for validation
- Frame-by-frame state tracking
- Tested with real SID files (Angular.sid, etc.)
- Based on siddump.c architecture

### API

```python
from sidm2.cpu6502_emulator import CPU6502Emulator

# Create emulator instance
cpu = CPU6502Emulator()

# Load memory
cpu.load_memory(0x1000, sid_data)

# Set entry points
cpu.pc = init_address
cpu.a = subtune_number

# Initialize
cpu.jsr(init_address)

# Run frames
for frame in range(num_frames):
    cpu.jsr(play_address)
    sid_writes = cpu.get_sid_writes()
    # Process SID register writes
```

### Use Cases

- SID playback simulation
- Register write validation
- Debug analysis of player code
- Frame-by-frame state inspection

### Status

✅ Production-ready, tested with real SID files

---

## SID Player (`sidm2/sid_player.py`)

### Overview

**Version**: v0.6.2
**Lines**: 560
**Purpose**: High-level SID file player and analyzer

### Features

- PSID/RSID header parsing
- Note detection and frequency analysis
- Siddump-compatible frame dump output
- Playback result analysis

### CLI Usage

```bash
# Play SID file for 30 seconds
python -m sidm2.sid_player SID/file.sid 30

# Default duration (10 seconds)
python -m sidm2.sid_player SID/file.sid
```

### API Usage

```python
from sidm2.sid_player import SIDPlayer

# Create player
player = SIDPlayer('SID/Angular.sid')

# Play for N seconds
results = player.play(seconds=30)

# Analyze results
print(f"Frames: {results['frames']}")
print(f"Registers: {results['register_writes']}")
print(f"Notes: {results['notes_detected']}")
```

### Output Format

Compatible with siddump output format for easy comparison.

### Use Cases

- Quick SID file testing
- Note detection for sequence extraction
- Frequency analysis
- Validation baseline generation

---

## SF2 Player Parser (`sidm2/sf2_player_parser.py`)

### Overview

**Version**: v0.6.2
**Lines**: 389
**Purpose**: Parser for SF2-exported SID files

### Features

- Pattern-based table extraction with SF2 reference
- Heuristic extraction mode (in development)
- Tested with 15 SIDSF2player files
- Header parsing: 100% success rate
- Table extraction: Works with matching SF2 reference

### API

```python
from sidm2.sf2_player_parser import SF2PlayerParser

# Parse with reference SF2
parser = SF2PlayerParser(
    sid_path='exported.sid',
    reference_sf2='original.sf2'
)

# Extract tables
tables = parser.extract_tables()

# Access specific tables
wave_table = tables['wave']
pulse_table = tables['pulse']
filter_table = tables['filter']
```

### Modes

1. **Reference Mode** (100% accuracy)
   - Requires original SF2 file
   - Extracts tables using known offsets

2. **Heuristic Mode** (in development)
   - Attempts extraction without reference
   - Uses pattern matching and scoring

### Test Suite

`scripts/test_sf2_player_parser.py` - Validation tests
- Tests multiple SID files with/without reference
- Reports extraction success rates
- Example output structure validation

---

## Siddump Sequence Extractor (`sidm2/siddump_extractor.py`)

### Overview

**Version**: v1.3
**Lines**: 438
**Purpose**: Runtime-based sequence extraction using siddump output
**Status**: ✅ Integrated in pipeline (Step 1.5)

### Features

- Parses siddump frame-by-frame output (pipe-delimited format)
- Detects repeating patterns in voice events
- Converts patterns to SF2 sequence format with proper gate markers
- Implements SF2 gate system per user manual:
  - `0x7E` = gate on (+++), `0x80` = gate off (---) or no change (--)
  - `0x7F` = end marker

### Hybrid Approach

Combines static table extraction with runtime sequence extraction:
1. Static: Extract wave/pulse/filter tables from memory
2. Runtime: Capture actual played sequences via siddump
3. Inject: Replace static sequences with runtime-analyzed sequences

### API

```python
from sidm2.siddump_extractor import extract_sequences_from_siddump

# Extract sequences from SID file
sequences = extract_sequences_from_siddump(
    sid_path='SID/Angular.sid',
    duration_seconds=30
)

# Access per-voice sequences
voice_0_seq = sequences['voice_0']
voice_1_seq = sequences['voice_1']
voice_2_seq = sequences['voice_2']
```

### Functions

#### `run_siddump(sid_path, seconds=30)`
Execute siddump and capture output.

```python
dump_output = run_siddump('SID/file.sid', seconds=30)
```

#### `parse_siddump_output(dump_text)`
Parse voice events from siddump pipe-delimited format.

```python
events = parse_siddump_output(dump_output)
# Returns: [{'frame': 0, 'voice': 1, 'freq': 1234, 'waveform': 17, ...}, ...]
```

#### `detect_patterns(events, min_length=4)`
Identify repeating note patterns.

```python
patterns = detect_patterns(events)
# Returns: [{'notes': [...], 'count': 5, 'length': 8}, ...]
```

#### `convert_pattern_to_sequence(pattern)`
Convert pattern to SF2 format with proper gates.

```python
sf2_sequence = convert_pattern_to_sequence(pattern)
# Returns: bytes with gate on/off markers (0x7E, 0x80, 0x7F)
```

### Integration

- Integrated into `complete_pipeline_with_validation.py` (Step 1.5)
- Runs after initial SF2 conversion
- Injects runtime sequences into SF2 file
- Significantly improves sequence accuracy

---

## Gate Inference (`sidm2/gate_inference.py`)

**Version**: v1.5.0
**Purpose**: Waveform-based gate detection for accurate ADSR envelope control
**Lines**: 306

### Overview

Gate inference analyzes SID register writes from siddump output to infer proper SF2 gate markers. The SID chip's gate bit (waveform register bit 0) controls ADSR envelopes, while SF2 uses explicit gate markers (0x7E gate-on, 0x80 gate-off).

**Accuracy Impact**: +10-15% potential improvement for files with valid orderlists

### Architecture

Three-tier inference system:

1. **Simple Inference** - Pattern-based gate detection (no siddump data needed)
2. **Waveform-Based Inference** - Analyzes actual SID register writes
3. **Accuracy Analysis** - Validates inference quality

### Key Classes

#### WaveformEvent
```python
@dataclass
class WaveformEvent:
    """Represents a waveform control register write from siddump."""
    frame: int          # Frame number
    voice: int          # Voice number (0-2)
    waveform: int       # Waveform control byte
    frequency: int      # Frequency value (0-65535)
    note: Optional[str] # Note string from siddump (e.g., "C-3")

    @property
    def gate_on(self) -> bool:
        """Check if gate bit is set."""
        return bool(self.waveform & GATE_BIT)

    @property
    def waveform_type(self) -> int:
        """Get waveform type (without gate bit)."""
        return self.waveform & 0xFE
```

#### WaveformGateAnalyzer
```python
class WaveformGateAnalyzer:
    """Analyzes siddump waveform data to infer gate markers."""

    def __init__(self, siddump_data: Optional[Dict] = None):
        """Initialize with optional siddump data."""

    def infer_gates_simple(self, events: List[SequenceEvent]) -> List[SequenceEvent]:
        """Enhanced pattern-based gate inference.

        Improvements:
        - Detects note changes (not just presence)
        - Handles sustained notes properly
        - Avoids redundant gate markers
        """

    def infer_gates_from_waveforms(
        self,
        events: List[SequenceEvent],
        voice: int = 0,
        frames_per_event: int = 1
    ) -> List[SequenceEvent]:
        """Infer gates from actual waveform data.

        Uses siddump waveform history to detect gate changes and insert
        proper SF2 gate markers at exact frames where SID gate bit changed.
        """

    def analyze_gate_accuracy(
        self,
        original_events: List[SequenceEvent],
        inferred_events: List[SequenceEvent]
    ) -> Dict[str, float]:
        """Compare inferred gates against expected gates for accuracy."""
```

### Gate Detection Strategy

**SID Waveform Register Format**:
```
Bit 7  6  5  4  3  2  1  0
    |  |  |  |  |  |  |  |
    |  |  |  |  |  |  |  └─ Gate bit (0=off, 1=on)
    |  |  |  |  |  |  └──── Sync bit
    |  |  |  |  |  └─────── Ring modulation
    |  |  |  |  └────────── Test bit (hard reset)
    |  |  |  └───────────── Triangle waveform
    |  |  └──────────────── Sawtooth waveform
    |  └─────────────────── Pulse waveform
    └────────────────────── Noise waveform
```

**Detection Process**:
1. Monitor waveform control register (SID $04, $0B, $12)
2. Detect gate bit changes (0→1, 1→0)
3. Detect waveform changes requiring gate resets
4. Correlate with frequency changes for note triggers
5. Insert SF2 gate markers at proper timing

**SF2 Gate Markers**:
- `0x7E` - Gate on (+++)  - Start attack/sustain
- `0x80` - Gate off (---) - Start release
- `0x7F` - End marker

### Integration Points

**Static Extraction** (`sequence_translator.py`):
```python
def _insert_gate_markers_enhanced(self, events: List[SequenceEvent]) -> List[SequenceEvent]:
    """Enhanced gate marker insertion with improved detection."""
    from .gate_inference import WaveformGateAnalyzer

    analyzer = WaveformGateAnalyzer()
    return analyzer.infer_gates_simple(events)
```

**Runtime Extraction** (`siddump_extractor.py`):
```python
def convert_pattern_to_sequence(pattern: List[Dict],
                               use_waveform_gates: bool = True) -> List[List[int]]:
    """Convert pattern to SF2 sequence with waveform-based gate detection."""

    # Track waveform state
    prev_gate_state = False
    prev_waveform = 0

    for event in pattern:
        waveform = event.get('wave', 0)
        current_gate = bool(waveform & GATE_BIT)
        waveform_changed = (waveform & 0xFE) != (prev_waveform & 0xFE)

        # Insert gate-off if gate bit changed or waveform changed
        if prev_gate_state and (not current_gate or waveform_changed):
            sequence.append([NO_CHANGE, NO_CHANGE, GATE_OFF])
```

### Testing Results

**Implementation Status**: ✅ Complete and working

**Test Methodology**: Complete pipeline on 18 test files

**Gate Inference Working**:
- Sequence event counts increased (281 → 293 events)
- Gate markers properly inserted at note boundaries
- Waveform transitions detected and handled
- No errors or regressions

**Blocked by Orderlist Bug**:
- 6/18 files (33%) have 0% accuracy
- All orderlist entries reference sequence index 0
- Causes "invalid sequence address $0000" errors
- Gate inference cannot help until orderlists are fixed

**Next Priority**: Fix orderlist generation to unlock gate inference benefits

### See Also

- **Implementation details** → `docs/implementation/GATE_INFERENCE_IMPLEMENTATION.md`
- **SID register reference** → `docs/reference/SID_REGISTERS_REFERENCE.md`
- **Accuracy roadmap** → `docs/analysis/ACCURACY_ROADMAP.md`

---

## Validation System

### Multi-File Validation Report (`scripts/generate_validation_report.py`)

**Version**: v0.6.1
**Purpose**: Comprehensive validation report generator

#### Features

- Validates all SID files in a directory
- Generates HTML report (`output/validation_report.html`)
- Identifies systematic vs file-specific validation issues
- Categorizes warnings (Instrument Pointer Bounds, Note Range, etc.)
- Current status: 16 test files validated with improved boundary checking
- False-positive warnings reduced by 50% for Angular.sid (4→2)

#### Usage

```bash
python scripts/generate_validation_report.py SID/ output/validation_report.html
```

### SID Accuracy Validation (`scripts/validate_sid_accuracy.py`)

**Version**: v0.6.0
**Purpose**: Frame-by-frame register comparison tool

#### Features

- Compares original SID vs exported SID using siddump
- Measures Overall (weighted), Frame, Voice, Register, and Filter accuracy
- Default 30-second validation for detailed analysis
- Generates accuracy reports with grades (EXCELLENT/GOOD/FAIR/POOR)

#### Accuracy Metrics Formula

```
Overall = Frame×0.40 + Voice×0.30 + Register×0.20 + Filter×0.10
```

#### Accuracy Grades

- **EXCELLENT**: ≥99% overall accuracy
- **GOOD**: 95-98% overall accuracy
- **FAIR**: 80-94% overall accuracy
- **POOR**: <80% overall accuracy

#### Usage

```bash
# Full 30-second validation
python scripts/validate_sid_accuracy.py SID/original.sid output/exported.sid

# Custom duration
python scripts/validate_sid_accuracy.py SID/original.sid output/exported.sid --duration 60
```

#### Baseline Accuracy (v0.6.0)

- Angular.sid: 9.0% overall (POOR)
- Target: 99% overall (see `docs/analysis/ACCURACY_ROADMAP.md`)

### Lightweight Validation Module (`sidm2/validation.py`)

**Version**: v0.6.0
**Purpose**: Lightweight validation for pipeline integration

#### Functions

##### `quick_validate(original_sid, exported_sid, seconds=10)`
10-second validation for batch processing.

```python
from sidm2.validation import quick_validate

accuracy = quick_validate(
    'SID/original.sid',
    'output/exported.sid',
    seconds=10
)
# Returns: {'overall': 0.09, 'frame': 0.10, 'voice': 0.08, ...}
```

##### `generate_accuracy_summary(accuracy)`
Formats results for info.txt files.

```python
from sidm2.validation import generate_accuracy_summary

summary = generate_accuracy_summary(accuracy)
# Returns: "Overall: 9.0% (POOR)\nFrame: 10.0%\n..."
```

##### `get_accuracy_grade(accuracy)`
Converts accuracy to quality grade.

```python
from sidm2.validation import get_accuracy_grade

grade = get_accuracy_grade(0.99)  # Returns "EXCELLENT"
grade = get_accuracy_grade(0.09)  # Returns "POOR"
```

#### Integration

- Integrated into `convert_all.py` automatically
- Used in pipeline validation reports

### Round-trip Validation (`scripts/test_roundtrip.py`)

**Purpose**: Complete SID→SF2→SID round-trip validation

#### Features

- Performs 8-step automated testing
- Generates HTML reports with detailed comparisons
- Uses siddump for register-level verification
- Organized output: `roundtrip_output/{SongName}/Original/` and `/New/`

#### 8-Step Process

1. Setup - Create output directories
2. Convert - SID → SF2
3. Pack - SF2 → SID
4. Render WAVs - Original and exported audio
5. Siddump original - Register capture
6. Siddump exported - Register capture
7. Compare - Frame-by-frame analysis
8. Report - Generate HTML report

#### Usage

```bash
# Single file round-trip
python scripts/test_roundtrip.py SID/file.sid

# Batch with round-trip validation
python scripts/convert_all.py --roundtrip
```

#### Output

- HTML report: `roundtrip_output/{song}_roundtrip_report.html`
- Original files in `roundtrip_output/{song}/Original/`
- Converted files in `roundtrip_output/{song}/New/`

---

## Complete Pipeline (`complete_pipeline_with_validation.py`)

### Overview

**Version**: v1.3
**Purpose**: Comprehensive 12-step conversion pipeline with full validation

See `docs/ARCHITECTURE.md` for detailed pipeline architecture.

### Quick Reference

**Steps**: 12 (SID→SF2, siddump sequences, SF2→SID, dumps, WAV, hex, trace, info, disassembly, MIDI comparison, validation, summary)

**Output**: 16 files per SID (11 in New/, 5 in Original/)

**Usage**:
```bash
python complete_pipeline_with_validation.py
```

**Test Suite**:
```bash
python scripts/test_complete_pipeline.py -v
```

**Latest Results** (2025-12-06):
- 18 SID files processed
- 1/18 (5.6%) complete success
- 17/18 (94.4%) partial success (missing .asm due to packer bug)

---

## Module Dependencies

```
complete_pipeline_with_validation.py
├── scripts/sid_to_sf2.py
│   ├── sidm2/sf2_packer.py
│   │   └── sidm2/cpu6502.py
│   └── sidm2/siddump_extractor.py
├── scripts/sf2_to_sid.py
│   └── sidm2/sf2_packer.py
├── scripts/generate_info.py
├── scripts/disassemble_sid.py
└── sidm2/validation.py
```

---

## Testing

### Test Files

| Test File | Purpose | Tests |
|-----------|---------|-------|
| `scripts/test_converter.py` | Unit tests for converter | 69 |
| `scripts/test_sf2_format.py` | Format validation tests | 12 |
| `scripts/test_complete_pipeline.py` | Pipeline validation | 19 |
| `scripts/test_sf2_player_parser.py` | Parser tests | 15 |

### Running Tests

```bash
# All converter tests
python scripts/test_converter.py -v

# Format validation
python scripts/test_sf2_format.py -v

# Pipeline tests
python scripts/test_complete_pipeline.py -v
```

---

---

## Error Handling Module (`sidm2/errors.py`)

### Overview

**Version**: v2.5.0
**Lines**: 500+
**Purpose**: User-friendly error messages with troubleshooting guidance

### Features

- **Structured Error Format**: Clear "What happened", "Why", "How to fix" sections
- **Similar File Finder**: Suggests similar filenames for FileNotFound errors using difflib
- **Documentation Links**: Auto-converts relative paths to GitHub URLs
- **Optional Colors**: ANSI color support with graceful degradation
- **Convenience Functions**: Quick error raising helpers
- **Serialization**: `to_dict()` method for logging/debugging

### Exception Classes

#### Base Class: `SIDMError`
```python
class SIDMError(Exception):
    """Base exception with rich formatting."""

    def __init__(
        self,
        message: str,
        what_happened: Optional[str] = None,
        why_happened: Optional[List[str]] = None,
        how_to_fix: Optional[List[str]] = None,
        docs_link: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
        technical_details: Optional[str] = None
    )
```

#### Specialized Exceptions

**FileNotFoundError** - File not found with similar file suggestions:
```python
from sidm2.errors import FileNotFoundError

raise FileNotFoundError(
    path="SID/song.sid",
    context="input SID file",
    suggestions=[
        "Check file path: python scripts/sid_to_sf2.py --help",
        "Use absolute path instead of relative",
        "List files: ls SID/ (or dir SID\\ on Windows)"
    ],
    docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md"
)
```

**InvalidInputError** - Invalid file format or corrupted data:
```python
from sidm2.errors import InvalidInputError

raise InvalidInputError(
    input_type="SID file",
    value="corrupted.sid",
    expected="PSID or RSID format",
    got="Unknown magic bytes: ABCD",
    suggestions=["Verify file is valid", "Re-download from HVSC"],
    docs_link="reference/format-specification.md"
)
```

**MissingDependencyError** - Missing modules with install instructions:
```python
from sidm2.errors import MissingDependencyError

raise MissingDependencyError(
    dependency="sidm2.laxity_converter",
    install_command="pip install -e .",
    alternatives=["Use standard drivers: --driver driver11"],
    docs_link="README.md#installation"
)
```

**PermissionError** - File/directory permission issues:
```python
from sidm2.errors import PermissionError

raise PermissionError(
    operation="write",
    path="output/protected/file.sf2",
    docs_link="README.md#troubleshooting"
)
```

**ConfigurationError** - Invalid configuration values:
```python
from sidm2.errors import ConfigurationError

raise ConfigurationError(
    setting="driver",
    value="invalid_driver",
    valid_options=["driver11", "np20", "laxity"],
    example="python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity",
    docs_link="reference/DRIVER_REFERENCE.md"
)
```

**ConversionError** - Conversion failures with diagnosis:
```python
from sidm2.errors import ConversionError

raise ConversionError(
    stage="table extraction",
    reason="Failed to locate instrument table in SID memory",
    input_file="SID/unknown_player.sid",
    suggestions=["Try different driver: --driver driver11"],
    docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md#troubleshooting"
)
```

### Convenience Functions

```python
from sidm2.errors import file_not_found, invalid_input

# Quick file not found
raise file_not_found("missing.sid", "SID file")

# Quick invalid input
raise invalid_input("config", "bad_value", expected="number", got="string")
```

### Error Output Format

```
ERROR: Input Sid File Not Found

What happened:
  Could not find the input SID file: SID/song.sid

Why this happened:
  * File path may be incorrect or contains typos
  * File may have been moved or deleted
  * Working directory may be wrong

How to fix:
  1. Check the file path: python scripts/sid_to_sf2.py --help
  2. Use absolute path instead of relative
  3. List files: ls SID/ (or dir SID\ on Windows)

Alternative:
  Similar files found in the same directory:
    * SID\Angular.sid
    * SID\songs.sid

Need help?
  * Documentation: https://github.com/MichaelTroelsen/SIDM2conv/blob/master/docs/guides/LAXITY_DRIVER_USER_GUIDE.md
  * Issues: https://github.com/MichaelTroelsen/SIDM2conv/issues
  * README: https://github.com/MichaelTroelsen/SIDM2conv#readme

Technical details:
  Full path checked: C:\Users\mit\claude\c64server\SIDM2\SID\song.sid
```

### Integration

**Fully integrated (v2.5.2+)**:

**Scripts** (v2.5.0-v2.5.1):
- `scripts/sid_to_sf2.py` (v1.1.0) - Main SID to SF2 converter
- `scripts/sf2_to_sid.py` (v1.1.0) - SF2 to SID exporter
- `scripts/convert_all.py` (v0.7.2) - Batch conversion script
- `scripts/validate_sid_accuracy.py` (v0.1.1) - Accuracy validation tool
- `scripts/test_roundtrip.py` - Round-trip validation test

**Core Modules** (v2.5.2 - NEW):
- `sidm2/sid_parser.py` (v1.1.0) - SID file parsing with enhanced error messages
- `sidm2/sf2_writer.py` (v1.1.0) - SF2 file writing with I/O error handling
- `sidm2/sf2_packer.py` (v1.1.0) - SF2→SID packing with validation errors

**All core modules now provide**:
- Context-aware error messages
- Step-by-step troubleshooting guidance
- Platform-specific suggestions
- Documentation links
- Similar file suggestions (for FileNotFoundError)

### Demo Script

```bash
# See all error types with examples
python test_errors_demo.py
```

Demonstrates all 8 error scenarios with realistic examples and proper formatting.

### See Also

- `UX_IMPROVEMENT_PLAN.md` - Complete UX improvement strategy
- `test_errors_demo.py` - Demonstration script

---

## See Also

- `CLAUDE.md` - Quick reference and workflows
- `docs/TOOLS_REFERENCE.md` - External tools documentation
- `docs/ARCHITECTURE.md` - System architecture
- `docs/guides/VALIDATION_GUIDE.md` - Comprehensive validation system guide (v2.0.0)
- `docs/analysis/ACCURACY_ROADMAP.md` - Accuracy improvement plan
