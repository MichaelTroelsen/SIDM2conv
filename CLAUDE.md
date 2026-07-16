# CLAUDE.md - AI Assistant Quick Reference

**SIDM2 v3.21.0** | SID→SF2 Converter | C64 Music Tools | Updated 2026-07-16

Converts native Laxity NP21 SID files to SF2 format (100% accuracy). Features: Auto-driver selection, VSID audio export, Batch Analysis (multi-pair comparison), Accuracy Heatmap (4 viz modes), Trace Comparison (tabbed HTML), SF2 Viewer, Conversion Cockpit, SID Inventory (658+ files), Python siddump/SIDwinder, Batch Testing, User Docs (4,300+ lines), CI/CD (5 workflows), 200+ tests

---

## Critical Rules

1. **Keep Root Clean**: ALL .py files in `pyscript/` only. No .py in root.
2. **Run Tests**: `test-all.bat` (164+ tests) before committing
3. **Update Docs**: Update README.md, CLAUDE.md, docs/ when changing code

**Enforcement**: `cleanup.bat --scan` | **See**: `docs/guides/ROOT_FOLDER_RULES.md`

---

## Quick Commands

```bash
# Convert (auto-selects best driver)
sid-to-sf2.bat input.sid output.sf2                  # Auto driver + validation
sid-to-sf2.bat input.sid output.sf2 --driver laxity  # Manual override
sid-to-sf2.bat input.sid output.sf2 --export-audio   # With VSID audio export
sid-to-sf2.bat input.sid output.sf2 --annotate       # With ASM annotation (text)
sid-to-sf2.bat input.sid output.sf2 --annotate --annotate-format html  # HTML docs

# GUI Tools
sf2-viewer.bat [file.sf2]     # View/export SF2
conversion-cockpit.bat        # Batch conversion GUI

# Analysis Tools
trace-viewer.bat input.sid -f 300                       # Interactive HTML trace (frame-by-frame)
trace-compare.bat file_a.sid file_b.sid                 # Compare two SID traces (tabbed HTML)
accuracy-heatmap.bat file_a.sid file_b.sid              # Accuracy heatmap (4 viz modes, Canvas)
batch-analysis.bat originals/ exported/                 # Batch analysis (standalone, HTML+CSV+JSON)
batch-analysis-validate.bat originals/ exported/        # Batch analysis (validation DB integration)
validation-dashboard.bat                                # Validation results dashboard
python pyscript/generate_stinsen_html.py file.sid       # HTML docs (3,700+ annotations)

# Batch Operations
batch-convert-laxity.bat      # All Laxity files
test-all.bat                  # 200+ tests
cleanup.bat                   # Clean + inventory

# Python Tools
python pyscript/siddump_complete.py input.sid -t30           # Frame dump
python pyscript/sidwinder_trace.py --trace out.txt input.sid # Trace (text)
python pyscript/create_sid_inventory.py                      # SID catalog
python pyscript/validate_filter_accuracy.py [--sid F] [--csv F] [--verbose]  # Filter accuracy vs zig64 ground truth

# Testing & Automation
test-batch-pyautogui.bat --directory G5/examples --max-files 10
install-vice.bat              # VSID for audio export
```

**Logging**: `-v/-vv` (verbose), `-q` (quiet), `--debug`, `--log-file`, `--log-json`

---

## Auto Driver Selection

Auto-selects best driver by player type via `DriverSelector.PLAYER_REGISTRY` (single source of truth):

| Player (player-id.exe string) | Driver | Accuracy |
|-------------------------------|--------|----------|
| `Laxity_NewPlayer_V21`, `Vibrants/Laxity`, `256bytes/Laxity` | Laxity | 99.93% |
| `SidFactory_II/*`, `SidFactory/*`, `SF2_Exported` | Driver11 | 100% |
| `NewPlayer_20`, `NewPlayer_20.G4`, `NP20` | NP20 | 70-90% |
| `Martin_Galway`, `Galway` | Galway | 88-96% |
| Unknown | Driver11 | safe default |

**Note**: "SidFactory_II/Laxity" = SF2-exported by author Laxity → Driver11 (NOT Laxity driver). Outputs: `output.sf2` + `output.txt`.

**Adding a new player** (3 steps): (1) Add to `DriverSelector.PLAYER_REGISTRY` in `sidm2/driver_selector.py`, (2) Add to `PLAYER_EXTRACTORS` or `PLAYER_CONVERTERS` in `sidm2/conversion_pipeline.py`, (3) Implement analyzer extending `player_base.BasePlayerAnalyzer`. See: `docs/reference/ACCURACY_MATRIX.md`

