# SIDM2 Documentation Index

**Complete navigation to all project documentation**

**Last Updated**: 2026-07-05
**Version**: v3.13.0
**Status**: Native-driver era — Laxity production + native SF2 drivers for Galway / ROMUZAK / Maniacs of Noise; consolidated player knowledge in `docs/players/`

---

## 🎹 Players (SID → SF2 support) — START HERE for conversion work

| Document | Purpose |
|----------|---------|
| [players/README.md](players/README.md) | **Player support index** — every supported player, driver, corpus |
| [players/PLAYBOOK.md](players/PLAYBOOK.md) | **The consolidated cross-player playbook** — staged porting method, shared pipeline, size caps, gotchas, new-player checklist |
| [reference/ACCURACY_MATRIX.md](reference/ACCURACY_MATRIX.md) | **Accuracy source of truth** (v3.13.0) |
| [players/LAXITY.md](players/LAXITY.md) | Laxity NewPlayer v21 (production, 99.93–100%) |
| [players/GALWAY.md](players/GALWAY.md) | Martin Galway (native driver ~100%, 40-tune corpus) |
| [players/MON.md](players/MON.md) | Maniacs of Noise / Jeroen Tel — Hawkeye, Cybernoid, Myth, Supremacy (byte-exact native) |
| [players/ROMUZAK.md](players/ROMUZAK.md) | ROMUZAK V6.3 (native driver, byte-exact wf/pulse/AD-SR) |
| [players/FUTURECOMPOSER.md](players/FUTURECOMPOSER.md) | Future Composer (Stage A) |
| [players/DRIVER11.md](players/DRIVER11.md) | SF2-exported / Driver 11 (100%) |
| [players/NP20.md](players/NP20.md) | NewPlayer 20 (70–90%) |
| [players/CLUSTERS.md](players/CLUSTERS.md) | NP21-adjacent clusters (Stinsen/Beast/Angular, DRAX, 2000 A.D., Wizax, V20) |
| [../whats-next.md](../whats-next.md) | Active frontier handoff (MoN part-count structural rebuild) |

---

## 📚 Core Documentation

Start here for general information:

| Document | Purpose |
|----------|---------|
| [README.md](../README.md) | **Main user guide** - Installation, usage, examples |
| [CLAUDE.md](../CLAUDE.md) | **AI assistant guide** - Project structure, conventions |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | **Contribution guidelines** - How to contribute |
| [CHANGELOG.md](../CHANGELOG.md) | **Version history** - All releases and changes |

---

## 📋 Project Management & Planning

Active tracking documents for improvements and task management:

| Document | Purpose |
|----------|---------|
| [IMPROVEMENTS_TODO.md](../IMPROVEMENTS_TODO.md) | **Active TODO tracking** - All improvement suggestions, bugs, features (v1.0) |
| [UX_IMPROVEMENT_PLAN.md](../UX_IMPROVEMENT_PLAN.md) | **UX enhancement plan** - User experience improvements and priorities |
| [ALL_FIXES_SUMMARY.md](../ALL_FIXES_SUMMARY.md) | **Consolidated fixes** - Summary of all bug fixes and improvements |
| [TEST_FIX_SUMMARY.md](../TEST_FIX_SUMMARY.md) | **Test fixes** - Test suite corrections and improvements |
| [ROUNDTRIP_TEST_FIX.md](../ROUNDTRIP_TEST_FIX.md) | **Roundtrip validation fixes** - SF2→SID→SF2 test corrections |
| [LOGGING_ERROR_IMPROVEMENTS_SUMMARY.md](../LOGGING_ERROR_IMPROVEMENTS_SUMMARY.md) | **Logging enhancements** - Summary of logging system improvements |
| [RELEASE_NOTES_v2.3.3.md](../RELEASE_NOTES_v2.3.3.md) | **Release notes** - v2.3.3 specific release documentation |

### Implementation Plans

| Plan | Purpose | Version |
|------|---------|---------|
| [JC64_ADVANCED_FEATURES_PLAN.md](plans/JC64_ADVANCED_FEATURES_PLAN.md) | **JC64 advanced features** - SID disassembly, player detection, frequency analysis (6 phases, 30-46 hours) | v1.0.0 |

---

