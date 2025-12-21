# Python File Analysis & Archive Plan

**Generated**: 2025-12-21
**Total Python Files**: 252
**Purpose**: Identify unused files for archiving

---

## Summary

| Category | Count | Action |
|----------|-------|--------|
| **Core Package** (sidm2/) | 52 | ✅ KEEP ALL (official package) |
| **Core Scripts** (scripts/) | 20 | ✅ KEEP (actively used) |
| **Core Tools** (pyscript/) | 8 | ✅ KEEP (maintenance tools) |
| **Archive** (already archived) | 73 | ℹ️ ALREADY ARCHIVED |
| **Temp** (untracked) | 22 | ℹ️ UNTRACKED (cleanup done) |
| **Implementation Scripts** (scripts/) | 39 | 🗄️ ARCHIVE (implementation artifacts) |
| **Experimental Scripts** (pyscript/) | 29 | 🗄️ ARCHIVE (debugging/experiments) |
| **Experiments** | 2 | 🗄️ ARCHIVE |
| **Drivers** | 1 | ✅ KEEP |

**Total to Archive**: 70 files (39 from scripts/ + 29 from pyscript/ + 2 from experiments/)
**Total to Keep**: 81 files (52 + 20 + 8 + 1)
**Already Managed**: 95 files (73 archived + 22 untracked)

---

## Category 1: KEEP - Core Package (52 files)

**Location**: `sidm2/`
**Status**: ✅ **KEEP ALL**
**Reason**: Official Python package - all modules are part of the public API

This is the core package following PEP 8 conventions. All 52 files should be kept.

---

## Category 2: KEEP - Core Scripts (20 files)

**Location**: `scripts/`
**Status**: ✅ **KEEP**
**Reason**: Actively used, documented in README/CLAUDE.md, or part of test suite

### Conversion Scripts (4 files)
- ✅ `sid_to_sf2.py` - Main SID→SF2 converter (CORE)
- ✅ `sf2_to_sid.py` - SF2→SID exporter (CORE)
- ✅ `convert_all.py` - Batch conversion (CORE)
- ✅ `test_roundtrip.py` - Round-trip validation (CORE)

### Validation Scripts (5 files)
- ✅ `validate_sid_accuracy.py` - Frame-by-frame accuracy validation (CORE)
- ✅ `generate_validation_report.py` - Multi-file validation reports (CORE)
- ✅ `run_validation.py` - Validation system runner v1.4 (CORE)
- ✅ `generate_dashboard.py` - Dashboard generator v1.4 (CORE)
- ✅ `analyze_waveforms.py` - Waveform analysis & HTML reports (CORE)

### Analysis Scripts (3 files)
- ✅ `test_midi_comparison.py` - Python MIDI emulator validation (CORE)
- ✅ `compare_musical_content.py` - Musical content validator (CORE)
- ✅ `disassemble_sid.py` - 6502 disassembler (CORE)

### Utility Scripts (2 files)
- ✅ `extract_addresses.py` - Extract data structure addresses (CORE)
- ✅ `update_inventory.py` - File inventory updater (CORE)

### Test Suites (5 files)
- ✅ `test_converter.py` - Main test suite (86 tests) (CORE)
- ✅ `test_sf2_format.py` - SF2 format validation (12 tests) (CORE)
- ✅ `test_complete_pipeline.py` - Pipeline tests (19 tests) (CORE)
- ✅ `test_backward_compatibility.py` - Backward compatibility tests (CORE)
- ✅ `test_laxity_baseline.py` - Laxity baseline tests (CORE)

### Package Init (1 file)
- ✅ `__init__.py` - Package marker (CORE)

---

## Category 3: KEEP - Core Tools (8 files)

**Location**: `pyscript/`
**Status**: ✅ **KEEP**
**Reason**: Active maintenance tools and SF2 Viewer

### Maintenance Tools (4 files)
- ✅ `cleanup.py` - Automated cleanup tool v2.3 (CORE)
- ✅ `update_inventory.py` - File inventory updater (CORE)
- ✅ `new_experiment.py` - Experiment template generator (CORE)
- ✅ `complete_pipeline_with_validation.py` - Main 12-step pipeline (CORE)

### SF2 Viewer (4 files)
- ✅ `sf2_viewer_gui.py` - SF2 Viewer GUI v2.2 (CORE)
- ✅ `sf2_viewer_core.py` - SF2 format parser (CORE)
- ✅ `sf2_visualization_widgets.py` - Visualization widgets (CORE)
- ✅ `sf2_playback.py` - Playback engine (CORE)

---

## Category 4: ARCHIVE - Implementation Scripts (39 files)

