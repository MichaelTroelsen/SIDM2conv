# Filter Format Analysis

**Date**: 2025-12-27
**Version**: SIDM2 v2.9.7
**Status**: 🔍 Analysis Complete - Ready for Implementation

---

## Executive Summary

**Problem**: Filter accuracy is currently 0% because Laxity's **animation-based filter format** is incompatible with SF2's **static value format**.

**Root Cause**: Direct byte copying without format conversion.

**Solution**: Implement filter format converter that interprets Laxity's sweep parameters and generates appropriate static SF2 values.

---

## Format Comparison

### Laxity NewPlayer v21 Filter Format

**Address**: `$1A1E`
**Size**: 32 entries × 4 bytes = 128 bytes
**Indexing**: Y-register multiplied by 4 (`LDA $1A1E,Y` where Y = entry_index × 4)

**4-Byte Entry Structure** (Animation-Based):
```
Byte 0: Target Cutoff High Byte
  - Range: 0x00-0xFF
  - Represents target filter cutoff frequency (8-bit)
  - 0xFF = keep current value
  - 0x40-0xFE = target cutoff values
  - 0x00 = no filter

Byte 1: Delta (Add/Subtract Value Per Frame)
  - Range: 0x00-0xFF
  - Amount to add/subtract each frame
  - 0x00 = instant jump to target
  - 0x01-0xFF = gradual sweep rate

Byte 2: Duration + Direction
  - Bits 0-6: Duration in frames (0-127)
  - Bit 7: Direction (0=add, 1=subtract)
  - Example: 0x20 = add for 32 frames
  - Example: 0xA0 = subtract for 32 frames

Byte 3: Next Entry Index (Y-Indexed Format)
  - Pre-multiplied by 4 for Y-register indexing
  - 0x00 = end of chain
  - 0x04 = next entry at index 1
  - 0x08 = next entry at index 2
  - 0x7F = terminator
```

**Example Entry**:
```
Filter entry at index 0:
  0x40 = target cutoff $40
  0x02 = change by 2 per frame
  0x20 = add for 32 frames
  0x04 = then jump to entry 1

Interpretation: Start at current cutoff, sweep UP by 2 per frame
for 32 frames targeting $40, then continue with entry 1.
```

---

### SF2 Driver 11 Filter Format

**Address**: Varies by driver (typically `$0F03`)
**Size**: 32 entries × 4 bytes = 128 bytes
**Indexing**: Direct index (`LDA table,X` where X = entry_index)

**4-Byte Entry Structure** (Static Values):
```
Byte 0: Cutoff High Byte (bits 3-10)
  - Range: 0x00-0x07 (3 bits)
  - Combined with byte 1 forms 11-bit cutoff (0-2047)

Byte 1: Cutoff Low Byte (bits 0-2)
  - Range: 0x00-0x07 (3 bits)
  - Lower 3 bits of 11-bit cutoff value

Byte 2: Resonance
  - Range: 0x00-0xFF (8 bits)
  - SID register D417 resonance value (bits 4-7 used)
  - Actual range: 0x00-0xF0 (4 bits, left-shifted)

Byte 3: Next Entry Index (Direct Format)
  - Range: 0x00-0x1F (5 bits)
  - 0x7F = end marker
  - 0x00 = no chaining (instant stop)
  - 0x01-0x1F = next entry index
```

**11-Bit Cutoff Calculation**:
```
cutoff_11bit = (byte0 << 8) | byte1
cutoff_11bit &= 0x07FF  // Mask to 11 bits (0-2047)
```

**Example Entry**:
```
SF2 Filter entry at index 0:
  0x03 = cutoff high byte
  0xB5 = cutoff low byte
  0x80 = resonance
  0x00 = no next entry

Cutoff value: (0x03 << 8) | 0xB5 = 0x03B5 = 949
Resonance: 0x80 (middle resonance)
```

---

## Key Differences

| Aspect | Laxity Format | SF2 Format |
|--------|---------------|------------|
| **Purpose** | Animation/sweep data | Static values |
| **Cutoff** | 8-bit target value | 11-bit absolute value |
| **Byte 1** | Sweep rate (delta) | Cutoff low bits |
| **Byte 2** | Duration + direction | Resonance value |
| **Indexing** | Y×4 (pre-multiplied) | Direct index |
| **Philosophy** | Dynamic filter sweeps | Static filter states |

---

## Conversion Challenge

**The Problem**: Two fundamentally different data models!

1. **Laxity** stores filter **animations**:
   - Target cutoff
   - Sweep rate (how fast to get there)
   - Duration (how long to sweep)
   - Chaining (what to do next)

2. **SF2** stores filter **snapshots**:
   - Absolute cutoff value
   - Resonance value
   - Next state pointer

**Example**:
```
Laxity: "Sweep from current to $40 at rate 2 for 32 frames, then go to entry 1"
SF2:    "Set cutoff to 949, resonance to 128"
```

---

## Conversion Strategy

### Option 1: Static Conversion (Recommended)

**Approach**: Convert Laxity target values to SF2 static values, ignoring sweep animations.

