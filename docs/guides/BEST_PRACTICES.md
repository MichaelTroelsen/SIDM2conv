# SIDM2 Best Practices

**Version**: 2.9.7
**Updated**: 2025-12-27

Expert tips, patterns, and optimization strategies for SIDM2.

---

## Table of Contents

### Conversion Best Practices
1. [Driver Selection Strategy](#driver-selection-strategy)
2. [Quality Validation](#quality-validation)
3. [Batch Conversion Optimization](#batch-conversion-optimization)

### Workflow Best Practices
4. [File Organization](#file-organization)
5. [Testing Strategy](#testing-strategy)
6. [Error Handling](#error-handling)

### Development Best Practices
7. [Python API Usage](#python-api-usage)
8. [Performance Optimization](#performance-optimization)
9. [Debugging Techniques](#debugging-techniques)

### Common Patterns
10. [Conversion Patterns](#conversion-patterns)
11. [Validation Patterns](#validation-patterns)
12. [Automation Patterns](#automation-patterns)

---

## Driver Selection Strategy

### Best Practice: Trust Automatic Selection

**Do**:
```bash
# Let SIDM2 auto-select the best driver
sid-to-sf2.bat input.sid output.sf2
```

**Don't**:
```bash
# Don't force drivers unless you know better
sid-to-sf2.bat input.sid output.sf2 --driver laxity  # Only if you're sure
```

**Why**: Automatic selection uses validated patterns to choose optimal drivers, resulting in 99.93% accuracy for Laxity files and 100% for SF2-exported files.

### Best Practice: Verify Driver Selection

**Do**:
```bash
# Always check the .txt file after conversion
sid-to-sf2.bat music.sid output.sf2
type output.txt
```

Look for:
```
Player identified: Laxity NewPlayer v21
Driver selected: laxity
Expected accuracy: 99.93% frame accuracy
```

### Best Practice: Manual Override Only When Needed

**When to override**:
- You know the exact player type
- Auto-detection fails (rare)
- Experimenting with different drivers
- Troubleshooting conversion issues

**Example workflow**:
```bash
# 1. Try automatic first
sid-to-sf2.bat unknown.sid test.sf2
type test.txt

# 2. If accuracy is poor, try other drivers
sid-to-sf2.bat unknown.sid test_laxity.sf2 --driver laxity
sid-to-sf2.bat unknown.sid test_np20.sf2 --driver np20

# 3. Compare results
python scripts/validate_sid_accuracy.py unknown.sid test_laxity.sid
python scripts/validate_sid_accuracy.py unknown.sid test_np20.sid

# 4. Use the best result
```

### Best Practice: Document Your Overrides

If you must override, document why:

```bash
# conversion_notes.txt
File: special_case.sid
Driver Override: laxity (auto-selected driver11 but known to be Laxity NP21)
Reason: Manual verification of player code confirmed Laxity
Result: Accuracy improved from 85% to 99.93%
```

---

## Quality Validation

### Best Practice: Always Validate

**Do**:
```bash
# Check validation results in .txt file
sid-to-sf2.bat input.sid output.sf2
type output.txt | findstr "Validation"
```

Should see:
```
Validating SF2 format...
[OK] SF2 format valid
[OK] All required blocks present
[OK] Voice orderlists valid
[OK] Sequences valid
[OK] Instruments valid
```

### Best Practice: Validate Before Distribution

Before sharing converted files:

```bash
# 1. Convert
sid-to-sf2.bat collection/*.sid

# 2. Validate all
for %%f in (SF2\*.sf2) do (
    sf2-viewer.bat "%%f"  # Visual check
)

# 3. Batch test
test-batch-pyautogui.bat --directory SF2

# 4. Only distribute files that pass 100%
```

### Best Practice: Compare Original vs Converted

**For critical conversions**:

```bash
# Export SF2 back to SID
python scripts/sf2_to_sid.py output.sf2 roundtrip.sid

# Validate accuracy
python scripts/validate_sid_accuracy.py original.sid roundtrip.sid
```

Target accuracy:
- Laxity files: >99%
- SF2-exported: 100%
- Other formats: >85%

### Best Practice: Use Multiple Validation Methods

```bash
# Method 1: Automated validation (built-in)
sid-to-sf2.bat input.sid output.sf2  # Checks .txt file

# Method 2: Frame comparison
python pyscript/siddump_complete.py original.sid -t30 > original.txt
python pyscript/siddump_complete.py converted.sid -t30 > converted.txt
fc original.txt converted.txt

# Method 3: Audio comparison
# Play both in VICE and listen for differences

# Method 4: Visual inspection
sf2-viewer.bat output.sf2  # Check for anomalies
```

---

## Batch Conversion Optimization

### Best Practice: Organize Before Converting

**Good folder structure**:
```
SIDCollection/
├── Laxity/          # Laxity NP21 files
├── SF2Exported/     # SF2-exported files
├── NewPlayer20/     # NP20.G4 files
├── Unknown/         # Unidentified files
└── Converted/       # Output folder
    ├── Laxity/
    ├── SF2Exported/
    └── ...
```

**Conversion script**:
```bash
# Convert each category with optimal settings
batch-convert-laxity.bat
# ... etc
```

### Best Practice: Use Parallel Processing

**For large collections (100+ files)**:

```python
# parallel_convert.py
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import subprocess

def convert_file(sid_path):
    sf2_path = Path("SF2") / f"{sid_path.stem}.sf2"
    result = subprocess.run([
        "python", "scripts/sid_to_sf2.py",
        str(sid_path), str(sf2_path)
    ])
    return sid_path.name, result.returncode == 0

sid_files = list(Path("SID").glob("*.sid"))

# Use all CPU cores
with ProcessPoolExecutor() as executor:
    results = executor.map(convert_file, sid_files)

# Report
for filename, success in results:
    print(f"{filename}: {'OK' if success else 'FAIL'}")
```

**Performance gain**: 4x faster on quad-core CPU

### Best Practice: Filter Before Converting

**Pre-filter for duplicates**:
```python
# deduplicate.py
import hashlib
from pathlib import Path

def get_hash(file_path):
    return hashlib.md5(file_path.read_bytes()).hexdigest()

sid_files = list(Path("SID").glob("*.sid"))
seen_hashes = {}
duplicates = []

for sid_file in sid_files:
    file_hash = get_hash(sid_file)
    if file_hash in seen_hashes:
        duplicates.append((sid_file.name, seen_hashes[file_hash]))
    else:
        seen_hashes[file_hash] = sid_file.name

print(f"Found {len(duplicates)} duplicates")
for dup, original in duplicates:
    print(f"  {dup} is duplicate of {original}")
```

### Best Practice: Checkpoint Long Conversions

**For 1000+ file batches**:

```python
# checkpoint_convert.py
import json
from pathlib import Path

checkpoint_file = Path("conversion_checkpoint.json")

# Load checkpoint
if checkpoint_file.exists():
    completed = set(json.loads(checkpoint_file.read_text()))
else:
    completed = set()

sid_files = list(Path("SID").glob("*.sid"))

for i, sid_file in enumerate(sid_files):
    if sid_file.name in completed:
        print(f"[{i+1}/{len(sid_files)}] Skipping {sid_file.name} (already done)")
        continue

    # Convert
    convert_file(sid_file)

    # Save checkpoint
    completed.add(sid_file.name)
    checkpoint_file.write_text(json.dumps(list(completed)))

print("Conversion complete!")
```

**Benefit**: Resume after interruption without re-converting

---

## File Organization

### Best Practice: Consistent Naming Convention

**Good naming**:
```
Original_Song_Name.sid        -> Original_Song_Name.sf2
Artist_-_Title_v1.2.sid      -> Artist_-_Title_v1.2.sf2
HVSC/MUSICIANS/H/Hubbard.sid -> Hubbard.sf2
```

**Preserve metadata**:
```python
# preserve_metadata.py
def convert_with_metadata(sid_path, sf2_dir):
    """Preserve original path structure"""

    # Extract relative path
    relative = sid_path.relative_to("SID")

    # Create matching output structure
    output_path = Path(sf2_dir) / relative.parent / f"{relative.stem}.sf2"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert
    convert_file(sid_path, output_path)

    return output_path
```

### Best Practice: Include Conversion Metadata

**Always create .txt files**:
```
output/
├── Song1.sf2
├── Song1.txt          # Driver info, validation
├── Song2.sf2
├── Song2.txt
└── ...
```

**Enhanced metadata file**:
```python
# enhanced_metadata.py
def create_metadata(sid_path, sf2_path, driver, accuracy):
    """Create comprehensive metadata"""

    metadata = {
        "original_sid": str(sid_path),
        "converted_sf2": str(sf2_path),
        "conversion_date": datetime.now().isoformat(),
        "player_type": detect_player_type(sid_path),
        "driver_used": driver,
        "expected_accuracy": accuracy,
        "validation_status": validate_sf2(sf2_path),
        "file_sizes": {
            "sid": sid_path.stat().st_size,
            "sf2": sf2_path.stat().st_size
        }
    }

    # Save as JSON
    json_path = sf2_path.with_suffix(".json")
    json_path.write_text(json.dumps(metadata, indent=2))

    return json_path
```

### Best Practice: Archive Original SIDs

**Never delete originals**:
```
Project/
├── SID_Originals/     # Preserve forever
│   └── backup/        # Additional backup
├── SF2_Working/       # Active conversions
└── SF2_Final/         # Distribution copies
```

**Automated backup**:
```bash
# backup.bat
robocopy SID_Originals SID_Originals\backup /MIR /R:3 /W:10
echo Backup complete: %date% %time%
```

---

## Testing Strategy

### Best Practice: Test at Multiple Stages

**Stage 1: Single file smoke test**
```bash
sid-to-sf2.bat test.sid test.sf2
type test.txt
```

**Stage 2: Small batch (10 files)**
```bash
test-batch-pyautogui.bat --max-files 10
```

**Stage 3: Medium batch (100 files)**
```bash
test-batch-pyautogui.bat --max-files 100
```

**Stage 4: Full collection**
```bash
test-batch-pyautogui.bat --directory SF2
```

### Best Practice: Regression Testing

**Create baseline**:
```bash
# First conversion
sid-to-sf2.bat collection/*.sid

# Save baseline
python pyscript/siddump_complete.py output/*.sid -t30 > baseline.txt
```

**Test after changes**:
```bash
# Reconvert
sid-to-sf2.bat collection/*.sid

# Generate new results
python pyscript/siddump_complete.py output/*.sid -t30 > current.txt

# Compare
diff baseline.txt current.txt
```

Should be identical or better.

### Best Practice: Continuous Integration

**Add to your CI pipeline**:

```yaml
# .github/workflows/conversion-quality.yml
name: Conversion Quality Check

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Convert test files
        run: |
          python scripts/sid_to_sf2.py SID/test1.sid test1.sf2
          python scripts/sid_to_sf2.py SID/test2.sid test2.sf2

      - name: Validate
        run: |
          python scripts/validate_sid_accuracy.py SID/test1.sid test1.sid
          python scripts/validate_sid_accuracy.py SID/test2.sid test2.sid
```

---

## Error Handling

### Best Practice: Graceful Degradation

**Do**:
```python
try:
    result = convert_file(sid_path, sf2_path)
    if result:
        print(f"[OK] {sid_path.name}")
    else:
        print(f"[WARN] {sid_path.name} - conversion returned False")
        # Continue with next file
except Exception as e:
    print(f"[ERROR] {sid_path.name} - {e}")
    # Log error and continue
    with open("errors.log", "a") as f:
        f.write(f"{sid_path.name}: {e}\n")
    # Don't crash entire batch
```

**Don't**:
```python
# Don't crash entire batch on single failure
result = convert_file(sid_path, sf2_path)  # Unhandled exception stops batch
```

### Best Practice: Detailed Error Logging

**Use logging levels**:
```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('conversion.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Usage
logger.debug(f"Processing {sid_path}")
logger.info(f"Converted {sid_path.name}")
logger.warning(f"Low accuracy for {sid_path.name}")
logger.error(f"Failed to convert {sid_path.name}")
```

### Best Practice: Retry Logic

**For network/filesystem issues**:
```python
import time

def convert_with_retry(sid_path, sf2_path, max_retries=3):
    """Convert with automatic retry on failure"""

    for attempt in range(max_retries):
        try:
            return convert_file(sid_path, sf2_path)
        except (OSError, IOError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Retry {attempt+1}/{max_retries} after {wait_time}s")
                time.sleep(wait_time)
            else:
                print(f"Failed after {max_retries} attempts: {e}")
                raise

    return False
```

---

## Python API Usage

### Best Practice: Use Context Managers

**For file operations**:
```python
from sidm2.laxity_parser import LaxityParser

# Good: Automatic cleanup
with LaxityParser() as parser:
    data = parser.parse_sid("input.sid")
    # Parser is automatically cleaned up

# Also good: Manual cleanup
parser = LaxityParser()
try:
    data = parser.parse_sid("input.sid")
finally:
    parser.close()
```

### Best Practice: Reuse Components

**Don't create new instances unnecessarily**:

**Inefficient**:
```python
for sid_file in sid_files:
    # Creates new parser every iteration
    parser = LaxityParser()
    data = parser.parse_sid(sid_file)
```

**Efficient**:
```python
# Reuse parser instance
parser = LaxityParser()
for sid_file in sid_files:
    data = parser.parse_sid(sid_file)
```

**Performance gain**: 2-3x faster for batches

### Best Practice: Handle Optional Dependencies

```python
# Check for optional dependencies
try:
    from PyQt6.QtWidgets import QApplication
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False

# Graceful fallback
if HAS_PYQT6:
    # Use GUI
    app = QApplication([])
    viewer = SF2Viewer()
    viewer.show()
else:
    # Use CLI fallback
    print("PyQt6 not found, using text export")
    export_sf2_as_text(sf2_path)
```

---

## Performance Optimization

### Best Practice: Profile Before Optimizing

**Find bottlenecks**:
```bash
# Profile a conversion
python pyscript/siddump_complete.py input.sid -t30 -p

# Output shows time spent in each function
```

**Python profiling**:
```python
import cProfile
import pstats

# Profile conversion
profiler = cProfile.Profile()
profiler.enable()

convert_file(sid_path, sf2_path)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

### Best Practice: Optimize Hot Paths

**Example: Cache repeated calculations**:

**Before** (slow):
```python
def get_wave_value(frame, offset):
    # Recalculates every time
    return (frame * 0.123 + offset) % 256
```

**After** (fast):
```python
# Pre-calculate lookup table
WAVE_TABLE = [(frame * 0.123 + offset) % 256
              for frame in range(10000)
              for offset in range(256)]

def get_wave_value(frame, offset):
    # O(1) lookup
    return WAVE_TABLE[frame * 256 + offset]
```

**Speedup**: 100x for 10,000 frames

### Best Practice: Use Batch Operations

**File I/O**:

**Inefficient**:
```python
for byte in data:
    file.write(bytes([byte]))  # 10,000 write calls
```

**Efficient**:
```python
file.write(bytes(data))  # 1 write call
```

**Speedup**: 100-1000x

---

## Debugging Techniques

### Best Practice: Enable Verbose Logging

```bash
# Verbose mode
python scripts/sid_to_sf2.py input.sid output.sf2 -vv

# Debug mode
python scripts/sid_to_sf2.py input.sid output.sf2 --debug

# Log to file
python scripts/sid_to_sf2.py input.sid output.sf2 --log-file debug.log -vv
```

### Best Practice: Use Python siddump for Analysis

**Compare frame-by-frame**:
```bash
# Dump 30 seconds
python pyscript/siddump_complete.py original.sid -t30 > original.txt
python pyscript/siddump_complete.py converted.sid -t30 > converted.txt

# Find differences
diff original.txt converted.txt
```

### Best Practice: Trace SID Register Writes

**For deep debugging**:
```bash
# Full trace (1500 frames = 60 seconds)
python pyscript/sidwinder_trace.py --trace trace.txt --frames 1500 input.sid

# Analyze trace
grep "D400" trace.txt  # Voice 1 frequency low
grep "D401" trace.txt  # Voice 1 frequency high
```

### Best Practice: Visual Debugging

**Use SF2 Viewer**:
```bash
sf2-viewer.bat output.sf2
```

Check for:
- Empty sequences
- Duplicate sequences
- Unused instruments
- Suspicious table values (all zeros, all FFs)

---

## Conversion Patterns

### Pattern: Quality-First Workflow

```python
def quality_first_convert(sid_path, sf2_dir):
    """Convert with quality checks at each stage"""

    # Stage 1: Detect player
    player_type, driver = detect_and_select(sid_path)
    print(f"Player: {player_type}, Driver: {driver}")

    # Stage 2: Convert
    sf2_path = sf2_dir / f"{sid_path.stem}.sf2"
    success = convert_file(sid_path, sf2_path, driver)

    if not success:
        print(f"[FAIL] Conversion failed")
        return None

    # Stage 3: Validate format
    if not validate_sf2_format(sf2_path):
        print(f"[FAIL] Invalid SF2 format")
        return None

    # Stage 4: Validate accuracy
    roundtrip_sid = sf2_to_sid(sf2_path)
    accuracy = compare_sids(sid_path, roundtrip_sid)

    if accuracy < 85.0:
        print(f"[WARN] Low accuracy: {accuracy}%")
        # Try different driver?

    print(f"[OK] Conversion complete ({accuracy:.2f}%)")
    return sf2_path
```

### Pattern: Multi-Driver Comparison

```python
def find_best_driver(sid_path):
    """Try all drivers and choose best result"""

    drivers = ["laxity", "driver11", "np20"]
    results = {}

    for driver in drivers:
        # Convert
        sf2_path = f"test_{driver}.sf2"
        convert_file(sid_path, sf2_path, driver)

        # Measure accuracy
        roundtrip_sid = sf2_to_sid(sf2_path)
        accuracy = compare_sids(sid_path, roundtrip_sid)

        results[driver] = accuracy
        print(f"{driver}: {accuracy:.2f}%")

    # Choose best
    best_driver = max(results, key=results.get)
    best_accuracy = results[best_driver]

    print(f"\nBest: {best_driver} ({best_accuracy:.2f}%)")
    return best_driver
```

### Pattern: Incremental Batch Processing

```python
def incremental_batch(sid_files, sf2_dir, batch_size=10):
    """Process in small batches with checkpoints"""

    total = len(sid_files)
    for i in range(0, total, batch_size):
        batch = sid_files[i:i+batch_size]

        print(f"\nBatch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")

        for sid_file in batch:
            convert_file(sid_file, sf2_dir / f"{sid_file.stem}.sf2")

        # Checkpoint after each batch
        save_checkpoint(i + len(batch))

        print(f"Checkpoint saved: {i + len(batch)}/{total} complete")
```

---

## Validation Patterns

### Pattern: Multi-Level Validation

```python
def comprehensive_validation(sf2_path):
    """Validate at multiple levels"""

    results = {
        "format": False,
        "structure": False,
        "content": False,
        "playback": False
    }

    # Level 1: Format validation
    results["format"] = validate_sf2_format(sf2_path)
    if not results["format"]:
        return results

    # Level 2: Structure validation
    results["structure"] = validate_sf2_structure(sf2_path)
    if not results["structure"]:
        return results

    # Level 3: Content validation
    results["content"] = validate_sf2_content(sf2_path)

    # Level 4: Playback validation (optional)
    if has_editor():
        results["playback"] = test_playback(sf2_path)

    return results
```

### Pattern: Statistical Validation

```python
def statistical_validation(original_sid, converted_sid, threshold=95.0):
    """Validate using statistical analysis"""

    # Collect metrics
    metrics = {
        "frame_accuracy": 0.0,
        "register_match_rate": 0.0,
        "timing_deviation": 0.0
    }

    # Analyze frames
    original_frames = dump_sid(original_sid, 1500)
    converted_frames = dump_sid(converted_sid, 1500)

    matches = sum(1 for o, c in zip(original_frames, converted_frames) if o == c)
    metrics["frame_accuracy"] = (matches / len(original_frames)) * 100

    # Analyze registers
    # ... register analysis ...

    # Overall score
    overall = (metrics["frame_accuracy"] + metrics["register_match_rate"]) / 2

    return overall >= threshold, metrics
```

---

## Automation Patterns

### Pattern: Automated Pipeline

```python
def automated_pipeline(config_file):
    """Fully automated conversion pipeline"""

    # Load configuration
    config = load_config(config_file)

    # Stage 1: Discovery
    sid_files = discover_sid_files(config["input_dir"])
    print(f"Found {len(sid_files)} SID files")

    # Stage 2: Analysis
    categorized = categorize_by_player(sid_files)
    for player_type, files in categorized.items():
        print(f"  {player_type}: {len(files)} files")

    # Stage 3: Conversion
    results = convert_all(sid_files, config["output_dir"])

    # Stage 4: Validation
    validated = validate_all(results)

    # Stage 5: Reporting
    generate_report(validated, config["report_file"])

    # Stage 6: Distribution
    if config["auto_distribute"]:
        distribute_files(validated, config["dist_dir"])

    return validated
```

### Pattern: Watch Folder

```python
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SIDConverterHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".sid"):
            print(f"New SID detected: {event.src_path}")
            sf2_path = event.src_path.replace(".sid", ".sf2")
            convert_file(event.src_path, sf2_path)

# Setup watch folder
observer = Observer()
observer.schedule(SIDConverterHandler(), "watch_folder", recursive=False)
observer.start()

print("Watching for new SID files...")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
```

---

## Anti-Patterns to Avoid

### Anti-Pattern: Ignoring Validation

**Don't**:
```bash
# Convert without checking results
sid-to-sf2.bat file.sid output.sf2
# Distribute immediately without validation
```

**Do**:
```bash
# Convert and validate
sid-to-sf2.bat file.sid output.sf2
type output.txt  # Check validation
sf2-viewer.bat output.sf2  # Visual check
```

### Anti-Pattern: Hardcoded Paths

**Don't**:
```python
# Hardcoded paths break on other systems
convert_file("C:\\Users\\Me\\SID\\file.sid", "C:\\Output\\file.sf2")
```

**Do**:
```python
# Use Path objects and relative paths
from pathlib import Path
sid_dir = Path("SID")
sf2_dir = Path("SF2")
convert_file(sid_dir / "file.sid", sf2_dir / "file.sf2")
```

### Anti-Pattern: Silent Failures

**Don't**:
```python
try:
    convert_file(sid_path, sf2_path)
except:
    pass  # Silent failure - BAD!
```

**Do**:
```python
try:
    convert_file(sid_path, sf2_path)
except Exception as e:
    logger.error(f"Conversion failed for {sid_path.name}: {e}")
    # Save to error log
    with open("errors.log", "a") as f:
        f.write(f"{sid_path.name}: {e}\n")
```

### Anti-Pattern: One-Size-Fits-All

**Don't**:
```bash
# Force same driver for all files
for %%f in (*.sid) do (
    sid-to-sf2.bat "%%f" "output\%%~nf.sf2" --driver driver11
)
```

**Do**:
```bash
# Let auto-selection choose best driver per file
for %%f in (*.sid) do (
    sid-to-sf2.bat "%%f" "output\%%~nf.sf2"
)
```

---

## Quick Reference

### Conversion Checklist

- [ ] Use automatic driver selection
- [ ] Check validation in .txt file
- [ ] Test SF2 in viewer before distribution
- [ ] Keep original SID files
- [ ] Document any manual overrides

### Batch Processing Checklist

- [ ] Organize files by player type
- [ ] Use checkpointing for large batches
- [ ] Enable logging
- [ ] Validate sample before full batch
- [ ] Monitor resource usage

### Quality Assurance Checklist

- [ ] Validate SF2 format
- [ ] Compare original vs converted
- [ ] Test playback
- [ ] Check for anomalies in viewer
- [ ] Run batch testing

---

## Summary

**Key Principles**:
1. **Trust automation** - Auto-selection is validated and optimal
2. **Validate everything** - Never skip validation steps
3. **Fail gracefully** - Handle errors without crashing
4. **Document everything** - Track conversions and decisions
5. **Optimize smartly** - Profile before optimizing

**Remember**: Quality first, speed second.

---

## Additional Resources

- **[Getting Started](GETTING_STARTED.md)** - Basics
- **[Tutorials](TUTORIALS.md)** - Step-by-step workflows
- **[FAQ](FAQ.md)** - Common questions
- **[Troubleshooting](TROUBLESHOOTING.md)** - Error solutions

---

**Last Updated**: 2025-12-27
**Version**: 2.9.7
**Status**: Production Ready