## 📖 User Guides

Comprehensive guides for using the system:

### Essential Guides
| Guide | Purpose | Version |
|-------|---------|---------|
| [LAXITY_DRIVER_USER_GUIDE.md](guides/LAXITY_DRIVER_USER_GUIDE.md) | **Laxity driver complete user guide** - 99.93% accuracy conversions | v2.0.0 |
| [VALIDATION_GUIDE.md](guides/VALIDATION_GUIDE.md) | **Validation system guide** - Three-tier validation, dashboard, regression tracking | v2.0.0 |
| [SF2_VIEWER_GUIDE.md](guides/SF2_VIEWER_GUIDE.md) | **SF2 Viewer & Tools** - GUI, text exporter, editor enhancements | v2.4.0 |
| [WAVEFORM_ANALYSIS_GUIDE.md](guides/WAVEFORM_ANALYSIS_GUIDE.md) | **Waveform analysis tool** - HTML reports, metrics, troubleshooting | v0.7.2 |
| [EXPERIMENTS_WORKFLOW_GUIDE.md](guides/EXPERIMENTS_WORKFLOW_GUIDE.md) | **Experiment system workflow** - Lifecycle, templates, best practices | v2.2 |
| [CLEANUP_SYSTEM.md](guides/CLEANUP_SYSTEM.md) | **Cleanup system guide** - Automated cleanup, git protection, file organization | v2.3 |
| [SIDWINDER_GUIDE.md](guides/SIDWINDER_GUIDE.md) | **SIDwinder integration guide** - Features, usage, rebuilding | - |
| [ROOT_FOLDER_RULES.md](guides/ROOT_FOLDER_RULES.md) | **Root folder management** - What belongs in root, organization rules | - |
| [TROUBLESHOOTING.md](guides/TROUBLESHOOTING.md) | **Troubleshooting guide** - Common errors, solutions, debugging tips | v2.0.0 |
| [LOGGING_AND_ERROR_HANDLING_GUIDE.md](guides/LOGGING_AND_ERROR_HANDLING_GUIDE.md) | **Logging system guide** - Enhanced logging v2.0.0, CLI flags, JSON output | v2.0.0 |
| [ERROR_MESSAGE_STYLE_GUIDE.md](guides/ERROR_MESSAGE_STYLE_GUIDE.md) | **Error message guidelines** - Consistent error reporting standards | - |
| [CONVERSION_COCKPIT_TECHNICAL_REFERENCE.md](guides/CONVERSION_COCKPIT_TECHNICAL_REFERENCE.md) | **Cockpit technical reference** - Internal architecture, API details | v2.5.0 |
| [SID_INVENTORY_GUIDE.md](guides/SID_INVENTORY_GUIDE.md) | **SID Inventory system guide** - Complete documentation for SID file cataloging system | v2.8.0 |
| [SID_INVENTORY_README.md](guides/SID_INVENTORY_README.md) | **SID Inventory quick reference** - Quick start guide for inventory system | v2.8.0 |

---

## 🔍 Technical Reference

Technical specifications and format details:

### Format Specifications
| Document | Content |
|----------|---------|
| [SF2_FORMAT_SPEC.md](reference/SF2_FORMAT_SPEC.md) | Complete SF2 format specification |
| [SF2_TRACKS_AND_SEQUENCES.md](SF2_TRACKS_AND_SEQUENCES.md) | Tracks and sequences format guide |
| [SF2_INSTRUMENTS_REFERENCE.md](SF2_INSTRUMENTS_REFERENCE.md) | Instruments format guide |
| [SID_REGISTERS_REFERENCE.md](SID_REGISTERS_REFERENCE.md) | SID chip register quick reference |
| [DRIVER_REFERENCE.md](reference/DRIVER_REFERENCE.md) | All SF2 drivers (11-16, NP20, Laxity) |
| [ACCURACY_MATRIX.md](reference/ACCURACY_MATRIX.md) | **Accuracy source of truth** — all players, wired + native |
| [CONVERSION_STRATEGY.md](reference/CONVERSION_STRATEGY.md) | Laxity → SF2 mapping details |
| [format-specification.md](reference/format-specification.md) | PSID/RSID formats |

