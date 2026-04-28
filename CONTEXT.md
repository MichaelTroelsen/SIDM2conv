# SIDM2 Project Context

**Version**: 3.2.1
**Last Updated**: 2026-04-28
**Status**: ✅ Production — first end-to-end success on Stinsen + Unboxed shipped (criteria 1, 2, 4 closed; criterion 3 deferred to scheduled agent on 2026-05-11)
**Current Focus**: Edit-affects-playback architectural gap (criterion 3) — runtime SF2→NP21 sequence translator in laxity SF2 driver

---

## Current State Snapshot

### What We're Working On RIGHT NOW (2026-04-28)

**Recently Completed & Pushed**: ✅ **First end-to-end success + project cleanup** (commits `afffc05`–`1d4e82a`)

**Status**: 4-criterion converter goal — 3 of 4 closed:
- ✅ **Criterion 1: Plays correctly in SID Factory II** — auto-detect picks laxity driver for both Stinsen (`SidFactory_II/Laxity`) and Unboxed (`Laxity_NewPlayer_V21`); zig64 trace 100% match
- ✅ **Criterion 2: Editor displays real sequences** — Block 5 MusicData populated with real addresses; `pyscript/verify_editor_view.py` simulator confirms decoding succeeds without asserts
- ⏸️ **Criterion 3: Edits affect playback** — architectural gap; player and editor disagree on byte format. Deferred to scheduled remote agent (`trig_01Hv7p9xq98LuEVobHVHz5xb`, fires 2026-05-11). Documented inline as `EDITABLE-REPLAY GAP` comment in `sidm2/sf2_writer.py`
- ✅ **Criterion 4: Round-trip SID→SF2→SID** — register accuracy 100%, title/author/copyright preserved via SF2 aux block id=5 reader

**Test Status**: ✅ **786 passed, 8 skipped** (consistent baseline through cleanup)

### What Just Happened (Recent Commits)

1. `1d4e82a` - "fix: update path references for SID/<composer> dir migration" (Apr 28, 2026) ⭐ **Latest**
2. `482c239` - "chore: archive 24 stale/redundant docs (cleanup 2026-04-28)" (Apr 28, 2026)
3. `c7e13b1` - "chore: archive 5 batches of unused project files (cleanup 2026-04-28)" (Apr 28, 2026)
4. `1564c6e` - "chore: gitignore root-level session test artifacts" (Apr 28, 2026)
5. `7b39286` - "release: v3.2.1 — first end-to-end success for Stinsen + Unboxed" (Apr 27, 2026)
6. `afffc05` - "fix: First successful end-to-end conversion for Stinsen + Unboxed" (Apr 27, 2026)

---

## Project Overview

### What is SIDM2?

SIDM2 converts Commodore 64 SID music files to SID Factory II (SF2) format for editing and remixing.

**Key Achievement**: 100% frame accuracy on Stinsen + Unboxed (verified against zig64 cycle-accurate ground truth, 1909/1909 + 2733/2733 register writes match) for Laxity NewPlayer v21 files using a custom driver.

**Open architectural piece**: criterion 3 (editor edits affect playback) requires runtime SF2→NP21 sequence translation in the laxity SF2 driver — scheduled agent fires 2026-05-11.

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
│   ├── archive/           # Archived documentation
│   │   └── changelogs/    # Versioned changelog archives (v0.x, v1.x, v2.x)
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

### Current Context (2026-01-02)

**Latest Work**: Changelog split and organization (commit 7ae28f8, Jan 2, 2026)
**Current State**: Clean - all tests passing (260+), working tree clean
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

**Changelog Organization** (Jan 2, 2026):
- Split CHANGELOG.md into versioned archives (48% size reduction)
- Organized by major version for easier navigation
- All 43 versions preserved with complete history
- Archive navigation guide in `docs/archive/changelogs/README.md`

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
- **Changelog**: `CHANGELOG.md` (current v3.x), `docs/archive/changelogs/` (v0.x-v2.x archives)

---

**Last Updated**: 2026-04-28
**Updated By**: Claude Opus 4.7 (1M context)
**Next Review**: After scheduled criterion-3 agent fires (2026-05-11)
