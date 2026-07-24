# CLAUDE.md - AI Assistant Quick Reference

**SIDM2 v3.21.0** | SID→SF2 Converter | C64 Music Tools | Updated 2026-07-16

Converts native Laxity NP21 SID files to SF2 format (100% accuracy). Features: Auto-driver selection, VSID audio export, Batch Analysis (multi-pair comparison), Accuracy Heatmap (4 viz modes), Trace Comparison (tabbed HTML), SF2 Viewer, Conversion Cockpit, SID Inventory (658+ files), Python siddump/SIDwinder, Batch Testing, User Docs, CI/CD (5 workflows), ~1,900 tests

---

## Critical Rules

1. **Keep Root Clean**: ALL .py files in `pyscript/` only. No .py in root.
2. **Run Tests**: `test-all.bat` (7 suites) before committing; `python -m pytest` runs all ~1,900
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
audio-tightness.bat orig.sid conv.sf2 --driver-init 0x1000 --driver-play 0x1003  # Onset-timing/attack-shape "tightness" (register-exact != audio-tight)
batch-analysis.bat originals/ exported/                 # Batch analysis (standalone, HTML+CSV+JSON)
batch-analysis-validate.bat originals/ exported/        # Batch analysis (validation DB integration)
validation-dashboard.bat                                # Validation results dashboard
python pyscript/generate_stinsen_html.py file.sid       # HTML docs (3,700+ annotations)

# Batch Operations
batch-convert-laxity.bat      # All Laxity files
test-all.bat                  # 7 suites (pytest runs all ~1,900)
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

**SIDwinder** (`pyscript/sidwinder_trace.py`): Frame trace, 27 tests, cross-platform. Docs: `docs/archive/analysis_2026-01-02/SIDWINDER_PYTHON_DESIGN.md` (archived)

**HTML Annotation Tool** (`pyscript/generate_stinsen_html.py`): Interactive HTML docs with 3,700+ annotations, clickable navigation, 11 data sections, dynamic ROM/RAM detection. Docs: `docs/guides/HTML_ANNOTATION_TOOL.md`

**VSID** (`sidm2.vsid_wrapper`): SID→WAV via VICE, auto-fallback to SID2WAV. Docs: `docs/VSID_INTEGRATION_GUIDE.md`

**SF2 Automation** (`sidm2.sf2_editor_automation`): PyAutoGUI auto-loading, 100% pass. Docs: `archive/cleanup_2026-04-28/old_docs/completion_reports/PYAUTOGUI_INTEGRATION_COMPLETE.md` (archived)

**Filter Accuracy Validator** (`pyscript/validate_filter_accuracy.py`): Cross-validates Laxity NP21 filter tables extracted from SID binary against cycle-accurate zig64 ground truth trace. Checks resonance byte, sweep speed, and mode bits. Ground truth: `SID/stinsen_sid_trace_300frames.csv`

**Regenerator 2000 Labeler** (archived 2026-04-29 → `archive/cleanup_2026-04-29/orphaned_utils/regen2000_label_laxity_np21.py`): Auto-labels any NP21 file loaded in Regenerator 2000 via MCP HTTP. Restore from archive if needed.

**Regenerator 2000 Project Generator** (archived 2026-04-29 → `archive/cleanup_2026-04-29/orphaned_utils/gen_regen2000_project.py`): Generates `.regen2000proj` directly from a PRG binary with NP21 labels pre-applied. Restore from archive if needed.

**zig64 SID Tracer** (`tools/sidm2-sid-trace.exe`): Pre-built cycle-accurate SID register tracer. Usage: `sidm2-sid-trace.exe file.prg [frames] [init_hex] [play_hex] [subtune]`. Pass init/play (from the PSID header) + subtune for non-Laxity files (e.g. Galway); defaults are $1000/$1003/0. Output: CSV on stderr. **Fails honestly (v3.21.0)**: prints `FAILED:` + exits non-zero when it cannot drive a file (unresolved/implausible IRQ handler, or 0 SID writes across the window) — an empty trace is NEVER emitted as if it were a silent tune. **Check the exit code**; don't just parse stderr. Gotcha: a too-short window looks identical to a broken trace (Arkanoid = 0 writes at 5 frames, 460 at 200) — use ≥200 frames before calling a file broken. Source of truth: `tools/sidm2_sid_trace.zig` **in this repo** (rebuild: copy to `C:\Users\mit\Downloads\zig64\src\examples\`, `zig build`, copy `zig-out/bin/sidm2-sid-trace.exe` back — the zig64 copy goes stale).

