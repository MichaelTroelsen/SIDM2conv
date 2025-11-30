# TODO: WAV Comparison and Custom Player Enhancement

## Phase 1: Add WAV Comparison to Validation Pipeline

### Objectives
1. Generate WAV files from original and converted SID files
2. Compare WAV files using audio analysis
3. Include audio accuracy metrics in validation reports
4. Identify audible differences that register-level comparison might miss

### Implementation Tasks

#### 1.1 WAV Generation
- [ ] Add `generate_wav()` function using tools/SID2WAV.EXE
- [ ] Handle WAV generation errors/timeouts
- [ ] Store WAV files alongside validation outputs
- [ ] Add WAV file cleanup after comparison

#### 1.2 WAV Comparison Methods
- [ ] **Basic**: File size and byte-level comparison
- [ ] **RMS Difference**: Calculate root-mean-square difference between waveforms
- [ ] **Spectral Analysis**: Compare frequency spectrum (FFT)
- [ ] **MFCC Comparison**: Mel-frequency cepstral coefficients for perceptual similarity

#### 1.3 Integration
- [ ] Update `validate_sid_accuracy.py` with WAV comparison
- [ ] Add `--wav-compare` flag (optional, as WAV generation can be slow)
- [ ] Include WAV accuracy metrics in HTML report
- [ ] Add audio diff visualization (waveform overlay)

#### 1.4 Batch Validation Updates
- [ ] Update `batch_validate_sidsf2player.py` to support WAV comparison
- [ ] Add WAV accuracy to summary reports
- [ ] Store representative WAV files for manual listening

### Expected Results
- Audio accuracy percentage (0-100%)
- RMS error metric
- Spectral difference score
- Visual waveform comparison in HTML report

---

## Phase 2: Enhanced Custom Player for Detailed Extraction

### Objectives
Use existing `sidm2/cpu6502_emulator.py` and `sidm2/sid_player.py` to:
1. Extract detailed music structure BEFORE conversion
2. Extract detailed music structure AFTER conversion
3. Compare structures to validate conversion accuracy
4. Learn from differences to improve conversion

### Current Capabilities (Already Implemented!)

**sidm2/cpu6502_emulator.py** (1,242 lines):
- Full 6502 CPU emulation
- SID register write capture
- Frame-by-frame state tracking
- Memory access logging

**sidm2/sid_player.py** (560 lines):
- SID file player
- Note detection from frequencies
- Frame dump output (siddump-compatible)
- Playback result analysis

### RECOMMENDATION: Use VSID as Foundation

**User Suggestion**: "You could use VSID as basis for building your own player to extract all the information you need to compare before conversion and after conversion of the SID."

**Why VSID is Better**:
- **Proven Accuracy**: Battle-tested SID emulation (6581 and 8580)
- **Complete**: Full VICE emulation suite
- **Extensible**: Can be modified to extract structure
- **Reference**: De facto standard for SID accuracy
- **Features**: Already has logging, debugging, register capture

**Implementation Options**:
1. **Integrate VSID Libraries**: Use VICE libsidplayfp as a library
2. **Extend VSID**: Add structure extraction to VSID source
3. **Wrap VSID**: Call VSID as subprocess and parse output
4. **Hybrid**: Use VSID for playback, our code for analysis

**Next Step**: Research VICE/VSID integration options

### Enhancement Tasks

#### 2.1 Music Structure Extraction
- [ ] **Pattern Detection**: Identify repeating sequences in register writes
- [ ] **Voice Separation**: Track each voice independently
- [ ] **Tempo Detection**: Calculate actual playback speed from frame timing
- [ ] **Instrument Identification**: Group ADSR+waveform combinations into instruments
- [ ] **Command Detection**: Identify slide, vibrato, arpeggio, filter sweeps
- [ ] **Loop Point Detection**: Find where music loops

#### 2.2 Pre-Conversion Analysis
- [ ] Run custom player on original SID
- [ ] Extract:
  - Sequence data (notes, rests, ties)
  - Instrument definitions (ADSR, waveform, pulse, filter)
  - Orderlist/pattern structure
  - Tempo/speed changes
  - Command usage (effects)
