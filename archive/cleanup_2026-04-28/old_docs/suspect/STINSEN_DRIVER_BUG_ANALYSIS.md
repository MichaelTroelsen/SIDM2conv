# Stinsen Driver Selection Bug Analysis

**Date**: 2025-12-28
**Issue**: `analyze_sid_file()` ignores `--driver` flag and driver selector mapping
**Impact**: Files detected as "SidFactory_II/Laxity" always use Laxity analyzer regardless of actual driver

---

## Problem Summary

When converting `Stinsens_Last_Night_of_89.sid` with `--driver driver11`, the conversion pipeline ignores the flag and forces use of the Laxity analyzer.

### User's Clarification

> "stinsen do not use laxity player, but player 11 standard from SF2. SF2 player and laxity newplayer 21 is not the same."

The file was CREATED in SID Factory II by Laxity (the author) using Driver 11 format, but player-id detects it as "SidFactory_II/Laxity" causing the wrong analyzer to be selected.

---

## Root Cause

### Location: `sidm2/conversion_pipeline.py` lines 309-315

```python
# Detect player type
player_type = detect_player_type(filepath)  # Returns "SidFactory_II/Laxity"

# Check for SF2 marker
has_sf2_magic = b'\x37\x13' in c64_data
is_laxity_file = 'Laxity' in player_type or 'NewPlayer' in player_type

# Use SF2 parser ONLY if:
# 1. We find the SF2 magic marker in the data, AND
# 2. It's not primarily a Laxity file (Laxity parser has 99.93% accuracy)
is_sf2_exported = has_sf2_magic and not is_laxity_file
```

### The Bug

1. `player_type` = "SidFactory_II/Laxity" (from player-id.exe)
2. `is_laxity_file` = True (because string contains "Laxity")
3. `is_sf2_exported` = False (always, regardless of SF2 magic!)
4. Result: **Laxity analyzer is ALWAYS used**

### What SHOULD Happen

1. `driver_selector.py` line 50 correctly maps `'SidFactory_II/Laxity'` → `'driver11'`
2. The `--driver` flag should override auto-detection
3. **But** `analyze_sid_file()` never checks the driver selector mapping!

---

## Evidence

### Player Detection
```bash
$ tools/player-id.exe "Laxity/Stinsens_Last_Night_of_89.sid"
Laxity/Stinsens_Last_Night_of_89.sid                     SidFactory_II/Laxity
```

### Conversion Log (with --driver driver11)
```
2025-12-28 20:50:29 [    INFO] sidm2.conversion_pipeline:342 - Using Laxity player analyzer (original Laxity SID)
```

**Notice**: Despite `--driver driver11` flag, it still uses "Laxity player analyzer"!

### File Comparison
- Original SID: No SF2 magic marker (0x1337)
- Output SF2 files: Show "Driver Common block too small" warnings
- File sizes: 5.2K (small, incorrect) vs expected ~12K for Driver 11

---

## Correct Behavior

### driver_selector.py Mapping (Line 48-68)

```python
PLAYER_MAPPINGS = {
    # SF2-exported files (100% accuracy with Driver 11)
    'SidFactory_II/Laxity': 'driver11',  # ← CORRECT MAPPING!
    'SidFactory/Laxity': 'driver11',
    'SidFactory_II': 'driver11',
    'SidFactory': 'driver11',

    # Native Laxity variants (99.93% accuracy with Laxity driver)
    'Laxity_NewPlayer_V21': 'laxity',
    'Vibrants/Laxity': 'laxity',
    '256bytes/Laxity': 'laxity',
    ...
}
```

**The mapping is CORRECT**: "SidFactory_II/Laxity" should use Driver 11.

**The bug is**: `analyze_sid_file()` doesn't use this mapping!

---

## Fix Strategy

### Option 1: Use Driver Selector Mapping

Modify `analyze_sid_file()` to:
1. Call `DriverSelector.select_driver(player_type, manual_override=config.driver)`
2. Use the selected driver to determine which analyzer to use
3. Respect `--driver` override flag

### Option 2: Improve Player Type Detection

Change the simple string match:
```python
is_laxity_file = 'Laxity' in player_type  # TOO BROAD!
```

To explicit mapping:
```python
# Only use Laxity analyzer for NATIVE Laxity files
NATIVE_LAXITY_TYPES = ['Laxity_NewPlayer_V21', 'Vibrants/Laxity', '256bytes/Laxity']
is_native_laxity = player_type in NATIVE_LAXITY_TYPES
```

### Recommended: **Option 1** (respects driver selector logic)

---

## Test Cases

### Before Fix
```bash
python scripts/sid_to_sf2.py "Laxity/Stinsens_Last_Night_of_89.sid" test.sf2 --driver driver11
# Result: Uses Laxity analyzer (WRONG!)
```

### After Fix
```bash
python scripts/sid_to_sf2.py "Laxity/Stinsens_Last_Night_of_89.sid" test.sf2 --driver driver11
# Result: Uses Driver 11 analyzer (CORRECT!)
# Output: ~12K SF2 file with proper Driver 11 data
# No warnings about block sizes
```

---

## Impact

### Files Affected
- Any SID file created in SID Factory II by Laxity using Driver 11
- Player-id detects as "SidFactory_II/Laxity"
- Currently forced to use Laxity analyzer (99.93% accuracy)
- Should use Driver 11 (100% accuracy for SF2-exported files)

### User Workflow Issue
- User specifies `--driver driver11` explicitly
- System ignores the flag
- Produces incorrect output with warnings

---

## Next Steps

1. ✅ Document root cause
2. ⏳ Implement fix (Option 1 recommended)
3. ⏳ Test with Stinsen file
4. ⏳ Update test suite to verify --driver override works
5. ⏳ Commit fix and documentation

---

**End of Analysis**