### Technical References
| Document | Content |
|----------|---------|
| [LAXITY_DRIVER_TECHNICAL_REFERENCE.md](reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md) | **Laxity driver technical details** - Architecture, memory layout, pointer patching | v2.0.0 |
| [STINSENS_PLAYER_DISASSEMBLY.md](reference/STINSENS_PLAYER_DISASSEMBLY.md) | Laxity NewPlayer v21 disassembly |
| [SF2_CLASSES.md](reference/SF2_CLASSES.md) | SF2 class structure reference |
| [external-repositories.md](reference/external-repositories.md) | External source code repositories |
| [jc64dis-source-repository.md](reference/jc64dis-source-repository.md) | **JC64dis source code** - Complete Java source for C64 emulator and 6502 disassembler |
| [sourcerepository.md](reference/sourcerepository.md) | Complete source code repository index |

### Implementation Limitations
| Document | Content |
|----------|---------|
| [SF2_TO_SID_LIMITATIONS.md](reference/SF2_TO_SID_LIMITATIONS.md) | Known packer limitations |
| [WAVE_TABLE_PACKING.md](reference/WAVE_TABLE_PACKING.md) | Wave table packing details |

---

## 🏗️ Architecture & Components

System architecture and module documentation:

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | **Complete system architecture** - Conversion flow, pipeline, constants |
| [COMPONENTS_REFERENCE.md](COMPONENTS_REFERENCE.md) | **Python modules reference** - All sidm2/ modules with APIs |
| [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) | **External tools documentation** - siddump, SIDwinder, SID2WAV, etc. |

### Feature Documentation
| Document | Purpose | Version |
|----------|---------|---------|
| [BATCH_HISTORY_FEATURE.md](BATCH_HISTORY_FEATURE.md) | **Batch History (CC-3)** - Save/load batch configurations, history management | v1.0.0 |
| [PROGRESS_ESTIMATION_FEATURE.md](PROGRESS_ESTIMATION_FEATURE.md) | **Progress Estimation (CC-5)** - Data-driven time estimates, confidence levels | v1.0.0 |
| [COCKPIT_UI_STYLING.md](COCKPIT_UI_STYLING.md) | **UI Styling System** - Professional styling, icons, color scheme | v1.0.0 |

---

## 🔬 Analysis & Research

Technical analysis, validation results, and findings:

