# Driver Selection Guide

**Automatic SID Player Detection and Driver Selection**

**Version**: 2.8.0+
**Feature**: Auto-Select Driver
**Policy**: Quality-First v2.0

---

## Overview

SIDM2 automatically selects the best SF2 driver based on the source SID player type, ensuring maximum conversion accuracy without manual configuration.

**Key Benefits**:
- ✅ **Automatic** - No manual `--driver` flag needed
- ✅ **Quality-First** - Selects best driver for each player type
- ✅ **Documented** - Creates info file explaining selection
- ✅ **Validated** - Checks SF2 format compatibility
- ✅ **Flexible** - Expert override available

---

## How It Works

### 1. Player Identification

Uses `tools/player-id.exe` to identify the SID player type:

```bash
$ tools/player-id.exe music.sid
music.sid  SidFactory_II/Laxity
```

### 2. Driver Selection

Maps player type to optimal driver:

| Source Player | Selected Driver | Accuracy | Reason |
|--------------|----------------|----------|--------|
| **Laxity NewPlayer v21** | Laxity | **99.93%** | Custom optimized driver |
| **SF2-exported** | Driver 11 | **100%** | Perfect roundtrip |
| **NewPlayer 20.G4** | NP20 | **70-90%** | Format-specific driver |
| **Unknown/Others** | Driver 11 | Safe default | Maximum compatibility |

### 3. Conversion

Converts using selected driver and validates output:

```bash
$ python scripts/sid_to_sf2.py input.sid output.sf2
Driver Selection:
  Player Type:     SidFactory_II/Laxity
  Selected Driver: LAXITY (sf2driver_laxity_00.prg)
  Expected Acc:    99.93%
  Reason:          Laxity-specific driver for maximum accuracy
  Alternative:     Driver 11 (1-8% accuracy - not recommended)

Conversion complete: output.sf2 (10,892 bytes)
Info file created: output.txt
```

### 4. Documentation

Creates `output.txt` info file with:
- Player type identification
- Driver selection rationale
- Expected accuracy
- Validation results

---

## Usage Examples

### Basic Usage (Automatic Selection)

```bash
# Automatic - recommended for most files
python scripts/sid_to_sf2.py input.sid output.sf2

# Batch conversion - automatic for each file
python scripts/batch_convert_laxity.py
```

### Expert Override

```bash
# Force specific driver (use with caution)
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11
python scripts/sid_to_sf2.py input.sid output.sf2 --driver np20
```

**Warning**: Manual override bypasses automatic selection and may reduce accuracy.

### Programmatic Usage

```python
from pathlib import Path
from sidm2.driver_selector import DriverSelector

# Initialize selector
selector = DriverSelector()

# Automatic selection
result = selector.select_driver(Path('music.sid'))
print(f"Selected: {result.driver_name}")
print(f"Accuracy: {result.expected_accuracy}")
print(f"Reason: {result.selection_reason}")

# Output formatted info
print(selector.format_selection_output(result))

# Expert override
forced = selector.select_driver(
    Path('music.sid'),
    force_driver='driver11'
)
```

---

## Player Type Mappings

### Laxity Variants

Maps to **Laxity Driver (99.93% accuracy)**:

- `Laxity_NewPlayer_V21`
- `Vibrants/Laxity`
- `SidFactory_II/Laxity`
- `SidFactory/Laxity`
- `256bytes/Laxity`
- Any player name containing "laxity" (case-insensitive)

**Accuracy**: 99.93% frame accuracy (validated on multiple test files)

**Alternative**: Driver 11 (1-8% accuracy - **not recommended**)

---

### NewPlayer 20.G4 Variants

Maps to **NP20 Driver (70-90% accuracy)**:

- `NewPlayer_20`
- `NewPlayer_20.G4`
- `NP20`
- Player names containing both "newplayer" and "20"

**Accuracy**: 70-90% (format-specific driver)

**Alternative**: Driver 11 (~10-20% accuracy)

---

### SF2-Exported Files

Maps to **Driver 11 (100% accuracy)**:

- `SF2_Exported`
- `Driver_11`
- Player names containing "sf2" or "driver"

**Accuracy**: 100% (perfect roundtrip)

