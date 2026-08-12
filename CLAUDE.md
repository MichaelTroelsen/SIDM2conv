# CLAUDE.md - AI Assistant Quick Reference

**SIDM2 v3.27.0** | SID→SF2 Converter | C64 Music Tools | Updated 2026-08-12

Converts native Laxity NP21 SID files to SF2 format (100% accuracy). Features: Auto-driver selection, VSID audio export, Batch Analysis (multi-pair comparison), Accuracy Heatmap (4 viz modes), Trace Comparison (tabbed HTML), SF2 Viewer, Conversion Cockpit, SID Inventory (658+ files), Python siddump/SIDwinder, Batch Testing, User Docs, CI/CD (5 workflows), audio-domain listening tooling (feature summary + spectrograms, calibrated), ~2,300 tests

---

## Critical Rules

1. **Keep Root Clean**: ALL .py files in `pyscript/` only. No .py in root.
2. **Run Tests**: `test-all.bat` (7 suites) before committing; `python -m pytest` runs all ~2,300
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
audio-tightness.bat orig.sid conv.sf2 --driver-init 0x1000 --driver-play 0x1003 --voice all  # + per-voice sweep, isolation guard, repeatability floor, registers x audio cross-tab
audio-tightness.bat a.sid b.sid --spectrogram out.png    # SID2SID/WAV2WAV/mixed (accepts .sid/.sf2/.wav on either side): whole-file feature-summary text (level dBFS+dBA/brightness/noisiness/chroma, always-on unless --no-listen) + a 3-panel orig/driver/diff spectrogram PNG Claude can view with the Read tool -- "a way to listen" beyond onset timing
audio-tightness.bat a.sid b.sf2 --windowed 5 --band-scale mel  # per-section features + worst-window call-out (localizes a defect a whole-file mean dilutes); mel band spacing is opt-in
instrument-map.bat orig.sid conv.sf2 [--annotate dump.txt]  # WHICH INSTRUMENT sounds on each siddump frame (onsets keyed by ADSR, table found by search); prints a verdict on whether the key holds at all and emits no table when it doesn't
python pyscript/instrument_map_sweep.py -n 2                # key-verdict calibration sweep (27 files/13 dirs: 16 reliable, 6 insufficient-data, 2 no-trace, 2 degenerate, 1 unusable)
sid-to-sf2.bat in.sid out.sf2 --audio-export --audio-export-voices  # + 3 per-voice isolated stems via sidplayfp (VSID has no voice mute); muting is NOT clean isolation on every tune
batch-analysis.bat originals/ exported/                 # Batch analysis (standalone, HTML+CSV+JSON)
batch-analysis-validate.bat originals/ exported/        # Batch analysis (validation DB integration)
validation-dashboard.bat                                # Validation results dashboard
python pyscript/generate_stinsen_html.py file.sid       # HTML docs (3,700+ annotations)

# Batch Operations
batch-convert-laxity.bat      # All Laxity files
test-all.bat                  # 7 suites (pytest runs all ~2,300)
cleanup.bat                   # Clean + inventory

# Python Tools
python pyscript/siddump_complete.py input.sid -t30           # Frame dump
python pyscript/sidwinder_trace.py --trace out.txt input.sid # Trace (text)
python pyscript/create_sid_inventory.py                      # SID catalog
python pyscript/validate_filter_accuracy.py [--sid F] [--csv F] [--verbose]  # Filter accuracy vs zig64 ground truth

# Testing & Automation
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

**VSID** (`sidm2.vsid_wrapper`): SID→WAV via VICE, auto-fallback to sidplayfp (`sidm2.sidplayfp_wrapper`, replaced SID2WAV.EXE 2026-08-07). Docs: `docs/VSID_INTEGRATION_GUIDE.md`, `docs/TOOLS_REFERENCE.md`

**SF2 Automation** (`sidm2.sf2_editor_automation`): PyAutoGUI auto-loading, 100% pass. Docs: `archive/cleanup_2026-04-28/old_docs/completion_reports/PYAUTOGUI_INTEGRATION_COMPLETE.md` (archived)

