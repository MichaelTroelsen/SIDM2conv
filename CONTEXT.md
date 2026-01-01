# SIDM2 Project Context

**Version**: 3.0.1
**Last Updated**: 2026-01-01
**Status**: ✅ Clean State - HTML Annotation Tool Added
**Current Focus**: Interactive SID analysis documentation

---

## Current State Snapshot

### What We're Working On RIGHT NOW (2026-01-01)

**Recently Completed & Committed**: ✅ **HTML Annotation Tool v1.0** (committed Jan 1, 2026)

**Commit**: `bfdac30` - "feat: Add HTML Annotation Tool for interactive SID analysis"

**Implementation Summary**:
- ✅ **Interactive HTML Documentation Generator** (3,700+ annotations per file)
- ✅ **11 DataBlock_6 Sections Auto-Detected** (Voice Control, Pulse, Wave, Filter, Instruments, Sequences)
- ✅ **7 Specialized Annotation Functions** (Note decoding, SID registers, table semantics)
- ✅ **Clickable Navigation** (Table names → sections, addresses → hex dumps)
- ✅ **Professional VS Code Dark Theme** (Syntax highlighting + collapsible sections)
- ✅ **Complete Documentation** (544-line guide + README/CLAUDE updates)

**Files Added** (22 files, +38,484 insertions):
- `pyscript/generate_stinsen_html.py` (470 lines) - Main generator with 7 annotation functions
- `pyscript/html_export.py` (modified) - HTML export with navigation
- `docs/guides/HTML_ANNOTATION_TOOL.md` (544 lines) - Comprehensive guide
- `analysis/` (17 HTML examples) - Generated documentation files

**Current Uncommitted Changes**: Root cleanup in progress

**Test Status**: ✅ **All tests passing** (200+ tests, zero failures)

### What Just Happened (Recent Commits)

1. `bfdac30` - "feat: Add HTML Annotation Tool for interactive SID analysis" (Jan 1, 2026) ⭐ **Latest**
2. `7311a6f` - "docs: Update all documentation to v3.0.1" (Dec 28, 2025)
3. `371b167` - "docs: Update CHANGELOG.md for v3.0.1" (Dec 28, 2025)
4. `f03c547` - "fix: Restore working Laxity driver" (Dec 28, 2025)
5. `74489a9` - "release: v3.0.0 - Automatic SF2 Reference File Detection" (Dec 27, 2025)

---

## Project Overview

### What is SIDM2?

SIDM2 converts Commodore 64 SID music files to SID Factory II (SF2) format for editing and remixing.

**Key Achievement**: 99.93% frame accuracy for Laxity NewPlayer v21 files using custom driver.

**New**: Interactive HTML documentation generator with 3,700+ semantic annotations per file.

### Architecture

```
Input: SID file → Analysis → Driver Selection → SF2 Generation → Validation → Output: SF2 file
                                                                    ↓
                                     SF2 file → Packing → Output: Playable SID file
                                                                    ↓
                              SID file → HTML Generator → Interactive Documentation
```

**Driver Selection** (Auto-detection):
- Laxity NP21 → Laxity Driver (99.93% accuracy)
- SF2-exported → Driver 11 (100% accuracy)
- NewPlayer 20 → NP20 Driver (70-90% accuracy)
- Unknown → Driver 11 (safe default)

---

## Key Statistics

### Accuracy Metrics
- **Laxity Driver**: 99.93% frame accuracy (507/507 register writes)
- **SF2 Roundtrip**: 100% accuracy (perfect)
- **Test Suite**: 200+ tests, 100% pass rate
- **Real-world Validation**: 286 Laxity files, 100% success

### Codebase Stats
- **Python Files**: ~35 active scripts
- **Test Coverage**: 200+ tests across 15+ test files
- **Documentation**: 50+ markdown files in `docs/`
- **SID Collection**: 658+ files cataloged

### Performance
- **Conversion Speed**: 8.1 files/second (Laxity batch)
- **HTML Generation**: <5 seconds per file
- **SF2 Viewer Launch**: <2 seconds
- **Validation Run**: ~1 minute for 18 files

---

## Project Structure

