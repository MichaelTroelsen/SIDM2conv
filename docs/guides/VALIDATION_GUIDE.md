# SID Accuracy Validation System
## Comprehensive Guide to Achieving 99% Conversion Accuracy

**Version:** 0.1.0
**Date:** 2025-11-25
**Status:** Phase 1 (Foundation) - In Progress

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Three-Tier Validation Approach](#three-tier-validation-approach)
4. [Current Tools](#current-tools)
5. [Data Capture Strategy](#data-capture-strategy)
6. [Accuracy Metrics](#accuracy-metrics)
7. [Implementation Roadmap](#implementation-roadmap)
8. [Quick Start Guide](#quick-start-guide)
9. [Troubleshooting](#troubleshooting)
10. [References](#references)

---

## Executive Summary

This document describes a comprehensive validation system designed to achieve **99% accuracy** in SID → SF2 → SID round-trip conversion. The system uses a three-tier validation approach combining:

1. **Register-Level Validation** - Frame-by-frame comparison of SID chip register writes
2. **Semantic Validation** - Music structure and pattern analysis
3. **Audio Validation** - Spectral and perceptual audio quality analysis

### Current Status

- ✅ **Phase 1 Foundation**: Basic tools in place (siddump, validate_sid_accuracy.py)
- ✅ **WAV Conversion**: Integrated into convert_all.py pipeline
- ✅ **SF2 Packer**: Python packer producing VSID-playable SID files (v0.6.0)
- 🔄 **Validation Enhancement**: Improving siddump parsing and adding VICE integration
- ⏳ **Semantic Analysis**: Planning desidulate integration
- ⏳ **Audio Analysis**: Spectral comparison tools

### Key Achievement Target

**Overall Accuracy ≥ 99.0%** calculated as:

```
Overall = (
    Frame_Accuracy * 0.40 +      # Register-level
    Voice_Accuracy * 0.30 +      # Frequency + Waveform
    Register_Accuracy * 0.20 +   # Per-register precision
    Filter_Accuracy * 0.10        # Filter settings
)
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CONVERSION PIPELINE                       │
│                                                               │
│  SID File → SF2 Converter → SF2 File → SF2 Packer → SID File│
│             (sid_to_sf2.py)             (sf2_packer.py)     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  THREE-TIER VALIDATION                       │
├─────────────────────────────────────────────────────────────┤
│ TIER 1: REGISTER-LEVEL (50% weight)                         │
│  Tools: siddump.exe, VICE -sounddev dump                    │
│  Output: Frame-by-frame SID register states                 │
│  Metrics: Frame accuracy, per-register accuracy             │
├─────────────────────────────────────────────────────────────┤
│ TIER 2: SEMANTIC ANALYSIS (30% weight)                      │
│  Tools: desidulate, pattern detector                        │
│  Output: SSF (SID Sound Fragments), pattern analysis        │
│  Metrics: Instrument fidelity, pattern correlation          │
├─────────────────────────────────────────────────────────────┤
│ TIER 3: AUDIO VALIDATION (20% weight)                       │
│  Tools: SID2WAV, audio_analyzer.py                          │
│  Output: WAV files, spectral analysis                       │
│  Metrics: Spectral correlation, perceptual quality          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              COMPREHENSIVE REPORTING                         │
│  - HTML visual dashboards with charts                       │
│  - JSON structured data for analysis                        │
│  - Specific fix recommendations                             │
│  - Historical accuracy tracking                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Three-Tier Validation Approach

### Tier 1: Register-Level Validation (50% Weight)

**Purpose:** Verify that the exported SID file writes the exact same values to SID registers at the exact same frames as the original.

**Tools:**
- `tools/siddump.exe` - 6502 emulator with register capture
- `VICE -sounddev dump` - Alternative capture for cross-validation
- `validate_sid_accuracy.py` - Python comparison framework

**What It Captures:**
```python
{
    'frame': 123,
    'cycles': 1520,
    'registers': {
        0x00: 0x2E,  # Voice1_FreqLo
        0x01: 0xFD,  # Voice1_FreqHi
        0x04: 0x81,  # Voice1_Control
        0x05: 0x0F,  # Voice1_Attack_Decay
        # ... all 25 SID registers (0x00-0x18)
    }
}
```

**Metrics:**
- **Frame Accuracy**: `matching_frames / total_frames * 100`
- **Register Accuracy**: Per-register write accuracy
- **Voice Accuracy**: Frequency, waveform, ADSR per voice
- **Filter Accuracy**: Cutoff, resonance, mode accuracy

**Why It's Critical:**
This is the most direct measurement of conversion accuracy. If register writes don't match, the audio won't match.

### Tier 2: Semantic Validation (30% Weight)

**Purpose:** Verify that music structure and patterns are preserved, even if timing or exact register values differ slightly.

**Tools:**
- `desidulate` - Extracts SID Sound Fragments (SSF) from VICE dumps
- `pattern_detector.py` (future) - Detects repeating patterns
- `desidulate_wrapper.py` (future) - Python integration

**What It Captures:**
```python
{
    'instruments': [
        {
            'id': 0,
            'waveforms': [0x41, 0x40, 0x10],  # Pulse, Pulse, Triangle
            'adsr': (0x0F, 0x01, 0x00, 0x00),
            'duration': 12,  # frames
            'frequency_range': (0x0400, 0x0800),
        },
        # ... more instruments
    ],
    'patterns': [
        {
            'sequence': [0x00, 0x01, 0x02, 0x00, 0x01, 0x02],
            'loop_point': 0,
            'repetitions': 8,
        }
    ]
}
```

**Metrics:**
- **Instrument Fidelity**: How well instruments match
- **Pattern Correlation**: Cross-correlation of sequence patterns
- **Structure Preservation**: Loop points, variations, sections

**Why It's Important:**
Sometimes register timing can shift by 1-2 cycles but music structure remains intact. Semantic analysis catches these "functionally equivalent" conversions.

### Tier 3: Audio Validation (20% Weight)

**Purpose:** Verify that the actual audio output sounds the same to human ears.

**Tools:**
- `SID2WAV.EXE` - Renders SID files to WAV
- `audio_analyzer.py` (future) - Spectral comparison
- `librosa` (future) - Perceptual audio analysis

**What It Captures:**
```python
{
    'waveform_correlation': 99.8,  # Time-domain correlation
    'spectral_correlation': 98.5,  # Frequency-domain correlation
    'zero_crossing_rate': 0.95,    # ZCR similarity
    'rms_difference': 0.02,         # RMS level diff
    'peak_snr': 45.2,               # Signal-to-noise ratio
    'perceptual_quality': 96.3,     # MFCC-based (future)
}
```

**Metrics:**
- **Waveform Correlation**: Direct sample-by-sample comparison
- **Spectral Correlation**: FFT-based frequency domain comparison
- **Perceptual Metrics**: MFCC, spectral centroid, etc.

**Why It's Important:**
This is the ultimate test - does it sound right? Catches issues that register analysis might miss (like incorrect SID model emulation, timing drift accumulation).

---

## Current Tools

### 1. siddump.exe (EXISTING)

**Location:** `tools/siddump.exe`
**Source:** `tools/siddump.c`

**Purpose:** 6502 CPU emulator that plays SID files and logs register writes

**Usage:**
```bash
# Basic dump (3 seconds, cycle info)
tools/siddump.exe SID/Angular.sid -z -t3

# Extended dump (30 seconds)
tools/siddump.exe SID/Angular.sid -z -t30

# Specific subtune
tools/siddump.exe SID/Angular.sid -z -t30 -a1
```

**Output Format:**
```
| Frame | Freq Note/Abs WF ADSR Pul | ... | FCut RC Typ V | Cycl RL RB |
|     0 | 0000  ... ..  00 0000 000 | ... | 0000 00 Off 0 | 1521 19 1B |
|     1 | FD2E (B-7 DF) 80 .... 800 | ... | .... F1 ... F | 1520 19 1B |
```

**Status:** ✅ Working, needs enhanced JSON output mode

### 2. validate_sid_accuracy.py (NEW - v0.1.0)

**Location:** `validate_sid_accuracy.py`
**Created:** 2025-11-25

**Purpose:** Comprehensive validation framework with HTML reporting

**Usage:**
```bash
# Basic comparison
python validate_sid_accuracy.py original.sid exported.sid

# With options
python validate_sid_accuracy.py original.sid exported.sid \
    --duration 60 \
    --output report.html \
    --json data.json \
    --verbose
```

**Features:**
- Frame-by-frame register comparison
- Voice-level analysis (frequency, waveform, ADSR, pulse width)
- Filter analysis
- Weighted accuracy scoring
- HTML report generation
- JSON export

**Status:** ⚠️ Needs fixing - siddump parsing not working (captures 0 frames)

### 3. convert_all.py (ENHANCED)

**Location:** `convert_all.py`
**Version:** 0.6.0

**New Features (2025-11-25):**
- ✅ Automatic WAV conversion for all files
- ✅ Original WAV: `output/{SongName}/Original/{name}.wav`
- ✅ Exported WAV: `output/{SongName}/New/{name}_exported.wav`
- ✅ 16-bit stereo, 30 second duration
- ✅ Integrated SF2 packer for automatic SID export

**Usage:**
```bash
# Convert all SID files with WAV generation
python convert_all.py

# Custom input/output
python convert_all.py --input SID --output output
```

### 4. SF2 Packer (WORKING)

**Location:** `sidm2/sf2_packer.py`
**Version:** 0.6.0

**Purpose:** Converts SF2 files back to playable SID format

**Status:** ✅ Working - produces VSID-playable SID files

**Key Features:**
- Extracts driver code from absolute address $1000
- 6502 instruction-level pointer relocation
- PSID v2 header generation
- Average output: ~3,800 bytes (comparable to manual exports)

---

## Data Capture Strategy

### What Data to Capture

#### **Priority 1: CRITICAL DATA** (Current Focus)

| Data Type | Granularity | Frequency | Tool | Status |
|-----------|-------------|-----------|------|--------|
| SID Register Writes | All 25 registers | Every frame (50Hz) | siddump | ⚠️ Fix needed |
| Voice Frequencies | 16-bit values | Per change | siddump | ⚠️ Fix needed |
| Waveform Control | Control register | Per change | siddump | ⚠️ Fix needed |
| ADSR Envelopes | Attack/Decay/Sustain/Release | Per change | siddump | ⚠️ Fix needed |
| Pulse Width | 12-bit PWM values | Per change | siddump | ⚠️ Fix needed |
| Filter Settings | Cutoff/Res/Mode | Per change | siddump | ⚠️ Fix needed |

#### **Priority 2: HIGH VALUE DATA** (Next Phase)

| Data Type | Source | Purpose | Status |
|-----------|--------|---------|--------|
| SSF Fragments | desidulate | Instrument analysis | ⏳ Planned |
| Pattern Sequences | desidulate | Structure validation | ⏳ Planned |
| Audio WAV Files | SID2WAV | Perceptual validation | ✅ Done |

#### **Priority 3: NICE-TO-HAVE DATA** (Future)

| Data Type | Source | Purpose | Status |
|-----------|--------|---------|--------|
| CPU Cycle Timing | siddump | Timing analysis | ⏳ Planned |
| Memory Snapshots | siddump | State verification | ⏳ Planned |
| Spectral Analysis | librosa | Audio quality | ⏳ Planned |

### Data Storage Format

**JSON Structure:**
```json
{
    "metadata": {
        "original_sid": "Angular.sid",
        "exported_sid": "Angular_exported.sid",
        "capture_date": "2025-11-25T19:30:00",
        "duration_seconds": 30,
        "tool_version": "0.1.0"
    },
    "frames": [
        {
            "frame": 0,
            "cycles": 1521,
            "registers": {
                "Voice1_FreqLo": 0,
                "Voice1_FreqHi": 0,
                "Voice1_Control": 0,
                ...
            },
            "changes": ["Voice1_FreqLo", "Voice1_Control"]
        },
        ...
    ],
    "analysis": {
        "frame_accuracy": 98.5,
        "voice_accuracy": {
            "Voice1": {"frequency": 99.2, "waveform": 98.8},
            "Voice2": {"frequency": 99.0, "waveform": 98.5},
            "Voice3": {"frequency": 98.8, "waveform": 98.2}
        },
        "register_accuracy": {...},
        "filter_accuracy": 97.5,
        "overall_accuracy": 98.7
    }
}
```

---

## Accuracy Metrics

### Overall Accuracy Formula

```python
def calculate_overall_accuracy(results):
    """
    Calculate weighted composite accuracy score
    Target: >= 99.0%
    """
    return (
        results['frame_accuracy'] * 0.40 +      # 40% weight
        results['voice_accuracy'] * 0.30 +      # 30% weight
        results['register_accuracy'] * 0.20 +   # 20% weight
        results['filter_accuracy'] * 0.10       # 10% weight
    )
```

### Component Targets

| Component | Target | Weight | Critical? |
|-----------|--------|--------|-----------|
| Frame-level accuracy | ≥ 99.0% | 40% | YES |
| Voice frequency accuracy | ≥ 99.5% | 15% | YES |
| Voice waveform accuracy | ≥ 99.5% | 15% | YES |
| Register accuracy (avg) | ≥ 98.0% | 20% | NO |
| Filter accuracy | ≥ 98.0% | 10% | NO |
| **OVERALL** | **≥ 99.0%** | **100%** | **YES** |

### Acceptance Criteria

- 🟢 **Excellent**: Overall ≥ 99.0% - Ready for production
- 🟡 **Good**: Overall ≥ 95.0% - Minor issues, acceptable
- 🟠 **Needs Work**: Overall ≥ 80.0% - Significant issues
- 🔴 **Poor**: Overall < 80.0% - Major problems, not usable

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1) - **IN PROGRESS**

- [x] Create WAV conversion pipeline (**DONE** 2025-11-25)
- [x] Create validate_sid_accuracy.py framework (**DONE** 2025-11-25)
- [x] Commit validation tool to git (**DONE** 2025-11-25)
- [ ] Fix siddump output parsing (table format)
- [ ] Remove Unicode emojis for Windows compatibility
- [ ] Test validation with Angular.sid
- [ ] Add JSON export functionality
- [ ] Document current accuracy baseline for all 16 SID files

**Deliverable:** Working register-level validation tool

### Phase 2: Enhanced Capture (Week 2)

- [ ] Enhance siddump.c with `--json` output flag
- [ ] Compile enhanced siddump.exe
- [ ] Create VICE dump wrapper (`sidm2/vice_capture.py`)
- [ ] Build EnhancedRegisterLogger (`sidm2/register_logger.py`)
- [ ] Cross-validate siddump vs VICE output
- [ ] Add delta tracking (only log changes)

**Deliverable:** Multi-source register capture with cross-validation

### Phase 3: Semantic Analysis (Week 3)

- [ ] Install desidulate: `pip install desidulate`
- [ ] Create DesidulateBridge (`sidm2/desidulate_wrapper.py`)
- [ ] Generate VICE dumps automatically
- [ ] Process dumps with desidulate
- [ ] Extract SSF (SID Sound Fragments)
- [ ] Build instrument fingerprint comparison
- [ ] Add pattern detection algorithms

**Deliverable:** Semantic validation layer with SSF comparison

### Phase 4: Audio Analysis (Week 4)

- [ ] Create AudioSpectralAnalyzer (`sidm2/audio_analyzer.py`)
- [ ] Implement FFT-based spectral correlation
- [ ] Add zero-crossing rate comparison
- [ ] Calculate RMS difference
- [ ] Measure peak SNR
- [ ] Optional: Add librosa for MFCC/DTW analysis

**Deliverable:** Audio-level validation with spectral comparison

### Phase 5: Integration & Reporting (Week 5)

- [ ] Build ComprehensiveValidator (`validate_comprehensive.py`)
- [ ] Integrate all three validation tiers
- [ ] Calculate weighted composite scores
- [ ] Generate enhanced HTML reports with charts
- [ ] Add register heatmaps
- [ ] Add audio spectrograms
- [ ] Integrate into convert_all.py pipeline
- [ ] Create comparison matrix across all 16 SID files

**Deliverable:** Unified validation dashboard with actionable insights

### Phase 6: Optimization (Week 6)

- [ ] Performance tuning (parallel processing)
- [ ] Caching (WAV renders, dumps)
- [ ] Incremental validation (only changed files)
- [ ] CI/CD integration
- [ ] Regression testing
- [ ] Automatic accuracy tracking
- [ ] User documentation
- [ ] Developer guide

**Deliverable:** Production-ready validation system

---

## Quick Start Guide

### Getting Started Today

**1. Test Current Pipeline:**
```bash
# Convert a single SID file
python sid_to_sf2.py SID/Angular.sid SF2/Angular_d11.sf2 --driver driver11

# Run full conversion pipeline (includes WAV generation)
python convert_all.py --input SID --output output
```

**2. Check Generated Files:**
```bash
# Look at output structure
ls output/Angular/Original/    # Original SID + WAV
ls output/Angular/New/          # SF2 files + Exported SID + WAV
```

**3. Test Validation Tool (When Fixed):**
```bash
# Compare original vs exported
python validate_sid_accuracy.py \
    SID/Angular.sid \
    output/Angular/New/Angular_exported.sid \
    --duration 30 \
    --output validation_angular.html
```

### Understanding the Output

**Directory Structure:**
```
output/
└── Angular/
    ├── Original/
    │   ├── Angular.sid          # Copy of original
    │   ├── Angular.wav          # Original audio render
    │   ├── Angular.dump         # Register dump (future)
    │   └── Angular_info.txt     # Metadata
    └── New/
        ├── Angular_d11.sf2      # Driver 11 version
        ├── Angular_g4.sf2       # NP20 (G4) version
        ├── Angular_exported.sid # Packed from D11
        ├── Angular_exported.wav # Exported audio render
        ├── Angular_exported.dump # Register dump
        └── Angular_info.txt     # Conversion details
```

---

## Troubleshooting

### Common Issues

#### 1. validate_sid_accuracy.py captures 0 frames

**Problem:** Siddump output parsing not working

**Cause:** Code expects hex dump format (`D400: 01 02 03`) but siddump outputs formatted table

**Fix:** Need to update `_parse_siddump_output()` to parse table format

**Workaround:** Use manual siddump inspection:
```bash
tools/siddump.exe SID/Angular.sid -z -t10 > angular_dump.txt
# Manually inspect angular_dump.txt
```

#### 2. Unicode encoding errors on Windows

**Problem:** Checkmark emojis (✅) cause `UnicodeEncodeError`

**Fix:** Remove emojis or use ASCII alternatives:
- ✅ → [OK] or PASS
- ❌ → [X] or FAIL
- ⚠️ → [!] or WARN

#### 3. WAV files sound different despite high accuracy

**Problem:** Register accuracy looks good but audio differs

**Possible Causes:**
- SID model mismatch (6581 vs 8580)
- Sample rate differences
- Filter emulation accuracy
- Timing drift accumulation

**Debugging:**
1. Check spectral analysis (future)
2. Compare siddump output frame-by-frame
3. Look for timing pattern differences

#### 4. Conversion accuracy varies by song

**Problem:** Some songs convert at 99%, others at 85%

**Explanation:** Different songs use different features:
- Complex filter sweeps are harder
- Arpeggio commands may not extract perfectly
- Hard restart timing is critical
- Pulse width modulation needs precision

**Strategy:** Focus on one song, achieve 99%, then apply learnings to others

---

## References

### External Tools

- **VICE Emulator**: https://vice-emu.sourceforge.io/
- **desidulate**: https://github.com/anarkiwi/desidulate
- **libsidplayfp**: https://github.com/libsidplayfp/libsidplayfp
- **SID Factory II**: https://blog.chordian.net/sf2/

### Documentation

- `docs/SF2_FORMAT_SPEC.md` - SF2 file format specification
- `docs/CONVERSION_STRATEGY.md` - Laxity to SF2 mapping
- `docs/DRIVER_REFERENCE.md` - All driver specifications
- `docs/LAXITY_PLAYER_ANALYSIS.md` - Laxity player internals
- `PACK_STATUS.md` - SF2 packer implementation status
- `README.md` - Project overview

### Key Project Files

- `sid_to_sf2.py` - SID to SF2 converter
- `convert_all.py` - Batch conversion pipeline
- `validate_sid_accuracy.py` - Validation framework
- `sidm2/sf2_packer.py` - SF2 to SID packer
- `sidm2/cpu6502.py` - 6502 instruction relocation
- `tools/siddump.c` - Register capture tool source

---

## Next Steps

### Immediate Actions (This Week)

1. **Fix validate_sid_accuracy.py:**
   - Update siddump output parser
   - Remove Unicode emojis
   - Test with Angular.sid

2. **Establish Baseline:**
   - Run validation on all 16 SID files
   - Document current accuracy levels
   - Identify patterns in failures

3. **Quick Wins:**
   - Install desidulate: `pip install desidulate`
   - Test VICE dump generation
   - Generate first SSF comparison

### Medium Term (Next 2 Weeks)

4. **Build Enhanced Tools:**
   - EnhancedRegisterLogger
   - VICE capture wrapper
   - Pattern detector

5. **Semantic Layer:**
   - DesidulateBridge
   - Instrument comparison
   - Pattern correlation

### Long Term (Next Month)

6. **Complete System:**
   - Audio spectral analyzer
   - Comprehensive validator
   - Automated reporting
   - CI/CD integration

7. **Achieve 99% Accuracy:**
   - Systematic fixing of issues
   - Iterative refinement
   - Documentation of solutions

---

## Conclusion

This validation system provides a comprehensive, multi-layered approach to achieving 99% accuracy in SID → SF2 → SID conversion. By combining register-level precision, semantic music structure analysis, and perceptual audio quality validation, you can systematically identify and fix conversion issues.

The key to success is **iterative refinement**: run validation, identify issues, fix the converter, re-validate, repeat. Each validation cycle provides specific, actionable insights into where the conversion is failing and how to improve it.

**Current Status:** Phase 1 (Foundation) is 60% complete. The core architecture is in place and working tools exist. Next priority is fixing the siddump parser to get the first baseline accuracy measurements.

**Target:** Achieve 99% accuracy on Angular.sid, then apply learnings to all 16 SID files.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-25
**Maintainer:** Claude Code
**Status:** Living Document - Updated as system evolves
