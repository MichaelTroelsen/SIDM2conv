# SIDM2 Conversion Policy & Quality Standards

**Version**: 1.0.0
**Date**: 2025-12-24
**Status**: 🎯 **MANDATORY** - All conversions must follow this policy

---

## Core Conversion Policy

### Target Player: SF2 Driver 11 (Default)

**Rule**: All SID ↔ SF2 conversions MUST use **SF2 Driver 11** as the default target player.

**Rationale**:
- ✅ **Maximum compatibility** with SID Factory II Editor
- ✅ **100% accuracy** for SF2-exported SIDs
- ✅ **Universal support** - works with all SF2 editor features
- ✅ **Proven stability** - industry-standard driver

### Exception: NewPlayer 20.G4 Files

**Rule**: Files identified as **NewPlayer 20.G4** MUST use the **NP20 driver** instead.

**Identification**:
- Use player-id.exe or pattern matcher
- Check for "NewPlayer_20" or "NP20" or "20.G4" in player detection
- Manual override allowed with `--driver np20` flag

**Rationale**:
- NewPlayer 20.G4 has specific format requirements
- NP20 driver optimized for this player type
- Driver 11 may not preserve all NP20-specific features

---

## Mandatory Validation Step

### SF2 Editor Load Test (Required)

**Rule**: ALL generated SF2 files MUST be validated by successfully loading them into SID Factory II Editor.

**Implementation**: Add validation step to conversion pipeline:

```
┌─────────────────┐
│  SID Input      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Convert to SF2 │  ◄── Use Driver 11 (or NP20 if exception)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SF2 Generated  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ VALIDATION:     │  ◄── MANDATORY STEP
│ Load in SF2     │
│ Editor          │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌──────┐
│SUCCESS│ │FAILED│
└───────┘ └──────┘
    │         │
    │         └──► Report error, reject conversion
    │
    └──► Accept conversion, continue pipeline
```

**Validation Criteria**:
- ✅ SF2 file loads without errors
- ✅ Editor can parse all metadata blocks
- ✅ All sequences, instruments, tables accessible
- ✅ No corruption detected

**Failure Handling**:
- ❌ If validation fails → **REJECT conversion**
- 📝 Log error details
- 🔄 Attempt re-conversion with alternate driver (if applicable)
- 🚨 Alert user to manual review

---

## Conversion Workflows

### Workflow 1: SID → SF2 (Standard)

```bash
# Input: original.sid
# Output: output.sf2
# Driver: SF2 Driver 11 (default)

python scripts/sid_to_sf2.py original.sid output.sf2 --driver driver11

# Validation (automatic in pipeline)
python scripts/validate_sf2_editor.py output.sf2

# Result: output.sf2 (validated, ready for editing)
```

**Steps**:
1. Parse SID file (header, code, data)
2. Identify player type (player-id.exe or pattern matcher)
3. Select driver:
   - If NewPlayer 20.G4 → Use NP20 driver
   - Otherwise → Use Driver 11
4. Convert to SF2 format
5. **VALIDATE**: Load in SF2 Editor (mandatory)
6. If validation passes → Success
7. If validation fails → Reject, log error

### Workflow 2: SF2 → SID (Roundtrip)

```bash
# Input: edited.sf2
# Output: exported.sid
# Driver: SF2 Driver 11 (must match original conversion)

python scripts/sf2_to_sid.py edited.sf2 exported.sid --driver driver11

# Validation (automatic in pipeline)
python scripts/validate_sf2_editor.py edited.sf2  # Pre-export validation
python scripts/validate_sid_accuracy.py original.sid exported.sid  # Accuracy validation
```

**Steps**:
1. Parse SF2 file
2. Extract driver type from SF2 metadata
3. Pack to SID format using same driver
4. **VALIDATE**: Accuracy comparison (if original available)
5. If validation passes → Success
6. If validation fails → Reject, log error

### Workflow 3: NewPlayer 20.G4 Exception

```bash
# Input: np20_file.sid (detected as NewPlayer 20.G4)
# Output: output.sf2
# Driver: NP20 (exception to default rule)

python scripts/sid_to_sf2.py np20_file.sid output.sf2 --driver np20

# Validation (automatic in pipeline)
python scripts/validate_sf2_editor.py output.sf2

# Result: output.sf2 (uses NP20 driver, validated)
```

