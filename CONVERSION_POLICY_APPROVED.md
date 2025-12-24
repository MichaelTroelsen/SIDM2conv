# SIDM2 Conversion Policy - APPROVED

**Version**: 2.0.0
**Date**: 2025-12-24
**Status**: ✅ **APPROVED & ACTIVE**
**Approach**: Quality-First with SF2 Format Validation

---

## Core Policy (Approved)

### Goal: Maximum Quality + SF2 Compatibility

**All conversions must**:
1. ✅ Use **best available driver** for source player type
2. ✅ Produce **SF2-format-compatible** files (loadable in SF2 Editor)
3. ✅ Pass **automated format validation**
4. ✅ **Document which driver was used** in output

---

## Driver Selection Matrix

| Source Player Type | Target Driver | Expected Accuracy | Rationale |
|-------------------|---------------|-------------------|-----------|
| **Laxity NewPlayer v21** | **Laxity Driver** | 99.93% | Custom driver optimized for Laxity |
| **SF2-exported SID** | **Driver 11** | 100% | Preserve original driver |
| **NewPlayer 20.G4** | **NP20** | 70-90% | Format-specific driver |
| **Rob Hubbard** | Driver 11 | Safe default | Standard conversion |
| **Martin Galway** | Driver 11 | Safe default | Standard conversion |
| **JCH NewPlayer** | Driver 11 | Safe default | Standard conversion |
| **Soundmonitor** | Driver 11 | Safe default | Standard conversion |
| **Unknown/Generic** | Driver 11 | Safe default | Universal compatibility |

### Driver Selection Logic

```python
def select_driver(sid_file: Path) -> Tuple[str, str, str]:
    """Select best driver for SID file.

    Returns:
        (driver_name, expected_accuracy, selection_reason)
    """
    player = identify_player(sid_file)

    if player == "Laxity_NewPlayer_V21":
        return ("laxity", "99.93%", "Laxity-specific driver for maximum accuracy")

    elif player in ["Vibrants/Laxity", "SidFactory_II/Laxity", "SidFactory/Laxity"]:
        return ("laxity", "99.93%", "Laxity variant - using Laxity driver")

    elif player == "NewPlayer_20.G4":
        return ("np20", "70-90%", "NewPlayer 20.G4 specific driver")

    elif "SF2" in player or "Driver_11" in player:
        return ("driver11", "100%", "SF2-exported file - preserving Driver 11")

    else:
        return ("driver11", "Safe default", "Standard SF2 driver for maximum compatibility")
```

---

## Mandatory Requirements

### 1. Driver Information Documentation ✅

**Every conversion MUST document**:
- Source player type (identified by player-id.exe or pattern matcher)
- Selected driver (laxity, driver11, np20)
- Expected accuracy percentage
- Selection reason
- Conversion timestamp

**Where to document**:
- Console output during conversion
- Log file (`conversion.log`)
- Info file (`output/[file]/info.txt`)
- SF2 metadata (if possible)

**Example Output**:
```
================================================================================
Converting: Stinsens_Last_Night_of_89.sid
================================================================================

Source Analysis:
  Player Type:     Laxity_NewPlayer_V21
  Load Address:    $1000
  Init Address:    $1000
  Play Address:    $1006
  Songs:           1

Driver Selection:
  Selected Driver: Laxity Driver (sf2driver_laxity_00.prg)
  Expected Acc:    99.93%
  Reason:          Laxity-specific driver for maximum accuracy
  Alternative:     Driver 11 (1-8% accuracy - not recommended)

Conversion:
  Status:          SUCCESS
  Output:          output.sf2
  File Size:       12,345 bytes

Validation:
  Format Check:    PASS - Valid SF2 format
  Metadata:        PASS - All blocks present
  Tables:          PASS - All tables valid

Result: ✅ Conversion successful with 99.93% expected accuracy
================================================================================
```

### 2. SF2 Format Validation ✅

**Every generated SF2 file MUST**:
- Pass automated format validation (`scripts/validate_sf2_format.py`)
- Have valid PRG header
- Have all metadata blocks present
- Have valid table structures
- Have no truncation or corruption

**Validation is MANDATORY** - Failed validation = reject conversion

### 3. Info File Generation ✅

**Every conversion MUST create an info file**:

**Location**: `output/[filename]/info.txt`

