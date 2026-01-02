# SIDM2 Developer Guide

**Version 3.1.0** | **Last Updated**: 2026-01-02

A comprehensive guide for developers contributing to the SIDM2 project. This guide focuses on **how to** develop for SIDM2, complementing the reference-style [ARCHITECTURE.md](../ARCHITECTURE.md).

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Understanding the Codebase](#understanding-the-codebase)
3. [Adding a New SF2 Driver](#adding-a-new-sf2-driver)
4. [Adding Support for a New Player Type](#adding-support-for-a-new-player-type)
5. [Debugging Conversion Issues](#debugging-conversion-issues)
6. [Common Development Tasks](#common-development-tasks)
7. [Code Patterns and Idioms](#code-patterns-and-idioms)
8. [Testing Guide](#testing-guide)
9. [Performance Optimization](#performance-optimization)
10. [Troubleshooting Development Issues](#troubleshooting-development-issues)

---

## Getting Started

### Prerequisites

**Required**:
- Python 3.8+ (3.7+ may work)
- Git
- Windows (for external tools) or Wine (Linux/Mac)

**Recommended**:
- Visual Studio Code with Python extension
- VICE emulator (for testing)
- SID Factory II (for manual verification)

### Developer Setup

```bash
# Clone repository
git clone https://github.com/MichaelTroelsen/SIDM2conv.git
cd SIDM2conv

# Verify Python version
python --version  # Should be 3.8+

# Install development dependencies (if any)
pip install pytest coverage  # Optional: for advanced testing

# Verify setup by running tests
test-all.bat  # Should show 200+ tests passing

# Try a conversion
sid-to-sf2.bat "G5/examples/Driver 11 Test - Arpeggio.sid" test_output.sf2
```

### Project Structure Overview

```
SIDM2/
├── sidm2/                  # Core library (71 modules)
│   ├── conversion_pipeline.py    # Main conversion orchestrator
│   ├── driver_selector.py        # Auto driver selection
│   ├── laxity_parser.py          # Laxity format parser
│   ├── laxity_converter.py       # Laxity→SF2 converter
│   ├── sf2_packer.py             # SF2→SID packer
│   ├── siddump.py                # Pure Python siddump
│   └── errors.py                 # Custom error classes
│
├── scripts/                # Production scripts
│   ├── sid_to_sf2.py             # Main CLI converter
│   ├── sf2_to_sid.py             # SF2→SID packer CLI
│   └── validate_sid_accuracy.py  # Validation tool
│
├── pyscript/               # All other Python scripts
│   ├── conversion_cockpit_gui.py # Batch conversion GUI
│   ├── sf2_viewer_gui.py         # SF2 viewer GUI
│   ├── siddump_complete.py       # Enhanced siddump
│   ├── sidwinder_trace.py        # Python SIDwinder
│   └── test_*.py                 # 200+ unit tests
│
├── G5/drivers/             # SF2 driver templates
│   ├── laxity/                   # Laxity driver
│   ├── driver11/                 # Standard driver
│   └── np20/                     # NewPlayer 20 driver
│
├── docs/                   # Documentation
│   ├── guides/                   # User & developer guides
│   ├── reference/                # Technical references
│   └── ARCHITECTURE.md           # Architecture reference
│
└── *.bat                   # Windows launchers
```

### Key Files to Read First

1. **README.md** - Project overview and quick start
2. **CLAUDE.md** - Quick reference for AI assistants (very concise)
3. **docs/ARCHITECTURE.md** - Architecture reference (834 lines)
4. **docs/guides/BEST_PRACTICES.md** - Best practices guide
5. **CONTRIBUTING.md** - Contribution guidelines

---

## Understanding the Codebase

### Core Module Walkthrough

#### 1. `sidm2/conversion_pipeline.py` (Main Orchestrator)

**Purpose**: Orchestrates the entire SID→SF2 conversion process

**Key Classes**:
- `ConversionPipeline` - Main pipeline class
- `ConversionConfig` - Configuration dataclass

**Key Methods**:
```python
def convert(sid_file: Path, output_file: Path, driver: str = None) -> ConversionResult:
    """Main conversion entry point"""

def analyze_sid_file(sid_data: bytes) -> SIDMetadata:
    """Parse SID header and metadata"""

def select_converter(player_type: str) -> BaseConverter:
    """Select appropriate converter based on player type"""
```

**Flow**:
1. Parse SID header → SIDMetadata
2. Identify player type (player-id.exe)
3. Select driver (DriverSelector)
4. Select converter (LaxityConverter or fallback)
5. Run conversion → SF2 file
6. Validate output
7. Generate reports

**When to Modify**: Adding new player type support, changing validation logic

---

#### 2. `sidm2/driver_selector.py` (Auto Driver Selection)

**Purpose**: Automatically selects the best SF2 driver based on player type

**Key Classes**:
- `DriverSelector` - Main selector class
- `DriverSelection` - Result dataclass

**Key Mappings**:
```python
PLAYER_MAPPINGS = {
    # SF2-exported files (100% accuracy with Driver 11)
    'SidFactory_II/Laxity': 'driver11',  # Author name, NOT player format!
    'SidFactory_II': 'driver11',

    # Native Laxity files (99.93% accuracy with Laxity driver)
    'Laxity_NewPlayer_V21': 'laxity',
    'Vibrants/Laxity': 'laxity',

    # NewPlayer 20
    'NewPlayer_20.G4': 'np20',
}
```

**Critical Distinction**:
- `'SidFactory_II/Laxity'` = Files **created IN SF2** by author "Laxity" → Use Driver 11
- `'Laxity_NewPlayer_V21'` = Native **Laxity player format** → Use Laxity driver

**When to Modify**: Adding support for new player types, changing driver selection logic

---

#### 3. `sidm2/laxity_parser.py` (Laxity Format Parser)

**Purpose**: Extracts music data from Laxity NewPlayer v21 SID files

**Key Constants**:
```python
INIT_ADDR = 0x1000          # Player init entry point
PLAY_ADDR = 0x10A1          # Player play entry point
INSTRUMENTS_ADDR = 0x1A6B   # Instrument table (32 × 8 bytes)
WAVE_TABLE_ADDR = 0x1ACB    # Wave table (dual array format)
```

**Key Methods**:
```python
def parse_instruments(memory: bytearray) -> List[Instrument]:
    """Extract 32 instruments (ADSR + table pointers)"""

def parse_wave_table(memory: bytearray) -> List[Tuple[int, int]]:
    """Extract wave table (waveform, note_offset) pairs"""

def parse_sequences(memory: bytearray) -> Dict[int, List[SequenceEvent]]:
    """Extract sequences from orderlists"""
```

**Wave Table Format (CRITICAL)**:
- Laxity: Column-major dual arrays (waveforms at 0x1ACB, note offsets at 0x1AFB)
- SF2: Row-major interleaved pairs (waveform, note_offset, waveform, note_offset, ...)

**When to Modify**: Laxity format changes, accuracy improvements

---

#### 4. `sidm2/laxity_converter.py` (Laxity→SF2 Converter)

**Purpose**: Converts extracted Laxity data to SF2 format

**Key Classes**:
- `LaxityConverter` - Main converter
- `ConversionResult` - Result dataclass

**Conversion Steps**:
1. Load Laxity driver template (`G5/drivers/laxity/sf2driver_laxity_00.prg`)
2. Extract tables (instruments, wave, pulse, filter, arpeggio)
3. Extract sequences (orderlists → sequences → events)
4. Apply 40 pointer patches (redirect table access)
5. Inject extracted data into template
6. Pack into SF2 format

**40 Pointer Patches**:
- Redirects table access from Laxity defaults to injected SF2 data
- Critical for 99.93% accuracy

**When to Modify**: Laxity driver improvements, accuracy optimization

---

#### 5. `sidm2/sf2_packer.py` (SF2→SID Packer)

**Purpose**: Packs SF2 files back into playable SID format

**Key Methods**:
```python
def pack_sf2_to_sid(sf2_file: Path, output_sid: Path) -> None:
    """Pack SF2 → SID"""

def extract_music_data(sf2_data: bytes) -> MusicData:
    """Extract sequences, instruments, tables from SF2"""

def build_sid_file(music_data: MusicData) -> bytes:
    """Build complete SID file with driver + data"""
```

**When to Modify**: SF2 format changes, packing improvements

---

#### 6. `sidm2/siddump.py` (Pure Python Siddump)

**Purpose**: 100% Python implementation of siddump (no external dependencies)

**Features**:
- Complete C64/SID emulation (CPU + SID registers)
- Frame-by-frame execution trace
- Register write logging
- Cross-platform (no .exe dependencies)

**Key Classes**:
- `SIDdump` - Main emulator
- `CPU6502` - 6502 CPU emulator
- `SIDChip` - SID register emulation

**When to Modify**: Emulation accuracy, performance optimization

---

#### 7. `sidm2/errors.py` (Custom Error Classes)

**Purpose**: Structured error handling with actionable messages

**Error Classes**:
```python
FileNotFoundError        # Missing files/directories
InvalidInputError        # Invalid/corrupted data
MissingDependencyError   # Missing modules/tools
PermissionError          # Access denied issues
ConfigurationError       # Invalid settings
ConversionError          # Conversion failures
```

**Usage**:
```python
from sidm2 import errors

if not os.path.exists(input_path):
    raise errors.FileNotFoundError(
        path=input_path,
        context="input SID file",
        suggestions=[
            "Check the file path",
            "Use absolute path instead of relative",
        ],
        docs_link="guides/TROUBLESHOOTING.md#file-not-found"
    )
```

**When to Modify**: Adding new error types, improving error messages

---

### Data Flow Diagram

```
SID File
   │
   ├──> Parse Header ──> SIDMetadata
   │
   ├──> Identify Player Type ──> player-id.exe ──> "Laxity_NewPlayer_V21"
   │
   ├──> Select Driver ──> DriverSelector ──> "laxity"
   │
   ├──> Select Converter ──> LaxityConverter
   │
   ├──> Parse Tables ──> LaxityParser ──> Instruments, Wave, Pulse, etc.
   │
   ├──> Parse Sequences ──> LaxityParser ──> Orderlists ──> Sequences
   │
   ├──> Load Template ──> G5/drivers/laxity/sf2driver_laxity_00.prg
   │
   ├──> Apply Patches ──> 40 pointer patches
   │
   ├──> Inject Data ──> SF2Packer ──> Complete SF2 file
   │
   └──> Validate ──> ValidationSystem ──> Accuracy report
```

---

## Adding a New SF2 Driver

### Overview

SF2 drivers are pre-built 6502 assembly programs that play music from SF2 format data structures. Each driver has different capabilities and memory layouts.

**Existing Drivers**:
- **Driver 11** (default) - Full features, 100% SF2 compatibility
- **Laxity** - Custom driver for Laxity NP21, 99.93% accuracy
- **NP20** - NewPlayer 20.G4 compatibility, 70-90% accuracy

### Step-by-Step: Creating a New Driver

#### Step 1: Research the Target Player Format

**Goal**: Understand the original player's data structures and execution flow

**Tasks**:
1. Disassemble the original SID file
2. Identify table locations (instruments, wave, pulse, filter, sequences)
3. Document table formats
4. Identify init/play entry points
5. Document memory layout

**Tools**:
- `tools/SIDwinder.exe disassemble input.sid output.asm`
- `pyscript/quick_disasm.py input.sid`
- Manual analysis with hex editor

**Example** (Laxity NP21):
```
Init Address:    $1000
Play Address:    $10A1
Instruments:     $1A6B (32 × 8 bytes)
Wave Table:      $1ACB (dual array, 48 × 2 bytes)
Pulse Table:     $1B4B
Filter Table:    $1B6B
Arpeggio Table:  $1B8B
```

---

#### Step 2: Design the Driver Architecture

**Decision**: Extract & Wrap vs Full Rewrite

**Extract & Wrap** (recommended):
- Use original player code
- Add SF2 wrapper for init/play entry points
- Inject SF2-formatted data
- Example: Laxity driver

**Full Rewrite**:
- Write driver from scratch
- More control, more work
- Example: Driver 11

**For Extract & Wrap**:
1. Extract player code ($1000-$19FF)
2. Relocate to SF2-compatible address (e.g., $0E00)
3. Create wrapper at $0D7E (SF2 standard entry point)
4. Apply pointer patches to redirect table access

---

#### Step 3: Create Driver Template

**Directory Structure**:
```
G5/drivers/my_driver/
├── my_driver.asm              # Driver source (if writing from scratch)
├── sf2driver_my_driver_00.prg # Compiled driver template
├── README.md                  # Driver documentation
└── patches.txt                # Pointer patch documentation
```

**Driver Template Structure**:
```
Address   Size    Purpose
--------  ------  ---------------------------
$0D7E     130B    SF2 Wrapper (init/play/stop)
$0E00     2KB     Relocated player code
$1700     512B    SF2 header blocks
$1900+    Var     Music data (injected at conversion time)
```

**SF2 Entry Points** (standard):
```asm
; Entry point table at $0D7E
sf2_init:     JMP init_routine    ; $0D7E
sf2_play:     JMP play_routine    ; $0D81
sf2_stop:     JMP stop_routine    ; $0D84
```

---

#### Step 4: Implement Pointer Patching

**Purpose**: Redirect table access from original locations to injected SF2 data

**Example** (Laxity driver):
```python
# Original code reads instruments from $1A6B
# LDA $1A6B,Y  →  BD 6B 1A

# After relocation to $0E00, this becomes:
# LDA $0E6B,Y  →  BD 6B 0E

# But we want it to read from injected data at $1900:
# LDA $1900,Y  →  BD 00 19

POINTER_PATCHES = [
    # Instrument table access (8 patches)
    (0x0FE6, b'\x00\x19'),  # $0E6B → $1900
    (0x0FEA, b'\x08\x19'),  # $0E73 → $1908
    # ... 38 more patches
]
```

**How to Find Patches**:
1. Disassemble relocated driver
2. Search for table address references
3. Note patch locations and new addresses
4. Test each patch individually

---

#### Step 5: Create Converter Class

**File**: `sidm2/my_driver_converter.py`

```python
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass

class MyDriverConverter:
    """Converter for My Driver format."""

    DRIVER_TEMPLATE = Path('G5/drivers/my_driver/sf2driver_my_driver_00.prg')

    # Table addresses in original player
    INSTRUMENTS_ADDR = 0x1234
    WAVE_TABLE_ADDR = 0x5678

    # Injection addresses in SF2
    SF2_INSTRUMENTS = 0x1900
    SF2_WAVE_TABLE = 0x1A00

    POINTER_PATCHES = [
        # (offset, new_bytes)
        (0x1234, b'\x00\x19'),
        # ...
    ]

    def __init__(self, sid_file: Path):
        self.sid_file = sid_file
        self.memory = bytearray(65536)
        self._load_sid()

    def convert(self, output_file: Path) -> ConversionResult:
        """Main conversion method."""
        # 1. Load driver template
        template = self._load_template()

        # 2. Extract tables
        instruments = self._extract_instruments()
        wave_table = self._extract_wave_table()

        # 3. Extract sequences
        sequences = self._extract_sequences()

        # 4. Apply pointer patches
        template = self._apply_patches(template)

        # 5. Inject data
        template = self._inject_data(template, instruments, wave_table, sequences)

        # 6. Write output
        output_file.write_bytes(template)

        return ConversionResult(
            success=True,
            output_file=output_file,
            driver="my_driver"
        )

    def _extract_instruments(self) -> List[Instrument]:
        """Extract instrument table."""
        instruments = []
        addr = self.INSTRUMENTS_ADDR

        for i in range(32):  # Assuming 32 instruments
            attack = self.memory[addr + i*8 + 0]
            decay = self.memory[addr + i*8 + 1]
            sustain = self.memory[addr + i*8 + 2]
            release = self.memory[addr + i*8 + 3]

            instruments.append(Instrument(
                attack=attack,
                decay=decay,
                sustain=sustain,
                release=release
            ))

        return instruments
```

---

#### Step 6: Integrate with Driver Selector

**File**: `sidm2/driver_selector.py`

```python
DRIVER_FILES = {
    'laxity': 'sf2driver_laxity_00.prg',
    'driver11': 'sf2driver_11.prg',
    'np20': 'sf2driver_np20.prg',
    'my_driver': 'sf2driver_my_driver_00.prg',  # ADD THIS
}

PLAYER_MAPPINGS = {
    # ... existing mappings ...
    'My_Player_Format': 'my_driver',  # ADD THIS
}

EXPECTED_ACCURACY = {
    # ... existing accuracies ...
    'my_driver': '85-95%',  # ADD THIS
}
```

---

#### Step 7: Add Tests

**File**: `pyscript/test_my_driver.py`

```python
import unittest
from pathlib import Path
from sidm2.my_driver_converter import MyDriverConverter

class TestMyDriverConverter(unittest.TestCase):
    """Tests for My Driver converter."""

    def setUp(self):
        self.test_sid = Path('test_data/my_player_test.sid')

    def test_convert_basic(self):
        """Test basic conversion."""
        converter = MyDriverConverter(self.test_sid)
        result = converter.convert(Path('test_output.sf2'))

        self.assertTrue(result.success)
        self.assertTrue(Path('test_output.sf2').exists())

    def test_extract_instruments(self):
        """Test instrument extraction."""
        converter = MyDriverConverter(self.test_sid)
        instruments = converter._extract_instruments()

        self.assertEqual(len(instruments), 32)
        self.assertIsInstance(instruments[0], Instrument)

    # Add more tests...
```

---

#### Step 8: Documentation

**Create**: `G5/drivers/my_driver/README.md`

```markdown
# My Driver - SF2 Driver for My Player Format

## Overview

Custom SF2 driver for My Player format SID files, achieving 85-95% accuracy.

## Player Type

- **Format**: My Player v2.5
- **Player-ID Signature**: `My_Player_Format`
- **Author**: John Doe

## Memory Layout

```
Address   Size    Purpose
--------  ------  ---------------------------
$0D7E     130B    SF2 Wrapper
$0E00     2KB     Relocated player code
$1700     512B    SF2 header blocks
$1900     256B    Instruments (32 × 8 bytes)
$1A00     256B    Wave table
$1B00+    Var     Sequences
```

## Accuracy

- **Expected**: 85-95%
- **Tested Files**: 15 test files
- **Validation**: See `validation_results.txt`

## Usage

```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --driver my_driver
```

## Limitations

- Filter accuracy: 0% (filter format not yet converted)
- Maximum sequence length: 256 events
- Single subtune only

## Technical Details

- 25 pointer patches applied
- Extract & Wrap architecture
- Original player code preserved
```

---

#### Step 9: Validation

1. **Convert test files**:
   ```bash
   python scripts/sid_to_sf2.py test1.sid test1.sf2 --driver my_driver
   ```

2. **Pack back to SID**:
   ```bash
   python scripts/sf2_to_sid.py test1.sf2 test1_exported.sid
   ```

3. **Compare accuracy**:
   ```bash
   python scripts/validate_sid_accuracy.py test1.sid test1_exported.sid
   ```

4. **Run validation suite**:
   ```bash
   test-all.bat
   ```

---

## Adding Support for a New Player Type

### Overview

Adding parser support for a new SID player format (e.g., GoatTracker, JCH, etc.)

### Step 1: Analyze the Player Format

**Tools**:
- `tools/player-id.exe` - Identify player type
- `tools/SIDwinder.exe disassemble` - Disassemble player code
- Hex editor - Manual analysis

**Questions to Answer**:
1. What is the init address? Play address?
2. Where are instruments stored? (Format? Count?)
3. Where is the wave table? (Format?)
4. Where are pulse/filter/arpeggio tables?
5. How are sequences stored? (Orderlists? Pattern table?)
6. What command bytes are used?

---

### Step 2: Create Parser Module

**File**: `sidm2/myplayer_parser.py`

```python
"""Parser for My Player format."""

from typing import List, Dict, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Constants (discovered from analysis)
INIT_ADDR = 0x1234
PLAY_ADDR = 0x5678
INSTRUMENTS_ADDR = 0x2000
WAVE_TABLE_ADDR = 0x2100

@dataclass
class MyPlayerInstrument:
    """My Player instrument format."""
    attack: int
    decay: int
    sustain: int
    release: int
    wave_ptr: int
    pulse_ptr: int

class MyPlayerParser:
    """Parser for My Player format SID files."""

    def __init__(self, memory: bytearray, load_addr: int):
        self.memory = memory
        self.load_addr = load_addr

    def parse_instruments(self) -> List[MyPlayerInstrument]:
        """Extract instruments."""
        instruments = []

        for i in range(16):  # Assuming 16 instruments
            addr = INSTRUMENTS_ADDR + i * 6

            instruments.append(MyPlayerInstrument(
                attack=self.memory[addr + 0],
                decay=self.memory[addr + 1],
                sustain=self.memory[addr + 2],
                release=self.memory[addr + 3],
                wave_ptr=self.memory[addr + 4],
                pulse_ptr=self.memory[addr + 5],
            ))

        return instruments

    def parse_wave_table(self) -> List[Tuple[int, int]]:
        """Extract wave table."""
        wave_table = []
        addr = WAVE_TABLE_ADDR

        # Read until end marker (e.g., $FF)
        while self.memory[addr] != 0xFF:
            waveform = self.memory[addr]
            note_offset = self.memory[addr + 1]
            wave_table.append((waveform, note_offset))
            addr += 2

        return wave_table

    def parse_sequences(self) -> Dict[int, List]:
        """Extract sequences for all 3 voices."""
        # Implementation depends on sequence format
        pass
```

---

### Step 3: Create Converter

**File**: `sidm2/myplayer_converter.py`

```python
from sidm2.myplayer_parser import MyPlayerParser

class MyPlayerConverter:
    """Converts My Player format to SF2."""

    def convert(self, output_file: Path) -> ConversionResult:
        # Parse My Player data
        parser = MyPlayerParser(self.memory, self.load_addr)
        instruments = parser.parse_instruments()
        wave_table = parser.parse_wave_table()

        # Convert to SF2 format
        sf2_instruments = self._convert_instruments(instruments)
        sf2_wave_table = self._convert_wave_table(wave_table)

        # Use appropriate driver (Driver 11 or custom)
        driver_template = self._load_driver_template('driver11')

        # Inject data
        # ...
```

---

### Step 4: Register with Conversion Pipeline

**File**: `sidm2/conversion_pipeline.py`

```python
from sidm2.myplayer_converter import MyPlayerConverter

def select_converter(player_type: str) -> BaseConverter:
    """Select appropriate converter."""

    if 'My_Player' in player_type:
        return MyPlayerConverter
    elif 'Laxity' in player_type:
        return LaxityConverter
    else:
        return Driver11Converter  # Fallback
```

---

### Step 5: Update Driver Selector

**File**: `sidm2/driver_selector.py`

```python
PLAYER_MAPPINGS = {
    # ... existing ...
    'My_Player_Format': 'driver11',  # Use Driver 11 for now
}
```

---

## Debugging Conversion Issues

### Diagnostic Workflow

```
Conversion Failed?
   │
   ├──> Check Player Type
   │    └──> tools/player-id.exe input.sid
   │         Is it supported? (Laxity NP21, SF2-exported)
   │
   ├──> Check SID Header
   │    └──> python pyscript/siddump_complete.py input.sid -t10
   │         Valid init/play addresses?
   │
   ├──> Compare Dumps
   │    ├──> python pyscript/siddump_complete.py original.sid -t300 > orig.txt
   │    ├──> python pyscript/siddump_complete.py converted.sid -t300 > conv.txt
   │    └──> diff orig.txt conv.txt
   │         Where do they diverge?
   │
   ├──> Check Tables
   │    └──> python pyscript/quick_disasm.py input.sid
   │         Are tables extracted correctly?
   │
   └──> Validate Driver Selection
        └──> python scripts/sid_to_sf2.py input.sid output.sf2 -vv
             Is correct driver selected?
```

---

### Common Issues and Solutions

#### Issue 1: Low Accuracy (< 50%)

**Symptoms**: Converted SID sounds wrong, low accuracy score

**Diagnosis**:
```bash
# 1. Check player type
tools/player-id.exe input.sid
# Output: "Laxity_NewPlayer_V21"

# 2. Check driver selection
python scripts/sid_to_sf2.py input.sid output.sf2 -vv
# Should show: "Selected Driver: LAXITY"

# 3. If wrong driver, force correct one
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
```

**Common Causes**:
- Wrong driver selected (SF2-exported file detected as Laxity)
- Unsupported player format
- Table extraction failed

---

#### Issue 2: Sequences Not Playing Correctly

**Symptoms**: Notes missing, wrong order, timing issues

**Diagnosis**:
```python
# Debug sequence extraction
from sidm2.laxity_parser import LaxityParser

parser = LaxityParser(memory, load_addr)
sequences = parser.parse_sequences()

# Check sequence lengths
for voice, seq in sequences.items():
    print(f"Voice {voice}: {len(seq)} events")

# Check for common markers
for event in sequences[0][:20]:  # First 20 events
    print(f"${event.note:02X} ${event.instrument:02X}")
```

**Common Causes**:
- End marker ($7F) not detected
- Orderlist parsing incorrect
- Shared sequence not copied to all voices

---

#### Issue 3: Filter/Pulse Effects Wrong

**Symptoms**: Effects sound wrong, filters not applied

**Known Limitation**: Laxity driver has 0% filter accuracy (filter format not yet converted)

**Workaround**: Focus on note/instrument accuracy first

---

### Debugging Tools

**1. Siddump Comparison**:
```bash
# Compare frame-by-frame register writes
python pyscript/siddump_complete.py original.sid -t300 > orig_dump.txt
python pyscript/siddump_complete.py converted.sid -t300 > conv_dump.txt
diff orig_dump.txt conv_dump.txt
```

**2. SIDwinder Trace**:
```bash
# Detailed execution trace
python pyscript/sidwinder_trace.py --trace trace.txt original.sid
python pyscript/sidwinder_trace.py --trace trace_conv.txt converted.sid
diff trace.txt trace_conv.txt
```

**3. Disassembly Comparison**:
```bash
# Compare disassembled code
tools/SIDwinder.exe disassemble original.sid orig.asm
tools/SIDwinder.exe disassemble converted.sid conv.asm
diff orig.asm conv.asm
```

**4. Batch Analysis**:
```bash
# Compare multiple file pairs
batch-analysis.bat originals/ converted/ -o results/
# Open results/batch_summary.html
```

**5. Validation Dashboard**:
```bash
# Generate validation dashboard
python scripts/generate_dashboard.py
# Open validation/dashboard.html
```

---

## Common Development Tasks

### Task 1: Adding a New Command Byte

**File**: `sidm2/command_mapping.py`

```python
# Add to SF2_COMMAND_MAP
SF2_COMMAND_MAP = {
    # ... existing ...
    0xB5: 0x85,  # New command: My effect → SF2 effect
}

# Document in ARCHITECTURE.md
```

---

### Task 2: Improving Table Extraction

**File**: `sidm2/table_extraction.py`

```python
def find_wave_table_improved(memory: bytearray) -> int:
    """Enhanced wave table detection."""
    # Search for signature pattern
    for addr in range(0x1000, 0x2000):
        if self._is_wave_table(addr):
            return addr
    return None

def _is_wave_table(self, addr: int) -> bool:
    """Check if address contains wave table."""
    # Check for valid waveform values (0x11, 0x21, 0x41, 0x81)
    # Check for reasonable note offsets (-24 to +24)
    # Check for end marker or table length
    pass
```

---

### Task 3: Adding Validation Checks

**File**: `sidm2/conversion_pipeline.py`

```python
def validate_output(self, sf2_file: Path) -> ValidationResult:
    """Validate conversion output."""

    # Check file size
    if sf2_file.stat().st_size < 8192:
        return ValidationResult(
            valid=False,
            reason="Output file too small (< 8KB)"
        )

    # Check SF2 magic marker
    sf2_data = sf2_file.read_bytes()
    if sf2_data[0x0900:0x0902] != b'\x37\x13':
        return ValidationResult(
            valid=False,
            reason="Missing SF2 magic marker"
        )

    # Run accuracy check
    accuracy = self._check_accuracy(original_sid, sf2_file)

    return ValidationResult(
        valid=accuracy > 50.0,
        accuracy=accuracy,
        reason=f"Accuracy: {accuracy:.1f}%"
    )
```

---

## Code Patterns and Idioms

### Error Handling

**Pattern**: Use custom error classes from `sidm2.errors`

```python
from sidm2 import errors

# Good
if not input_path.exists():
    raise errors.FileNotFoundError(
        path=input_path,
        context="input SID file",
        suggestions=["Check path", "Use absolute path"]
    )

# Bad
if not input_path.exists():
    raise Exception(f"File not found: {input_path}")
```

---

### Logging

**Pattern**: Use module-level logger with structured logging

```python
import logging

logger = logging.getLogger(__name__)

# Good
logger.info(f"Converting {sid_file.name}")
logger.debug(f"Load address: ${load_addr:04X}")
logger.warning(f"Unsupported command: ${cmd:02X}")
logger.error(f"Table extraction failed at ${addr:04X}")

# Bad
print(f"Converting {sid_file.name}")
```

---

### Memory Access

**Pattern**: Use helper methods with bounds checking

```python
def read_word(self, addr: int) -> int:
    """Read 16-bit word (little-endian)."""
    if addr < 0 or addr >= 65535:
        raise IndexError(f"Address out of range: ${addr:04X}")
    return self.memory[addr] | (self.memory[addr + 1] << 8)

# Usage
instrument_ptr = self.read_word(0x1A6B)
```

---

### Type Hints

**Pattern**: Use type hints for all public methods

```python
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass

def convert_sid(
    input_file: Path,
    output_file: Path,
    driver: Optional[str] = None
) -> ConversionResult:
    """Convert SID to SF2."""
    pass
```

---

## Testing Guide

### Test Structure

```
pyscript/
├── test_conversion_pipeline.py    # Pipeline tests
├── test_driver_selector.py        # Driver selection tests
├── test_laxity_parser.py          # Parser tests
├── test_laxity_converter.py       # Converter tests
├── test_sf2_packer.py             # Packer tests
└── test_siddump.py                # Siddump emulator tests
```

---

### Writing Unit Tests

```python
import unittest
from pathlib import Path
from sidm2.laxity_parser import LaxityParser

class TestLaxityParser(unittest.TestCase):
    """Tests for Laxity parser."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures (runs once)."""
        cls.test_sid = Path('test_data/angular.sid')

    def setUp(self):
        """Set up before each test."""
        self.memory = bytearray(65536)
        # Load test SID...

    def test_parse_instruments(self):
        """Test instrument parsing."""
        parser = LaxityParser(self.memory, 0x1000)
        instruments = parser.parse_instruments()

        self.assertEqual(len(instruments), 32)
        self.assertIsInstance(instruments[0].attack, int)
        self.assertGreaterEqual(instruments[0].attack, 0)
        self.assertLessEqual(instruments[0].attack, 15)

    def test_parse_wave_table(self):
        """Test wave table parsing."""
        parser = LaxityParser(self.memory, 0x1000)
        wave_table = parser.parse_wave_table()

        self.assertGreater(len(wave_table), 0)

        # Check format
        waveform, note_offset = wave_table[0]
        self.assertIn(waveform, [0x11, 0x21, 0x41, 0x81])
        self.assertGreaterEqual(note_offset, -24)
        self.assertLessEqual(note_offset, 24)
```

---

### Running Tests

```bash
# All tests
test-all.bat

# Specific test file
python -m pytest pyscript/test_laxity_parser.py -v

# Specific test class
python -m pytest pyscript/test_laxity_parser.py::TestLaxityParser -v

# Specific test method
python -m pytest pyscript/test_laxity_parser.py::TestLaxityParser::test_parse_instruments -v

# With coverage
coverage run -m pytest pyscript/test_*.py
coverage report
coverage html  # Generate HTML report
```

---

### Integration Tests

**Pattern**: Test complete conversions with real SID files

```python
class TestIntegrationConversion(unittest.TestCase):
    """Integration tests for full conversion."""

    def test_convert_angular_laxity(self):
        """Test converting Angular.sid (Laxity NP21)."""
        input_sid = Path('batch_test/originals/Angular.sid')
        output_sf2 = Path('test_output/Angular.sf2')

        # Convert
        result = convert_sid(input_sid, output_sf2, driver='laxity')

        # Verify output exists
        self.assertTrue(output_sf2.exists())

        # Verify accuracy (should be 100%)
        accuracy = validate_accuracy(input_sid, output_sf2)
        self.assertGreater(accuracy, 95.0)
```

---

## Performance Optimization

### Profiling

```python
import cProfile
import pstats

# Profile conversion
cProfile.run('convert_sid(input_sid, output_sf2)', 'profile_stats.txt')

# Analyze results
p = pstats.Stats('profile_stats.txt')
p.sort_stats('cumulative')
p.print_stats(20)  # Top 20 slowest functions
```

---

### Common Bottlenecks

1. **SIDdump emulation** - CPU emulation is slow
   - Solution: Use external siddump.exe when available
   - Fallback to Python only on non-Windows

2. **Table extraction** - Scanning entire memory
   - Solution: Use known address ranges
   - Cache extraction results

3. **Validation** - Running siddump twice
   - Solution: Run only when needed (validation flag)
   - Batch validations in parallel

---

## Troubleshooting Development Issues

### Issue: Tests Failing After Changes

**Solution**:
```bash
# 1. Check what changed
git diff

# 2. Run specific failing test
python -m pytest pyscript/test_failing.py::test_method -vv

# 3. Check test data
ls test_data/

# 4. Restore known-good version
git checkout HEAD -- sidm2/module.py

# 5. Reapply changes incrementally
```

---

### Issue: Import Errors

**Solution**:
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify module structure
ls sidm2/__init__.py

# Reinstall in development mode
pip install -e .
```

---

### Issue: External Tools Not Found

**Solution**:
```bash
# Check tools directory
ls tools/player-id.exe

# Download missing tools
# (See README.md for tool sources)

# Verify PATH
echo %PATH%  # Windows
echo $PATH   # Linux/Mac
```

---

## Resources

### Official Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - Architecture reference
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Contribution guidelines
- [README.md](../../README.md) - Project overview

### Technical References

- [SF2_FORMAT_SPEC.md](../reference/SF2_FORMAT_SPEC.md) - SF2 format specification
- [LAXITY_DRIVER_TECHNICAL_REFERENCE.md](../reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md) - Laxity driver deep dive
- [SID_REGISTERS_REFERENCE.md](../SID_REGISTERS_REFERENCE.md) - SID chip reference

### User Guides

- [GETTING_STARTED.md](GETTING_STARTED.md) - Quick start guide
- [LAXITY_DRIVER_USER_GUIDE.md](LAXITY_DRIVER_USER_GUIDE.md) - Laxity driver usage
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - User troubleshooting

---

## Getting Help

1. **Check existing documentation** - Most questions are answered in docs/
2. **Search issues** - https://github.com/MichaelTroelsen/SIDM2conv/issues
3. **Read the code** - Well-commented and structured
4. **Ask questions** - Open a GitHub issue with "Question:" prefix

---

**End of Developer Guide**

**Version**: 3.1.0 | **Lines**: ~1,200 | **Last Updated**: 2026-01-02