---

## Python Tools

**siddump** (`pyscript/siddump_complete.py`): 100% musical match, 44 tests. Classic siddump v1.08 format by default; opt-in `-b`/`--bits` bit-field column mode (waveform/filter bytes → named bit columns + note cents) and `-w`/`--written` write-precision mode (only registers the playroutine actually wrote this frame) — sid2txt-inspired. Docs: `docs/implementation/SIDDUMP_PYTHON_IMPLEMENTATION.md`

**SIDwinder** (`pyscript/sidwinder_trace.py`): Frame trace, 27 tests, cross-platform. Docs: `docs/analysis/SIDWINDER_PYTHON_DESIGN.md`

**HTML Annotation Tool** (`pyscript/generate_stinsen_html.py`): Interactive HTML docs with 3,700+ annotations, clickable navigation, 11 data sections, dynamic ROM/RAM detection. Docs: `docs/guides/HTML_ANNOTATION_TOOL.md`

**VSID** (`sidm2.vsid_wrapper`): SID→WAV via VICE, auto-fallback to SID2WAV. Docs: `docs/VSID_INTEGRATION_GUIDE.md`

**SF2 Automation** (`sidm2.sf2_editor_automation`): PyAutoGUI auto-loading, 100% pass. Docs: `PYAUTOGUI_INTEGRATION_COMPLETE.md`

**Filter Accuracy Validator** (`pyscript/validate_filter_accuracy.py`): Cross-validates Laxity NP21 filter tables extracted from SID binary against cycle-accurate zig64 ground truth trace. Checks resonance byte, sweep speed, and mode bits. Ground truth: `SID/stinsen_sid_trace_300frames.csv`

**Regenerator 2000 Labeler** (archived 2026-04-29 → `archive/cleanup_2026-04-29/orphaned_utils/regen2000_label_laxity_np21.py`): Auto-labels any NP21 file loaded in Regenerator 2000 via MCP HTTP. Restore from archive if needed.

**Regenerator 2000 Project Generator** (archived 2026-04-29 → `archive/cleanup_2026-04-29/orphaned_utils/gen_regen2000_project.py`): Generates `.regen2000proj` directly from a PRG binary with NP21 labels pre-applied. Restore from archive if needed.

**zig64 SID Tracer** (`tools/sidm2-sid-trace.exe`): Pre-built cycle-accurate SID register tracer. Usage: `sidm2-sid-trace.exe file.prg [frames] [init_hex] [play_hex] [subtune]`. Pass init/play (from the PSID header) + subtune for non-Laxity files (e.g. Galway); defaults are $1000/$1003/0. Output: CSV on stderr. **Fails honestly (v3.21.0)**: prints `FAILED:` + exits non-zero when it cannot drive a file (unresolved/implausible IRQ handler, or 0 SID writes across the window) — an empty trace is NEVER emitted as if it were a silent tune. **Check the exit code**; don't just parse stderr. 22 RSID files are honestly untraceable (no autonomous VIC/CIA interrupt delivery). Gotcha: a too-short window looks identical to a broken trace (Arkanoid = 0 writes at 5 frames, 460 at 200) — use ≥200 frames before calling a file broken. Source of truth: `tools/sidm2_sid_trace.zig` **in this repo** (rebuild: copy to `C:\Users\mit\Downloads\zig64\src\examples\`, `zig build`, copy `zig-out/bin/sidm2-sid-trace.exe` back — the zig64 copy goes stale).

---

## Project Structure

```
SIDM2/
├── pyscript/           # ALL Python scripts (v2.6)
│   ├── siddump_complete.py, sidwinder_trace.py  # Python tools
│   ├── conversion_cockpit_gui.py, sf2_viewer_gui.py
│   └── test_*.py                    # 200+ unit tests
├── scripts/            # Production tools
│   ├── sid_to_sf2.py               # Main converter
│   ├── sf2_to_sid.py, validate_sid_accuracy.py
├── sidm2/              # Core package
│   ├── laxity_parser.py, laxity_converter.py, sf2_packer.py
│   ├── driver_selector.py (v2.8.0), siddump.py, logging_config.py
├── tools/              # External tools (optional fallback)
├── G5/drivers/         # SF2 drivers (laxity, driver11, np20)
├── docs/               # Documentation
└── *.bat               # Launchers
```

**Complete**: `docs/FILE_INVENTORY.md`

---

## Essential Constants