**Location**: `scripts/`
**Status**: 🗄️ **ARCHIVE**
**Reason**: Implementation artifacts, phase testing, specific conversions, no longer actively used

### Laxity Phase Tests (6 files) - v1.8.0 Implementation
- 🗄️ `test_phase1_foundation.py` - Phase 1 implementation tests
- 🗄️ `test_phase2_memory_analysis.py` - Phase 2 implementation tests
- 🗄️ `test_phase3_table_extraction.py` - Phase 3 implementation tests
- 🗄️ `test_phase4_table_injection.py` - Phase 4 implementation tests
- 🗄️ `test_phase6_conversion_integration.py` - Phase 6 implementation tests
- 🗄️ `batch_test_laxity_driver.py` - Batch Laxity driver testing
- 🗄️ `batch_test_laxity_driver_parallel.py` - Parallel batch testing

### Laxity Implementation Tools (4 files) - v1.8.0 Development
- 🗄️ `extract_laxity_player.py` - Laxity player extraction (Phase 1)
- 🗄️ `design_laxity_sf2_header.py` - Header design (Phase 2)
- 🗄️ `relocate_laxity_player.py` - Code relocation (Phase 3)
- 🗄️ `analyze_laxity_relocation.py` - Relocation analysis
- 🗄️ `generate_sf2_header.py` - SF2 header generation

### Specific Collections (1 file)
- 🗄️ `convert_galway_collection.py` - Galway-specific batch conversion

### Old Validation Scripts (7 files) - Pre-v1.4
- 🗄️ `validate_conversion.py` - Old validation (superseded by validate_sid_accuracy.py)
- 🗄️ `validate_psid.py` - PSID validation (specific)
- 🗄️ `validate_structure.py` - Structure validation (specific)
- 🗄️ `comprehensive_validate.py` - Old comprehensive validation (superseded)
- 🗄️ `batch_validate_sidsf2player.py` - SIDSF2player batch validation (specific)
- 🗄️ `test_table_validation.py` - Table validation tests
- 🗄️ `test_extraction_validator.py` - Extraction validator tests

### Old Test Scripts (4 files) - Superseded
- 🗄️ `test_config.py` - Config testing
- 🗄️ `test_sf2_editor.py` - SF2 editor testing
- 🗄️ `test_sf2_player_parser.py` - SF2 player parser testing
- 🗄️ `test_sf2_compatibility.py` - Compatibility testing
- 🗄️ `test_memory_overlap.py` - Memory overlap testing
- 🗄️ `test_all_musical_content.py` - Musical content testing (superseded by compare_musical_content.py)

### Analysis Tools (8 files) - Specific/One-off
- 🗄️ `analyze_midi_diff.py` - MIDI diff analysis (specific)
- 🗄️ `analyze_sid_collections.py` - SID collection analysis (specific)
- 🗄️ `parse_analysis_reports.py` - Report parsing (specific)
- 🗄️ `laxity_parser.py` - Laxity parser (superseded by sidm2/laxity_parser.py)
- 🗄️ `format_tables.py` - Table formatting (utility)
- 🗄️ `trace_orderlist_access.py` - Orderlist tracing (debugging)
- 🗄️ `generate_driver_analysis.py` - Driver analysis generation

### Collection Management (3 files) - Specific
- 🗄️ `convert_all_sidsf2player.py` - SIDSF2player batch conversion
- 🗄️ `create_detailed_inventory.py` - Detailed inventory (superseded by update_inventory.py)
- 🗄️ `create_enhanced_collection_inventory.py` - Enhanced collection inventory
- 🗄️ `create_collection_grid_inventory.py` - Grid inventory

### Extraction Tools (2 files) - Old/Specific
- 🗄️ `extract_sf2_properly.py` - SF2 extraction (old method)
- 🗄️ `generate_info.py` - Info generation (superseded by pipeline)

### CI/CD (1 file) - Superseded by GitHub Actions
- 🗄️ `ci_local.py` - Local CI testing (superseded by .github/workflows/)

---

## Category 5: ARCHIVE - Experimental Scripts (29 files)

**Location**: `pyscript/`
**Status**: 🗄️ **ARCHIVE**
**Reason**: Debugging scripts, experiments, obsolete tools

