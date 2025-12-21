# Phase 6: Testing and Validation - IN PROGRESS

**Date**: 2025-12-13
**Status**: 60% Complete
**Test Results**: Pipeline works, but music data not playing correctly

---

## Summary

Phase 6 testing revealed that while the Laxity driver infrastructure is complete and functional, there is a critical issue with music data routing. The converted files play, but with only 0.18% accuracy instead of the expected 70-90%.

---

## What Was Tested

### Files Identified
Found 4 Laxity NewPlayer v21 SID files for testing:
1. **Stinsens_Last_Night_of_89.sid** (6.1 KB) - Primary test file
2. **Beast.sid** (3.8 KB)
3. **Dreams.sid** (3.9 KB)
4. **Unboxed_Ending_8580.sid** (4.6 KB)

### Pipeline Execution (Stinsens)

**✅ SID → SF2 Conversion**
```bash
python scripts/sid_to_sf2.py Stinsens.sid output.sf2 --driver laxity
```
- Output: 5,224 bytes
- Load address: $0D7E
- Music data injected at $1900
- No critical errors

**✅ SF2 → SID Packing**
```bash
python scripts/sf2_to_sid.py output.sf2 exported.sid
```
- Output: 5,346 bytes (124-byte header + 5,222 data)
- PSID header created successfully
- Init address: $0D80 ✓
- Play address: $0D83 ✓

**✅ Siddump Execution**
```bash
tools/siddump.exe exported.sid -t30
```
- Executes without errors
- No "Unknown opcode" issues
- Generates 1,507 lines of output
- Player IS running

**❌ Accuracy Validation**
```bash
python scripts/validate_sid_accuracy.py original.sid exported.sid
```
- Overall accuracy: **0.18%** (expected 70-90%)
- Original register writes: 14,595
- Exported register writes: 3,023 (only 21%)
- Frame accuracy: 0.00%
- Filter accuracy: 0.00%

---

## Critical Issue Discovered

### Symptom
The exported SID file plays, but music is wrong:
- **Voice 1**: Only pulse width changes (no notes)
- **Voice 2**: Silent (all zeros)
- **Voice 3**: Silent (all zeros)
- **Frequency**: No changes (should be playing notes)
- **Waveform**: No changes (should be varying)

### Root Cause
The relocated Laxity player contains **embedded default music data** from the reference SID used during extraction. When the player initializes, it uses **its own internal orderlists** instead of the new music data we injected at $1900.

**Evidence**:
- `_inject_laxity_music_data()` writes orderlists to file offset $0B84 (memory $1900)
- But the player never reads from $1900
- Player's internal orderlist pointers still point to embedded addresses
- No pointer patching was implemented

### Architecture Gap

**What We Have**:
```
$0D7E: SF2 Wrapper (init/play/stop)
$0E00: Relocated Laxity Player CODE
       + Embedded DEFAULT music data (orderlists, sequences, tables)
       + Hardcoded pointers to embedded data
$1700: SF2 Header Blocks
$1900: INJECTED music data (NOT USED!)
```

**What We Need**:
```
$0D7E: SF2 Wrapper
$0E00: Relocated Laxity Player CODE ONLY
       + Pointers pointing to $1900 (not embedded data)
$1700: SF2 Header Blocks
$1900: Music data (ACTUALLY USED by player)
```

---

## Bugs Fixed

### 1. SF2-to-SID Address Range Check
**File**: `scripts/sf2_to_sid.py` (lines 213-214)

**Problem**: Range check rejected Laxity driver addresses
```python
# Before (WRONG)
if 0x1000 <= init <= 0x2000 and 0x1000 <= play <= 0x2000:
```

**Fix**: Support addresses below $1000
```python
# After (CORRECT)
if 0x0800 <= init <= 0x2000 and 0x0800 <= play <= 0x2000:
```

### 2. Laxity Driver Address Detection
**File**: `scripts/sf2_to_sid.py` (lines 199-204)