### Current Analysis (docs/analysis/ — native-driver era)
| Document | Content |
|----------|---------|
| [GALWAY_SF2_DRIVER_PLAN.md](analysis/GALWAY_SF2_DRIVER_PLAN.md) | **Galway native-driver staged plan** (Stage A/B — the template all later players followed) |
| [ROMUZAK_SF2_DRIVER_PLAN.md](analysis/ROMUZAK_SF2_DRIVER_PLAN.md) | ROMUZAK native-driver plan |
| [GALWAY_1STGEN_ENGINE.md](analysis/GALWAY_1STGEN_ENGINE.md) | Galway 1st-gen bytecode engine map |
| [GALWAY_FM_PM_SYNTH.md](analysis/GALWAY_FM_PM_SYNTH.md) | Galway per-frame FM/PM synth analysis |
| [GALWAY_TO_DRIVER11_MAPPING.md](analysis/GALWAY_TO_DRIVER11_MAPPING.md) | Stage-A transpile mapping |
| [SF2_DRIVER_BINARY_FORMAT.md](analysis/SF2_DRIVER_BINARY_FORMAT.md) | SF2 driver descriptor format (RE'd — needed for native drivers) |
| [DRIVER11_TABLE_FORMATS.txt](analysis/DRIVER11_TABLE_FORMATS.txt) | Driver 11 wave/pulse/filter table interpreter spec |
| [DRIVER_FEATURES_COMPARISON.md](analysis/DRIVER_FEATURES_COMPARISON.md) | SF2 drivers 11-16 / NP20 / Laxity comparison |
| [DRIVER_LIMITATIONS.md](analysis/DRIVER_LIMITATIONS.md) | Known SF2 driver limitations |
| [SF2_VALIDATION_STATUS.md](analysis/SF2_VALIDATION_STATUS.md) | SF2 validation system status |
| [CONVERSION_MASTERY_ANALYSIS.md](analysis/CONVERSION_MASTERY_ANALYSIS.md) | Conversion mastery deep analysis |

> **Archived analysis** (pre-2026 deep dives: SF2 format dives, siddump/SIDwinder design, JC64, pattern DB, Galway batch timing, etc.) moved to [archive/analysis_2026-01-02/](archive/analysis_2026-01-02/).

### External Tools Integration
| Document | Content | Version |
|----------|---------|---------|
| [JC64_BUILD_AND_TEST_RESULTS.md](integration/JC64_BUILD_AND_TEST_RESULTS.md) | **JC64 build and test results** - Python wrapper, PSID parsing, player detection, known issues | v1.0.0 |

### Conversion Policy & Driver Integration (NEW - v2.8.0)
| Document | Content | Version |
|----------|---------|---------|
| [CONVERSION_POLICY_APPROVED.md](integration/CONVERSION_POLICY_APPROVED.md) | **Conversion Policy v2.0** - Quality-first approach, driver selection matrix, validation requirements | v2.0.0 |
| [POLICY_INTEGRATION_COMPLETE.md](integration/POLICY_INTEGRATION_COMPLETE.md) | **Policy integration summary** - Implementation status, testing verification, production readiness | v2.0.0 |
| [DRIVER_SELECTION_TEST_RESULTS.md](integration/DRIVER_SELECTION_TEST_RESULTS.md) | **Driver selection test results** - 4 player types tested, 100% pass rate | v2.0.0 |
| [INTEGRATION_SUMMARY.md](integration/INTEGRATION_SUMMARY.md) | **Integration summary** - How driver selection works, console output examples | v2.0.0 |
| [POLICY_ANALYSIS.md](integration/POLICY_ANALYSIS.md) | **Policy analysis** - Analysis of quality-first approach vs strict Driver 11 policy | v2.0.0 |
| [POLICY_IMPLEMENTATION_SUMMARY.md](integration/POLICY_IMPLEMENTATION_SUMMARY.md) | **Policy implementation** - Technical implementation details, file changes | v2.0.0 |
| [CONVERSION_POLICY.md](integration/CONVERSION_POLICY.md) | **Conversion Policy v1.0** - Earlier draft (superseded by v2.0 APPROVED) | v1.0.0 |

### Status Documents
| Document | Content |
|----------|---------|
| [STATUS.md](STATUS.md) | **Current project status** - Features, recent changes, roadmap | v2.3.0 |
| [IMPROVEMENT_PLAN.md](../archive/cleanup_2026-04-28/old_docs/completion_reports/IMPROVEMENT_PLAN.md) (archived) | Improvement planning and tracking |
| [ROADMAP.md](ROADMAP.md) | Project roadmap |

---

## 🛠️ Implementation Documentation

Detailed implementation guides and reports:

### Laxity Driver Implementation
| Document | Content |
|----------|---------|
| [laxity/PHASE5_COMPLETE.md](../archive/cleanup_2026-04-28/old_docs/completion_reports/PHASE5_COMPLETE.md) (archived) | Phase 5: Pipeline integration |
| [laxity/PHASE6_POINTER_ANALYSIS.md](implementation/laxity/PHASE6_POINTER_ANALYSIS.md) | Phase 6: Pointer patching analysis |
| [laxity/PHASE6_POINTER_PATCHING_RESULTS.md](implementation/laxity/PHASE6_POINTER_PATCHING_RESULTS.md) | Pointer patching results |
| [laxity/PHASE6_SUCCESS_SUMMARY.md](../archive/cleanup_2026-04-28/old_docs/completion_reports/PHASE6_SUCCESS_SUMMARY.md) (archived) | Phase 6 success summary |
| [laxity/POINTER_PATCHING_RESULTS.md](implementation/laxity/POINTER_PATCHING_RESULTS.md) | Detailed pointer patching results |
| [laxity/WAVE_TABLE_FORMAT_FIX.md](implementation/laxity/WAVE_TABLE_FORMAT_FIX.md) | Wave table format fix (99.93% accuracy breakthrough) |
| [laxity/WAVE_TABLE_FORMAT_COMPLETE.md](implementation/laxity/WAVE_TABLE_FORMAT_COMPLETE.md) | Complete wave table format documentation |
| [laxity/WAVE_TABLE_IMPLEMENTATION_SUMMARY.md](implementation/laxity/WAVE_TABLE_IMPLEMENTATION_SUMMARY.md) | Wave table implementation summary |

### Core Implementation
| Document | Content | Version |
|----------|---------|---------|
| [SIDDUMP_PYTHON_IMPLEMENTATION.md](implementation/SIDDUMP_PYTHON_IMPLEMENTATION.md) | **Python siddump complete** - 595 lines, 100% musical accuracy, production ready | v2.6.0 |
| [GATE_INFERENCE_IMPLEMENTATION.md](implementation/GATE_INFERENCE_IMPLEMENTATION.md) | Waveform-based gate detection | v1.5.0 |
| [SIDDECOMPILER_INTEGRATION.md](implementation/SIDDECOMPILER_INTEGRATION.md) | SIDdecompiler integration | v1.4 |
| [SIDDECOMPILER_LESSONS_LEARNED.md](implementation/SIDDECOMPILER_LESSONS_LEARNED.md) | Lessons learned from SIDdecompiler integration | - |
| [RUNTIME_TABLE_BUILDING_IMPLEMENTATION.md](implementation/RUNTIME_TABLE_BUILDING_IMPLEMENTATION.md) | Runtime table building | - |
| [SF2_VIEWER_FEATURE_PARITY_PLAN.md](implementation/SF2_VIEWER_FEATURE_PARITY_PLAN.md) | SF2 Viewer feature parity planning | - |

### Laxity Driver Implementation (Detailed)
| Document | Content |
|----------|---------|
| [laxity/PHASE5_COMPLETE.md](../archive/cleanup_2026-04-28/old_docs/completion_reports/PHASE5_COMPLETE.md) (archived) | Phase 5: Pipeline integration complete |
| [laxity/PHASE5_INTEGRATION_STATUS.md](../archive/cleanup_2026-04-28/old_docs/completion_reports/PHASE5_INTEGRATION_STATUS.md) (archived) | Phase 5: Integration status tracking |
| [laxity/PHASE5_SUMMARY.md](../archive/cleanup_2026-04-28/old_docs/completion_reports/PHASE5_SUMMARY.md) (archived) | Phase 5: Summary and results |
| [laxity/PHASE6_POINTER_ANALYSIS.md](implementation/laxity/PHASE6_POINTER_ANALYSIS.md) | Phase 6: Pointer patching analysis |
| [laxity/PHASE6_POINTER_PATCHING_RESULTS.md](implementation/laxity/PHASE6_POINTER_PATCHING_RESULTS.md) | Phase 6: Pointer patching results |
| [laxity/PHASE6_STATUS.md](implementation/laxity/PHASE6_STATUS.md) | Phase 6: Status tracking |
| [laxity/PHASE6_SUCCESS_SUMMARY.md](../archive/cleanup_2026-04-28/old_docs/completion_reports/PHASE6_SUCCESS_SUMMARY.md) (archived) | Phase 6: Success summary |
| [laxity/WAVE_TABLE_FORMAT_FIX.md](implementation/laxity/WAVE_TABLE_FORMAT_FIX.md) | **Wave table format fix** - 99.93% accuracy breakthrough |

---

## 🔧 Solutions & Discoveries

Major technical breakthroughs and solutions:

| Document | Content |
|----------|---------|
| [solutions/WAVE_TABLE_DUAL_FORMAT.md](solutions/WAVE_TABLE_DUAL_FORMAT.md) | **Wave table dual format** - Critical format mismatch discovery |
| [solutions/THREE_TABLE_FORMAT_DISCOVERY.md](solutions/THREE_TABLE_FORMAT_DISCOVERY.md) | **Three-table format discovery** - SF2 table architecture |

---

## 🧪 Testing & Validation

Test results and validation reports:

| Document | Content |
|----------|---------|
| [testing/C64_OCR_TEST_RESULTS.md](testing/C64_OCR_TEST_RESULTS.md) | C64 OCR testing results |
| [testing/MCP_OCR_TEST_RESULTS.md](testing/MCP_OCR_TEST_RESULTS.md) | MCP OCR testing results |
| [testing/IMAGESORCERY_MCP_WORKAROUNDS_SUMMARY.md](testing/IMAGESORCERY_MCP_WORKAROUNDS_SUMMARY.md) | ImageSorcery MCP workarounds |

---

## ✅ Compliance & Quality

Compliance testing and quality reports:

| Document | Content |
|----------|---------|
| [../compliance_test/COMPLIANCE_REPORT.md](../compliance_test/COMPLIANCE_REPORT.md) | Compliance test results and findings |
| [../compliance_test/FINAL_COMPLIANCE_SUMMARY.md](../compliance_test/FINAL_COMPLIANCE_SUMMARY.md) | Final compliance summary |

---

## 🧪 Experiments

Experimental features and investigations:

| Document | Content |
|----------|---------|
| [../experiments/README.md](../experiments/README.md) | Experiments overview and catalog |
| [../experiments/ocr_sf2_screenshots/README.md](../experiments/ocr_sf2_screenshots/README.md) | OCR SF2 screenshots experiment |
| [../experiments/ocr_sf2_screenshots/SUMMARY.md](../experiments/ocr_sf2_screenshots/SUMMARY.md) | OCR experiment summary and results |

---

## 📚 Learning Resources

Educational documentation and reference materials:

| Document | Content |
|----------|---------|
| [../learnings/KNOWLEDGE_BASE_INDEX.md](../learnings/KNOWLEDGE_BASE_INDEX.md) | **Knowledge base index** - Complete learning resources catalog |
| [../learnings/C64_SID_PROGRAMMING_REFERENCE.md](../learnings/C64_SID_PROGRAMMING_REFERENCE.md) | C64 SID chip programming reference |
| [../learnings/6502_ADDRESSING_MODES_REFERENCE.md](../learnings/6502_ADDRESSING_MODES_REFERENCE.md) | 6502 CPU addressing modes reference |
| [../learnings/CODE_RELOCATION_TECHNIQUES.md](../learnings/CODE_RELOCATION_TECHNIQUES.md) | 6502 code relocation techniques |
| [../learnings/SELF_MODIFYING_CODE_GUIDE.md](../learnings/SELF_MODIFYING_CODE_GUIDE.md) | Self-modifying code patterns and guide |
| [../learnings/MUSIC_PLAYER_ARCHITECTURE.md](../learnings/MUSIC_PLAYER_ARCHITECTURE.md) | C64 music player architecture reference |

---

## 🗄️ Test Collections

Test file sets and validation data:

| Document | Content |
|----------|---------|
| [../test_collections/README.md](../test_collections/README.md) | Test collection catalog and organization |

---

## 📊 Validation Data

Validation results and dashboard:

| Document | Content |
|----------|---------|
| [../validation/SUMMARY.md](../validation/SUMMARY.md) | Validation summary and statistics |

---

## 📦 Archive

Historical reports, completed work, and consolidated documentation:

### Recent Consolidation Archives (2025-12-21)
| Directory | Content |
|-----------|---------|
| [archive/consolidation_2025-12-21/laxity/](archive/consolidation_2025-12-21/laxity/) | Original Laxity documentation (11 files → 2 consolidated guides) |
| [archive/consolidation_2025-12-21/validation/](archive/consolidation_2025-12-21/validation/) | Original validation documentation (4 files → 1 guide) |
| [archive/consolidation_2025-12-21/midi/](archive/consolidation_2025-12-21/midi/) | Original MIDI documentation (2 files → 1 complete report) |
| [archive/consolidation_2025-12-21/cleanup/](archive/consolidation_2025-12-21/cleanup/) | Original cleanup documentation (3 files → 1 guide) |

### Historical Archives
| Directory | Content |
|-----------|---------|
| [archive/2025-12-11/](archive/2025-12-11/) | Cleanup system documentation archive |
| [archive/2025-12-06/](archive/2025-12-06/) | Pipeline execution reports |

---

## 🗂️ Auto-Generated

| Document | Purpose |
|----------|---------|
| [FILE_INVENTORY.md](FILE_INVENTORY.md) | Complete file inventory (auto-generated) |

---

## Quick Links by Task

### I want to...

**...convert a Laxity SID file with high accuracy**
→ See [LAXITY_DRIVER_USER_GUIDE.md](guides/LAXITY_DRIVER_USER_GUIDE.md) (99.93% accuracy)

**...convert any SID file**
→ Start with [README.md - Basic Conversion](../README.md#basic-conversion)

**...understand SF2 format**
→ Read [SF2_FORMAT_SPEC.md](reference/SF2_FORMAT_SPEC.md)

**...use SIDwinder**
→ See [SIDWINDER_GUIDE.md](guides/SIDWINDER_GUIDE.md)

**...validate conversion accuracy**
→ See [VALIDATION_GUIDE.md](guides/VALIDATION_GUIDE.md)

**...understand Laxity driver internals**
→ Read [LAXITY_DRIVER_TECHNICAL_REFERENCE.md](reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md)

**...clean up temporary files**
→ See [CLEANUP_SYSTEM.md](guides/CLEANUP_SYSTEM.md)

**...understand the codebase**
→ Read [CLAUDE.md](../CLAUDE.md)

**...contribute code**
→ See [CONTRIBUTING.md](../CONTRIBUTING.md)

**...improve accuracy**
→ See [ACCURACY_ROADMAP.md](../archive/cleanup_2026-04-28/old_docs/old_analysis/ACCURACY_ROADMAP.md) (archived)

**...check MIDI validation results**
→ See [MIDI_VALIDATION_COMPLETE.md](../archive/cleanup_2026-04-28/old_docs/meta_reports/MIDI_VALIDATION_COMPLETE.md) (archived)

**...use Python siddump**
→ See [SIDDUMP_PYTHON_IMPLEMENTATION.md](implementation/SIDDUMP_PYTHON_IMPLEMENTATION.md) (v2.6.0, 100% accuracy)

**...use Python SIDwinder**
→ See [SIDWINDER_PYTHON_DESIGN.md](archive/analysis_2026-01-02/SIDWINDER_PYTHON_DESIGN.md) (archived; v2.8.0, cross-platform)

**...convert a Galway / ROMUZAK / Maniacs-of-Noise SID with a native driver**
→ See [players/PLAYBOOK.md](players/PLAYBOOK.md) and the per-player docs in [players/](players/README.md)

**...port a NEW player to SF2**
→ Follow the checklist in [players/PLAYBOOK.md §6](players/PLAYBOOK.md)

**...track project improvements**
→ See [IMPROVEMENTS_TODO.md](../IMPROVEMENTS_TODO.md) (active task tracking)

**...understand Batch History feature**
→ See [BATCH_HISTORY_FEATURE.md](BATCH_HISTORY_FEATURE.md) (save/load configs)

**...understand Progress Estimation**
→ See [PROGRESS_ESTIMATION_FEATURE.md](PROGRESS_ESTIMATION_FEATURE.md) (data-driven estimates)

**...troubleshoot errors**
→ See [TROUBLESHOOTING.md](guides/TROUBLESHOOTING.md) (common errors and solutions)

**...configure logging**
→ See [LOGGING_AND_ERROR_HANDLING_GUIDE.md](guides/LOGGING_AND_ERROR_HANDLING_GUIDE.md) (enhanced logging v2.0.0)

---

## Documentation Statistics (v2.8.0)

**Before Consolidation** (v2.2.0):
- Total documentation files: ~173 MD files
- Root clutter: 26 files in docs/ root
- Redundant documentation: 20+ duplicate files

**After v2.8.0 Updates**:
- Total documentation files: ~170+ MD files (includes new features)
- Root organization: 4 core files + 7 project management files
- Consolidated guides: 12 comprehensive guides (from 20+ files)
- New sections: Solutions, Compliance, Experiments, Learning Resources, Test Collections, Validation Data

**Organization**:
- **Core**: 4 files (README, CLAUDE, CONTRIBUTING, CHANGELOG)
- **Project Management**: 7 tracking files (IMPROVEMENTS_TODO, UX_IMPROVEMENT_PLAN, etc.)
- **Guides**: 12 comprehensive guides (Laxity, Validation, SF2 Viewer, Troubleshooting, Logging, etc.)
- **Reference**: 13+ technical references (SF2 format, drivers, SID registers, etc.)
- **Analysis**: 25+ analysis documents (external tools, drivers, technical deep dives)
- **Implementation**: 20+ implementation docs (siddump.py, laxity phases, SF2 viewer, etc.)
- **Solutions**: 2 major discoveries (wave table dual format, three-table format)
- **Testing**: 3 test result documents
- **Compliance**: 2 quality reports
- **Experiments**: 3 experimental documentation files
- **Learning Resources**: 6 educational references
- **Archive**: 30+ historical files (with consolidation archives)
- **Auto-generated**: 1 file (FILE_INVENTORY.md)

**Benefits Achieved**:
- ✅ Single source of truth for each topic
- ✅ Clear documentation hierarchy
- ✅ Easy navigation with organized structure
- ✅ All information current and accurate
- ✅ Professional documentation standards
- ✅ Reduced maintenance burden
- ✅ Faster contributor onboarding

---

## Maintenance

### Update File Inventory
```bash
python pyscript/update_inventory.py
```

### Clean Temporary Files
```bash
python cleanup.py --scan          # Preview cleanup
python cleanup.py --clean         # Execute cleanup
```

---

## Recent Changes

### v3.13.0 (2026-07-05) - Native-Driver Era Consolidation
- Added the 🎹 Players section (docs/players/ was previously unindexed): support index, **PLAYBOOK.md** (consolidated cross-player knowledge), MON.md, CLUSTERS.md
- Rewrote [reference/ACCURACY_MATRIX.md](reference/ACCURACY_MATRIX.md) for v3.13.0 (was v3.1.1)
- Replaced the stale analysis tables with the current docs/analysis/ contents; noted the archive move to archive/analysis_2026-01-02/
- Fixed dead/moved links (SF2 format quick refs live in docs/ root; SIDwinder design archived; SF2_DRIVER11_DISASSEMBLY / SF2_VIEWER_V2.4_COMPLETE removed)
- New improvement roadmap: [ROADMAP.md](ROADMAP.md)

### v2.8.0 (2025-12-24) - INDEX Comprehensive Update
- Added 40+ missing documentation files to INDEX
- New sections: Project Management & Planning, Solutions, Compliance, Experiments, Learning Resources
- Updated all file descriptions and version numbers
- Added quick links for new features (siddump.py, sidwinder.py, batch history, progress estimation)
- Reorganized analysis section with subsections (External Tools, Implementation, Technical Deep Dives)
- Updated statistics to reflect v2.8.0 state

### v2.6.0 - v2.8.0 (2025-12-22 - 2025-12-24) - External Tools Independence
- Python siddump complete (v2.6.0) - 595 lines, 100% musical accuracy
- Python SIDwinder design (v2.8.0) - Cross-platform trace and disassembly
- Conversion Cockpit features: Batch History (CC-3), Progress Estimation (CC-5), UI Polish (CC-6)
- Accuracy improvements: 99.93% → 100% frame accuracy
- Enhanced logging system v2.0.0

### v2.3.0 (2025-12-21) - Documentation Consolidation

**Phase 1: Critical Consolidations**
- Laxity documentation: 11 files → 2 guides (User Guide + Technical Reference)
- Validation documentation: 4 files → 1 comprehensive guide (v2.0.0)
- MIDI documentation: 2 files → 1 complete report (v2.0.0)
- Cleanup documentation: 3 files → 1 guide (v2.3)

**Phase 2: Organization & Cleanup**
- Created docs/testing/ and docs/implementation/laxity/
- Reorganized 23 files to appropriate directories
- Removed 16 generated disassembly files (~1MB)
- Updated .gitignore for generated files

**Phase 3: Content Verification**
- Updated STATUS.md to v2.3.0
- Updated CHANGELOG.md with v2.3.0 entry
- Updated all version numbers across documentation
- Fixed all cross-references to consolidated locations

**Phase 4: Index & Navigation**
- Updated INDEX.md to reflect consolidation
- All documentation links verified

---

**Document Status**: Comprehensive INDEX with all MD files cataloged (v3.13.0)
**Last Updated**: 2026-07-05
**Last Major Consolidation**: 2026-07-05 (native-driver era; players/ tree indexed)
**Maintainer**: SIDM2 Project
**Completeness**: ✅ All MD files indexed with descriptions

🤖 Generated with [Claude Code](https://claude.com/claude-code)