### SF2 Viewer Development (9 files) - v2.x Development Artifacts
- 🗄️ `verify_gui_display.py` - GUI display verification (development)
- 🗄️ `display_sequences.py` - Sequence display testing (development)
- 🗄️ `run_viewer.py` - Viewer runner (superseded by launch_sf2_viewer.py)
- 🗄️ `run_viewer_with_log.py` - Viewer with logging (debugging)
- 🗄️ `launch_with_laxity_file.py` - Laxity file launcher (development)
- 🗄️ `test_track_view_parity.py` - Track view parity testing (development)
- 🗄️ `compare_track3_v2.py` - Track 3 comparison v2 (development)
- 🗄️ `compare_track3_flexible.py` - Track 3 flexible comparison (development)
- 🗄️ `search_for_sequence.py` - Sequence search tool (debugging)

### Text Export Development (2 files) - v2.2 Development
- 🗄️ `combine_sf2_export.py` - SF2 export combination (development)
- 🗄️ `combine_export.py` - Export combination (development)

### Pipeline Experiments (3 files) - Performance Testing
- 🗄️ `pipeline_with_timings.py` - Pipeline with timing tracking
- 🗄️ `parallel_galway_pipeline.py` - Parallel Galway pipeline
- 🗄️ `generate_galway_timing_report.py` - Galway timing reports
- 🗄️ `aggregate_galway_timings.py` - Galway timing aggregation

### Laxity Driver Development (8 files) - v1.8.0 Development Artifacts
- 🗄️ `test_laxity_accuracy.py` - Laxity accuracy testing (superseded by pipeline)
- 🗄️ `convert_all_laxity.py` - Laxity batch conversion (superseded by sid_to_sf2.py --driver laxity)
- 🗄️ `build_laxity_driver_with_headers.py` - Driver building with headers
- 🗄️ `analyze_driver_headers.py` - Driver header analysis
- 🗄️ `investigate_entry_stubs.py` - Entry stub investigation
- 🗄️ `analyze_sf2_layout.py` - SF2 layout analysis
- 🗄️ `trace_scanning.py` - Trace scanning
- 🗄️ `analyze_broware_structure.py` - Broware structure analysis

### Analysis Tools (7 files) - Specific/Debugging
- 🗄️ `analyze_raw_bytes.py` - Raw byte analysis (debugging)
- 🗄️ `validate_sf2.py` - SF2 validation (old)
- 🗄️ `cleanup_md_files.py` - MD file cleanup (superseded by cleanup.py)
- 🗄️ `check_pulse_data.py` - Pulse data checking (specific)

---

## Category 6: ALREADY ARCHIVED (73 files)

**Location**: `archive/`
**Status**: ℹ️ **ALREADY ARCHIVED**
**Reason**: Previously archived experiments and old code

These files are already in `archive/experiments/` and properly managed.

---

## Category 7: UNTRACKED (22 files)

**Location**: `temp/`
**Status**: ℹ️ **UNTRACKED**
**Reason**: Already removed from git tracking in cleanup commit eadfdcb

These files are local-only and not tracked by git.

---

## Category 8: DRIVERS (1 file)

**Location**: `drivers/laxity/`
**Status**: ✅ **KEEP**
**Reason**: Part of Laxity driver implementation

- ✅ `build_driver.py` - Laxity driver build script (CORE)

---

## Archive Plan

### Step 1: Create Archive Directory
```
archive/python_cleanup_2025-12-21/
├── scripts_implementation/    # 39 files from scripts/
├── pyscript_experimental/     # 29 files from pyscript/
├── experiments/               # 2 files from experiments/
└── README.md                  # Archive documentation
```

### Step 2: Archive Script Files (39 files)

