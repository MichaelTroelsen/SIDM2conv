# Python Cleanup Archive - 2025-12-21

**Archive Date**: 2025-12-21
**Total Files Archived**: 68 Python files
**Reason**: Implementation artifacts, development scripts, and superseded tools

---

## Summary

This archive contains 68 Python files that were removed from active use in the repository. All files have been preserved with complete git history using `git mv`.

### Files by Category

| Category | Files | Location |
|----------|-------|----------|
| **Laxity Implementation** | 12 | scripts_implementation/ |
| **Old Validation** | 7 | scripts_validation_old/ |
| **Old Tests** | 6 | scripts_tests_old/ |
| **Specific Analysis** | 7 | scripts_analysis_specific/ |
| **Old Inventory** | 3 | scripts_inventory_old/ |
| **Old Extraction** | 2 | scripts_extraction_old/ |
| **Old CI** | 1 | scripts_ci_old/ |
| **Old Conversions** | 1 | scripts_conversions_old/ |
| **Collections** | 1 | scripts_collections/ |
| **SF2 Viewer Dev** | 9 | pyscript_sf2_viewer_dev/ |
| **Export Dev** | 2 | pyscript_export_dev/ |
| **Pipeline Experiments** | 4 | pyscript_pipeline_experiments/ |
| **Laxity Dev** | 8 | pyscript_laxity_dev/ |
| **Analysis Debug** | 4 | pyscript_analysis_debug/ |
| **Total** | **68** | |

---

## Category Details

### scripts_implementation/ (12 files)

**Laxity Phase Tests (v1.8.0)** - 7 files:
- test_phase1_foundation.py - Phase 1 implementation tests
- test_phase2_memory_analysis.py - Phase 2 implementation tests
- test_phase3_table_extraction.py - Phase 3 implementation tests
- test_phase4_table_injection.py - Phase 4 implementation tests
- test_phase6_conversion_integration.py - Phase 6 implementation tests
- batch_test_laxity_driver.py - Batch Laxity driver testing
- batch_test_laxity_driver_parallel.py - Parallel batch testing

**Laxity Tools** - 5 files:
- extract_laxity_player.py - Laxity player extraction (Phase 1)
- design_laxity_sf2_header.py - Header design (Phase 2)
- relocate_laxity_player.py - Code relocation (Phase 3)
- analyze_laxity_relocation.py - Relocation analysis
- generate_sf2_header.py - SF2 header generation

**Reason**: Laxity driver v1.8.0 implementation is complete and validated on 286 files. These phase test scripts and implementation tools are no longer needed for active development.

---

### scripts_validation_old/ (7 files)

**Pre-v1.4 Validation Scripts**:
- validate_conversion.py - Old validation (superseded by validate_sid_accuracy.py)
- validate_psid.py - PSID validation (specific use case)
- validate_structure.py - Structure validation (specific)
- comprehensive_validate.py - Old comprehensive validation (superseded)
- batch_validate_sidsf2player.py - SIDSF2player batch validation (specific)
- test_table_validation.py - Table validation tests
- test_extraction_validator.py - Extraction validator tests

**Reason**: Validation system v1.4 introduced a comprehensive validation framework with dashboard, regression tracking, and CI/CD integration. These older validation scripts have been superseded.

---

### scripts_tests_old/ (6 files)

**Superseded Test Scripts**:
- test_config.py - Config testing
- test_sf2_editor.py - SF2 editor testing
- test_sf2_player_parser.py - SF2 player parser testing
- test_sf2_compatibility.py - Compatibility testing
- test_memory_overlap.py - Memory overlap testing
- test_all_musical_content.py - Musical content testing (superseded by compare_musical_content.py)

**Reason**: These test scripts were used during early development and have been superseded by the comprehensive test suite (test_converter.py, test_sf2_format.py, test_complete_pipeline.py).

---

### scripts_analysis_specific/ (7 files)

**One-off Analysis Tools**:
- analyze_midi_diff.py - MIDI diff analysis (specific)
- analyze_sid_collections.py - SID collection analysis (specific)
- parse_analysis_reports.py - Report parsing (specific)
- laxity_parser.py - Laxity parser (superseded by sidm2/laxity_parser.py)
- format_tables.py - Table formatting (utility)
- trace_orderlist_access.py - Orderlist tracing (debugging)
- generate_driver_analysis.py - Driver analysis generation

**Reason**: These were specific analysis tools used for one-off investigations. The functionality has been integrated into core tools or is no longer needed.

---

### scripts_inventory_old/ (3 files)

**Old Inventory Scripts**:
- create_detailed_inventory.py - Detailed inventory (superseded)
- create_enhanced_collection_inventory.py - Enhanced collection inventory
- create_collection_grid_inventory.py - Grid inventory

**Reason**: Superseded by `pyscript/update_inventory.py` which generates the official FILE_INVENTORY.md.

---

### scripts_extraction_old/ (2 files)

**Old Extraction Tools**:
- extract_sf2_properly.py - SF2 extraction (old method)
- generate_info.py - Info generation (superseded by pipeline)

**Reason**: Extraction functionality integrated into main conversion pipeline.

---

### scripts_ci_old/ (1 file)

**Local CI Testing**:
- ci_local.py - Local CI testing

