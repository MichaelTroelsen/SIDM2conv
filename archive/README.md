# Archive Directory

This directory contains experimental code and documentation from the development process that is no longer needed for daily use but preserved for historical reference.

## Contents

### `experiments/` - Experimental Python Scripts

Contains 40+ experimental scripts created during the development of the SF2 conversion pipeline:

**Sequence Extraction Research**:
- Various approaches to extracting sequences from packed SID files
- Pattern detection algorithms
- Orderlist analysis scripts
- Sequence validation and verification tools

**SF2 Format Reverse Engineering**:
- Scripts for analyzing SF2 file structure
- Memory region dumping and comparison
- Table extraction prototypes
- Format understanding utilities

**Siddump Integration Experiments**:
- Siddump output parsing prototypes
- Trace data analysis
- Register write capture experiments

**File Categories**:
- `analyze_*.py` - Analysis and investigation scripts
- `extract_*.py` - Table and sequence extraction experiments
- `find_*.py` - Search and pattern detection scripts
- `inject_*.py` - Data injection prototypes
- `parse_*.py` - Parsing experiments
- Other utility scripts

### `old_docs/` - Historical Documentation

Contains documentation from various stages of development:

**Status Reports**:
- `SEQUENCE_EXTRACTION_STATE.md` - Sequence extraction progress
- `STINSEN_CONVERSION_STATUS.md` - Stinsen file conversion investigation
- `FINAL_STATUS_AND_RECOMMENDATIONS.md` - Summary of findings
- `NEXT_STEPS.md` - Development roadmap (superseded by CHANGELOG.md)

**Technical Investigations**:
- `SF2_FORMAT_SOLVED.md` - SF2 format discoveries
- `SIDDUMP_EXTRACTION_SUCCESS.md` - Siddump integration experiments
- `SIDDUMP_TRACE_STATUS.md` - SIDwinder trace investigation
- `RETRODEBUGGER_SEQUENCE_INVESTIGATION.md` - Debugging notes
- `understand_player_architecture.md` - Player code analysis

**Reconstruction Research**:
- `COMPLETE_SF2_RECONSTRUCTION_SUMMARY.md` - Full reconstruction approach
- `FINAL_UNDERSTANDING.md` - Format understanding summary
- `SEQUENCE_INVESTIGATION_SUMMARY.md` - Sequence research summary
- `SEQUENCE_EXTRACTION_FINAL_REPORT.md` - Final extraction report

**Test/Verification Files**:
- `reference_validation.txt` - Reference file validation
- `stinsens_pipeline_verification.txt` - Pipeline tests
- `test_direct_verification.txt` - Direct testing results
- `test_pipeline_integration_verification.txt` - Integration tests
- `sequences_extracted.txt` - Extracted sequence data
- `pipeline_run.log` - Pipeline execution logs

## Why Archived?

These files were moved to the archive on **2025-12-10** for the following reasons:

1. **Experiments Completed**: The research phase is complete, and the final implementations are in the main codebase
2. **Documentation Superseded**: Newer, consolidated documentation exists (CHANGELOG.md, SIDDUMP_INTEGRATION_SUMMARY.md, etc.)
3. **Cleaner Repository**: Reduces clutter in the main directory for easier navigation
4. **Historical Reference**: Preserved for understanding the development process and decision-making

## Current Active Files

The main project now uses these clean, production-ready files:

**Core Pipeline**:
- `complete_pipeline_with_validation.py` - Main 11-step conversion pipeline
- `sidm2/siddump_extractor.py` - Production siddump integration
- `sidm2/sf2_packer.py` - SF2 to SID packer

**Utilities**:
- `validate_sf2.py` - SF2 structure validation
- `update_inventory.py` - File inventory management

**Documentation**:
- `README.md` - Main project documentation
- `CLAUDE.md` - AI assistant guide
- `CHANGELOG.md` - Version history and changes
- `SIDDUMP_INTEGRATION_SUMMARY.md` - Latest integration work
- `SF2_VALIDATION_STATUS.md` - Current validation status

## Accessing Archived Content

If you need to reference the experimental code or old documentation:

```bash
# View experiments
cd archive/experiments
ls *.py

# View old documentation
cd archive/old_docs
ls *.md
```

## Note

These files are **not maintained** and may contain outdated information or non-functional code. They are preserved only for historical and reference purposes. For current, working code, always use the files in the main project directory.

---

*Archived: 2025-12-10*
*Total Files: 40+ scripts, 19 documentation files*