**RSID escape hatch — the VICE wrapper** (`C:\Users\mit\claude\sid-reference-project\scripts\dev\vsid-trace.js`, a *separate* project): zig64 has **no autonomous VIC/CIA interrupt delivery**, so RSID files that declare `play=$0000` and install their own IRQ are untraceable here — the tracer now says so instead of faking a 0-write trace. `vsid` runs a full emulated C64, so the machine drives the player. **21 of SIDM2's 22 untraceable RSIDs trace under it** (incl. `Broken_Ass` 1068 writes, `Myth` 259, `A_Mind_Is_Born` 100; only `Final_Countdown_BASIC` = 0, plausibly genuine). Cross-validated: on a PSID both tools drive (Stinsen, 16 frames) both report **exactly 90** changed-value writes. Usage: `node vsid-trace.js <file.sid> --frames N --json --changed-only` (`--changed-only` matches this tracer's semantics; vsid otherwise records redundant writes). Gotchas: **vsid exits 1 on normal termination** — check for the dump file, not the exit code; cycle timings are NOT comparable between the tools (~1 frame apart), only the write *sequence* agrees. Not wired into SIDM2. See `docs/players/PLAYBOOK.md`.

---

## Project Structure

```
SIDM2/
├── pyscript/           # ALL Python scripts (v2.6)
│   ├── siddump_complete.py, sidwinder_trace.py  # Python tools
│   ├── conversion_cockpit_gui.py, sf2_viewer_gui.py
│   └── test_*.py                    # ~1,900 unit tests
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
| Mainstream MoN / Jeroen Tel (SID/Tel_Jeroen, 179 files) → mon_parser | B1-indirect bucket: **12/24 onset-EXACT** (unchanged), plus **Tel_1 24%→86%** via a new row-tie flag, and **Monitor_Madness_1 2%→75/106, Monitor_Madness_2 3/146→90/146, Trying_Out_2 1/59→41/59** via a `bin/mon_validate.py` calibration fix (see note below). Trying_Out 78%, Zynon_Zak 84%, Bantam 77%, Starball 76%, Alloyrun 61% | 🚧 NEW MoN GENERATION cracked (ab99032): `_locate_b1` + `_voice_blocks_tel`. Same-day `_locate_b1_row_variant` + `_locate_tel_instr_fields`, 4 rounds (orderlist REPEAT/off1/classic-row → row-ctrl off1 → row length-mask read per-file → column-major instrument tables). **Row ctrl bit5 is a TIE flag** (`_tel_row_tie`, disassembly-confirmed via a raw zig64/vsid register trace) — a row can skip its own end-of-note gate-off, holding the SID gate through to the next row so THAT row's fresh waveform write doesn't retrigger the envelope on real hardware. Tel_1's residual was mid-note wave-program gate cycling (genuine Stage-B, hand-traced, not a grammar gap). **The validator itself (`bin/mon_validate.py`) was ALSO miscalibrating 3 files** — their raster-IRQ init primes a voice's waveform register at frame 0, and siddump's `is_first_frame` display rule shows that as a spurious onset; rewrote the offset calibration as a joint brute-force search over offset + a per-voice "drop leading artifact" candidate (first attempt regressed Cybernoid sub1 by dropping unconditionally — fixed by making the drop a search candidate, not a forced step). All signature-gated + disassembly-confirmed; one earlier round caused a real regression mid-session (over-loose proximity match), caught + fixed with a stride-consistency check before shipping — verify against the FULL bucket AND the 5-check byte-exact gate, not just the target file. Remaining: Monitor_Madness_2/Trying_Out_2 not at their theoretical max (validator finds a locally-good, not fully optimal, offset); 85-file no-copy bucket untouched. See `memory/mainstream-mon-tel.md` |
| Rob Hubbard V1 → native driver | pulse 100% (modelled engine, all voices/4 tunes), freq 99.3-100; **filter NOT exercised** (Hubbard never writes cutoff — the old "filter 100%" was 0==0) | ✅ 12 V1 tunes + subsongs (`bin/`, not default); per-instrument pulse engine; see `docs/players/HUBBARD.md` |
| Rob Hubbard V2 (Delta class) → native driver | Delta theme freq 100%, wf 85-97% (pessimistic — residual is pure ±1-frame skew); **pulse 100% is CAPTURED, not modelled** (`hp_engine=0`); filter not exercised | 🚧 6 split-songs + Delta + 7 swallow built; swallow-class state-region relocation + spin-class + note-format laggards open; see `docs/players/HUBBARD.md` |
| Jeroen Kimmel (Hubbard-derived) → Driver 11 | **11/12 voice-medians exact 100%** (frame-pitch) | ✅ 4 files / 9 SF2s incl. Radax 6 subtunes; arp+PWM+freq-slide(T0)+drum ported (`bin/`, not default); see `docs/players/KIMMEL.md` |
| Charles Deenen (MoN/Deenen replay) → Driver 11 | 7 clean wins (Ding, B_A_T, LotR, After_the_War, Zamzara all exactly 100/100; Constant_Runner 100/97.7; Astro 77.4/91.5); 10/19 located | 🚧 + 8 freebies at 100% (3 SM shim, 2 Hubbard, 3 MoN-TTWII sub0); per-file tempo + per-voice audio validator; builder REFUSES implausible decodes (`bin/`, not default); see `docs/players/DEENEN.md` |
| Future Composer → Driver 11 | trace-validated | 🚧 Stage A only, `$1800` variant; native driver TODO |
| DMC (Demo Music Creator, Johannes Bjerregaard) → native driver | **Balloon 77 parts → ONE 400s SF2, wf/pulse 100×3 over the FULL 400s** (n=19996/voice, freq 80.6/100/97.7); Rockbuster ~97/100/100 *on part 1 of 16*. **Every % is window-dependent** (one file reads 100/89/95 @6s, 44/38/39 @20s) — quote the window | 🚧 56/88 build-eligible = a **mode count, NOT accuracy** (an eligible file can still score 39%); all build (`bin/`, not default); see `docs/players/DMC.md` |
| Sound Monitor (Hülsbeck) → native driver | corpus strict sweep **99.23% freq+wf** (n≈841k, median 99.97) over **26 of 27 parts** (Dance part01 missing from the sweep log; restoring it → 99.25%, so it understates). freq+wf = best 2 of 4: pulse 96.67, filter 97.33. 100.0 on every register: Fuck_Off 242s + Dance parts **03/04 only** | ✅ 11/11 Fun_Fun files build, 11 songs/27 parts (`bin/`, not default); headline comes from **untracked** scratch, no tracked test — not reproducible from a fresh clone; see `docs/players/SOUNDMONITOR.md` |
| SID Duzz' It (Gallefoss/Tjelta) → Driver 11 (Stage A) | strict onset+pitch medians: A 98.3, D 100, **C 86.0** (was 66.7), B 74.8, **E 50.8** (was 47.5), **DELTA win 89.8 / strict 55.5** (8 files), V 21.8. n: A 50 B 43 C 80 D 18 E 118 DELTA 8 V 6. **Only A+D are unfitted** (C/E/DELTA/V pick a timing model best-of-N) | 🚧 **343 locate → 348 Stage A SF2s** (343 + 5 subtune), **324 sweep-validated** — three different denominators, don't conflate. "0 failures" = emitted OK, not fidelity: 274/324 ship some default instrument data. C walk decoded + E $Cx trailing-delay fix + E single-store-init gen + DELTA-class play+3 wrapper cracked + multi-subtune (A/C/E) + "sixth layout" wrapper cracked; native Stage B TODO; see `docs/players/SDI.md` |

**Critical**: "SidFactory_II/Laxity" ≠ native Laxity! Check player-id: "SidFactory" = use Driver 11, "Laxity_NewPlayer_V21" = use Laxity driver

**Other**: Only native Laxity NP21 supported by Laxity driver, single subtune only, filter accuracy 100% (Stinsen verified v3.1.4)

---

## Documentation

**Start**: `README.md` | `docs/guides/GETTING_STARTED.md` | `docs/guides/TROUBLESHOOTING.md`

**User Guides** (3,400+ lines): `TUTORIALS.md`, `FAQ.md`, `BEST_PRACTICES.md`, `SF2_VIEWER_GUIDE.md`, `CONVERSION_COCKPIT_USER_GUIDE.md`, `LAXITY_DRIVER_USER_GUIDE.md`, `VALIDATION_GUIDE.md`, `LOGGING_AND_ERROR_HANDLING_GUIDE.md`

**Technical**: `docs/ARCHITECTURE.md`, `docs/COMPONENTS_REFERENCE.md`, `docs/reference/SF2_FORMAT_SPEC.md`, `docs/guides/RETRODEBUGGER_GUIDE.md` (live 6502/C64 debugging via `mcp__retrodebugger__*` — breakpoints, memory read/write, live disassembly, warp-speed fast-forward; use when a static/offline model of a player keeps guessing wrong and you need real CPU ground truth)

**Players (consolidated 2026-07-05)**: `docs/players/PLAYBOOK.md` (**the cross-player porting method** — staged Stage A/B pipeline, size caps, gotchas, new-player checklist), `docs/players/README.md` (support index), per-player docs (`LAXITY`, `GALWAY`, `MON`, `ROMUZAK`, `HUBBARD` + `HUBBARD_V2_PLAN`, `KIMMEL`, `DEENEN`, `DMC`, `SOUNDMONITOR`, `SDI`, `FUTURECOMPOSER`, `DRIVER11`, `NP20`, `CLUSTERS`), `PATTERNS.md` (**the RE technique catalog** — cited as D2/D4 below), `NATIVE_DRIVER.md`, `docs/reference/ACCURACY_MATRIX.md` (accuracy source of truth, v3.21.0), `docs/ROADMAP.md` (consolidation/optimization plan)

**Complete index**: `docs/INDEX.md`

---

## For AI Assistants

**Tools**: Task(Explore) for broad searches | Read/Grep for specific files | EnterPlanMode for multi-file changes

**Before Commit**: Run `test-all.bat` (7 suites) | Update README.md, CLAUDE.md, docs/ if changed | Run `update-inventory.bat` if files added/removed

**After building native SF2s**: run `py -3 pyscript/gen_sf2_index.py` to refresh the complete build inventory (all songs + part counts) in `docs/SF2.md` (the curated fidelity tables above the GENERATED markers are hand-maintained). Also run `py -3 pyscript/gen_conversion_index.py` to keep the broader `docs/SID_TO_SF2_CONVERSIONS.md` (every converted song, both `out/` and `SF2/`) current.

**On Version Bump**: Add the release entry to `CHANGELOG.md` (the canonical version history — NOT this file; CLAUDE.md stays compact) AND `STORY.md` (the project narrative — append to per-version index; update Eras / deep-tech sections only if a new architectural finding warrants it). Bump `sidm2/__init__.py __version__` + `__build_date__`. Update the Known Limitations table + relevant `docs/` if behavior changed.

**Debug**: Check `output.txt` → Compare dumps (`siddump_complete.py`) → Compare audio

---

## TDZ C64 Knowledge Base (shared MCP)

`mcp__tdz-c64-knowledge` is a **shared, cross-project** C64/SID knowledge base (other projects read+write it too). SIDM2 has seeded 21 documents there: a **knowledge card per player** (Laxity, Galway, MoN, Hubbard, DMC, Sound Monitor, ROMUZAK, Future Composer, SDI, Driver 11), the **RE technique catalog** (from `PATTERNS.md`/`PLAYBOOK.md`), plus reference docs (SF2 + PSID formats, native-driver how-to, fidelity toolchain, tooling landscape, the STORY, the Laxity disassembly, 6502 primers).

**Use it:**
- **Before starting a new player**: `search_docs` / `list_docs` for an existing card or scene-history leads (SIDin ezines, c=hacking, codebase64 are all indexed) before hunting d64s/disassemblies from scratch.
- **After confirming new findings**: write a card back so the work is queryable outside this repo. Cards are `add_document`-only (no in-place edit): write the file to an allowed dir (`~/.tdz-c64-knowledge/temp/`, the repo, or `~/Downloads/tdz-c64-knowledge-input`), then ingest. Match the existing card schema (JSON block: id/name/aliases/authors/memory/entry/data_format/effects/edges/quirks/sources + prose Overview/Quirks/Disassembly/Verification/Sources). Cards stay `status: in-progress` until assembled+run through the KB's own `mcp-c64` tool — describe SIDM2's own byte-exact verification honestly in the Verification prose.
- **NOT a substitute** for SIDM2's own zig64/py65 byte-exact discipline (PATTERNS.md D2/D4 — never trust a source blindly). The general corpus won't have compiled-binary table offsets for any specific rip; that's still native RE per file/variant.

Full details + card schema: `memory/tdz-c64-knowledge-base.md`. **Note**: `memory/*.md` throughout this repo's docs is NOT a tracked repo directory — it's the Claude Code auto-memory store (`~/.claude/projects/<this-project>/memory/`, outside this git repo). Ask your assistant to recall the named file if you need its contents; it isn't in the working tree.

---

## Version History

Full release history lives in **`CHANGELOG.md`** (Keep-a-Changelog format,
v0.x–current). Project narrative: **`STORY.md`**. This file stays compact —
do not add per-version entries here.

---

**End of Quick Reference**

**Lines**: ~215 (version history moved to CHANGELOG.md) | **For full docs**: See README.md and docs/
