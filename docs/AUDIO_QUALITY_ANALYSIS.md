# Audio Quality Analysis: SID to SF2 Conversion Issues

**Date**: 2025-11-24
**Status**: CRITICAL - Audio output doesn't match original SID files
**Priority**: HIGH - Core functionality issue

---

## Executive Summary

The SID to SF2 converter is producing audio that differs from the original SID files. After analyzing the conversion pipeline, I've identified **7 critical areas** where data loss or incorrect mapping occurs.

---

## Root Cause Analysis

### 1. **Sequence Duration/Timing Loss** ⚠️ CRITICAL

**Location**: `sidm2/laxity_analyzer.py:499-505`

**Problem**: Duration bytes (0x80-0x9F) are completely **skipped** during sequence parsing:

```python
# Duration/timing: 0x80-0x9F (Laxity uses full range)
elif 0x80 <= b <= 0x9F:
    # Duration bytes set timing for subsequent notes
    # Skip them - SF2 handles timing via tempo table, not inline bytes
    # Note: In full conversion, this would map to SF2 row timing
    i += 1
    continue  # ← SKIPPED! Timing information lost
```

**Impact**:
- Notes play at wrong duration
- Rhythmic patterns corrupted
- Fast/slow passages play at uniform speed

**Evidence**: Laxity format uses duration bytes to control note length:
- `0x80` = 1 frame
- `0x81` = 2 frames
- `0x82` = 3 frames
- ... up to `0x9F` = 32 frames

**SF2 Equivalent**: SF2 doesn't use inline duration bytes. Instead, each sequence event occupies one row, and the tempo table controls playback speed. The correct conversion should:

1. **Expand sequences**: Each Laxity note with duration `N` should become `N` rows in SF2
2. **First row**: Note + instrument + command
3. **Subsequent rows**: `0x7E` (gate on / "+++") to sustain

**Fix Required**:
```python
# Proposed fix (pseudo-code)
elif 0x80 <= b <= 0x9F:
    current_duration = b - 0x80 + 1
    i += 1
    continue

# When writing note:
elif b <= 0x7F:
    note = b
    seq.append(SequenceEvent(current_instr, current_cmd, note))
    # Add sustain events for duration
    for _ in range(current_duration - 1):
        seq.append(SequenceEvent(0x80, 0x00, 0x7E))  # Gate on
    current_instr = 0x80
    current_cmd = 0x00
    current_duration = 1  # Reset
```

---

### 2. **Command Parameters Not Extracted** ⚠️ CRITICAL

**Location**: `sidm2/laxity_analyzer.py:491-497`

**Problem**: Command parameter bytes are **skipped** without extraction:

```python
# Command: 0xC0-0xCF (followed by parameter byte)
elif 0xC0 <= b <= 0xCF:
    current_cmd = b
    i += 1
    # Skip parameter byte
    if i < len(raw_seq):
        i += 1  # ← PARAMETER LOST!
    continue
```

**Impact**:
- Slide commands have no speed value
- Vibrato has no frequency/depth
- Portamento has no glide rate
- ADSR changes have no values

**Evidence from CONVERSION_STRATEGY.md**:
- `$0x yy` - Slide up speed $xyy (2 bytes: command + param)
- `$60 xy` - Vibrato, x=frequency, y=amplitude
- `$8x xx` - Portamento, speed $xxx
- `$9x yy` - Set AD=x, SR=yy (ADSR values in params!)

**SF2 Equivalent**: SF2 stores command parameters in the Command Table (3 bytes per command: type, param1, param2).

**Fix Required**:
```python
# Extract command parameter
elif 0xC0 <= b <= 0xCF:
    current_cmd = b
    i += 1
    if i < len(raw_seq):
        param_byte = raw_seq[i]
        # Store both command AND parameter
        current_cmd_with_param = (b, param_byte)
        i += 1
    continue
```

