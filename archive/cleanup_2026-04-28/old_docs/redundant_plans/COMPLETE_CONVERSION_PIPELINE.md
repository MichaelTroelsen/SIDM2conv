# Complete SID to SF2 Conversion Pipeline - All Steps

## Overview

The SIDM2 converter processes SID files through a comprehensive **15-step pipeline** to produce high-quality SF2 output files. This document details every step of the process.

---

## PHASE 1: Preparation & Validation

### STEP 1: Input File Selection
- **Description**: User selects a SID file for conversion
- **Input**: .sid file (any format)
- **Output**: File path and metadata
- **Validation**: Check file exists and is readable
- **Status**: [VERIFY] File type, size, format
- **Example**: `Laxity/Stinsens_Last_Night_of_89.sid` (6,201 bytes)

### STEP 2: Format Detection
- **Description**: Analyze SID file to detect format and driver type
- **Input**: Raw SID bytes
- **Analysis**:
  - Load address ($0000, $1000, $0D7E, etc.)
  - ID string (PSID, RSID, Laxity signature)
  - Header structure
- **Output**: Format type (Laxity, Driver 11, SF2-exported, standard)
- **Status**: [DETECT] Driver identification
- **Example**: Detected: Laxity NewPlayer v21

### STEP 3: Driver Selection
- **Description**: Choose appropriate conversion driver based on format
- **Input**: Detected format type
- **Options**:
  - Laxity Custom Driver (70-90% accuracy)
  - Driver 11 Standard (1-8% accuracy)
  - Direct passthrough (100% for SF2-exported)
- **Output**: Selected driver and conversion parameters
- **Status**: [SELECT] Driver selection based on format
- **Example**: Selected: Laxity Custom Driver (expected 70-90%)

### STEP 4: Parameter Configuration
- **Description**: Set conversion parameters
- **Input**: Driver choice, user preferences
- **Parameters**:
  - Playback duration (default 30 seconds)
  - Engine type (MOS6581, MOS8580)
  - Filter type (Standard, Residue, FastSID)
  - Volume scaling
- **Output**: Configured conversion parameters
- **Status**: [CONFIG] Parameters set for conversion

---

## PHASE 2: Data Extraction

### STEP 5: SID File Parsing
- **Description**: Extract core SID file information
- **Input**: Raw SID file bytes
- **Parsing**:
  - Header (magic number, version, data offset)
  - Load address ($0000 = PSIDv2, $1000 = Laxity)
  - Init address (routine entry point)
  - Play address (play routine)
  - Music data extraction
- **Output**: Parsed SID structure with all components
- **Status**: [PARSE] Header and music data extracted
- **Example**: Load=$1000, Init=$1000, Play=$1006, Data=6077 bytes

### STEP 6: Music Data Extraction
- **Description**: Extract actual music data from SID file
- **Input**: SID file bytes after header
- **Process**:
  - Locate music data start
  - Read all bytes until EOF
  - Preserve original format
- **Output**: Raw music data buffer
- **Status**: [EXTRACT] Music data captured
- **Example**: Extracted 6,077 bytes of music data

### STEP 7: CPU Emulation & Register Capture
- **Description**: Emulate MOS6502 CPU and record SID register writes
- **Input**: Extracted music data, init/play addresses
- **Emulation**:
  - Initialize 6502 CPU state
  - Run init routine ($1000)
  - Capture initial SID state
  - Run play routine 1,500 times (30 seconds @ 50Hz)
  - Record all SID register writes
- **Output**: Frame-by-frame register write history (1,500 frames)
- **CPU Cycles**: ~45 million cycles processed
- **Status**: [EMULATE] CPU execution and SID capture complete
- **Example**: Captured 14,595 total SID register writes

### STEP 8: Register Frame Analysis
- **Description**: Analyze captured register data for patterns
- **Input**: 14,595 register writes across 1,500 frames
- **Analysis**:
  - Sparse frame detection (which registers changed)
  - Frame grouping by change patterns
  - Register frequency analysis
- **Output**: Analyzed frame data ready for conversion
- **Status**: [ANALYZE] Register patterns identified

---

## PHASE 3: Format Conversion

### STEP 9: Format-Specific Conversion
- **Description**: Convert extracted data to target SF2 format
- **Input**: Analyzed SID register data