```
SIDM2/
├── pyscript/              # ALL Python scripts
│   ├── conversion_cockpit_gui.py, sf2_viewer_gui.py
│   ├── siddump_complete.py, sidwinder_trace.py
│   ├── generate_stinsen_html.py    # NEW: HTML annotation tool
│   └── test_*.py                    # 200+ unit tests
├── scripts/               # Production conversion tools
│   ├── sid_to_sf2.py               # Main SID→SF2 converter
│   ├── sf2_to_sid.py               # SF2→SID packer
│   └── validate_sid_accuracy.py    # Frame-by-frame validator
├── sidm2/                 # Core Python package
│   ├── laxity_parser.py, laxity_converter.py, sf2_packer.py
│   ├── driver_selector.py, siddump.py, vsid_wrapper.py
│   └── sf2_editor_automation.py
├── docs/                  # Documentation (50+ files)
│   ├── guides/            # User guides + HTML_ANNOTATION_TOOL.md
│   ├── reference/         # Technical references
│   └── [various docs]
├── analysis/              # NEW: Generated HTML documentation
├── G5/drivers/            # SF2 driver templates
└── *.bat                  # Windows launchers
```

**See**: `docs/FILE_INVENTORY.md` for complete list

---

## Known Limitations

1. **Filter Accuracy**: 0% (Laxity filter format not converted)
   - Workaround: Manual filter editing in SF2 editor

2. **Voice 3**: Untested (no test files available)

3. **Multi-subtune**: Not supported (only first subtune converted)

4. **Laxity Only**: Custom driver only supports Laxity NewPlayer V21

---

## Development Guidelines

### Before Committing

1. **Run tests**: `test-all.bat` (200+ tests must pass)
2. **Update docs**: README.md, CLAUDE.md, CONTEXT.md
3. **Run cleanup**: `cleanup.bat --scan` (if files added/removed)
4. **Update inventory**: `update-inventory.bat` (if files moved)

### File Organization Rules

⚠️ **CRITICAL**: ALL `.py` files MUST be in `pyscript/` or `scripts/` or `sidm2/`
- ❌ NO `.py` files in project root
- ✅ Use `cleanup.bat --scan` to check compliance
- 📋 See `docs/guides/ROOT_FOLDER_RULES.md`

---

## Quick Reference

### Common Commands

**See CLAUDE.md for complete command reference**

```bash
# Convert SID to SF2
sid-to-sf2.bat input.sid output.sf2

# Generate HTML documentation
python pyscript/generate_stinsen_html.py input.sid

# View SF2 file
sf2-viewer.bat [file.sf2]

# Run all tests
test-all.bat

# Cleanup temporary files
cleanup.bat --clean --force
```

---

## Notes for AI Assistants

### Current Context (2026-01-01)

**Latest Work**: HTML Annotation Tool v1.0 (commit bfdac30, Jan 1, 2026)
**Current State**: Clean - all tests passing, root cleanup in progress
**Repository**: 100% compliant with ROOT_FOLDER_RULES.md
**Status**: Ready for continued work

### When Starting New Tasks

1. **Read this file first** - Understand current state
2. **Check git status** - See active changes
3. **Review CLAUDE.md** - Quick reference commands
4. **Run tests** - Ensure baseline works: `test-all.bat`

### Tool Usage Guidelines

- **Task(Explore)**: For open-ended codebase exploration
- **EnterPlanMode**: For non-trivial implementations
- **Read/Grep**: For specific files or patterns
- **TodoWrite**: Track multi-step tasks (use proactively)

### Testing Requirements

- **Always run**: `test-all.bat` before committing
- **Never commit**: If tests fail
- **Update docs**: When behavior changes

### Recent Features

**HTML Annotation Tool v1.0** (Jan 1, 2026):
- Interactive HTML generator with 3,700+ annotations
- 11 data sections, 7 annotation functions
- Clickable navigation, VS Code theme
- Complete documentation in `docs/guides/HTML_ANNOTATION_TOOL.md`

**Laxity Driver Restoration** (Dec 28, 2025):
- 99.93% accuracy restored (40-patch system)
- Wave table format fix (497x improvement)

**Auto SF2 Detection** (Dec 27, 2025):
- 100% accuracy for SF2-exported SID files
- Automatic driver selection

---

## References

- **Main Docs**: `README.md`, `CLAUDE.md`
- **Status**: `docs/STATUS.md`
- **Roadmap**: `docs/ROADMAP.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Troubleshooting**: `docs/guides/TROUBLESHOOTING.md`
- **Changelog**: `CHANGELOG.md`

---

**Last Updated**: 2026-01-01
**Updated By**: Claude Sonnet 4.5
**Next Review**: Before starting new work