**Contents**:
```
Conversion Information
======================
File: Stinsens_Last_Night_of_89.sid
Date: 2025-12-24 14:30:15
Converter: SIDM2 v2.8.0

Source File:
  Title:           Stinsen's Last Night of '89
  Author:          Thomas E. Petersen (Laxity)
  Copyright:       2021 Bonzai
  Player Type:     Laxity_NewPlayer_V21
  Format:          PSID v2
  Load Address:    $1000
  Init Address:    $1000
  Play Address:    $1006
  Songs:           1

Driver Selection:
  Selected Driver: Laxity Driver (sf2driver_laxity_00.prg)
  Expected Acc:    99.93%
  Reason:          Laxity-specific driver for maximum accuracy
  Alternative:     Driver 11 (1-8% accuracy)

Conversion Results:
  Status:          SUCCESS
  Output File:     Stinsens_Last_Night_of_89.sf2
  Output Size:     12,345 bytes
  Validation:      PASS

Quality Metrics:
  Expected Acc:    99.93%
  Frame Count:     1,500 (30 seconds)
  Register Writes: 2,475

Validation Details:
  ✓ File format:   Valid PRG
  ✓ Metadata:      All blocks present
  ✓ Sequences:     3 voices
  ✓ Instruments:   32 entries
  ✓ Wave table:    128 entries
  ✓ Integrity:     No corruption detected
```

---

## Conversion Pipeline (Mandatory Steps)

### Standard Conversion Flow

```
1. Parse SID File
   ↓
2. Identify Player Type (player-id.exe or pattern matcher)
   ↓
3. Select Best Driver (based on player type)
   ↓
4. LOG: Document driver selection & reason
   ↓
5. Convert to SF2 (using selected driver)
   ↓
6. VALIDATE: Format validation (mandatory)
   ↓
7. Generate Info File (document everything)
   ↓
8. LOG: Conversion result
   ↓
9. Output: SF2 file + info.txt + logs
```

### Validation Points

**Pre-Conversion Validation**:
- ✅ Valid SID file format (PSID/RSID)
- ✅ Player type identified (or default to Driver 11)
- ✅ Required driver available
- ✅ File integrity check

**Post-Conversion Validation** (MANDATORY):
- ✅ SF2 file generated
- ✅ SF2 format validation (automated)
- ✅ All metadata blocks present
- ✅ No corruption detected
- ✅ Info file generated

**Quality Validation** (Recommended):
- ✅ Frame-by-frame comparison (if original available)
- ✅ Accuracy score ≥ 95% (for roundtrip)
- ✅ Manual spot-check in SF2 Editor

---

## Implementation Details

### Driver Files

**Location**: `drivers/` or `G5/drivers/`

**Available Drivers**:
1. **Laxity Driver**: `sf2driver_laxity_00.prg` (8,192 bytes)
   - For: Laxity NewPlayer v21 files
   - Accuracy: 99.93%

2. **Driver 11**: `sf2driver_11.prg`
   - For: SF2-exported, Rob Hubbard, Martin Galway, generic files
   - Accuracy: 100% (SF2-exported), safe default (others)

3. **NP20 Driver**: `sf2driver_np20.prg`
   - For: NewPlayer 20.G4 files
   - Accuracy: 70-90%

### CLI Usage

**Automatic driver selection**:
```bash
python scripts/sid_to_sf2.py input.sid output.sf2
# Automatically selects best driver based on player type
```

**Manual driver override**:
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
# Forces Laxity driver (expert use)
```

**With validation**:
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --validate
# Includes SF2 format validation (recommended)
```

**Batch conversion**:
```bash
python scripts/batch_convert.py --dir Laxity/ --validate
# Auto-selects best driver for each file, validates all
```

---

## Output Documentation Requirements

### Console Output (Required)

Show during conversion:
```
Converting: filename.sid
Player Type: Laxity_NewPlayer_V21
Selected Driver: Laxity Driver (99.93% accuracy)
Reason: Laxity-specific driver for maximum accuracy

Converting... [====================] 100%
Validating... [====================] 100%

✅ SUCCESS: filename.sf2 (99.93% expected accuracy)
```

### Log File (Required)

**Location**: `conversion.log` or `output/[file]/conversion.log`

**Format**: Detailed log with timestamps
```
2025-12-24 14:30:15 [INFO] Starting conversion: Stinsens_Last_Night_of_89.sid
2025-12-24 14:30:15 [INFO] Parsing SID header...
2025-12-24 14:30:15 [INFO] Player identified: Laxity_NewPlayer_V21
2025-12-24 14:30:15 [INFO] Driver selection: Laxity Driver (sf2driver_laxity_00.prg)
2025-12-24 14:30:15 [INFO] Expected accuracy: 99.93%
2025-12-24 14:30:15 [INFO] Reason: Laxity-specific driver for maximum accuracy
2025-12-24 14:30:15 [INFO] Converting to SF2 format...
2025-12-24 14:30:16 [INFO] Conversion complete: 12,345 bytes
2025-12-24 14:30:16 [INFO] Validating SF2 format...
2025-12-24 14:30:16 [INFO] Validation: PASS - All checks passed
2025-12-24 14:30:16 [INFO] Generating info file...
2025-12-24 14:30:16 [SUCCESS] Conversion successful: output.sf2
```