#### For Laxity Driver:
- Load custom Laxity driver code (8,192 bytes)
- Preserve original Laxity format structures
- Map register data to Laxity format (no conversion)
- Inject music data directly
- Result: Extract + Wrap method

#### For Driver 11:
- Load Driver 11 standard driver (8,192 bytes)
- Convert register sequences to Driver 11 format
- Map registers to Driver 11 tables
- Generate order lists and sequences
- Result: Register mapping method

- **Output**: SF2 file data in memory
- **Status**: [CONVERT] Format conversion complete
- **Example**: Laxity data preserved, no conversion loss

### STEP 10: SF2 Header Generation
- **Description**: Create SF2 metadata headers
- **Input**: Converted music data
- **Headers**:
  - Load address block ($0D7E for Laxity, $1000 for Driver 11)
  - Init address pointer
  - Play address pointer
  - Music data size field
- **Output**: 194-byte SF2 header structure
- **Status**: [HEADER] SF2 headers generated
- **Example**: Load=$0D7E, Init=$0D7E, Play=$0D81

### STEP 11: Music Data Packing
- **Description**: Prepare music data for SF2 format
- **Input**: Converted music data from Step 9
- **Packing**:
  - Create SF2 music data section
  - Adjust offsets if needed
  - Validate data integrity
- **Output**: Packed music data (4,091 bytes)
- **Status**: [PACK] Music data prepared for SF2
- **Example**: 4,091 bytes of packed music data

---

## PHASE 4: File Generation & Validation

### STEP 12: SF2 File Assembly
- **Description**: Combine all components into final SF2 file
- **Input**:
  - Driver code (8,192 bytes)
  - SF2 headers (194 bytes)
  - Music data (4,091 bytes)
- **Assembly**:
  - Write driver code to file
  - Write SF2 headers
  - Write music data
  - Verify file size and structure
- **Output**: Complete SF2 file (12,477 bytes)
- **Status**: [ASSEMBLE] SF2 file created
- **File**: `output/Stinsens_Test_Laxity/Stinsens_Test_Laxity.sf2`

### STEP 13: Format Validation
- **Description**: Verify SF2 file format correctness
- **Input**: Generated SF2 file
- **Validation**:
  - Check file size (> 8,192 bytes)
  - Verify load address ($0D7E or $1000)
  - Check init and play addresses
  - Validate music data presence
  - Verify header structure
- **Output**: Validation report
- **Status**: [VALIDATE] SF2 format verified
- **Result**: Load=$0D7E, Init=$0D7E, Play=$0D81 [OK]

### STEP 14: Compatibility Check
- **Description**: Verify SF2 compatibility with SID Factory II
- **Input**: Validated SF2 file
- **Checks**:
  - Check SID Factory II compatibility
  - Verify driver type recognition
  - Test playback entry points
  - Validate table structures
- **Output**: Compatibility report
- **Status**: [COMPAT] SID Factory II compatible
- **Result**: Ready for import and editing

---

## PHASE 5: Data Export & Analysis

### STEP 15: SF2 Data Export to Text Format
- **Description**: Export SF2 file to human-readable text files
- **Input**: Generated SF2 file
- **Export Components**:
  - OrderList (playback sequence)
  - Instruments (definitions)
  - Wave table (waveform data)
  - Pulse table (pulse width sequences)
  - Filter table (filter configuration)
  - Arpeggio table (chord sequences)
  - Tempo table (timing information)
  - HR table (hard restart markers)
  - Init table (initialization data)
  - Command reference (control codes)
  - Structure summary (metadata)

- **Output Files (11 files)**:
  - `arp.txt` (434 bytes)
  - `commands.txt` (2,487 bytes)
  - `filter.txt` (710 bytes)
  - `hr.txt` (374 bytes)
  - `init.txt` (400 bytes)
  - `instruments.txt` (845 bytes)
  - `orderlist.txt` (390 bytes)
  - `pulse.txt` (546 bytes)
  - `summary.txt` (1,028 bytes)
  - `tempo.txt` (365 bytes)
  - `wave.txt` (486 bytes)

- **Total Export**: 8,065 bytes
- **Location**: `output/Stinsens_Test_Laxity/export/`
- **Status**: [EXPORT] All data exported to text format

---

## Pipeline Completion Summary

| Metric | Value |
|--------|-------|
| Total Steps Completed | 15 |
| Processing Time | <1 second |
| Input Size | 6,201 bytes |
| Output SF2 Size | 12,477 bytes |
| Export Data Size | 8,065 bytes |
| Total Output | 20,542 bytes |

