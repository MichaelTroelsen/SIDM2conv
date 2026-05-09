# SIDM2 Project Context

**Version**: 3.4.1
**Last Updated**: 2026-05-09
**Status**: ✅ Production — all four original criteria closed; F10-load 100% solo on canonical corpus
**Current Focus**: Reactive — chasing upstream resolution of [Chordian/sidfactory2#211](https://github.com/Chordian/sidfactory2/issues/211) (NULL `std::string` deref in SF2II's `m_TableColorRules` destructor at `+0x63fab`) which blocks Hubbard / Soundmonitor F10-load. Conversion succeeds for those files; only the editor crashes.

---

## Current State Snapshot

### What's Working

**4-criterion converter goal — all 4 closed:**
- ✅ **Criterion 1: Plays correctly in SID Factory II** — auto-detect picks laxity driver for both Stinsen (`SidFactory_II/Laxity`) and Unboxed (`Laxity_NewPlayer_V21`); zig64 trace 100% match (1910/1910 + 2734/2734 SID register writes)
- ✅ **Criterion 2: Editor displays real sequences** — Block 5 MusicData populated with real addresses; multi-pattern segmentation (Stage 2.5) splits each voice's NP21 stream into editor-friendly segments; Block 3 emits proper `TextFieldSize` byte format (v3.4.1)
- ✅ **Criterion 3: Edits affect playback** (closed in v3.3.0) — runtime translator at `$0F0E` regenerates shadow buffer on every PLAY tick from SF2-format edit-area bytes; `ch_seq_ptr` patched at `$1A1C/$1A1F`. Multi-pattern translator at `$0F8E` (87 bytes of 6502, v3.4.0) handles segmented voices
- ✅ **Criterion 4: Round-trip SID→SF2→SID** — register accuracy 100%, title/author/copyright preserved via SF2 aux block id=5 reader

**F10-load reliability** (v3.4.1):
- Stinsen + Unboxed solo F10-load: **100%** (15/15 each, no retry wrapper needed)
- Broader 11-file corpus: **9/11 = 82%**
- The 2 failures (Hubbard *Action_Biker* `$C000`, Soundmonitor *Byte_Bite* `$7FF8`) are blocked on upstream issue Chordian/sidfactory2#211. Conversion still produces a valid `.sf2`; audio plays via VICE / sidplayer.

**Test Status**: ✅ **798 passed, 7 skipped, 2 xfailed** as of commit `18a542d`.

### What Just Happened (Recent Commits)

1. `18a542d` — `test: fix 11 stale test_sf2_writer.py cases (Stage 2.5 contract drift)` (May 9, 2026) ⭐ **Latest**
2. `67f80df` — `release: v3.4.1 — Block 3 Format Fix + Stage 8.5 Toolkit` (May 9, 2026)
3. `3f94d55` — `feat(stage8.5): PageHeap exposes use-after-free at +0x63fab` (May 9, 2026)
4. `38447a5` — `chore(stage8.5): appverifier tune + disable scripts` (May 9, 2026)
5. `a4f0b2c` — `feat: Stage 8.5 debugging toolkit — AppVerifier setup + v2 debugger` (May 9, 2026)
6. `e3efadc` — `fix(stage8.5): editor-only Block 3 tables in edit area` (May 9, 2026)
7. `4950b04` — `fix: 4→5 tuple in empty-patterns path; corpus pass rate harness` (May 8, 2026)
8. `04f5829` — `fix: Block 3 emits TextFieldSize, not NameLen — solo-load 47% → 100%` (May 8, 2026)
9. `dc535e1` — `docs: CHANGELOG.md — v3.4.0 release entry` (May 8, 2026)
10. `5c7820f` — `add: star.html — Star Wars opening-crawl viewer for the changelog` (May 8, 2026)

---

## Project Overview

### What is SIDM2?

SIDM2 converts Commodore 64 SID music files to SID Factory II (SF2) format for editing and remixing.

**Key Achievement**: 100% frame accuracy on Stinsen + Unboxed (verified against zig64 cycle-accurate ground truth, 1910/1910 + 2734/2734 register writes match) for Laxity NewPlayer v21 files using a custom driver. F10-load now reliable enough to work without a retry wrapper for canonical files.

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
- Galway → Galway converter (88-96% accuracy)
- NewPlayer 20 → NP20 Driver (70-90% accuracy)
- Unknown / non-Laxity-with-c64_data → Stage 8 Path A embed-binary fallback (audio plays correctly via the original player code; editor view limited)

---

## Key Statistics

### Accuracy Metrics
- **Laxity Driver**: 100% frame accuracy on canonical corpus (Stinsen 1910/1910 + Unboxed 2734/2734)
- **SF2 Roundtrip**: 100% accuracy (perfect)
- **F10-load (canonical)**: 100% solo (no retry wrapper)
- **F10-load (broader 11-file corpus)**: 82% — 2 failures blocked upstream
- **Test Suite**: 798 tests, 100% pass rate
- **Real-world Validation**: 286 Laxity files, 100% conversion success

### Codebase Stats
- **Python Files**: ~40 active scripts
- **Test Coverage**: 798 tests across the test suite
- **Documentation**: 50+ markdown files in `docs/`
- **SID Collection**: 658+ files cataloged

### Performance
- **Conversion Speed**: 8.1 files/second (Laxity batch)
- **HTML Generation**: <5 seconds per file
- **SF2 Viewer Launch**: <2 seconds
- **F10-load (per attempt)**: ~5.5 seconds

---

## Project Structure

```
SIDM2/
├── pyscript/              # ALL Python scripts
│   ├── conversion_cockpit_gui.py, sf2_viewer_gui.py
│   ├── siddump_complete.py, sidwinder_trace.py
│   ├── sf2_debug_inspect_v2.py    # NEW v3.4.1: HW watchpoints + dbghelp
│   ├── sf2_corpus_pass_rate.py    # NEW v3.4.1: corpus harness
│   ├── sf2_pass_rate.py           # NEW v3.4.1: solo harness
│   ├── disasm_rva.py              # NEW v3.4.1: RVA disassembly
│   ├── diff_block3.py             # NEW v3.4.1: SF2 Block 3 diff
│   └── test_*.py                   # 798 unit tests
├── scripts/               # Production conversion tools
│   ├── sid_to_sf2.py               # Main SID→SF2 converter
│   ├── sf2_to_sid.py               # SF2→SID packer
│   └── validate_sid_accuracy.py    # Frame-by-frame validator
├── sidm2/                 # Core Python package
│   ├── laxity_parser.py, sf2_writer.py, sf2_packer.py
│   ├── sf2_header_generator.py    # v3.4.1: per-instance Block 3 addr overrides
│   ├── np21_pattern_segmenter.py  # v3.4.0: multi-pattern split
│   ├── driver_selector.py, conversion_pipeline.py
│   └── sf2_to_np21.py             # v3.3.0: runtime translator reference
├── docs/                  # Documentation (50+ files)
│   ├── stage8.5_debugging_toolkit.md   # NEW v3.4.1
│   ├── guides/, reference/, archive/
├── G5/drivers/            # SF2 driver templates
├── appverifier-*.bat      # NEW v3.4.1: AppVerifier setup/tune/disable
└── *.bat                  # Windows launchers
```

**See**: `docs/FILE_INVENTORY.md` for complete list

---

## Known Limitations

1. **Hubbard / Soundmonitor F10-load**: deterministic crash for SIDs with load_addr outside `$0E00-$3000`. Blocked on [Chordian/sidfactory2#211](https://github.com/Chordian/sidfactory2/issues/211). Conversion succeeds; audio plays externally.

2. **Multi-subtune**: Not supported (only first subtune converted).

3. **Editor edits to Wave/Pulse/Filter/Instruments tables**: don't propagate to playback (criterion-3 translator bridges sequences only). The NP21 binary embedded at `$1000` keeps reading its own table data. Only sequence edits are live.

4. **Pattern segmentation is heuristic**: NP21 has no native pattern table — Stage 2.5 splits the flat byte stream at instrument-prefix bytes (`0xA0-0xBF`) as a structurally-valid best-effort. Round-trip property preserves byte-for-byte audio fidelity.

---

## Development Guidelines

### Before Committing

1. **Run tests**:
   ```bash
   py -3 -m pytest pyscript/ -q --ignore=pyscript/test_detection_fix.py --ignore=pyscript/test_disassembler.py
   ```
   (798 tests; 2 ignored modules have unrelated import issues)
2. **Run corpus regression**:
   ```bash
   py -3 tests/test_corpus_regression.py
   ```
   (Stinsen + Unboxed zig64 trace match against `tests/golden/*.trace.csv`)
3. **Update docs**: README.md, CLAUDE.md, CONTEXT.md if behavior changed

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

# Solo F10-load harness (verify a single SF2 loads cleanly N times)
py -3 pyscript/sf2_pass_rate.py path/to.sf2 15

# Broader corpus harness (11 files × N trials)
py -3 pyscript/sf2_corpus_pass_rate.py 5

# Decode + diff Block 3 between two SF2 files
py -3 pyscript/diff_block3.py file_a.sf2 file_b.sf2

# View SF2 file
sf2-viewer.bat [file.sf2]

# Run all tests
test-all.bat
```

### Stage 8.5 Debugging Toolkit (admin once)

For diagnosing the Chordian/sidfactory2#211 upstream crash. See
`docs/stage8.5_debugging_toolkit.md` for the full workflow.

```cmd
appverifier-pageheap.bat       # Run as admin: enable PageHeap + WER LocalDumps
                               # Then run harness; new dumps in %LOCALAPPDATA%\CrashDumps
appverifier-disable.bat        # Run as admin: revert all changes

py -3 pyscript/sf2_debug_inspect_v2.py file.sf2          # spawn-debug + drive F10
py -3 pyscript/sf2_debug_inspect_v2.py --watch <addr> file.sf2  # HW watchpoint
py -3 pyscript/sf2_debug_inspect_v2.py --attach <pid>           # attach to running
```

---

## Notes for AI Assistants

### Current Context (2026-05-09)

**Latest work**: v3.4.1 release shipped (commits `04f5829..18a542d`). Block 3 NameLen→TextFieldSize fix took canonical-corpus solo F10-load from 47% to 100%. Stage 8.5 investigation localized residual non-Laxity F10 crash to upstream SF2II source bug (filed as Chordian/sidfactory2#211).

**Status**: Clean — all tests passing (798), working tree clean.

**Where to look first**:
- Memory at `~/.claude/projects/.../memory/`:
  - `project-status.md` — full investigation history (caveat: snapshot dated; Block 3 fix + Stage 8.5 closure documented in newer entries)
  - `stinsen-load-crash-resolved.md` — the v3.4.1 Block 3 fix story
  - `stage8.5-load-addr-crash.md` — the upstream-blocked crash; root cause + filed issue

### When Starting New Tasks

1. **Read this file first** — Understand current state
2. **Check git status** — See active changes
3. **Review CLAUDE.md** — Quick reference commands + version history
4. **Check memory index** — `~/.claude/projects/.../memory/MEMORY.md`
5. **Run tests** — `py -3 -m pytest pyscript/ -q --ignore=pyscript/test_detection_fix.py --ignore=pyscript/test_disassembler.py`

### Tool Usage Guidelines

- **Task(Explore)**: For open-ended codebase exploration
- **EnterPlanMode**: For non-trivial implementations
- **Read/Grep**: For specific files or patterns
- **TodoWrite / TaskCreate**: Track multi-step tasks (use proactively)

### Testing Requirements

- **Always run**: pytest + corpus regression before committing
- **Never commit**: If tests fail
- **Update docs**: When behavior changes (CHANGELOG, README, CLAUDE, CONTEXT)

---

## References

- **Main Docs**: `README.md`, `CLAUDE.md`
- **Status**: `docs/STATUS.md`
- **Roadmap**: `docs/ROADMAP.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Troubleshooting**: `docs/guides/TROUBLESHOOTING.md`
- **Stage 8.5 toolkit**: `docs/stage8.5_debugging_toolkit.md`
- **Changelog**: `CHANGELOG.md` (current v3.x), `docs/archive/changelogs/` (v0.x-v2.x archives)
- **Upstream issue tracking**: [Chordian/sidfactory2#211](https://github.com/Chordian/sidfactory2/issues/211)

---

**Last Updated**: 2026-05-09
**Updated By**: Claude Opus 4.7 (1M context)