**Filter Accuracy Validator** (`pyscript/validate_filter_accuracy.py`): Cross-validates Laxity NP21 filter tables extracted from SID binary against cycle-accurate zig64 ground truth trace. Checks resonance byte, sweep speed, and mode bits. Ground truth: `SID/stinsen_sid_trace_300frames.csv`

**Regenerator 2000 Labeler** (archived 2026-04-29 → `archive/cleanup_2026-04-29/orphaned_utils/regen2000_label_laxity_np21.py`): Auto-labels any NP21 file loaded in Regenerator 2000 via MCP HTTP. Restore from archive if needed.

**Regenerator 2000 Project Generator** (archived 2026-04-29 → `archive/cleanup_2026-04-29/orphaned_utils/gen_regen2000_project.py`): Generates `.regen2000proj` directly from a PRG binary with NP21 labels pre-applied. Restore from archive if needed.

**zig64 SID Tracer** (`tools/sidm2-sid-trace.exe`): cycle-accurate SID register tracer. `sidm2-sid-trace.exe file.prg [frames] [init_hex] [play_hex] [subtune]` (defaults `$1000/$1003/0`; pass real init/play+subtune for non-Laxity). CSV on stderr. **Fails honestly**: prints `FAILED:` and exits non-zero rather than emitting an empty trace as a silent tune — **check the exit code**, don't just parse stderr. ⚠️ A too-short window looks identical to a broken trace (Arkanoid: 0 writes at 5 frames, 460 at 200) — use **≥200 frames** before calling a file broken. Source of truth: `tools/sidm2_sid_trace.zig` **in this repo** (rebuild: copy to `C:\Users\mit\Downloads\zig64\src\examples\`, `zig build`, copy `zig-out/bin/sidm2-sid-trace.exe` back — the zig64 copy goes stale).

**RSID escape hatch — the VICE wrapper** (`C:\Users\mit\claude\sid-reference-project\scripts\dev\vsid-trace.js`, a *separate* project): zig64 has **no autonomous VIC/CIA interrupt delivery**, so RSID files declaring `play=$0000` are untraceable here; `vsid` runs a full emulated C64 and traces **21 of SIDM2's 22**. Cross-validated against zig64 on a PSID: both report exactly 90 changed-value writes. `node vsid-trace.js <f.sid> --frames N --json --changed-only`. ⚠️ **vsid exits 1 on normal termination** — check for the dump file, not the exit code; cycle timings are NOT comparable between the tools, only the write *sequence*. Not wired in. See `docs/players/PLAYBOOK.md`.

**Fidelity harness** (`sidm2/fidelity_common.py`): the shared measurement plumbing every scorer should route through — **do not write a new one**. Two guards that answer different questions, and you need both: `score_pct(ok, tot)` returns **None** (never 100.0/0.0) when `tot == 0` — *were there any frames?* — and `exercised(a, b)` returns False when both series are the same single constant — *did those frames carry information?* The second is not optional: **siddump force-displays every register on its first row** whether the playroutine wrote it or not, so a tune that never filters yields a full-length non-None series of zeroes on both sides and scores a confident 100%. That exact bug was fixed, re-appeared one layer down, and was caught by *running the tool* both times. Five separate copies of the same weighted-accuracy scheme existed in this repo, each independently broken — one scored **two identical captures at 50%**. Also here: an A/B baseline mode (`result_row`/`ab_pair`/`compare_runs`) that refuses on mismatched *measurement* settings but surfaces mismatched *build options* as "the change under test", a dimension registry so a report can generate — not hand-maintain — the list of registers **nothing it measured reads**, and `output_digest` so "no number moved" can be told apart from "the build never changed". A third helper, `shape_agreement`, is the phase-invariant companion for a **swept** register (pulse width, cutoff): movement count + travel, so a sweep that is correct but a few frames late stops reading as a dead engine (`5_Title_Tunes` osc3 pulse 4.5% strict = a -3-frame offset). Necessary, not sufficient — print it beside the strict number, never instead. See `PATTERNS.md` D4/D9.