**Reason**: Superseded by GitHub Actions workflow (.github/workflows/validation.yml) which runs automated validation on every PR and push.

---

### scripts_conversions_old/ (1 file)

**Old Conversion Scripts**:
- convert_all_sidsf2player.py - SIDSF2player batch conversion

**Reason**: Specific conversion script for SIDSF2player test data. Functionality covered by convert_all.py.

---

### scripts_collections/ (1 file)

**Collection-Specific Converters**:
- convert_galway_collection.py - Galway-specific batch conversion

**Reason**: Collection-specific converter. General batch conversion covered by convert_all.py.

---

### pyscript_sf2_viewer_dev/ (9 files)

**SF2 Viewer Development (v2.0-v2.2)**:
- verify_gui_display.py - GUI display verification
- display_sequences.py - Sequence display testing
- run_viewer.py - Viewer runner (superseded by launch_sf2_viewer.py)
- run_viewer_with_log.py - Viewer with logging (debugging)
- launch_with_laxity_file.py - Laxity file launcher
- test_track_view_parity.py - Track view parity testing
- compare_track3_v2.py - Track 3 comparison v2
- compare_track3_flexible.py - Track 3 flexible comparison
- search_for_sequence.py - Sequence search tool (debugging)

**Reason**: SF2 Viewer v2.2 is complete with single-track sequence support. These development and debugging scripts are no longer needed.

---

### pyscript_export_dev/ (2 files)

**Text Export Development (v2.2)**:
- combine_sf2_export.py - SF2 export combination
- combine_export.py - Export combination

**Reason**: Text exporter v2.2 is complete. Development scripts archived.

---

### pyscript_pipeline_experiments/ (4 files)

**Performance Testing**:
- pipeline_with_timings.py - Pipeline with timing tracking
- parallel_galway_pipeline.py - Parallel Galway pipeline
- generate_galway_timing_report.py - Galway timing reports
- aggregate_galway_timings.py - Galway timing aggregation

**Reason**: Performance experiments for pipeline optimization. Results documented, experiments complete.

---

### pyscript_laxity_dev/ (8 files)

**Laxity Driver Development (v1.8.0)**:
- test_laxity_accuracy.py - Laxity accuracy testing (superseded by pipeline)
- convert_all_laxity.py - Laxity batch conversion (superseded by sid_to_sf2.py --driver laxity)
- build_laxity_driver_with_headers.py - Driver building with headers
- analyze_driver_headers.py - Driver header analysis
- investigate_entry_stubs.py - Entry stub investigation
- analyze_sf2_layout.py - SF2 layout analysis
- trace_scanning.py - Trace scanning
- analyze_broware_structure.py - Broware structure analysis

**Reason**: Laxity driver v1.8.0 is production-ready with 99.93% accuracy. Development and analysis scripts archived.

---

### pyscript_analysis_debug/ (4 files)

**Analysis and Debugging**:
- analyze_raw_bytes.py - Raw byte analysis (debugging)
- validate_sf2.py - SF2 validation (old)
- cleanup_md_files.py - MD file cleanup (superseded by cleanup.py)
- check_pulse_data.py - Pulse data checking (specific)

**Reason**: Debugging and analysis tools used during development. Functionality integrated or no longer needed.

---

## Restoration

If you need to restore any of these files:

```bash
# Restore a specific file
git mv archive/python_cleanup_2025-12-21/scripts_implementation/test_phase1_foundation.py scripts/

# Restore an entire category
git mv archive/python_cleanup_2025-12-21/scripts_implementation/* scripts/
```

---

## Benefits of Archiving

**Before**:
- 252 Python files total
- 65 files in scripts/ (confusing mix)
- 37 files in pyscript/ (confusing mix)
- Difficult to identify core utilities

**After**:
- 81 actively used Python files
- 20 core scripts (essential tools only)
- 8 core pyscript (maintenance + SF2 Viewer)
- Clear organization and easy navigation

---

## Archive Structure

```
archive/python_cleanup_2025-12-21/
├── scripts_implementation/          # 12 files - Laxity implementation
├── scripts_validation_old/          # 7 files - Pre-v1.4 validation
├── scripts_tests_old/               # 6 files - Superseded tests
├── scripts_analysis_specific/       # 7 files - Specific analysis
├── scripts_inventory_old/           # 3 files - Old inventory tools
├── scripts_extraction_old/          # 2 files - Old extraction
├── scripts_ci_old/                  # 1 file - Local CI
├── scripts_conversions_old/         # 1 file - Old conversions
├── scripts_collections/             # 1 file - Collection-specific
├── pyscript_sf2_viewer_dev/         # 9 files - SF2 Viewer dev
├── pyscript_export_dev/             # 2 files - Export dev
├── pyscript_pipeline_experiments/   # 4 files - Performance tests
├── pyscript_laxity_dev/             # 8 files - Laxity dev
├── pyscript_analysis_debug/         # 4 files - Debugging
└── README.md                        # This file
```

---

## Related Documentation

- **PYTHON_FILE_ANALYSIS.md** - Complete analysis report
- **FILE_INVENTORY.md** - Current repository structure
- **CHANGELOG.md** - Version history

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

**Archive Date**: 2025-12-21
**Total Files**: 68
**Preserved**: All files moved with `git mv` (history intact)