**Algorithm**:
```python
def convert_laxity_to_sf2_filter(laxity_entry):
    target_cutoff_8bit, delta, duration_dir, next_idx_y4 = laxity_entry

    # Convert 8-bit target to 11-bit cutoff
    # Laxity: 0x00-0xFF (256 values)
    # SF2:    0x000-0x7FF (2048 values)
    # Scale: SF2 = Laxity × 8
    cutoff_11bit = target_cutoff_8bit * 8

    # Split into high/low bytes
    cutoff_hi = (cutoff_11bit >> 8) & 0xFF
    cutoff_lo = cutoff_11bit & 0xFF

    # Default resonance (middle value)
    resonance = 0x80  # Mid-range resonance

    # Convert Y×4 index to direct index
    next_idx_direct = next_idx_y4 // 4 if next_idx_y4 % 4 == 0 else 0x7F

    return (cutoff_hi, cutoff_lo, resonance, next_idx_direct)
```

**Pros**:
- Simple and reliable
- Preserves filter order and chaining
- Works with all Laxity files

**Cons**:
- Loses sweep animation (instant jumps)
- May sound different from original

**Expected Accuracy**: 60-80% (filter values present, but no animation)

---

### Option 2: Sweep Simulation (Complex)

**Approach**: Generate multiple SF2 entries to simulate sweeps.

**Algorithm**:
```python
def simulate_sweep(laxity_entry, output_entries, entry_idx):
    target, delta, duration_dir, next_idx = laxity_entry

    duration = duration_dir & 0x7F
    subtract = (duration_dir & 0x80) != 0

    # Generate intermediate values
    if duration > 1 and delta > 0:
        for frame in range(duration):
            current = target - (delta * (duration - frame)) if subtract else \
                      target + (delta * (duration - frame))

            # Clamp to valid range
            current = max(0, min(255, current))

            # Convert to SF2
            sf2_entry = convert_to_sf2_static(current, frame)
            output_entries.append(sf2_entry)

            # Chain to next frame
            sf2_entry[3] = len(output_entries)  # Point to next

    # Final entry points to original next
    output_entries[-1][3] = next_idx // 4
```

**Pros**:
- More accurate animation
- Better sound fidelity

**Cons**:
- Complex implementation
- May exceed 32-entry limit
- Chaining becomes complicated

**Expected Accuracy**: 80-95% (but implementation risk)

---

## Recommended Implementation

**Use Option 1: Static Conversion**

**Rationale**:
1. Simpler and more reliable
2. Works within 32-entry limit
3. Filter sweeps are rarely critical to music quality
4. Can iterate to Option 2 later if needed

**Implementation Location**: `sidm2/laxity_converter.py` - new method `convert_filter_table()`

**Integration Point**: `sidm2/sf2_writer.py` - modify `_inject_filter_table()` to call converter

---

## Test Files

**Files with Filter Usage** (from validation):
- `Laxity/Aids_Trouble.sid` - D416 sweep ($00 → $FF)
- Filter registers used: D415 (cutoff lo), D416 (cutoff hi), D417 (resonance), D418 (volume)

**Validation Method**:
1. Extract filter table from original SID
2. Convert using new algorithm
3. Inject into SF2
4. Trace SF2 playback
5. Compare filter register writes

---

## Expected Results

### Before Conversion (Current):
```
Filter accuracy: 0%
Reason: Laxity animation bytes copied as-is to SF2 static format
Result: Garbage filter values, no filtering
```

### After Conversion (Static):
```
Filter accuracy: 60-80% (estimated)
Reason: Correct cutoff values, but no sweep animation
Result: Filters present and functional, instant changes instead of sweeps
Sound quality: Good (most music doesn't rely heavily on sweeps)
```

### After Conversion (Sweep Simulation - Future):
```
Filter accuracy: 80-95% (estimated)
Reason: Sweep animation simulated with chained entries
Result: Near-identical filter behavior
Sound quality: Excellent
```

---

## Implementation Plan

### Phase 1: Static Converter (8 hours)
1. Create `sidm2/laxity_converter.py::convert_filter_table()`
2. Implement 8-bit → 11-bit cutoff scaling
3. Handle Y×4 → direct index conversion
4. Add default resonance values

### Phase 2: Integration (2 hours)
1. Modify `sidm2/sf2_writer.py::_inject_filter_table()`
2. Call converter before injection
3. Update logging to show conversion

### Phase 3: Testing (2 hours)
1. Test on Aids_Trouble.sid (known filter usage)
2. Compare before/after register writes
3. Validate cutoff values in trace
4. Measure accuracy improvement

### Phase 4: Documentation (2 hours)
1. Update LAXITY_DRIVER_TECHNICAL_REFERENCE.md
2. Document conversion algorithm
3. Add examples and validation results

**Total Effort**: 14 hours (vs 8-12 estimated in roadmap)

---

## Success Criteria

1. ✅ Filter table extracted from Laxity SID
2. ✅ Conversion algorithm implemented
3. ✅ SF2 files contain valid filter data
4. ✅ Filter registers write non-zero values during playback
5. ✅ Filter accuracy improves from 0% to 60%+
6. ✅ No regression in other table accuracies

---

## References

- **Laxity Filter Extraction**: `sidm2/table_extraction.py::find_and_extract_filter_table()`
- **SF2 Filter Injection**: `sidm2/sf2_writer.py::_inject_filter_table()`
- **Filter Validation**: `docs/testing/FILTER_FIX_VALIDATION_SUMMARY.md`
- **SID Filter Registers**: D415 (cutoff lo), D416 (cutoff hi), D417 (resonance/routing), D418 (volume/mode)

---

**Status**: ✅ Analysis Complete - Ready for Implementation

**Next Step**: Implement static filter converter in `sidm2/laxity_converter.py`

---

**Generated**: 2025-12-27
**Tool**: Manual analysis + codebase inspection
**Analyst**: Claude Sonnet 4.5

🤖 Generated with [Claude Code](https://claude.com/claude-code)
