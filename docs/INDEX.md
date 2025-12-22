# SIDM2 Documentation Index

**Complete navigation to all project documentation after v2.3.0 consolidation**

**Last Updated**: 2025-12-22
**Version**: v2.5.3
**Status**: Consolidated & Organized

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

---

## 🔍 Technical Reference

Technical specifications and format details:

### Format Specifications
| Document | Content |
|----------|---------|
| [SF2_FORMAT_SPEC.md](reference/SF2_FORMAT_SPEC.md) | Complete SF2 format specification |
| [SF2_TRACKS_AND_SEQUENCES.md](reference/SF2_TRACKS_AND_SEQUENCES.md) | Tracks and sequences format guide |
| [SF2_INSTRUMENTS_REFERENCE.md](reference/SF2_INSTRUMENTS_REFERENCE.md) | Instruments format guide |
| [SID_REGISTERS_REFERENCE.md](reference/SID_REGISTERS_REFERENCE.md) | SID chip register quick reference |
| [DRIVER_REFERENCE.md](reference/DRIVER_REFERENCE.md) | All SF2 drivers (11-16, NP20, Laxity) |
| [CONVERSION_STRATEGY.md](reference/CONVERSION_STRATEGY.md) | Laxity → SF2 mapping details |
| [format-specification.md](reference/format-specification.md) | PSID/RSID formats |

### Technical References
| Document | Content |
|----------|---------|
| [LAXITY_DRIVER_TECHNICAL_REFERENCE.md](reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md) | **Laxity driver technical details** - Architecture, memory layout, pointer patching | v2.0.0 |
| [STINSENS_PLAYER_DISASSEMBLY.md](reference/STINSENS_PLAYER_DISASSEMBLY.md) | Laxity NewPlayer v21 disassembly |
| [SF2_DRIVER11_DISASSEMBLY.md](reference/SF2_DRIVER11_DISASSEMBLY.md) | SF2 Driver 11 player analysis |
| [SF2_CLASSES.md](reference/SF2_CLASSES.md) | SF2 class structure reference |
| [external-repositories.md](reference/external-repositories.md) | External source code repositories |
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

---

## 🔬 Analysis & Research

Technical analysis, validation results, and findings:

### Consolidated Analysis (NEW - v2.3.0)
| Document | Content | Version |
|----------|---------|---------|
| [MIDI_VALIDATION_COMPLETE.md](analysis/MIDI_VALIDATION_COMPLETE.md) | **Complete MIDI validation results** - 100.66% accuracy, perfect matches | v2.0.0 |

### Project Analysis
| Document | Content |
|----------|---------|
| [CONSOLIDATION_2025-12-21_COMPLETE.md](analysis/CONSOLIDATION_2025-12-21_COMPLETE.md) | **Authoritative consolidation documentation** - Complete Phase 1-4 documentation |
| [ACCURACY_ROADMAP.md](analysis/ACCURACY_ROADMAP.md) | Accuracy improvement plan - Path to 99% accuracy |
| [PACK_STATUS.md](analysis/PACK_STATUS.md) | Packer status - SF2→SID implementation details |
| [TRACK_VIEW_TEST_RESULTS.md](analysis/TRACK_VIEW_TEST_RESULTS.md) | Track view testing results |

### Implementation Analysis
| Document | Content |
|----------|---------|
| [SIDDECOMPILER_INTEGRATION_ANALYSIS.md](analysis/SIDDECOMPILER_INTEGRATION_ANALYSIS.md) | SIDdecompiler integration analysis |
| [LAXITY_BATCH_CONVERSION_RESULTS.md](analysis/LAXITY_BATCH_CONVERSION_RESULTS.md) | Laxity batch conversion results |
| [LAXITY_WAVE_TABLE_ANALYSIS.md](analysis/LAXITY_WAVE_TABLE_ANALYSIS.md) | Wave table format analysis |

### Status Documents
| Document | Content |
|----------|---------|
| [STATUS.md](STATUS.md) | **Current project status** - Features, recent changes, roadmap | v2.3.0 |
| [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md) | Improvement planning and tracking |
| [ROADMAP.md](ROADMAP.md) | Project roadmap |

---

## 🛠️ Implementation Documentation

Detailed implementation guides and reports:

### Laxity Driver Implementation
| Document | Content |
|----------|---------|
| [laxity/PHASE5_COMPLETE.md](implementation/laxity/PHASE5_COMPLETE.md) | Phase 5: Pipeline integration |
| [laxity/PHASE6_POINTER_ANALYSIS.md](implementation/laxity/PHASE6_POINTER_ANALYSIS.md) | Phase 6: Pointer patching analysis |
| [laxity/PHASE6_POINTER_PATCHING_RESULTS.md](implementation/laxity/PHASE6_POINTER_PATCHING_RESULTS.md) | Pointer patching results |
| [laxity/PHASE6_SUCCESS_SUMMARY.md](implementation/laxity/PHASE6_SUCCESS_SUMMARY.md) | Phase 6 success summary |
| [laxity/POINTER_PATCHING_RESULTS.md](implementation/laxity/POINTER_PATCHING_RESULTS.md) | Detailed pointer patching results |
| [laxity/WAVE_TABLE_FORMAT_FIX.md](implementation/laxity/WAVE_TABLE_FORMAT_FIX.md) | Wave table format fix (99.93% accuracy breakthrough) |
| [laxity/WAVE_TABLE_FORMAT_COMPLETE.md](implementation/laxity/WAVE_TABLE_FORMAT_COMPLETE.md) | Complete wave table format documentation |
| [laxity/WAVE_TABLE_IMPLEMENTATION_SUMMARY.md](implementation/laxity/WAVE_TABLE_IMPLEMENTATION_SUMMARY.md) | Wave table implementation summary |

### Core Implementation
| Document | Content |
|----------|---------|
| [GATE_INFERENCE_IMPLEMENTATION.md](implementation/GATE_INFERENCE_IMPLEMENTATION.md) | Waveform-based gate detection (v1.5.0) |
| [SIDDECOMPILER_INTEGRATION.md](implementation/SIDDECOMPILER_INTEGRATION.md) | SIDdecompiler integration (v1.4) |
| [RUNTIME_TABLE_BUILDING_IMPLEMENTATION.md](implementation/RUNTIME_TABLE_BUILDING_IMPLEMENTATION.md) | Runtime table building |
| [SF2_VIEWER_V2.4_COMPLETE.md](implementation/SF2_VIEWER_V2.4_COMPLETE.md) | SF2 Viewer v2.4 completion |
| [PHASE2_ENHANCEMENTS_SUMMARY.md](implementation/PHASE2_ENHANCEMENTS_SUMMARY.md) | Phase 2 enhancements |
| [PHASE3_4_VALIDATION_REPORT.md](implementation/PHASE3_4_VALIDATION_REPORT.md) | Phase 3 & 4 validation report |

---

## 🧪 Testing & Validation

Test results and validation reports:

| Document | Content |
|----------|---------|
| [C64_OCR_TEST_RESULTS.md](testing/C64_OCR_TEST_RESULTS.md) | C64 OCR testing results |
| [MCP_OCR_TEST_RESULTS.md](testing/MCP_OCR_TEST_RESULTS.md) | MCP OCR testing results |
| [IMAGESORCERY_MCP_WORKAROUNDS_SUMMARY.md](testing/IMAGESORCERY_MCP_WORKAROUNDS_SUMMARY.md) | ImageSorcery MCP workarounds |

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
→ See [ACCURACY_ROADMAP.md](analysis/ACCURACY_ROADMAP.md)

**...check MIDI validation results**
→ See [MIDI_VALIDATION_COMPLETE.md](analysis/MIDI_VALIDATION_COMPLETE.md)

---

## Documentation Statistics (v2.3.0)

**Before Consolidation** (v2.2.0):
- Total documentation files: ~173 MD files
- Root clutter: 26 files in docs/ root
- Redundant documentation: 20+ duplicate files

**After Consolidation** (v2.3.0):
- Total documentation files: ~145-150 MD files
- Root organization: <10 core files in docs/ root
- Consolidated guides: 6 comprehensive guides (from 20 files)
- File reduction: 23-28 files removed (13-16%)
- Repository size reduction: ~1.2MB (generated files + archives)

**Organization**:
- Core: 4 files (root)
- Guides: 5 comprehensive guides (NEW consolidation)
- Reference: 13 technical references
- Analysis: 10+ analysis documents
- Implementation: 15+ implementation docs (including laxity/)
- Testing: 3 test results
- Archive: 30+ historical files (with consolidation archives)
- Auto-generated: 1 file

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

## Recent Changes (v2.3.0 - 2025-12-21)

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

**Phase 4: Index & Navigation** (IN PROGRESS)
- Updated INDEX.md to reflect consolidation
- All documentation links verified

---

**Document Status**: Complete consolidation index (v2.3.0)
**Last Consolidation**: 2025-12-21
**Maintainer**: SIDM2 Project

🤖 Generated with [Claude Code](https://claude.com/claude-code)