**scripts/implementation/** (Laxity Phase Tests - 7 files):
- test_phase1_foundation.py
- test_phase2_memory_analysis.py
- test_phase3_table_extraction.py
- test_phase4_table_injection.py
- test_phase6_conversion_integration.py
- batch_test_laxity_driver.py
- batch_test_laxity_driver_parallel.py

**scripts/implementation/** (Laxity Tools - 5 files):
- extract_laxity_player.py
- design_laxity_sf2_header.py
- relocate_laxity_player.py
- analyze_laxity_relocation.py
- generate_sf2_header.py

**scripts/collections/** (1 file):
- convert_galway_collection.py

**scripts/validation_old/** (7 files):
- validate_conversion.py
- validate_psid.py
- validate_structure.py
- comprehensive_validate.py
- batch_validate_sidsf2player.py
- test_table_validation.py
- test_extraction_validator.py

**scripts/tests_old/** (5 files):
- test_config.py
- test_sf2_editor.py
- test_sf2_player_parser.py
- test_sf2_compatibility.py
- test_memory_overlap.py
- test_all_musical_content.py

**scripts/analysis_specific/** (8 files):
- analyze_midi_diff.py
- analyze_sid_collections.py
- parse_analysis_reports.py
- laxity_parser.py
- format_tables.py
- trace_orderlist_access.py
- generate_driver_analysis.py

**scripts/inventory_old/** (3 files):
- create_detailed_inventory.py
- create_enhanced_collection_inventory.py
- create_collection_grid_inventory.py

**scripts/extraction_old/** (2 files):
- extract_sf2_properly.py
- generate_info.py

**scripts/ci_old/** (1 file):
- ci_local.py

**scripts/conversions_old/** (1 file):
- convert_all_sidsf2player.py

### Step 3: Archive Pyscript Files (29 files)

**pyscript/sf2_viewer_dev/** (9 files):
- verify_gui_display.py
- display_sequences.py
- run_viewer.py
- run_viewer_with_log.py
- launch_with_laxity_file.py
- test_track_view_parity.py
- compare_track3_v2.py
- compare_track3_flexible.py
- search_for_sequence.py

**pyscript/export_dev/** (2 files):
- combine_sf2_export.py
- combine_export.py

**pyscript/pipeline_experiments/** (4 files):
- pipeline_with_timings.py
- parallel_galway_pipeline.py
- generate_galway_timing_report.py
- aggregate_galway_timings.py

**pyscript/laxity_dev/** (8 files):
- test_laxity_accuracy.py
- convert_all_laxity.py
- build_laxity_driver_with_headers.py
- analyze_driver_headers.py
- investigate_entry_stubs.py
- analyze_sf2_layout.py
- trace_scanning.py
- analyze_broware_structure.py

**pyscript/analysis_debug/** (4 files):
- analyze_raw_bytes.py
- validate_sf2.py
- cleanup_md_files.py
- check_pulse_data.py

### Step 4: Archive Experiments (2 files)

**experiments/** (2 files):
- experiments/sf2_viewer/experiment.py
- experiments/laxity_analysis/experiment.py

---

## Execution Commands

```bash
# Step 1: Create archive directory
mkdir -p archive/python_cleanup_2025-12-21/scripts_implementation
mkdir -p archive/python_cleanup_2025-12-21/scripts_collections
mkdir -p archive/python_cleanup_2025-12-21/scripts_validation_old
mkdir -p archive/python_cleanup_2025-12-21/scripts_tests_old
mkdir -p archive/python_cleanup_2025-12-21/scripts_analysis_specific
mkdir -p archive/python_cleanup_2025-12-21/scripts_inventory_old
mkdir -p archive/python_cleanup_2025-12-21/scripts_extraction_old
mkdir -p archive/python_cleanup_2025-12-21/scripts_ci_old
mkdir -p archive/python_cleanup_2025-12-21/scripts_conversions_old
mkdir -p archive/python_cleanup_2025-12-21/pyscript_sf2_viewer_dev
mkdir -p archive/python_cleanup_2025-12-21/pyscript_export_dev
mkdir -p archive/python_cleanup_2025-12-21/pyscript_pipeline_experiments
mkdir -p archive/python_cleanup_2025-12-21/pyscript_laxity_dev
mkdir -p archive/python_cleanup_2025-12-21/pyscript_analysis_debug
mkdir -p archive/python_cleanup_2025-12-21/experiments

# Step 2: Move files with git mv (preserves history)
# ... (detailed commands to follow in execution phase)

# Step 3: Update FILE_INVENTORY.md
python pyscript/update_inventory.py

# Step 4: Commit
git add -A
git commit -m "chore: Archive 70 unused Python files (implementation artifacts)"
```

---

## Benefits

**Before**:
- 252 Python files total
- 65 files in scripts/ (confusing mix of core + implementation)
- 37 files in pyscript/ (confusing mix of tools + experiments)
- Difficult to find core utilities

**After**:
- 81 actively used Python files (clear and organized)
- 20 core scripts/ (only essential tools)
- 8 core pyscript/ (only maintenance tools + SF2 Viewer)
- 70 files archived with clear organization
- Easy to navigate and maintain

**Archive Organization**:
- Clear categorization (implementation/, dev/, experiments/, old/)
- All files preserved with git history
- README.md explaining what was archived and why
- Can be restored if needed

---

## Notes

1. **sidm2/ package**: All 52 files kept (official package API)
2. **Test suites**: All core test files kept (test_converter.py, test_sf2_format.py, test_complete_pipeline.py)
3. **Implementation artifacts**: Phase test files archived (v1.8.0 implementation complete)
4. **Development scripts**: SF2 Viewer development scripts archived (v2.2 complete)
5. **Old validation**: Pre-v1.4 validation scripts archived (validation system complete)
6. **Git history**: All moves use `git mv` to preserve history

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