**Why**: Preserves original Driver 11 structure for perfect fidelity

---

### Unknown/Others

Maps to **Driver 11 (safe default)**:

- `Unknown`
- `UNIDENTIFIED`
- Rob Hubbard files
- Martin Galway files
- Any unrecognized player

**Accuracy**: Variable (safe, universally compatible)

**Reason**: Driver 11 is the standard SF2 driver that works with most files

---

## Selection Process

### Step 1: Player Identification

```
Input SID → player-id.exe → Player Type
```

**Methods** (in priority order):
1. Run `tools/player-id.exe` on file
2. Parse output for player type
3. Return "Unknown" if identification fails

**Example**:
```bash
$ tools/player-id.exe Broware.sid
Broware.sid  SidFactory_II/Laxity
```

---

### Step 2: Driver Mapping

```
Player Type → Selection Logic → Best Driver
```

**Selection Rules**:
1. **Exact Match**: Check `PLAYER_MAPPINGS` dictionary
2. **Partial Match**: Check for "laxity", "newplayer", "sf2", "driver" in name
3. **Default**: Fall back to Driver 11 (safe, universal)

**Code**:
```python
def _select_best_driver(self, player_type: str) -> str:
    # Check exact mapping
    if player_type in PLAYER_MAPPINGS:
        return PLAYER_MAPPINGS[player_type]

    # Check partial matches (case-insensitive)
    player_lower = player_type.lower()

    if 'laxity' in player_lower:
        return 'laxity'

    if 'newplayer' in player_lower and '20' in player_lower:
        return 'np20'

    if 'sf2' in player_lower or 'driver' in player_lower:
        return 'driver11'

    # Default to Driver 11 (safe, universal)
    return 'driver11'
```

---

### Step 3: Result Building

```
Driver Name → Build DriverSelection → Complete Info
```

**DriverSelection** contains:
- `driver_name` - Selected driver ("laxity", "driver11", "np20")
- `driver_file` - Driver PRG file ("sf2driver_laxity_00.prg")
- `expected_accuracy` - Expected conversion accuracy
- `selection_reason` - Why this driver was selected
- `player_type` - Identified player type
- `alternative_driver` - Alternative option (if applicable)
- `alternative_accuracy` - Alternative accuracy (if applicable)

---

### Step 4: Conversion & Validation

```
DriverSelection → Convert → Validate → Info File
```

**Outputs**:
1. **SF2 File** - Converted music file
2. **Info File** - Complete conversion information
3. **Console Output** - Driver selection summary

---

## Info File Format

Example `output.txt`:

```
Conversion Information
======================================================================
File: Broware.sid
Date: 2025-12-27 12:34:56
Converter: SIDM2 v2.8.0

Source File:
  Title:           Broware
  Author:          Laxity
  Copyright:       1991
  Player Type:     SidFactory_II/Laxity
  Format:          PSID v2
  Load Address:    $1000
  Init Address:    $1000
  Play Address:    $10A1
  Songs:           1

Driver Selection:
  Selected Driver: LAXITY (sf2driver_laxity_00.prg)
  Expected Acc:    99.93%
  Reason:          Laxity-specific driver for maximum accuracy
  Alternative:     Driver 11 (1-8% accuracy)

Conversion Results:
  Status:          SUCCESS
  Output File:     Broware.sf2
  Output Size:     10,892 bytes
  Validation:      PASSED

Validation Details:
  ✓ Magic number present (0x1337)
  ✓ Load address valid ($0D7E)
  ✓ Init/play addresses valid
  ✓ SF2 header blocks complete
  ✓ Music data present
```

---

## Error Handling

### Player Identification Fails

**Symptoms**:
- `player-id.exe` not found
- Timeout during identification
- Exception during subprocess execution

**Behavior**:
- Returns `"Unknown"` as player type
- Selects Driver 11 (safe default)
- Logs warning in debug output

**Solution**: Usually not a problem - Driver 11 works for most files.

---

### Forced Driver Not Found

**Symptoms**:
```bash
$ python scripts/sid_to_sf2.py input.sid output.sf2 --driver invalid
Error: Unknown driver 'invalid'
```

**Valid drivers**: `laxity`, `driver11`, `np20`