**Laxity**: `INIT=0x1000`, `PLAY=0x10A1`, `INSTRUMENTS=0x1A6B`, `WAVE=0x1ACB`
**SF2 Driver 11**: `SEQ=0x0903`, `INST=0x0A03`, `WAVE=0x0B03`, `PULSE=0x0D03`, `FILTER=0x0F03`
**Control**: `END=0x7F`, `GATE_ON=0x7E`, `GATE_OFF=0x80`, `TRANSPOSE=0xA0`

**Full reference**: `docs/ARCHITECTURE.md`

---

## Known Limitations

| Source → Driver | Accuracy | Status |
|----------------|----------|--------|
| SF2-exported → Driver 11 | 100% | ✅ Perfect (including SidFactory_II/Laxity) |
| Native Laxity NP21 → Laxity driver | 99.93-100% | ✅ Production |
| Native Laxity NP21 → Driver 11 | 1-8% | ⚠️ Use Laxity driver instead |
| Martin Galway → trace native driver | ~100% | ✅ 40/40 build, 30/40 objectively clean (`bin/`, not default); see `docs/players/GALWAY.md` |
| ROMUZAK V6.3 → native driver | ~98-100% | ✅ Byte-exact wf/pulse/AD-SR (`bin/`, not default) |
| Maniacs of Noise (Jeroen Tel) → native driver | 100% byte-exact (Hawkeye sub 2/3) | ✅ Hawkeye + Cybernoid I/II + Myth + Supremacy all build (`bin/`, not default); see `docs/players/MON.md` |
| Rob Hubbard V1 → native driver | pulse/freq/filter 100% (Monty/Commando/Zoids/Last_V8) | ✅ ~12 V1 tunes + subsongs (`bin/`, not default); per-instrument pulse engine; see `docs/players/HUBBARD.md` |
| Rob Hubbard V2 (Delta class) → native driver | Delta theme freq/pulse/filter 100% (wf 85-96%) | 🚧 6 split-songs built; swallow-class state-region relocation + spin-class + note-format laggards open; see `docs/players/HUBBARD.md` |
| Jeroen Kimmel (Hubbard-derived) → Driver 11 | **11/12 voice-medians exact 100%** (frame-pitch) | ✅ 4 files / 9 SF2s incl. Radax 6 subtunes; arp+PWM+freq-slide(T0)+drum ported (`bin/`, not default); see `docs/players/KIMMEL.md` |
| Charles Deenen (MoN/Deenen replay) → Driver 11 | 4 clean wins ~100/100 (Ding, B_A_T, LotR, After_the_War); 10/19 located | 🚧 + 8 freebies at 100% (3 SM shim, 2 Hubbard, 3 MoN-TTWII sub0); builder REFUSES implausible decodes (`bin/`, not default); see `docs/players/DEENEN.md` |
| Future Composer → Driver 11 | trace-validated | 🚧 Stage A only, `$1800` variant; native driver TODO |
| DMC (Demo Music Creator, Johannes Bjerregaard) → native driver | Rockbuster ~97/100/100; Balloon 77 parts → ONE 400s SF2 (wf/pulse 100×3, step-grid) | 🚧 **56/88 onset-eligible**, all build (`bin/`, not default); bundle-bound files keep high part counts; see `docs/players/DMC.md` |
| Sound Monitor (Hülsbeck) → native driver | corpus strict sweep 99.23% freq+wf (global-delay, EVERY part); Dance parts 2-6 + Fuck_Off 242s at 100.0 every register; 11 songs/27 parts | ✅ 11/11 Fun_Fun files build (`bin/`, not default); see `docs/players/SOUNDMONITOR.md` |
| SID Duzz' It (Gallefoss/Tjelta) → Driver 11 (Stage A) | strict onset+pitch medians: A 98.3, D 100, **C 86.0** (was 66.7), B 74.8, **E 50.8** (was 47.5; 114 files incl. the harder wrapper gen), **DELTA win 89.8/strict 55.5** (8 files, zp + page-$03 sub-variant), V 21.8 | 🚧 **324 located, 348 Stage A SF2s** (0 failures, `bin/`, not default); C walk decoded + E $Cx trailing-delay fix + E single-store-init gen + DELTA-class play+3 wrapper cracked + multi-subtune (A/C/E) + "sixth layout" wrapper cracked; native Stage B TODO; see `docs/players/SDI.md` |

**Critical**: "SidFactory_II/Laxity" ≠ native Laxity! Check player-id: "SidFactory" = use Driver 11, "Laxity_NewPlayer_V21" = use Laxity driver

**Other**: Only native Laxity NP21 supported by Laxity driver, single subtune only, filter accuracy 100% (Stinsen verified v3.1.4)

---

