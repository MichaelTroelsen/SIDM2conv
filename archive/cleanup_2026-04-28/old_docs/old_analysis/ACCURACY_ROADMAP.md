# SID to SF2 Conversion Accuracy Roadmap

## Current Status

**Baseline Accuracy**: 9.0% overall (Angular.sid)
**Target**: 99% accuracy
**Timeline**: 6-8 days of focused work

### Accuracy Breakdown (Angular.sid - v0.6.0)

```
Overall Accuracy:        9.0%  [POOR]
Frame-Level:             0.2%
Voice Accuracy:          0.7%
Register Accuracy:      29.6%
Filter Accuracy:        28.0%

Frames Compared:       500
Differences Found:     499

Grade:                 POOR
```

## Root Cause Analysis

### P0 - Critical Issues (90%+ of errors)

#### 1. Sequence Format Mismatch
**Impact**: 40-50% accuracy loss

The converter incorrectly assumes Laxity sequences follow SF2 format:

**Laxity Format** (from `docs/LAXITY_PLAYER_ANALYSIS.md`):
- Command-driven sequences
- Super commands: $0x (slide), $2x (slide down), $60 (vibrato), $8x (portamento)
- Implicit gate timing based on note duration
- Note values use frequency table lookups

**SF2 Format** (from `docs/SF2_FORMAT_SPEC.md`):
- Row-based sequences with explicit events
- Each row: `[instrument] [command] [note]`
- Explicit gate markers: `0x7E` (gate on), `0x80` (gate off)
- Note values are direct MIDI-like note numbers

**Current Bug**: `sidm2/sf2_writer.py` reads Laxity sequence bytes and writes them directly as SF2 events without translation.

#### 2. Note Frequency Errors
**Impact**: 20-30% accuracy loss

- All note frequencies are incorrect
- Missing transpose/detune handling
- Wave table note offsets not applied correctly
- File: `sidm2/sf2_writer.py:_inject_sequences()`

#### 3. Missing Gate Timing
**Impact**: 15-20% accuracy loss

SF2 requires explicit gate control for proper ADSR envelope triggering:

```
Correct SF2 sequence:
  0x7E        # Gate on (+++  in SF2 editor)
  0x30        # Note C-4
  0x80        # Gate off (--- in SF2 editor)
```

Current converter never emits `0x7E`/`0x80` markers.

- File: `sidm2/sf2_writer.py:_inject_sequences()`

#### 4. Filter Table Extraction Wrong
**Impact**: 15% accuracy loss (matches 28% filter accuracy)

Filter table extracted from wrong address or format.

**Correct Laxity address**: `$1A1E` (from `docs/LAXITY_PLAYER_ANALYSIS.md`)

**Format**: 4-byte entries `(cutoff_lo, cutoff_hi, resonance, mode)` until `0x7F`

- File: `sidm2/table_extraction.py:extract_filter_table()`

### P1 - High Priority

#### 5. Waveform Register Generation
**Impact**: 10-15% accuracy loss

Waveform table format mismatch between Laxity and SF2.

**Laxity**: `(note_offset, waveform)` pairs
**SF2**: `(waveform, note_offset)` pairs (swapped!)

Current converter may be writing bytes in wrong order.

- File: `sidm2/sf2_writer.py:_inject_wave_table()`

#### 6. Pulse Table Indices
**Impact**: 5-10% accuracy loss

Laxity uses Y*4 pre-multiplied pulse table indices, SF2 uses direct indices.

- File: `sidm2/table_extraction.py:extract_pulse_table()`

#### 7. Instrument ADSR Mismatches
**Impact**: 5-10% accuracy loss

From `output/Angular/New/Angular_info.txt`:
```
ADSR Validation:
  ADSR observed in playback: 0 unique combinations
  ADSR in instrument table:  1 entries
  Match rate: 100% (0/0 observed values found)
```

Instruments not being applied correctly or instrument table extraction incomplete.

- File: `sidm2/table_extraction.py:extract_instrument_table()`

### P2 - Medium Priority

#### 8. Command Parameter Extraction
**Impact**: 3-5% accuracy loss

Command parameters (vibrato depth, slide speed) not fully extracted from Laxity format.

- File: `sidm2/sf2_writer.py:_inject_commands()`

#### 9. Tempo/Speed Handling
**Impact**: 2-3% accuracy loss (compounds over time)