**Solution**: Use valid driver name or omit `--driver` for automatic selection.

---

### Conversion Fails with Selected Driver

**Symptoms**:
- File won't load in SID Factory II
- Playback errors
- Missing data

**Troubleshooting**:
1. Check `output.txt` for validation errors
2. Try forcing Driver 11: `--driver driver11`
3. Verify source SID plays correctly in VICE
4. Check `docs/guides/TROUBLESHOOTING.md`

---

## Testing

### Unit Tests

```bash
# Run driver selection tests
python pyscript/test_driver_selector.py

# Run all tests
test-all.bat
```

**Coverage**: 28 test cases covering:
- Laxity variant mapping (5 variants)
- NewPlayer 20 variant mapping (3 variants)
- SF2-exported mapping (2 variants)
- Unknown player defaults (5 cases)
- Partial matching (Laxity, NP20)
- Selection result building (Laxity, NP20, Driver 11 SF2, Driver 11 default)
- Forced driver override
- Output formatting (console, info file)
- Conversion info creation
- Player identification (success, unidentified, exception, no exe)
- Edge cases (empty player, case-insensitive, whitespace, special characters, long names)
- Validation (driver files, accuracy mappings)

---

## Performance

### Benchmarks

- **Player Identification**: ~0.02 seconds (player-id.exe)
- **Driver Selection**: <0.001 seconds (in-memory mapping)
- **Total Overhead**: Negligible (~2% of total conversion time)

### Caching (Future Enhancement)

Currently, player identification is performed on every conversion. Future optimization could cache results:

```python
# Potential caching implementation
cache = {}

def identify_player_cached(sid_file: Path) -> str:
    cache_key = (sid_file, sid_file.stat().st_mtime)
    if cache_key in cache:
        return cache[cache_key]

    result = identify_player(sid_file)
    cache[cache_key] = result
    return result
```

**Benefit**: Faster batch conversions (eliminate player-id.exe calls)
**Trade-off**: Memory usage for cache storage

---

## Best Practices

### 1. Use Automatic Selection (Recommended)

```bash
# DO THIS
python scripts/sid_to_sf2.py input.sid output.sf2
```

**Why**: Ensures best accuracy for each file type.

---

### 2. Check Info File

```bash
# View driver selection rationale
cat output.txt
```

**Why**: Understand why a specific driver was selected.

---

### 3. Validate Output

```bash
# Load in SID Factory II
# Check playback quality
```

**Why**: Confirm conversion accuracy.

---

### 4. Expert Override Only When Needed

```bash
# Only if you have specific requirements
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
```

**Why**: Automatic selection is optimized for quality.

---

### 5. Report Issues

If automatic selection produces poor results:

1. Check `output.txt` for driver selection
2. Try manual override to compare
3. Report issue with:
   - Player type identified
   - Driver selected
   - Expected vs actual accuracy
   - File details (title, author, player)

---

## FAQ

### Q: How does automatic selection work?

**A**: Uses `player-id.exe` to identify the SID player type, then maps to the best driver using a quality-first policy.

---

### Q: Can I override automatic selection?

**A**: Yes, use `--driver <name>` flag. But automatic selection is recommended for maximum accuracy.

---

### Q: What if player-id.exe fails?

**A**: Falls back to Driver 11 (safe default). Works for most files.

---

### Q: How accurate is automatic selection?

**A**: Selects correct driver 95%+ of time (based on player type detection accuracy).

---

### Q: Does it work for all SID files?

**A**: Driver selection works for all files. Driver 11 is universal fallback. Specific drivers (Laxity, NP20) optimize for known player types.

---

### Q: How do I know which driver was selected?

**A**: Check console output or `output.txt` info file.

---

### Q: Can I batch convert with automatic selection?

**A**: Yes! Each file gets automatic driver selection:

```bash
python scripts/batch_convert_laxity.py
```

---

### Q: What's the difference between drivers?

**A**:
- **Laxity**: Custom driver for Laxity NewPlayer v21 (99.93% accuracy)
- **Driver 11**: Standard SF2 driver (universal compatibility)
- **NP20**: Custom driver for NewPlayer 20.G4 (70-90% accuracy)

---

### Q: How can I add new player types?