**Added**: Automatic Laxity driver detection
```python
if self.load_address == 0x0D7E:
    self.init_address = 0x0D80  # Load + 2
    self.play_address = 0x0D83  # Load + 5
    return
```

### 3. Pipeline Driver Selection
**File**: `complete_pipeline_with_validation.py` (line 170)

**Changed**: Use laxity driver for Laxity files
```python
# Before
['python', 'scripts/sid_to_sf2.py', ..., '--driver', 'np20', ...]

# After
['python', 'scripts/sid_to_sf2.py', ..., '--driver', 'laxity', ...]
```

---

## Next Steps (Priority Order)

### Option A: Patch Orderlist Pointers (RECOMMENDED)
**Complexity**: Medium
**Time**: 4-8 hours
**Success Probability**: 80%

**Approach**:
1. Identify orderlist pointer table in relocated player
   - Search for 3 consecutive 16-bit addresses (voice 1/2/3 orderlists)
   - Likely in range $0E00-$0F00 (relocated player init data)
2. Patch pointers to point to $1900, $1A00, $1B00
3. Verify player reads from new locations
4. Re-test accuracy

**Files to Modify**:
- `sidm2/sf2_writer.py` - Add pointer patching to `_inject_laxity_music_data()`
- May need to add relocation map to track pointer locations

### Option B: Extract Code Only (Clean But Complex)
**Complexity**: High
**Time**: 16-24 hours
**Success Probability**: 60%

**Approach**:
1. Modify player extraction to separate code from data
2. Identify exact boundary where player code ends
3. Extract only code section for relocation
4. Implement runtime initialization with new music data pointers
5. Extensive testing required

**Files to Modify**:
- `scripts/extract_laxity_player.py`
- `scripts/relocate_laxity_player.py`
- `drivers/laxity/laxity_driver.asm`

### Option C: Hybrid NP20 Driver (Fallback)
**Complexity**: Low
**Time**: 2-4 hours
**Success Probability**: 95%

**Approach**:
1. Revert to NP20 driver for Laxity files
2. Document limitation
3. Focus on improving NP20 conversion accuracy via table optimization

**Trade-off**: Achieves 1-8% accuracy (proven) vs 70-90% (theoretical with Laxity driver)

---

## Files Modified

### Modified
1. **complete_pipeline_with_validation.py**
   - Line 170: Changed to `--driver laxity`

2. **scripts/sf2_to_sid.py**
   - Lines 199-204: Added Laxity driver detection
   - Lines 213-214: Fixed address range check