Laxity speed system uses filter table first 4 bytes for wrap lookup.

- File: `sidm2/table_extraction.py:extract_tempo_table()`

### P3 - Low Priority

#### 10. HR (Hard Restart) Table
**Impact**: 1-2% accuracy loss

Currently using defaults (`$0F $00`), should extract from Laxity.

- File: `sidm2/table_extraction.py` (not implemented)

#### 11. Arpeggio Table
**Impact**: <1% accuracy loss

Rare usage, defaults work for most tunes.

## Quick Wins (Phase 2)

These fixes can be implemented immediately with high confidence:

### 1. Fix Filter Table Extraction
**Expected Gain**: +15% accuracy (28% → 43%)

```python
# sidm2/table_extraction.py
def extract_filter_table(memory: bytearray) -> list:
    """Extract filter table from Laxity $1A1E address."""
    FILTER_TABLE_ADDR = 0x1A1E
    entries = []
    addr = FILTER_TABLE_ADDR

    while addr < len(memory):
        cutoff_lo = memory[addr]
        if cutoff_lo == 0x7F:  # End marker
            break
        cutoff_hi = memory[addr + 1]
        resonance = memory[addr + 2]
        mode = memory[addr + 3]
        entries.append((cutoff_lo, cutoff_hi, resonance, mode))
        addr += 4

    return entries
```

### 2. Add Explicit Gate Handling
**Expected Gain**: +20% accuracy (9% → 29%)

```python
# sidm2/sf2_writer.py:_inject_sequences()
def _inject_gate_markers(sequence: list) -> list:
    """Insert SF2 gate markers around notes."""
    output = []
    for event in sequence:
        if event['note'] < 0x7E:  # Regular note
            output.append(0x7E)  # Gate on
            output.append(event['instrument'])
            output.append(event['command'])
            output.append(event['note'])
            output.append(0x80)  # Gate off
        else:
            output.append(event)
    return output
```

### 3. Fix Waveform Byte Order
**Expected Gain**: +30% accuracy (9% → 39%)

```python
# sidm2/sf2_writer.py:_inject_wave_table()
# Current (wrong):
wave_data = [note_offset, waveform, ...]

# Correct:
wave_data = [waveform, note_offset, ...]
```

**Combined Quick Win Impact**: 9% → 40-60% accuracy (single session)

## 5-Phase Roadmap to 99%

### Phase 1: Sequence Parser Rewrite (2-3 days)
**Target**: 50% accuracy

**Tasks**:
1. Study Laxity sequence format in detail (`docs/LAXITY_PLAYER_ANALYSIS.md`)
2. Create Laxity sequence parser that understands super commands
3. Create Laxity-to-SF2 translator:
   - Map Laxity commands to SF2 commands
   - Convert note frequency lookups to SF2 note numbers
   - Insert explicit gate markers at correct timing
4. Test with Angular.sid and validate accuracy improvement

**Files**:
- New: `sidm2/players/laxity_sequence_parser.py`
- Modify: `sidm2/sf2_writer.py:_inject_sequences()`

**Success Criteria**: Voice accuracy > 40%, Overall > 50%

### Phase 2: Table Extraction Fixes (1-2 days)
**Target**: 70% accuracy

**Tasks**:
1. Implement proper filter table extraction (use address $1A1E)
2. Fix pulse table index translation (Y*4 → direct)
3. Improve instrument table extraction and validation
4. Add wave table byte order fix
5. Validate all table extractions against siddump

**Files**:
- `sidm2/table_extraction.py` (all extract_* functions)
- `sidm2/sf2_writer.py` (injection functions)

**Success Criteria**: Register accuracy > 60%, Filter > 80%, Overall > 70%

### Phase 3: Instrument & Note Mapping (1 day)
**Target**: 85% accuracy

**Tasks**:
1. Fix instrument ADSR application in sequences
2. Implement correct note transpose handling
3. Fix wave table note offset calculation
4. Add ADSR validation against siddump

**Files**:
- `sidm2/sf2_writer.py:_inject_sequences()`
- `sidm2/confidence.py` (instrument scoring)

**Success Criteria**: Voice accuracy > 70%, ADSR match > 80%, Overall > 85%

### Phase 4: Timing & Command Parameters (1 day)
**Target**: 95% accuracy