**A**: Edit `sidm2/driver_selector.py` and add to `PLAYER_MAPPINGS`:

```python
PLAYER_MAPPINGS = {
    'New_Player_Type': 'driver_name',
    # ...
}
```

Then submit a pull request!

---

## Advanced Usage

### Custom Player Detection

```python
from sidm2.driver_selector import DriverSelector

# Pre-identify player (e.g., from metadata)
player_type = "CustomPlayer_V3"

selector = DriverSelector()
result = selector.select_driver(
    Path('music.sid'),
    player_type=player_type
)
```

---

### Integration with Pipeline

```python
from pathlib import Path
from sidm2.driver_selector import DriverSelector

def convert_with_auto_selection(sid_file: Path, output_file: Path):
    # Create selector
    selector = DriverSelector()

    # Auto-select driver
    selection = selector.select_driver(sid_file)

    # Log selection
    print(selector.format_selection_output(selection))

    # Convert using selected driver
    from scripts.sid_to_sf2 import convert_sid_to_sf2
    convert_sid_to_sf2(
        sid_file,
        output_file,
        driver_type=selection.driver_name
    )

    # Create info file
    info_content = selector.create_conversion_info(
        selection,
        sid_file,
        output_file,
        sid_metadata={...}
    )

    info_file = output_file.with_suffix('.txt')
    info_file.write_text(info_content)
```

---

## Implementation Details

### Code Location

- **Main Module**: `sidm2/driver_selector.py`
- **Integration**: `scripts/sid_to_sf2.py` (uses DriverSelector)
- **Tests**: `pyscript/test_driver_selector.py`
- **Tool**: `tools/player-id.exe` (external)

---

### Class Structure

```python
class DriverSelector:
    # Driver file mappings
    DRIVER_FILES = {
        'laxity': 'sf2driver_laxity_00.prg',
        'driver11': 'sf2driver_11.prg',
        'np20': 'sf2driver_np20.prg',
    }

    # Player type → Driver mapping
    PLAYER_MAPPINGS = {
        'Laxity_NewPlayer_V21': 'laxity',
        # ...
    }

    # Expected accuracies
    EXPECTED_ACCURACY = {
        'laxity': '99.93%',
        'driver11_sf2': '100%',
        'driver11_default': 'Safe default',
        'np20': '70-90%',
    }

    def identify_player(self, sid_file) -> str
    def select_driver(self, sid_file, player_type=None, force_driver=None) -> DriverSelection
    def format_selection_output(self, selection) -> str
    def format_info_file_section(self, selection) -> str
    def create_conversion_info(self, selection, ...) -> str
```

---

### DriverSelection Dataclass

```python
@dataclass
class DriverSelection:
    driver_name: str              # "laxity", "driver11", "np20"
    driver_file: str              # "sf2driver_laxity_00.prg"
    expected_accuracy: str        # "99.93%", "100%", "70-90%"
    selection_reason: str         # Why this driver was selected
    player_type: str              # Identified player type
    alternative_driver: str = ""  # Alternative option
    alternative_accuracy: str = "" # Alternative accuracy
```

---

## Version History

### v2.8.0 (2025-12-22)
- ✅ Initial automatic driver selection implementation
- ✅ Player type mapping (Laxity, NP20, Driver 11)
- ✅ Info file generation
- ✅ Integration with sid_to_sf2.py

### v2.9.7 (2025-12-27) - Polish
- ✅ Comprehensive unit tests (28 test cases)
- ✅ Edge case handling (empty, whitespace, special characters)
- ✅ Documentation (this guide)
- ✅ Integration into test-all.bat

---

## References

- **ROADMAP.md** - Section 2.2: Player Format Auto-Detection
- **CONVERSION_POLICY_APPROVED.md** - Quality-First Policy v2.0
- **sidm2/driver_selector.py** - Implementation
- **pyscript/test_driver_selector.py** - Test suite
- **CLAUDE.md** - Quick reference (line 30-50)

---

## Support

**Issues**: https://github.com/MichaelTroelsen/SIDM2conv/issues
**Documentation**: See `docs/guides/TROUBLESHOOTING.md`
**Questions**: Check FAQ above or open GitHub Discussion

---

**End of Driver Selection Guide**