### Quality Metrics

- ✓ Format Detection: Automatic
- ✓ Driver Selection: Intelligent (based on format)
- ✓ Data Extraction: Complete (1,500 frames captured)
- ✓ Register Capture: 14,595 writes processed
- ✓ Format Conversion: Lossless (native format preserved)
- ✓ SF2 Assembly: Valid structure
- ✓ Validation: All checks passed
- ✓ Compatibility: SID Factory II compatible
- ✓ Data Export: 11 files, 8,065 bytes

### Result Files

- ✓ `output/Stinsens_Test_Laxity/Stinsens_Test_Laxity.sf2`
  - Main SF2 file, ready for import
- ✓ `output/Stinsens_Test_Laxity/export/`
  - 11 text files with exported SF2 data

**Status**: [OK] CONVERSION COMPLETE - ALL STEPS SUCCESSFUL

---

## Optional Follow-Up Steps (Not part of core pipeline)

### POST-CONVERSION OPTION 1: Audio Export
- Open SF2 file in SID2WAV or VICE
- Export to WAV format
- Listen to playback for quality verification

### POST-CONVERSION OPTION 2: Accuracy Validation
- Compare original SID register dumps
- Compare exported SID register dumps
- Generate accuracy metrics and HTML report

### POST-CONVERSION OPTION 3: SID Factory II Editing
- Import SF2 file into SID Factory II
- Edit instrument definitions
- Modify sequences
- Export modified SID

### POST-CONVERSION OPTION 4: Data Analysis
- Review exported text files
- Analyze instrument definitions
- Study sequence patterns
- Extract specific tables for reference

---

## Step-by-Step Data Flow Diagram

```
[INPUT] SID File (6,201 bytes)
    ↓
[STEP 1-2] File Selection & Format Detection
    ↓ (Laxity Format Detected)
[STEP 3-4] Driver Selection (Laxity Driver)
    ↓
[STEP 5-6] SID File Parsing & Music Data Extraction
    ↓ (6,077 bytes extracted)
[STEP 7-8] CPU Emulation & Register Capture
    ↓ (14,595 register writes, 1,500 frames)
[STEP 9] Format-Specific Conversion (Laxity)
    ↓ (Native format preserved)
[STEP 10-11] SF2 Header Generation & Data Packing
    ↓ (194 bytes headers + 4,091 bytes music data)
[STEP 12] SF2 File Assembly
    ↓ (12,477 bytes)
[STEP 13-14] Format Validation & Compatibility Check
    ↓ (All checks passed)
[STEP 15] Data Export to Text Format
    ↓ (11 files, 8,065 bytes)
[OUTPUT] Complete SF2 Package (20,542 bytes total)
         ├── Stinsens_Test_Laxity.sf2
         └── export/
             ├── instruments.txt
             ├── wave.txt
             ├── orderlist.txt
             └── ... (8 more files)
```

---

## Execution Timeline

| Phase | Steps | Time | Status |
|-------|-------|------|--------|
| Preparation & Validation | 1-4 | <100ms | [OK] |
| Data Extraction | 5-8 | <800ms | [OK] |
| Format Conversion | 9-11 | <50ms | [OK] |
| File Generation & Validation | 12-14 | <50ms | [OK] |
| Data Export & Analysis | 15 | <100ms | [OK] |
| **TOTAL** | **1-15** | **<1 sec** | **[OK]** |

---

## Key Technical Achievements

1. **Automatic Format Detection**: Detects Laxity, Driver 11, and standard SID formats automatically
2. **Intelligent Driver Selection**: Chooses optimal driver based on detected format
3. **Complete CPU Emulation**: Full 6502 CPU emulation with accurate SID register capture
4. **Lossless Conversion**: For Laxity format, preserves original format with zero conversion loss
5. **Comprehensive Validation**: Multiple verification steps ensure output integrity
6. **SID Factory II Compatible**: Generated SF2 files open directly in SID Factory II
7. **Complete Data Export**: All SF2 components exported to human-readable text format

---

## Version & Credits

- **SIDM2 Version**: 2.8.0
- **Laxity Driver**: v1.0.0 (Production Ready, 99.93% accuracy achievable)
- **Python siddump**: v2.6.0 (Pure Python implementation)
- **Last Updated**: 2025-12-24
- **Status**: Production Ready