Then in `sidm2/sequence_extraction.py`, the `extract_command_parameters()` function should store these properly.

---

### 3. **Wave Table Entry Point Validation Too Aggressive** ⚠️ HIGH

**Location**: `sidm2/sf2_writer.py:503-512`

**Problem**: Wave pointers are clamped if they exceed wave table size, potentially pointing to wrong waveforms:

```python
# Validate wave pointer - must be within wave table bounds and at valid entry point
if wave_table_size > 0 and wave_ptr >= wave_table_size:
    # Find closest valid entry point that's within bounds
    valid_in_bounds = [p for p in valid_wave_points if p < wave_table_size]
    if valid_in_bounds:
        # Find the closest valid entry point
        wave_ptr = min(valid_in_bounds, key=lambda p: abs(p - wave_ptr))
    else:
        wave_ptr = 0
    logger.debug(f"    Clamped wave_ptr for instrument {lax_instr['index']} to {wave_ptr}")
```

**Impact**:
- Instruments may use wrong waveform (pulse vs saw vs triangle)
- Vibratos and wave programs won't work correctly

**Root Cause**: Wave table extraction may be incomplete, or instruments reference extended wave sequences not extracted.

**Fix Required**:
1. Improve wave table extraction to ensure ALL entries are captured
2. Validate extraction completeness before clamping
3. Log warnings when clamping occurs (instrument name + expected ptr)

---

### 4. **Pulse Table Y*4 Index Conversion** ⚠️ HIGH

**Location**: Multiple files

**Problem**: Laxity uses `Y*4` indexing for pulse tables (entry 6 is at offset 24). The conversion divides by 4:

```python
# sidm2/sf2_writer.py:497-498
# Convert Laxity pulse_ptr from Y*4 indexing to direct index
if pulse_ptr != 0 and pulse_ptr % 4 == 0:
    pulse_ptr = pulse_ptr // 4
```

But also in pulse table "next entry" field:

```python
# sidm2/sf2_writer.py:707-708
if col == 3 and value != 0:  # Next entry column
    value = value // 4 if value % 4 == 0 else value
```

**Concern**: What if `pulse_ptr % 4 != 0`? This suggests a corrupted or misaligned pulse table entry, but the code silently keeps the incorrect value.

**Fix Required**:
- Log warning when `pulse_ptr % 4 != 0` is encountered
- Investigate why misaligned pointers occur

---

### 5. **Filter Table Extraction May Be Incomplete** ⚠️ MEDIUM

**Location**: `sidm2/laxity_analyzer.py:163-179`

**Problem**: Filter table extraction relies on `find_and_extract_filter_table()`, which may not capture all entries:

```python
def extract_filter_table(self) -> bytes:
    """Extract filter modulation table from Laxity SID.

    Returns bytes in SF2 format: 4 bytes per entry (cutoff, step, duration, next).
    """
    addr, entries = find_and_extract_filter_table(self.data, self.load_address)

    if not entries:
        return b''  # ← Returns empty if extraction fails
```

**Impact**:
- Filter sweeps won't work
- Resonance effects lost
- Instruments sound "flat" without filter motion

**Evidence**: The filter table is critical for SID character. Many classic SID tunes rely heavily on filter modulation.

**Fix Required**:
1. Improve filter table detection heuristics in `table_extraction.py`
2. Validate extracted filter entries against siddump $D416/$D417 writes
3. Use siddump data as fallback to reconstruct filter table

---

### 6. **Tempo and Multi-Speed Detection Issues** ⚠️ MEDIUM

**Location**: `sidm2/laxity_analyzer.py:54-65, 108-161`

**Problem**: Tempo extraction searches for `LDA #$xx` patterns in a limited range:

```python
def extract_tempo(self) -> int:
    """Extract tempo/speed from the SID file"""
    init_offset = self.header.init_address - self.load_address

    for i in range(init_offset, min(init_offset + 200, len(self.data) - 5)):
        if self.data[i] == 0xA9:  # LDA immediate
            value = self.data[i + 1]
            if 1 <= value <= 20:  # ← Limited range!
                if self.data[i + 2] in (0x85, 0x8D):
                    return value

    return 6  # ← Default fallback
```

**Issues**:
1. Assumes tempo is in range 1-20 (some tunes use higher values)
2. Only searches first 200 bytes of init routine
3. Multi-speed detection relies on JSR counting, which may miss complex setups

**Impact**:
- Song plays at wrong speed
- Multi-speed tunes have timing artifacts

**Fix Required**:
1. Use siddump frame timing to calculate actual tempo
2. Expand search range and tempo value limits
3. Cross-validate tempo with actual playback data

---

### 7. **Instrument ADSR Extraction from Siddump Not Used** ⚠️ LOW

**Location**: `sidm2/sf2_writer.py:464-469`

**Problem**: Siddump validation shows ADSR mismatch but extracted values are still used:

```python
if hasattr(self.data, 'siddump_data') and self.data.siddump_data:
    siddump_adsr = set(self.data.siddump_data['adsr_values'])
    laxity_adsr = set((i['ad'], i['sr']) for i in laxity_instruments)
    matches = len(siddump_adsr & laxity_adsr)
    match_rate = matches / len(siddump_adsr) if siddump_adsr else 0
    logger.debug(f"    Validation: {match_rate*100:.0f}% of siddump ADSR values found in extraction")
    # ← No correction applied if match_rate is low!
```

**Impact**:
- Incorrect envelope shapes (attack/decay/sustain/release)
- Instruments sound wrong even if waveform is correct

**Suggestion**: If match rate < 50%, use siddump ADSR values to reconstruct or supplement instrument table.

---

## Validation Data

### Current Test Results

From test suite (67/69 passing):
- **2 failing tests** (pre-existing, unrelated to current issues)
- **97.1% pass rate** for structural integrity
- **No audio quality tests** currently exist

### Siddump Comparison

The `compare_audio.py` tool exists but requires **manual workflow**:
1. Convert SID → WAV (automatic)
2. Export SF2 → PRG → SID (manual in SID Factory II)
3. Convert exported SID → WAV (automatic)
4. Compare waveforms (manual in Audacity)

**Improvement Needed**: Automated audio comparison pipeline.

---

## Known Limitations (Already Documented)

From CONVERSION_STRATEGY.md:

1. **Init table**: Not in Laxity format, uses defaults
2. **Arpeggio table**: Uses default patterns, not extracted
3. **HR table**: Often hardcoded, uses default $0F 00
4. **Command mapping**: Not all Laxity commands map cleanly to SF2
5. **Information loss**: Instrument names, bookmarks, metadata

These are **design limitations**, not bugs. The issues above are **implementation bugs** that cause incorrect audio.

---

## Priority Ranking

| Issue | Priority | Impact | Complexity |
|-------|----------|--------|------------|
| 1. Duration bytes skipped | **CRITICAL** | Rhythm completely wrong | Medium - requires sequence expansion |
| 2. Command params lost | **CRITICAL** | Effects don't work | Medium - requires param extraction |
| 3. Wave ptr clamping | **HIGH** | Wrong waveforms | Low - better extraction |
| 4. Pulse Y*4 conversion | **HIGH** | Pulse modulation broken | Low - add validation |
| 5. Filter table incomplete | **MEDIUM** | Missing filter sweeps | High - complex heuristics |
| 6. Tempo detection | **MEDIUM** | Wrong playback speed | Medium - use siddump timing |
| 7. ADSR validation unused | **LOW** | Envelope shapes off | Low - apply corrections |

---

## Recommended Action Plan

### Phase 1: Critical Fixes (Issues #1, #2)

**Goal**: Fix rhythm and command parameters