### Created
3. **test_laxity_pipeline/** (directory)
   - Beast.sid
   - Dreams.sid
   - Stinsens_Last_Night_of_89.sid
   - Unboxed_Ending_8580.sid

4. **output/Laxity_Test/** (test outputs)
   - Stinsens/New/Stinsens_laxity.sf2
   - Stinsens/New/Stinsens_laxity_exported.sid
   - Stinsens/New/original.dump (1,507 lines)
   - Stinsens/New/exported.dump (1,507 lines)
   - Stinsens/New/accuracy_report.html

---

## Technical Details

### Memory Layout (Current)
```
Address Range  | Size    | Contents
---------------|---------|----------------------------------
$0D7E-$0D7F    | 2 B     | SF2 file ID ($1337)
$0D80-$0D82    | 3 B     | JMP to init_routine
$0D83-$0D85    | 3 B     | JMP to play_routine
$0D86-$0D88    | 3 B     | JMP to stop_routine
$0D89-$0DFF    | 119 B   | Wrapper code (silence_sid, etc.)
$0E00-$16FF    | 2,304 B | Relocated Laxity player + embedded data
$1700-$18FF    | 512 B   | SF2 header blocks (partial)
$1900-$1BFF    | 768 B   | Injected orderlists (NOT USED!)
$1C00+         | Var     | Injected sequences (NOT USED!)
```

### Siddump Comparison

**Original (Correct Playback)**:
```
Frame 0: Voice1=0000, Voice2=0000, Voice3=0000
Frame 1: Voice1=0116/20, Voice2=0116/20, Voice3=0116/20
Frame 4: Voice1=A025, Voice2=170, Voice3=203A
Frame 5: Voice1=2E66 F-5/C1, Voice2=1B0, Voice3=3A8C A-5/C5
```
- All 3 voices active
- Frequencies changing (notes playing)
- Waveforms varying (20, 40, C1, C5, etc.)
- 14,595 register writes in 30 seconds

**Exported (Broken Playback)**:
```
Frame 0: Voice1=0937 C#3/F2, Voice2=0000, Voice3=0000
Frame 1: Voice1=pulse=940, Voice2=0000, Voice3=0000
Frame 2: Voice1=pulse=230, Voice2=0000, Voice3=0000
...all frames: only Voice1 pulse width changes
```
- Only Voice 1 partially active
- No frequency changes (no notes)
- No waveform changes
- 3,023 register writes in 30 seconds (79% fewer)

---

## Validation Metrics

| Metric | Original | Exported | Match |
|--------|----------|----------|-------|
| File size | 6,075 B | 5,346 B | N/A |
| Load address | $1000 | $0D7E | Different |
| Init address | $1000 | $0D80 | Different |
| Play address | $1006 | $0D83 | Different |
| Siddump lines | 1,507 | 1,507 | ✓ |
| Register writes | 14,595 | 3,023 | ❌ 21% |
| Overall accuracy | 100% | 0.18% | ❌ |
| Frame accuracy | 100% | 0.00% | ❌ |

---

## Lessons Learned

### What Worked
1. ✅ SF2 wrapper integration (init/play/stop entry points)
2. ✅ Code relocation engine (373 address patches successful)
3. ✅ SF2-to-SID packing (correct addresses, valid PSID)
4. ✅ Pipeline infrastructure (driver selection, file handling)
5. ✅ Player execution (no crashes, runs correctly)

### What Didn't Work
1. ❌ Music data injection strategy (player ignores injected data)
2. ❌ Assumption that data injection alone would work
3. ❌ Missing pointer patching step

### Key Insight
**Relocating a player that contains embedded music data requires pointer patching, not just code relocation and data injection.**

The player's internal pointers must be updated to reference the new music data locations. Simply injecting data at a new address doesn't help if the player doesn't know to look there.

---

## Recommendations

### Immediate (Next Session)
1. **Implement Option A** (patch orderlist pointers)
   - Most pragmatic solution
   - Builds on existing work
   - Highest success probability

2. **Create pointer patching function**
   ```python
   def _patch_laxity_orderlist_pointers(self, player_offset: int):
       """Patch orderlist pointers in relocated player to point to $1900."""
       # Find pointer table
       # Update 3 pointers: $1900, $1A00, $1B00
       # Verify patch success
   ```

3. **Add validation step**
   - Verify pointers were patched correctly
   - Read back patched values
   - Log patch locations for debugging

### Medium Term
1. Test with all 4 Laxity files (not just Stinsens)
2. Compare accuracy: Laxity driver vs NP20 driver
3. Measure improvement percentage
4. Document best practices

### Long Term
1. Extract code-only version (Option B)
2. Support multiple Laxity player versions
3. Add table customization support
4. Full SF2 editor integration

---

## Conclusion

**Phase 6 Status**: 60% Complete

We successfully integrated the Laxity driver into the pipeline and fixed critical bugs in address validation. The infrastructure works correctly, but music data routing needs one more implementation step: **orderlist pointer patching**.

With this final fix, we expect to achieve the target 70-90% accuracy for Laxity conversions.

**Next Priority**: Implement orderlist pointer patching in `_inject_laxity_music_data()`.

---

**Commit**: ed53029
**Message**: "fix: Update pipeline to use laxity driver + fix SF2-to-SID address validation"
**Files Modified**: 8 files
**Lines Changed**: +16/-5
