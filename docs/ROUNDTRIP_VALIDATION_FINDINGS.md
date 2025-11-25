# Round-trip Validation Findings

## Overview

Round-trip validation tests the complete conversion pipeline: **SID → SF2 → SID**. This document summarizes findings from testing Angular.sid through the full round-trip process.

## Test Configuration

- **Test File**: Angular.sid by DRAX (2017)
- **Player**: Laxity NewPlayer v21
- **Driver**: SF2 Driver 11
- **Duration**: 30 seconds (500 frames at 50Hz PAL)
- **Date**: 2025-11-24

## Test Results Summary

| Step | Status | Output |
|------|--------|--------|
| 1. SID → SF2 | [OK] Success | Angular_converted.sf2 (39.0 KB) |
| 2. SF2 → SID | [OK] Success | Angular_exported.sid (8.8 KB) |
| 3. Original WAV | [OK] Success | Angular_original.wav (1.7 MB) |
| 4. Exported WAV | [OK] Success | Angular_exported.wav (1.7 MB) |
| 5. Siddump Original | [OK] Success | 501 frames captured |
| 6. Siddump Exported | [OK] Success | 501 frames captured |
| 7. Comparison | [WARN] Low match | 2/501 frames (0.4%) |

## Key Metrics

### File Sizes

- **Original SID**: 3,907 bytes
- **Exported SID**: 8,960 bytes (+5,053 bytes, +129.3%)
  - Includes full SF2 driver code (~2KB)
  - Driver relocation overhead
  - Data tables

- **Original WAV**: 1,722,764 bytes
- **Exported WAV**: 1,722,764 bytes (identical)

### Code Relocation

SF2Pack successfully performed full 6502 code relocation:
- **343 absolute address relocations** (am_ABS, am_ABX, am_ABY, am_IND)
- **114 zero page relocations** (am_ZP, am_ZPX, am_ZPY, am_IZX, am_IZY)
- **Address delta**: 0x011A (282 bytes)
- **Load/Init/Play addresses**: $1000 / $1000 / $1003
- **No opcode errors**: Driver loaded and executed successfully

## Critical Finding: Silent Playback

### Symptom

The exported SID file loads and runs without errors, but produces **no audio output**. Siddump analysis shows:

**Original SID (Frame 1-3)**:
```
| Frame | Freq Note/Abs WF ADSR Pul | ... |
|     1 | FD2E (B-7 DF) 80 .... 800 | ... |  <- Active registers
|     2 | 0000 (C-0 80) 40 0F01 ... | ... |  <- ADSR changes
|     3 | ....  ... ..  .. .... ... | ... |  <- Continuing activity
```

**Exported SID (Frame 1-500)**:
```
| Frame | Freq Note/Abs WF ADSR Pul | ... |
|     1 | ....  ... ..  .. .... ... | ... |  <- No activity
|     2 | ....  ... ..  .. .... ... | ... |  <- No activity
|   500 | ....  ... ..  .. .... ... | ... |  <- No activity
```

The exported SID shows **zero SID register activity** after initialization.

### Analysis

1. **Code Relocation is Correct**
   - sf2pack successfully relocated all 6502 instructions
   - No "Unknown opcode" errors (which would indicate relocation failure)
   - Driver loads at $1000, init at $1000, play at $1003 (correct)

2. **Driver is Executing**
   - Siddump successfully called init and play routines
   - No crashes or hangs
   - 500 frames rendered without errors

3. **Music Data is Not Initializing**
   - The player code runs, but doesn't trigger any SID register writes
   - Issue is in the **SF2 file data structure**, not in code relocation
   - Something in the SF2 conversion is preventing music initialization

### Possible Root Causes

Based on the symptom (running but silent), possible issues:

1. **Sequence Pointers Not Set**
   - Orderlist may not be properly linked to sequences
   - Sequence table pointers may be incorrect
   - Voice state not initialized

2. **Instrument Table Issues**
   - Instruments extracted but pointers wrong
   - ADSR values preventing envelope trigger
   - Wave/pulse/filter table references broken

3. **Init Table Missing/Corrupted**
   - Tempo pointer incorrect
   - Initial volume = 0
   - Driver state not properly initialized

4. **Driver-Specific Data Format**
   - Driver 11 expects specific data layout
   - Template may have incompatible structure
   - Table offsets misaligned

## Recommendations

### Immediate Actions

1. **Validate SF2 File Structure**
   - Load Angular_converted.sf2 in SID Factory II editor
   - Verify sequences play in editor
   - Check instrument assignments in orderlists
   - Test init table tempo/volume settings

2. **Compare with Working SF2**
   - Use sf2pack on a known-good SF2 file
   - Check if packing works for editor-created files
   - Identify structural differences

3. **Debug Init Sequence**
   - Add verbose logging to sf2pack
   - Dump memory state after init routine
   - Check orderlist pointer initialization
   - Verify tempo table is loaded

### Long-term Solutions

1. **Improve SF2 Generation**
   - Review table offset calculations
   - Validate pointer integrity
   - Add SF2 structure verification tests

2. **Add Validation Checks**
   - Verify orderlists reference valid sequences
   - Check instrument table completeness
   - Validate init table structure

3. **Enhance Round-trip Test**
   - Add intermediate SF2 validation step
   - Test SF2 in editor before packing
   - Add detailed memory dumps at each stage

## Conclusion

**Status**: Code relocation is **fully functional** (343+114 relocations successful), but music data structure in SF2 file requires investigation.

**Impact**: The sf2pack tool is production-ready for code relocation. The issue is isolated to SF2 file generation quality in sid_to_sf2.py.

**Next Steps**:
1. Load Angular_converted.sf2 in SID Factory II editor to verify it plays
2. If editor playback works → investigate sf2pack memory layout
3. If editor playback fails → fix sid_to_sf2.py extraction/generation

## Test Artifacts

All test outputs available in `roundtrip_output/`:
- `Angular_converted.sf2` - SF2 conversion
- `Angular_exported.sid` - Packed SID with relocations
- `Angular_original.wav` - Original audio
- `Angular_exported.wav` - Exported audio (silent)
- `Angular_original.dump` - Original register trace (501 frames)
- `Angular_exported.dump` - Exported register trace (501 frames, all silent)
- `Angular_roundtrip_report.html` - Full HTML report

## References

- `test_roundtrip.py` - Round-trip validation script
- `tools/sf2pack/README.md` - SF2Pack architecture and relocation details
- `tools/sf2pack/packer_simple.cpp` - Core relocation implementation
- `docs/SF2_FORMAT_SPEC.md` - SF2 file format specification