**Steps**:
1. Parse SID file
2. Identify player type → **NewPlayer 20.G4**
3. **Exception triggered** → Use NP20 driver
4. Convert to SF2 format
5. **VALIDATE**: Load in SF2 Editor (mandatory)
6. If validation passes → Success
7. If validation fails → Reject, try Driver 11 as fallback

---

## Quality Standards

### Driver Selection Matrix

| Input Player Type | Target SF2 Driver | Rationale |
|-------------------|-------------------|-----------|
| **Laxity NewPlayer v21** | Driver 11 | Maximum compatibility |
| **Rob Hubbard** | Driver 11 | Standard conversion |
| **Martin Galway** | Driver 11 | Standard conversion |
| **JCH NewPlayer** | Driver 11 | Standard conversion |
| **Soundmonitor** | Driver 11 | Standard conversion |
| **NewPlayer 20.G4** | **NP20** | **EXCEPTION** - Specific format |
| **SF2-exported SID** | Driver 11 | Preserve original driver |
| **Unknown/Generic** | Driver 11 | Safe default |

### Validation Requirements

**Pre-Conversion Validation**:
- ✅ Valid SID file format (PSID/RSID)
- ✅ Player type identified (or use default)
- ✅ File integrity check (no corruption)

**Post-Conversion Validation** (MANDATORY):
- ✅ SF2 file generated successfully
- ✅ SF2 loads in SID Factory II Editor
- ✅ All metadata blocks present
- ✅ Sequences, instruments, tables accessible
- ✅ No parser errors or warnings

**Accuracy Validation** (Recommended for roundtrip):
- ✅ Frame-by-frame SID register comparison
- ✅ Frequency table validation
- ✅ Waveform/ADSR/pulse validation
- ✅ 95%+ accuracy threshold

---

## Implementation Checklist

### Phase 1: SF2 Editor Validation Tool ✅

- [x] Create `validate_sf2_editor.py` script
- [x] Implement SF2 file loading test
- [x] Implement metadata parsing validation
- [x] Implement error detection and reporting
- [x] Create batch validation mode

### Phase 2: Pipeline Integration

- [ ] Update `sid_to_sf2.py` to include validation step
- [ ] Update `sf2_to_sid.py` to include validation step
- [ ] Add `--skip-validation` flag for advanced users
- [ ] Add validation results to conversion logs
- [ ] Update batch conversion scripts

### Phase 3: Driver Selection Logic

- [ ] Implement automatic driver selection based on player type
- [ ] Add NewPlayer 20.G4 detection
- [ ] Add driver override warnings
- [ ] Update CLI help text with policy
- [ ] Add policy enforcement in conversion scripts

### Phase 4: Documentation

- [x] Create CONVERSION_POLICY.md (this document)
- [ ] Update README.md with policy reference
- [ ] Update user guides with validation requirements
- [ ] Create troubleshooting guide for validation failures
- [ ] Add policy to CLAUDE.md

### Phase 5: Testing

- [ ] Test Driver 11 conversions on all player types
- [ ] Test NP20 conversions on NewPlayer 20.G4 files
- [ ] Test SF2 Editor validation on 100+ files
- [ ] Measure validation success rate
- [ ] Document common validation failures

---

## Validation Script Specification

### SF2 Editor Validation Script

**File**: `scripts/validate_sf2_editor.py`

**Purpose**: Test if SF2 file can be loaded successfully in SID Factory II Editor

**Usage**:
```bash
# Single file validation
python scripts/validate_sf2_editor.py output.sf2

# Batch validation
python scripts/validate_sf2_editor.py --batch output/*.sf2

# Detailed mode (show all metadata)
python scripts/validate_sf2_editor.py output.sf2 --verbose
```

**Validation Steps**:
1. Check file exists and is readable
2. Verify SF2 file format (PRG header)
3. Parse all SF2 metadata blocks
4. Validate sequence data integrity
5. Validate instrument table structure
6. Validate wave/pulse/filter tables
7. Check for corruption or truncation
8. Report success or failure with details

**Exit Codes**:
- `0` = Validation passed (SF2 loads successfully)
- `1` = Validation failed (SF2 corrupted or invalid)
- `2` = File not found or unreadable
- `3` = Invalid SF2 format