1. Implement duration byte expansion in sequence parser
2. Extract and store command parameter bytes
3. Build proper command table with params
4. Add tests: validate sequence expansion and command params

**Expected Result**: Notes play at correct duration, effects work

### Phase 2: Table Quality (Issues #3, #4, #5)

**Goal**: Improve table extraction accuracy

1. Enhance wave table extraction to capture all entries
2. Add pulse table alignment validation
3. Improve filter table detection with siddump cross-validation
4. Add tests: table extraction coverage, pointer validity

**Expected Result**: Instruments use correct waveforms, pulse/filter effects work

### Phase 3: Tempo and Validation (Issues #6, #7)

**Goal**: Fine-tune playback accuracy

1. Implement siddump-based tempo calculation
2. Improve multi-speed detection
3. Use siddump ADSR values when extraction confidence is low
4. Add automated audio comparison tests

**Expected Result**: Playback speed matches original, ADSR envelopes accurate

---

## Testing Strategy

### Unit Tests (Immediate)

- `test_duration_extraction()` - Verify duration bytes are captured
- `test_command_param_extraction()` - Verify command params stored
- `test_sequence_expansion()` - Verify notes expanded to correct row count
- `test_pulse_index_conversion()` - Verify Y*4 division correctness

### Integration Tests (After fixes)

- `test_angular_conversion()` - Full conversion of Angular.sid
- `test_audio_comparison()` - Automated siddump comparison
- `test_playback_speed()` - Tempo accuracy validation

### Regression Tests

- Ensure existing 67 passing tests still pass after changes

---

## Tools and References

### Existing Tools

- `siddump.exe` - Captures register writes (ground truth for audio)
- `compare_audio.py` - Manual audio comparison workflow
- `player-id.exe` - Identifies player type

### Documentation

- `CONVERSION_STRATEGY.md` - Conversion mapping reference
- `SF2_FORMAT_SPEC.md` - SF2 format details
- `LAXITY_PLAYER_ANALYSIS.md` - Laxity format details

### Example Files

- `Angular.sid` - Primary test file (DRAX, 2017)
- 6 other test SID files in `SID/` directory

---

## Success Criteria

Conversion is considered **successful** when:

1. ✅ All sequences have correct note durations
2. ✅ Command effects (slide, vibrato, portamento) work correctly
3. ✅ Instrument waveforms match original (pulse/saw/triangle/noise)
4. ✅ Pulse width modulation patterns are preserved
5. ✅ Filter sweeps and resonance effects work
6. ✅ Playback tempo matches original
7. ✅ ADSR envelopes produce similar sound character
8. ✅ Siddump comparison shows >90% register write match

**Measurement**: Use `siddump` to compare original SID vs exported SF2 → SID:
- $D400-$D418 register writes should match >90% of the time
- Waveform ($D404/0B/12) should match 100%
- ADSR ($D405-06/0C-0D/13-14) should match >95%

---

## Conclusion

The audio conversion quality issue stems primarily from **data loss during sequence parsing**:

1. **Duration information is completely discarded** (Issue #1) - sequences play at uniform speed instead of preserving rhythm
2. **Command parameters are skipped** (Issue #2) - effects don't have their speed/depth values
3. **Table extraction is incomplete** (Issues #3-5) - waveforms and modulation don't work correctly

Fixing Issues #1 and #2 (Critical priority) will have the **most immediate impact** on audio quality. Issues #3-7 are important but less catastrophic.

The current code has good structural integrity (97% test pass rate) but lacks **semantic correctness** - it extracts tables and builds valid SF2 files, but the musical information inside is incomplete or incorrect.

**Estimated effort**:
- Phase 1 (Critical): 2-3 days
- Phase 2 (High): 3-4 days
- Phase 3 (Medium/Low): 2-3 days
- **Total**: ~7-10 days for full audio quality fix

---

**Next Steps**: Begin Phase 1 implementation - focus on duration byte expansion and command parameter extraction.
