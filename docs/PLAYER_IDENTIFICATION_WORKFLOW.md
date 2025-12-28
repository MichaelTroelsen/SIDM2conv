# Player Identification Workflow

**Rule**: **ALWAYS** identify player type before attempting SID conversion

**Date**: 2025-12-28
**Version**: 1.0

---

## Quick Reference

```bash
# STEP 1: Identify player type FIRST
tools/player-id.exe "input.sid"

# STEP 2: Convert with appropriate driver
python scripts/sid_to_sf2.py "input.sid" output.sf2 --driver [driver_type]
```

---

## Why This Matters

### The Problem

SID files can have confusing player type detection that doesn't match the actual player format:

**Example**: `Stinsens_Last_Night_of_89.sid`
- **Created by**: Laxity (composer)
- **Created in**: SID Factory II
- **Player format**: Driver 11 (standard SF2 player)
- **player-id detects**: "SidFactory_II/Laxity"

**Wrong assumption**: "Laxity" in player name → Use Laxity NewPlayer v21 driver → **FAILS!**

**Correct approach**: "SidFactory_II" prefix → Created in SF2 → Use Driver 11 → **Works!**

### The Confusion

Player detection strings can mean different things:

| Player String | Could Mean | Actual Driver |
|---------------|------------|---------------|
| `SidFactory_II/Laxity` | Created by Laxity in SF2 | **driver11** |
| `Laxity_NewPlayer_V21` | Native Laxity player | **laxity** |
| `SidFactory/Laxity` | SF2-exported by Laxity | **driver11** |
| `Vibrants/Laxity` | Laxity player variant | **laxity** |

**Key insight**: File authorship (who made it) ≠ Player format (how it plays)

---

## Standard Workflow

### Step 1: Identify Player Type

```bash
tools/player-id.exe "path/to/file.sid"
```

**Output example**:
```
path/to/file.sid                     SidFactory_II/Laxity

Detected players          Count
-------------------------------
SidFactory_II/Laxity          1
```

### Step 2: Determine Correct Driver

Use the mapping table:

| Player Detection | Driver | Reason |
|------------------|--------|--------|
| `SidFactory_II/*` | **driver11** | SF2-created file |
| `SidFactory/*` | **driver11** | SF2-exported file |
| `Laxity_NewPlayer_V21` | **laxity** | Native Laxity |
| `Vibrants/Laxity` | **laxity** | Laxity variant |
| `256bytes/Laxity` | **laxity** | Laxity variant |
| `NewPlayer_20*` | **np20** | NewPlayer 20 |
| `Unknown` | **driver11** | Safe default |

**Important**: Look at the PREFIX, not just "Laxity" in the name!

### Step 3: Convert with Correct Driver

```bash
# Example: SidFactory_II/Laxity → use driver11
python scripts/sid_to_sf2.py "input.sid" output.sf2 --driver driver11

# Example: Laxity_NewPlayer_V21 → use laxity
python scripts/sid_to_sf2.py "input.sid" output.sf2 --driver laxity

# Example: Auto-detection (uses driver_selector.py mapping)
python scripts/sid_to_sf2.py "input.sid" output.sf2
```

---

## Driver Selection Logic

### Automatic Selection (v3.0.1+)

The system uses `sidm2/driver_selector.py` mapping:

```python
PLAYER_MAPPINGS = {
    # SF2-created/exported (100% accuracy with Driver 11)
    'SidFactory_II/Laxity': 'driver11',
    'SidFactory/Laxity': 'driver11',
    'SidFactory_II': 'driver11',
    'SidFactory': 'driver11',

    # Native Laxity (99.93% accuracy with Laxity driver)
    'Laxity_NewPlayer_V21': 'laxity',
    'Vibrants/Laxity': 'laxity',
    '256bytes/Laxity': 'laxity',

    # NewPlayer 20
    'NewPlayer_20': 'np20',
    'NewPlayer_20.G4': 'np20',
}
```

### Manual Override

You can always override automatic selection:

```bash
python scripts/sid_to_sf2.py "input.sid" output.sf2 --driver driver11
```

**When to override**:
- You know the actual player format better than auto-detection
- Testing different drivers for comparison
- Auto-detection is wrong or uncertain

---

## Decision Tree

```
START
  |
  v
Run player-id.exe
  |
  v
Does player string start with "SidFactory" ?
  |
  +-- YES --> Use driver11 (SF2-created file)
  |
  +-- NO --> Does string contain "NewPlayer_V21" OR "Vibrants" OR "256bytes" ?
            |
            +-- YES --> Use laxity (Native Laxity player)
            |
            +-- NO --> Does string contain "NewPlayer_20" ?
                      |
                      +-- YES --> Use np20 (NewPlayer 20)
                      |
                      +-- NO --> Use driver11 (safe default)
```

---

## Common Mistakes

### ❌ WRONG: Simple String Matching

```python
# BAD CODE (v3.0.0 and earlier):
if 'Laxity' in player_type:
    use_laxity_driver()  # WRONG for SidFactory_II/Laxity!
```

This fails because "SidFactory_II/Laxity" contains "Laxity" but uses Driver 11!

### ✅ CORRECT: Use Driver Selector Mapping

```python
# GOOD CODE (v3.0.1+):
selector = DriverSelector()
selection = selector.select_driver(Path(filepath))
driver_type = selection.driver_name  # Respects mapping table
```

This correctly maps "SidFactory_II/Laxity" → "driver11"

---

## Expected Results

### Correct Driver Selection