## Documentation

**Start**: `README.md` | `docs/guides/GETTING_STARTED.md` | `docs/guides/TROUBLESHOOTING.md`

**User Guides** (3,400+ lines): `TUTORIALS.md`, `FAQ.md`, `BEST_PRACTICES.md`, `SF2_VIEWER_GUIDE.md`, `CONVERSION_COCKPIT_USER_GUIDE.md`, `LAXITY_DRIVER_USER_GUIDE.md`, `VALIDATION_GUIDE.md`, `LOGGING_AND_ERROR_HANDLING_GUIDE.md`

**Technical**: `docs/ARCHITECTURE.md`, `docs/COMPONENTS_REFERENCE.md`, `docs/reference/SF2_FORMAT_SPEC.md`

**Players (consolidated 2026-07-05)**: `docs/players/PLAYBOOK.md` (**the cross-player porting method** — staged Stage A/B pipeline, size caps, gotchas, new-player checklist), `docs/players/README.md` (support index), per-player docs (`LAXITY`, `GALWAY`, `MON`, `ROMUZAK`, `FUTURECOMPOSER`, `DRIVER11`, `NP20`, `CLUSTERS`), `docs/reference/ACCURACY_MATRIX.md` (accuracy source of truth, v3.13.0), `docs/ROADMAP.md` (consolidation/optimization plan)

**Complete index**: `docs/INDEX.md`

---

## For AI Assistants

**Tools**: Task(Explore) for broad searches | Read/Grep for specific files | EnterPlanMode for multi-file changes

**Before Commit**: Run `test-all.bat` (200+ tests) | Update README.md, CLAUDE.md, docs/ if changed | Run `update-inventory.bat` if files added/removed

**After building native SF2s**: run `py -3 pyscript/gen_sf2_index.py` to refresh the complete build inventory (all songs + part counts) in `docs/SF2.md` (the curated fidelity tables above the GENERATED markers are hand-maintained).

**On Version Bump**: Add the release entry to `CHANGELOG.md` (the canonical version history — NOT this file; CLAUDE.md stays compact) AND `STORY.md` (the project narrative — append to per-version index; update Eras / deep-tech sections only if a new architectural finding warrants it). Bump `sidm2/__init__.py __version__` + `__build_date__`. Update the Known Limitations table + relevant `docs/` if behavior changed.

**Debug**: Check `output.txt` → Compare dumps (`siddump_complete.py`) → Compare audio

---

## TDZ C64 Knowledge Base (shared MCP)

`mcp__tdz-c64-knowledge` is a **shared, cross-project** C64/SID knowledge base (other projects read+write it too). SIDM2 has seeded 21 documents there: a **knowledge card per player** (Laxity, Galway, MoN, Hubbard, DMC, Sound Monitor, ROMUZAK, Future Composer, SDI, Driver 11), the **RE technique catalog** (from `PATTERNS.md`/`PLAYBOOK.md`), plus reference docs (SF2 + PSID formats, native-driver how-to, fidelity toolchain, tooling landscape, the STORY, the Laxity disassembly, 6502 primers).

**Use it:**
- **Before starting a new player**: `search_docs` / `list_docs` for an existing card or scene-history leads (SIDin ezines, c=hacking, codebase64 are all indexed) before hunting d64s/disassemblies from scratch.
- **After confirming new findings**: write a card back so the work is queryable outside this repo. Cards are `add_document`-only (no in-place edit): write the file to an allowed dir (`~/.tdz-c64-knowledge/temp/`, the repo, or `~/Downloads/tdz-c64-knowledge-input`), then ingest. Match the existing card schema (JSON block: id/name/aliases/authors/memory/entry/data_format/effects/edges/quirks/sources + prose Overview/Quirks/Disassembly/Verification/Sources). Cards stay `status: in-progress` until assembled+run through the KB's own `mcp-c64` tool — describe SIDM2's own byte-exact verification honestly in the Verification prose.
- **NOT a substitute** for SIDM2's own zig64/py65 byte-exact discipline (PATTERNS.md D2/D4 — never trust a source blindly). The general corpus won't have compiled-binary table offsets for any specific rip; that's still native RE per file/variant.

Full details + card schema: `memory/tdz-c64-knowledge-base.md`.

---

## Version History

Full release history lives in **`CHANGELOG.md`** (Keep-a-Changelog format,
v0.x–current). Project narrative: **`STORY.md`**. This file stays compact —
do not add per-version entries here.

---

**End of Quick Reference**

**Lines**: ~215 (version history moved to CHANGELOG.md) | **For full docs**: See README.md and docs/