**Instrument attribution (`sidm2/instrument_map.py`)**: turns a per-VOICE fidelity number into a per-INSTRUMENT one by keying note onsets on ADSR (`$D405/$D406` is a verbatim per-instrument copy in many players — but h2g measured that on **one** family, so `key_reliability()` grades the key first and emits **no table** when it fails). The instrument table is **located by search, never by a constant** (`SF2/Angular.sf2` at Driver 11's documented `$1A03` matches 0 of 10 sounded envelopes — that file is Laxity, at `$1A6B`). `InstrumentScores` splits any per-frame comparison by record and **sums back**; in HardTrack Stage B, voice 0's 95.9% resolves to records 7/4-5/8 (77.8-88.5%) against 0/1 (96.4-97.2%). Gotchas that each cost a wrong answer once: stride aliases must be collapsed (ranking by base renumbered every Angular instrument by +20); `no-trace` ≠ `insufficient-data`; `incomplete` ≠ `layout-wrong` (Angular sounds `$0028` 50 times and NEITHER side's table declares it, byte-identically — a blind spot in the key, not a conversion gap). See `docs/plans/INSTRUMENT_MAP_PLAN.md`.

**Audio-domain "listening" (`sidm2/audio_listen.py`)**: the companion to `audio_tightness.py`'s onset timing — whole-file/per-section features (level in dBFS **and** A-weighted dBA, spectral centroid/rolloff, flatness, silence, 12-bin pitch-class **chroma**) plus a 3-panel spectrogram PNG the assistant reads directly. numpy+Pillow only. **Calibrated against 3 recorded human verdicts across 2 player families** (Blackbird B13+E3e, MoN/Cybernoid; `pyscript/calibration_cases.json`, `docs/AUDIO_LISTENING_CALIBRATION.md`) — read that before quoting any of it: onset match has **ordinal sensitivity but no absolute gate**, confirmed 3/3 (a 99.8%-register-exact build still scores 64.7% against an 85-91% original-vs-itself floor, so any threshold flagging a bad build condemns a good one too — use it against a baseline, never as pass/fail, and measure the floor per tune). **Which feature is informative is DEFECT-DEPENDENT, not universal**: A-weighting is the strongest discriminator (1.5-1.6x) on the two timing/percussive defects but scores as noise (0.011) on a pitch (vibrato-width) defect, where **chroma** is instead the one that fires (0.072, a correct NULL on the other two) — check chroma first for a suspected pitch/tuning defect. `--windowed`'s `silence_frac` confound is **fixed** (`_only_more_silent` in the module clips the one-directional startup-silence offset, verified 0.0/0.0 across all 3 cases), but windowing itself is much weaker on a defect that's continuous across the whole song rather than localized to one section. Several of these findings would have shipped a *confidently wrong* number that their own unit test passed; each was caught only by running against real material.

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
| ROMUZAK V6.3 → native driver | ~98-100% | ✅ Byte-exact wf/pulse/AD-SR (`bin/`, not default); see `docs/players/ROMUZAK.md` |
| Maniacs of Noise (Jeroen Tel) → native driver | 100% byte-exact (Hawkeye sub 2/3) on freq/wf/pulse/**cutoff**, and now `$D418` | ✅ Hawkeye + Cybernoid I/II + Myth + Supremacy build (`bin/`, not default). **Read older "filter 100%" figures as cutoff only** — `$D418` was scored by nothing until 2026-08-07. **Myth needs `bin/build_myth_native_song.py`**, not the generic `build_mon_native_song.py`. A "register-exact but SYNTHESIS on every voice" reading was **FALSIFIED** — it was metric noise; quote `--repeat-floor` beside any per-voice audio number (PATTERNS.md F5b). See `docs/players/MON.md` |
| Mainstream MoN / Jeroen Tel (SID/Tel_Jeroen, 179 files) → mon_parser | B1-indirect bucket: **12/24 onset-EXACT**; Tel_1 86%, Monitor_Madness_1 75/106, _2 90/146, Trying_Out_2 41/59, Trying_Out 78%, Zynon_Zak 84%, Bantam 77%, Starball 76%, Alloyrun 61% | 🚧 New MoN generation cracked; row-ctrl bit5 is a **TIE flag** (disassembly-confirmed). ⚠️ **Verify any change against the FULL bucket AND the 5-check byte-exact gate, not just the target file** — an over-loose proximity match caused a real regression mid-session. 85-file no-copy bucket untouched. Detail: `memory/mainstream-mon-tel.md` (auto-memory, **not** in the repo) |
| Rob Hubbard V1 → native driver | pulse 100% (modelled engine, all voices/4 tunes), freq 99.3-100; **filter NOT exercised** (Hubbard never writes cutoff — the old "filter 100%" was 0==0) | ✅ 12 V1 tunes + subsongs (`bin/`, not default). ⚠️ Stage A `Kings_of_the_Beach_intro` is **missing music** (needs 153 sequences vs the 128 cap) and can't use the shared windower. Open; see `docs/players/HUBBARD.md` |
| Rob Hubbard V2 (Delta class) → native driver | Delta theme freq 100%, wf 85-97% (pessimistic — residual is pure ±1-frame skew); **pulse 100% is CAPTURED, not modelled** (`hp_engine=0`); filter not exercised | 🚧 6 split-songs + Delta + 7 swallow built; swallow-class relocation + spin-class + note-format laggards open; see `docs/players/HUBBARD.md` |
| Jeroen Kimmel (Hubbard-derived) → Driver 11 | **11/12 voice-medians exact 100%** (frame-pitch) | ✅ 4 files / 9 SF2s incl. Radax 6 subtunes (`bin/`, not default); see `docs/players/KIMMEL.md` |
| Charles Deenen (MoN/Deenen replay) → Driver 11 | 7 clean wins (5 at exactly 100/100; Constant_Runner 100/97.7; Astro 77.4/91.5); 10/19 located | 🚧 + 8 freebies at 100%; builder **REFUSES implausible decodes** (`bin/`, not default); see `docs/players/DEENEN.md` |
| Future Composer → native driver | **Stage B: 14/15 corpus voices exactly 100.0% audible pitch, FULL song length** (n 346-2253); sole residual Triangle_Intro v1 83.6%. The builder's **raw** column (58-100%) understates — FC rests park `$0002` gate-off, inaudible; **read both columns with their n** | ✅ Stage B via a MON shim, no new driver (`bin/build_fc_native_song.py`); Stage A still can't gate long silent intros; see `docs/players/FUTURECOMPOSER.md` |
| Matt Gray → Driver 11 (Stage A) + native (Stage B) | **Stage B: 16 tunes across 3 games.** Register state vs the original (Last Ninja 2 sub 0, all frames): waveform/AD/SR/filter/`$D418` **100.00%**, freq **92.7/92.9/100.0** — the residual is 192 frames/voice where BOTH sides carry waveform `$00`, so the oscillator is silent and it is inaudible. Stage A: Driller onset+pitch **1513/1513** on *plain* instruments; pitch-modulated notes (n=468) **NOT claimed** (base-pitch 65.4%) | 🚧 `bin/`, not default. **Read `docs/players/MATTGRAY.md` before quoting any of this** — two of its own published claims have been retracted by measurement. Non-negotiables: the builder's **`audible` column is gate-on only and is BLIND to release-tail defects** (it read 99.5-100% through 236 wrong release runs); a **raw waveform correlation has a 0.58-0.74 floor** on byte-identical material, so it is never evidence — quote the phase-invariant measures (0.97-0.99 floor). The audio gap is **sub-millisecond write PHASE and is inaudible** — level, harmonics, per-octave energy and envelope all sit at the floor, while the per-window spectrogram loses 0.035 for **23 microseconds** of jitter, so **never quote it as an audio-fidelity figure**; measure the floor **per voice** (0.937-0.999 on one tune). All 16 decode via `layout='signature'`, NOT the validated `driller` path — **the decode is unverified**; 1 of 55 HVSC files located; sub 7 refused |
| DMC (Demo Music Creator, Johannes Bjerregaard) → native driver | **Balloon 77 parts → ONE 400s SF2, wf/pulse 100×3 over the FULL 400s** (n=19996/voice, freq 80.6/100/97.7); Rockbuster ~97/100/100 *on part 1 of 16*. **Every % is window-dependent** (one file reads 100/89/95 @6s, 44/38/39 @20s) — quote the window | 🚧 56/88 build-eligible = a **mode count, NOT accuracy** (an eligible file can still score 39%); all build (`bin/`, not default); see `docs/players/DMC.md` |
| Sound Monitor (Hülsbeck) → native driver | corpus strict sweep **99.25% freq+wf** over **all 27 of 27 parts**. freq+wf = best 2 of 4: pulse 96.67, filter 97.33 ✻ (**doc-carried, not re-aggregated by the current sweep**) | ✅ 11/11 Fun_Fun files build, 11 songs/27 parts (`bin/`, not default); **reproducible from a fresh clone** via tracked `pyscript/soundmonitor_sweep.py`; see `docs/players/SOUNDMONITOR.md` |
| Blackbird / lft → native driver | 16-file v1.2-exact corpus **mean 99.96** vs the validated simulator; **11 of 16 at exactly 100.0**, none below 99.8. NOTE the 16 are **not a chosen subset** — they are **every LFT rip `locate_blackbird` supports** (16 of 61 on disk; the other 45 are unlocatable variants). Glyptodont **162/162 note-ons** | ✅ B1-B25 + E3e/f/g + E4/E5/E6 (`bin/`, not default). Corpus sweep tracked + tested, **reproducible from a fresh clone**; see `docs/players/BLACKBIRD.md` |
| SID Duzz' It (Gallefoss/Tjelta) → Driver 11 (Stage A) | strict onset+pitch medians: A 98.3, D 100, C 86.0, B 74.8, E 50.8, DELTA 89.8 win / 55.5 strict, V 21.8. n: A 50 B 43 C 80 D 18 E 118 DELTA 8 V 6. **Only A+D are unfitted** (C/E/DELTA/V pick a timing model best-of-N) | 🚧 **343 locate → 348 Stage A SF2s → 324 sweep-validated — three different denominators, don't conflate.** "0 failures" = emitted OK, **not** fidelity: 274/324 ship some default instrument data. Native Stage B TODO; see `docs/players/SDI.md` |
| HardTrack Composer (Longhair/Brush) → Driver 11 (Stage A) + native (Stage B) | Parser vs siddump, byte-exact freq: **88.7%** where the sequencer owns the pitch, **2.6%** where the instrument's wave program does (field-5 bit 7). Register model: **100.00%** freq/wf/pulse on the 18 layout-seeded files (53,569 frames), **99.96%** on the 15 second-build files. Filter `$D416`/`$D417` **100.00%** (32,967 frames, 33 files). Stage B builds 33/33 | 🚧 RE + Stage A + Stage B (`bin/`, neither default). **Read `docs/players/HARDTRACK.md` before quoting any of this** — the numbers each carry a condition, and getting one wrong has produced published retractions here. Non-negotiables: **two columns, never averaged** (the second is the unmodelled synth engine); **always quote the match window** (it has no plateau); Stage A's 91.3% is an **artifact** above the parser — quote the 99.69% retention instead; `$D418` is 100% but **only 10 of 33 files exercise it** — quote the file count; the filter is **global, not per-voice**; Stage B needs **raw AND audible**, never net alone; the render sits at **−3** so judge any alignment against that. Tables are recovered **by code signature, never load+constant** (the last such constant, `vib_depth`, was wrong on 15 files). 5 of 38 refused; `SID/Shogoon/` is mixed-player, 38 of 150. Rungs 3 and 4 both **pass/run**; rung 4 found the `$D418` passband defect (also fixed in DMC). Open: ~half the brightness gap, best candidate ADSR 88–94% — and `hard_restart=1` is provably the wrong fix | 

**Critical**: "SidFactory_II/Laxity" ≠ native Laxity! Check player-id: "SidFactory" = use Driver 11, "Laxity_NewPlayer_V21" = use Laxity driver

**Other**: Only native Laxity NP21 supported by Laxity driver, single subtune only, filter accuracy 100% (Stinsen verified v3.1.4)

---

## Documentation

**Start**: `README.md` | `docs/guides/GETTING_STARTED.md` | `docs/guides/TROUBLESHOOTING.md`

**User Guides** (3,400+ lines): `TUTORIALS.md`, `FAQ.md`, `BEST_PRACTICES.md`, `SF2_VIEWER_GUIDE.md`, `CONVERSION_COCKPIT_USER_GUIDE.md`, `LAXITY_DRIVER_USER_GUIDE.md`, `VALIDATION_GUIDE.md`, `LOGGING_AND_ERROR_HANDLING_GUIDE.md`

**Technical**: `docs/ARCHITECTURE.md`, `docs/COMPONENTS_REFERENCE.md`, `docs/reference/SF2_FORMAT_SPEC.md`, `docs/guides/RETRODEBUGGER_GUIDE.md` (live 6502/C64 debugging via `mcp__retrodebugger__*` — breakpoints, memory read/write, live disassembly, warp-speed fast-forward; use when a static/offline model of a player keeps guessing wrong and you need real CPU ground truth)

**Players (consolidated 2026-07-05)**: `docs/players/PLAYBOOK.md` (**the cross-player porting method** — staged Stage A/B pipeline, size caps, gotchas, new-player checklist), `docs/players/README.md` (support index), per-player docs (`LAXITY`, `GALWAY`, `MON`, `ROMUZAK`, `HUBBARD` + `HUBBARD_V2_PLAN`, `KIMMEL`, `DEENEN`, `DMC`, `SOUNDMONITOR`, `SDI`, `BLACKBIRD`, `FUTURECOMPOSER`, `DRIVER11`, `NP20`, `CLUSTERS`), `PATTERNS.md` (**the RE technique catalog** — cited as D2/D4 below), `NATIVE_DRIVER.md`, `docs/reference/ACCURACY_MATRIX.md` (accuracy source of truth — it carries its own version stamp; do not repeat it here, that second copy is what drifted), `docs/ROADMAP.md` (consolidation/optimization plan)

**Complete index**: `docs/INDEX.md`

---

## For AI Assistants

**Tools**: Task(Explore) for broad searches | Read/Grep for specific files | EnterPlanMode for multi-file changes

**Before Commit**: Run `test-all.bat` (7 suites) | Update README.md, CLAUDE.md, docs/ if changed | Run `update-inventory.bat` if files added/removed

**After building native SF2s**: run `py -3 pyscript/gen_sf2_index.py` to refresh the complete build inventory (all songs + part counts) in `docs/SF2.md` (the curated fidelity tables above the GENERATED markers are hand-maintained). Also run `py -3 pyscript/gen_conversion_index.py` to keep the broader `docs/SID_TO_SF2_CONVERSIONS.md` (every converted song, both `out/` and `SF2/`) current.

**On Version Bump**: Add the release entry to `CHANGELOG.md` (the canonical version history — NOT this file; CLAUDE.md stays compact) AND `STORY.md` (the project narrative — append to per-version index; update Eras / deep-tech sections only if a new architectural finding warrants it). Bump `sidm2/__init__.py __version__` + `__build_date__`. **The doc stamps are now pinned by `pyscript/test_version_stamps_agree.py`** — README, this file, `ACCURACY_MATRIX.md` and `STORY.md` must all match the package, and the CHANGELOG must have a heading for it, so a half-done bump fails a test instead of shipping. It shipped twice before: the matrix sat at 3.22.0 through 3.23.0, and README's banner sat at 3.22.0 for **four** releases — both because a checklist is the wrong remedy for duplicated truth. Update the Known Limitations table + relevant `docs/` if behavior changed. **Also re-stamp `docs/reference/ACCURACY_MATRIX.md`** — it is named the accuracy source of truth below, so a version bump that skips it leaves the canonical copy stale (it sat at v3.22.0 through the 3.23.0 release because this list did not name it).

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

**Size**: **29.0 KB / ~7.3k tokens** — this file is loaded into **every** session, so measure it in **bytes**, not lines. It had drifted to 32.5 KB while *staying inside* a ~226-line budget, because prose migrates into table cells and a line count cannot see that: **one** HardTrack table row was 6,696 bytes, 21% of the whole file. Trimmed back in v3.26.0 after verifying all 23 of its claims survive in `docs/players/HARDTRACK.md`. Keep per-player rows to a **verdict + the caveats needed to quote the numbers correctly + a `docs/players/` link** — mechanism, evidence and history belong in the player doc. | **For full docs**: See README.md and docs/