**Output**:
```
Validating: output.sf2
✓ File format: Valid PRG
✓ Metadata blocks: 5 blocks parsed
✓ Sequences: 3 sequences (256 bytes)
✓ Instruments: 32 entries (256 bytes)
✓ Wave table: 128 entries (256 bytes)
✓ Pulse table: Present (256 bytes)
✓ Filter table: Present (256 bytes)
✓ No corruption detected

RESULT: PASS - SF2 file is valid and loadable
```

---

## Error Handling

### Validation Failure Scenarios

**Scenario 1: SF2 File Corrupted**

**Symptom**: SF2 file generates but fails validation

**Action**:
1. Re-run conversion with `--verbose` flag
2. Check conversion logs for errors
3. Verify input SID file is valid
4. Try alternate driver (Driver 11 ↔ NP20)
5. Report bug if reproducible

**Scenario 2: Driver Mismatch**

**Symptom**: Conversion succeeds but SF2 Editor can't parse

**Action**:
1. Check player type detection
2. Verify correct driver selected
3. For NewPlayer 20.G4 → Use NP20 driver
4. For all others → Use Driver 11
5. Manual override: `--driver driver11` or `--driver np20`

**Scenario 3: Unsupported Player Type**

**Symptom**: Player type not in supported list

**Action**:
1. Use Driver 11 as safe default
2. Test validation
3. If fails → Manual conversion required
4. Add player type to pattern database
5. Update driver selection matrix

---

## Enforcement

### Mandatory Compliance

**This policy is MANDATORY for**:
- All automated conversions (batch processing)
- Production conversions (releases)
- Roundtrip conversions (SF2 → SID → SF2)
- Quality assurance testing

**Exceptions Allowed for**:
- Development/testing (with `--skip-validation` flag)
- Manual expert conversions (user override)
- Experimental driver testing (research purposes)

**Warning**: Skipping validation may result in:
- ❌ Incompatible SF2 files
- ❌ Corrupted data
- ❌ SF2 Editor load failures
- ❌ Lost work if file can't be edited

---

## Metrics & Reporting

### Quality Metrics

**Track and report**:
- Conversion success rate (%)
- Validation success rate (%)
- Driver selection accuracy (%)
- Average conversion time
- File size distribution
- Accuracy scores (for roundtrip)

**Example Report**:
```
Conversion Batch Report
=======================
Total files:           100
Conversions succeeded: 98 (98%)
Validations passed:    96 (96%)
Validations failed:    2 (2%)

Driver Selection:
  Driver 11:          95 files (95%)
  NP20:               3 files (3%)
  Manual override:    2 files (2%)

Average accuracy:     98.5%
Average file size:    12.3 KB
Average time/file:    0.8 seconds
```

---

## Revision History

### v1.0.0 (2025-12-24)
- Initial policy document
- Defined Driver 11 as default target
- Defined NewPlayer 20.G4 exception (NP20)
- Specified mandatory SF2 Editor validation
- Created validation workflow
- Defined quality standards

---

## References

- **SF2 Format Specification**: `docs/SF2_FORMAT_SPEC.md`
- **Driver Documentation**: `docs/reference/DRIVERS_REFERENCE.md`
- **Validation Guide**: `docs/guides/VALIDATION_GUIDE.md`
- **Troubleshooting**: `docs/guides/TROUBLESHOOTING.md`

---

## Quick Reference

### Golden Rules

1. **Default Driver**: Always use **Driver 11** unless exception applies
2. **Exception**: Use **NP20** only for NewPlayer 20.G4 files
3. **Validation**: ALWAYS validate SF2 files in SF2 Editor
4. **No Exceptions**: Validation is mandatory for production conversions

### Quick Commands

```bash
# Standard conversion (Driver 11)
python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11
python scripts/validate_sf2_editor.py output.sf2

# NewPlayer 20.G4 exception (NP20)
python scripts/sid_to_sf2.py np20file.sid output.sf2 --driver np20
python scripts/validate_sf2_editor.py output.sf2

# Batch conversion with validation
python scripts/batch_convert.py --dir SIDs/ --validate --driver driver11
```

---

**Policy Owner**: SIDM2 Project Team
**Enforcement**: Automated (pipeline integration) + Manual code review
**Review Cycle**: Quarterly or as needed
**Status**: 🎯 ACTIVE & MANDATORY