**Tasks**:
1. Implement proper tempo/speed system (filter table wrap)
2. Extract command parameters (vibrato depth, slide speed)
3. Fix timing alignment between voices
4. Add frame-level timing validation

**Files**:
- `sidm2/table_extraction.py:extract_tempo_table()`
- `sidm2/sf2_writer.py:_inject_commands()`

**Success Criteria**: Frame accuracy > 80%, Overall > 95%

### Phase 5: Edge Cases & Polish (1 day)
**Target**: 99% accuracy

**Tasks**:
1. Implement HR table extraction
2. Handle special wave table cases ($80 note offset)
3. Fix vibrato/slide limitations (note offset $00)
4. Test with all 7 example SID files
5. Document remaining <1% discrepancies

**Files**:
- All `sidm2/*.py` modules
- Add edge case tests to `test_converter.py`

**Success Criteria**: Overall > 99% on Angular.sid, >95% on all example files

## Timeline Summary

```
Day 1:   Quick Wins (Phase 2)                    →  9% →  40-60%
Day 2-4: Sequence Parser Rewrite (Phase 1)       → 60% →  50%
Day 5-6: Table Extraction Fixes (Phase 2)        → 50% →  70%
Day 7:   Instrument & Note Mapping (Phase 3)     → 70% →  85%
Day 8:   Timing & Command Parameters (Phase 4)   → 85% →  95%
Day 9:   Edge Cases & Polish (Phase 5)           → 95% →  99%
```

**Note**: Accuracy may fluctuate as different aspects are fixed. The sequence parser rewrite (Phase 1) may temporarily reduce accuracy before improving it.

## Next Session Tasks

### Immediate (Phase 2 - Quick Wins):

1. **Fix filter table extraction** (`sidm2/table_extraction.py`):
   - Use address `0x1A1E` from Laxity player
   - Extract 4-byte entries until `0x7F`
   - Validate against siddump filter register captures

2. **Add gate handling** (`sidm2/sf2_writer.py`):
   - Insert `0x7E` (gate on) before each note
   - Insert `0x80` (gate off) at note duration end
   - Test with Angular.sid

3. **Fix waveform byte order** (`sidm2/sf2_writer.py`):
   - Swap from `(note, waveform)` to `(waveform, note)`
   - Validate against SF2 format spec

4. **Test and validate**:
   - Run `python validate_sid_accuracy.py`
   - Confirm accuracy increase to 40-60%
   - Update baseline in README.md

### Future (Phase 1 - Sequence Parser):

1. Study `docs/LAXITY_PLAYER_ANALYSIS.md` section on sequence format
2. Analyze how Laxity super commands map to SF2 commands
3. Design Laxity sequence parser architecture
4. Implement command translation layer

## Validation Strategy

After each phase, validate improvements using:

```bash
# Full validation (30 seconds)
python validate_sid_accuracy.py

# Quick validation (10 seconds) - integrated in pipeline
python convert_all.py
```

**Metrics to Track**:
- Overall Accuracy (weighted composite)
- Frame-Level Accuracy (exact frame matches)
- Voice Accuracy (frequency + waveform per voice)
- Register Accuracy (per-register correctness)
- Filter Accuracy (filter register correctness)

**Success Criteria**:
- Phase 1: Voice > 40%, Overall > 50%
- Phase 2: Register > 60%, Filter > 80%, Overall > 70%
- Phase 3: Voice > 70%, ADSR match > 80%, Overall > 85%
- Phase 4: Frame > 80%, Overall > 95%
- Phase 5: Overall > 99%

## References

- `docs/LAXITY_PLAYER_ANALYSIS.md` - Laxity sequence format details
- `docs/SF2_FORMAT_SPEC.md` - SF2 sequence and table formats
- `docs/CONVERSION_STRATEGY.md` - Laxity to SF2 mapping strategy
- `docs/VALIDATION_SYSTEM.md` - Three-tier validation architecture
- `output/Angular/New/Angular_info.txt` - Current extraction results
- `README.md` - Version history and changelog

## Version History

- **v0.6.0** (2025-11-25): Validation system integrated, baseline established (9%)
- **v0.7.0** (planned): Quick wins implemented (target 40-60%)
- **v0.8.0** (planned): Sequence parser rewritten (target 50%)
- **v0.9.0** (planned): Table extraction fixed (target 70%)
- **v1.0.0** (planned): Production ready (target 99%)