### Info File (Required)

**Location**: `output/[filename]/info.txt`

**See template above** - Must include:
- Source file metadata
- Player type identification
- Driver selection + reason + expected accuracy
- Conversion results
- Validation results

---

## Quality Standards

### Expected Accuracy Thresholds

| Driver | Source Type | Expected Accuracy | Quality Rating |
|--------|-------------|-------------------|----------------|
| Laxity | Laxity NP v21 | 99.93% | ✅ Excellent |
| Driver 11 | SF2-exported | 100% | ✅ Perfect |
| NP20 | NewPlayer 20.G4 | 70-90% | ✅ Good |
| Driver 11 | Rob Hubbard | Unknown | ⚠️ Safe default |
| Driver 11 | Martin Galway | Unknown | ⚠️ Safe default |
| Driver 11 | Generic | Unknown | ⚠️ Safe default |

### Validation Pass Criteria

**Format validation MUST pass**:
- ✅ Valid PRG file
- ✅ Correct load address
- ✅ File size 8KB-64KB
- ✅ All metadata blocks present
- ✅ All tables valid
- ✅ End markers present
- ✅ No truncation

**If validation fails** → Reject conversion, log error, investigate

---

## Manual Override Policy

### When Manual Override is Allowed

**Expert users can override driver selection**:
- Testing alternative drivers
- Research/experimentation
- Known special cases
- Bug investigation

**How to override**:
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11 --force
```

**Requirements when overriding**:
- Document reason in logs
- Accept quality trade-offs
- Still must pass format validation

---

## Error Handling

### Validation Failure

**If SF2 format validation fails**:
1. Log detailed error
2. Reject conversion
3. Try alternate driver (if applicable)
4. Report to user
5. Manual investigation required

### Player Identification Failure

**If player type cannot be identified**:
1. Default to Driver 11 (safe)
2. Log as "Unknown - using Driver 11"
3. Warn user about potential quality issues
4. Still validate format
5. Suggest adding pattern to database

### Driver Not Available

**If selected driver file missing**:
1. Log error
2. Fall back to Driver 11
3. Warn user about quality impact
4. Document fallback in info file

---

## Compliance

### Mandatory Compliance

This policy is **MANDATORY** for:
- ✅ All automated conversions
- ✅ Production conversions
- ✅ Batch processing
- ✅ Quality assurance
- ✅ Release builds

### Optional Compliance

Policy can be **relaxed** for:
- Development/testing (with --skip-validation)
- Expert manual overrides (with --force)
- Research experiments (documented)

---

## Metrics & Reporting

### Track and Report

**Per Conversion**:
- Player type identified
- Driver selected
- Expected accuracy
- Actual file size
- Validation result
- Conversion time

**Batch Summary**:
```
Batch Conversion Report
=======================
Total files:          100
Success:              98 (98%)
Failed:               2 (2%)

Driver Usage:
  Laxity Driver:      45 files (99.93% avg accuracy)
  Driver 11:          50 files
  NP20:               3 files

Validation:
  Passed:             98 files (98%)
  Failed:             2 files (2%)

Average accuracy:     97.8%
Average time/file:    0.9 seconds
```

---

## References

- **Driver Documentation**: `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md`
- **SF2 Format**: `docs/SF2_FORMAT_SPEC.md`
- **Validation Guide**: `docs/guides/VALIDATION_GUIDE.md`
- **Troubleshooting**: `docs/guides/TROUBLESHOOTING.md`

---

## Version History

### v2.0.0 (2025-12-24) - Quality-First Policy APPROVED
- Approved: Use best driver for each player type
- Mandatory: Document driver selection in output
- Mandatory: SF2 format validation
- Mandatory: Info file generation
- Driver matrix defined
- Validation pipeline specified

### v1.0.0 (2025-12-24) - Initial Draft
- Strict Driver 11 policy (rejected due to quality issues)

---

## Quick Reference Card

### Golden Rules

1. **Quality First**: Use best available driver
2. **Document Everything**: Log driver selection + reason
3. **Validate Always**: SF2 format validation is mandatory
4. **Info Files**: Generate info.txt for every conversion

### Driver Selection

- Laxity files → **Laxity driver** (99.93%)
- SF2-exported → **Driver 11** (100%)
- NewPlayer 20.G4 → **NP20** (70-90%)
- Others → **Driver 11** (safe default)

### Required Output

- ✅ SF2 file (validated)
- ✅ info.txt (driver documentation)
- ✅ conversion.log (detailed log)
- ✅ Console output (summary)

---

**Policy Status**: ✅ **APPROVED & ACTIVE**
**Enforcement**: Automated (pipeline integration)
**Review Date**: Quarterly or as needed