- [ ] Save analysis to JSON for comparison

#### 2.3 Post-Conversion Analysis
- [ ] Run custom player on converted SF2→SID
- [ ] Extract same structure as pre-conversion
- [ ] Generate detailed diff report

#### 2.4 Learning System
- [ ] Compare pre/post structures
- [ ] Identify systematic errors:
  - Missing sequences
  - Incorrect instrument parameters
  - Wrong note mappings
  - Timing errors
- [ ] Use findings to improve:
  - Laxity parser logic
  - SF2 writer algorithms
  - Table extraction heuristics

### Expected Benefits
1. **Better Diagnostics**: Know exactly what's wrong with failing conversions
2. **Improved Conversion**: Use extracted structure to guide conversion
3. **Validation**: Verify music structure matches, not just registers
4. **Learning**: Automatically improve converter based on comparison results

---

## Phase 3: Integration into Conversion Pipeline

### Workflow
```
Original SID
    ↓
[Custom Player Analysis] → Pre-conversion structure (JSON)
    ↓
[sid_to_sf2.py] ← Use structure to guide conversion
    ↓
SF2 File
    ↓
[sf2_to_sid.py]
    ↓
Converted SID
    ↓
[Custom Player Analysis] → Post-conversion structure (JSON)
    ↓
[Structure Comparison] → Detailed diff report
    ↓
[WAV Comparison] → Audio accuracy
    ↓
[Register Comparison] → Frame-by-frame accuracy
    ↓
COMPREHENSIVE VALIDATION REPORT
```

### Benefits of This Approach
1. **Multi-Level Validation**:
   - Structure level (sequences, instruments, patterns)
   - Register level (exact chip writes)
   - Audio level (actual sound output)

2. **Guided Conversion**:
   - Use pre-analysis to extract music structure
   - Convert structure directly (not reverse-engineer)
   - Validate post-conversion structure matches

3. **Continuous Improvement**:
   - Compare structures to find systematic errors
   - Update converter algorithms based on findings
   - Measure improvement over time

---

## Implementation Priority

### HIGH (Immediate)
1. Add WAV comparison to validation (Phase 1.1-1.3)
2. Enhance custom player for structure extraction (Phase 2.1-2.2)

### MEDIUM (Next Sprint)
3. Integrate structure-guided conversion (Phase 3)
4. Add learning system (Phase 2.4)

### LOW (Future)
5. Advanced audio analysis (spectral, MFCC)
6. Automated converter improvement based on learning

---

## User Feedback Integration

**User Request**: "You should do WAV compare as part of the conversion pipeline. You should use siddump to compare SID files before and after conversion."

**Already Doing**: Using siddump for register-level comparison ✅

**Need to Add**: WAV audio comparison ⏳

**User Request**: "Create your own player to extract detailed information that can be used before SID is converted and after SID is converted for you to learn and verify."

**Already Have**: cpu6502_emulator.py and sid_player.py ✅

**Need to Enhance**: Add music structure extraction ⏳

---

## Success Criteria

### Phase 1 (WAV Comparison)
- [ ] WAV files generated for all test cases
- [ ] Audio accuracy metrics calculated
- [ ] WAV comparison included in validation reports
- [ ] Can identify audible differences not caught by register comparison

### Phase 2 (Enhanced Player)
- [ ] Custom player extracts music structure from SID files
- [ ] Structure comparison shows exact differences
- [ ] Findings used to improve conversion accuracy
- [ ] Failing files' issues clearly identified

### Phase 3 (Integrated Pipeline)
- [ ] Conversion uses structure-guided approach
- [ ] Multi-level validation (structure + register + audio)
- [ ] Accuracy improves for currently failing files
- [ ] System learns and improves automatically

---

## Next Steps

1. **Implement WAV comparison** (this session if time permits)
2. **Enhance sid_player.py** with structure extraction (next session)
3. **Create structure comparison tool** (next session)
4. **Integrate into conversion pipeline** (future session)

This approach addresses both your immediate request (WAV comparison) and your strategic vision (custom player for learning and verification).