| Input File | Player Detection | Selected Driver | Output Size |
|------------|------------------|-----------------|-------------|
| Stinsens_Last_Night_of_89.sid | SidFactory_II/Laxity | **driver11** | ~12 KB |
| (Native Laxity file) | Laxity_NewPlayer_V21 | **laxity** | ~10-12 KB |
| (NewPlayer 20 file) | NewPlayer_20.G4 | **np20** | ~8-10 KB |

### Wrong Driver Selection

| Input File | Wrong Driver | Symptoms |
|------------|--------------|----------|
| Stinsens (Driver 11 file) | **laxity** | Small file (5.2 KB), missing data, "block too small" errors |
| Native Laxity file | **driver11** | Low accuracy (1-8%), poor playback |

---

## Verification Steps

### After Conversion

1. **Check file size**:
   - Driver 11: ~10-12 KB
   - Laxity: ~10-12 KB
   - Too small (<6 KB) → Wrong driver!

2. **Check SF2 Viewer**:
   ```bash
   python pyscript/sf2_viewer_gui.py output.sf2
   ```
   - Should NOT show "Driver Common block too small"
   - Should NOT show "Music Data block too small"

3. **Check driver info**:
   ```bash
   cat output.txt
   ```
   Look for: `Driver: driver11 (User override)` or `Driver: driver11 (Auto-selected)`

4. **Test in SID Factory II**:
   - File should load without errors
   - Playback should work
   - Data should be editable

---

## Troubleshooting

### Problem: Output file is too small

**Symptoms**:
- File is 5-6 KB instead of 10-12 KB
- SF2 Viewer shows "block too small" warnings

**Cause**: Wrong driver selected

**Solution**:
1. Re-run player-id.exe to verify player type
2. Check PLAYER_IDENTIFICATION_WORKFLOW.md for correct driver
3. Convert again with correct --driver flag

### Problem: Low accuracy conversion

**Symptoms**:
- Validation shows 1-8% accuracy
- Music sounds wrong

**Cause**: Using Driver 11 for Laxity file (or vice versa)

**Solution**:
1. Verify player type with player-id.exe
2. Use Laxity driver for Laxity_NewPlayer_V21 files
3. Use Driver 11 for SidFactory_II/* files

### Problem: player-id detects "Unknown"

**Solution**:
1. Default to Driver 11 (safe default)
2. Try conversion and check results
3. If output is poor, try Laxity driver manually
4. Report unknown player type for future mapping

---

## Testing Examples

### Example 1: Stinsen File

```bash
# Step 1: Identify
$ tools/player-id.exe "Laxity/Stinsens_Last_Night_of_89.sid"
Laxity/Stinsens_Last_Night_of_89.sid                     SidFactory_II/Laxity

# Step 2: Check mapping (SidFactory_II/* → driver11)
# Step 3: Convert
$ python scripts/sid_to_sf2.py "Laxity/Stinsens_Last_Night_of_89.sid" output.sf2 --driver driver11

# Result: 12 KB file, no warnings, 100% accuracy
```

### Example 2: Native Laxity File

```bash
# Step 1: Identify
$ tools/player-id.exe "path/to/native_laxity.sid"
path/to/native_laxity.sid                     Laxity_NewPlayer_V21

# Step 2: Check mapping (Laxity_NewPlayer_V21 → laxity)
# Step 3: Convert
$ python scripts/sid_to_sf2.py "path/to/native_laxity.sid" output.sf2 --driver laxity

# Result: 10-12 KB file, 99.93% accuracy
```

### Example 3: Auto-Detection

```bash
# Auto-detection uses driver_selector.py mapping
$ python scripts/sid_to_sf2.py "input.sid" output.sf2

# System will:
# 1. Run player-id.exe internally
# 2. Look up player type in PLAYER_MAPPINGS
# 3. Select correct driver automatically
# 4. Log selection reason
```

---

## Best Practices

1. **Always identify first**: Don't guess the player type
2. **Trust the mapping**: driver_selector.py has correct mappings
3. **Verify results**: Check file size and SF2 Viewer output
4. **Document special cases**: Add notes for unusual player types
5. **Report bugs**: If auto-detection fails, report it
6. **Use --driver override**: When you know better than auto-detection
7. **Check prefix first**: "SidFactory" prefix is more important than "Laxity" suffix

---

## Integration with SIDM2 Pipeline

### v3.0.1+ Behavior

The conversion pipeline now:
1. Calls `DriverSelector.select_driver()` to determine driver
2. Passes `driver_type` to `analyze_sid_file()`
3. Uses correct analyzer based on driver_type
4. Respects `--driver` manual override
5. Logs driver selection reason

### Code Reference

See `sidm2/conversion_pipeline.py`:
- Line 286: `analyze_sid_file()` accepts `driver_type` parameter
- Line 311: Uses `DriverSelector.select_driver()`
- Line 344-357: Selects analyzer based on `driver_type`

See `sidm2/driver_selector.py`:
- Line 48-68: `PLAYER_MAPPINGS` table
- Line 156: `select_driver()` method

---

## Summary

**The Golden Rule**: **ALWAYS identify player type BEFORE conversion**

**Key Points**:
- Player name ≠ Player format
- "Laxity" in name doesn't always mean Laxity driver
- "SidFactory" prefix indicates SF2-created file → Driver 11
- Use driver_selector.py mapping, not simple string matching
- Verify results (file size, SF2 Viewer, playback)
- Manual override is always available with --driver flag

**Fixed in v3.0.1**:
- analyze_sid_file() now respects driver_selector.py mapping
- --driver flag is properly honored
- "SidFactory_II/Laxity" files now correctly use Driver 11

---

**End of Workflow Guide**
