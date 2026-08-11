# CLAUDE.md - AI Assistant Quick Reference

**SIDM2 v3.25.0** | SID→SF2 Converter | C64 Music Tools | Updated 2026-08-10

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

**zig64 SID Tracer** (`tools/sidm2-sid-trace.exe`): Pre-built cycle-accurate SID register tracer. Usage: `sidm2-sid-trace.exe file.prg [frames] [init_hex] [play_hex] [subtune]`. Pass init/play (from the PSID header) + subtune for non-Laxity files (e.g. Galway); defaults are $1000/$1003/0. Output: CSV on stderr. **Fails honestly (v3.21.0)**: prints `FAILED:` + exits non-zero when it cannot drive a file (unresolved/implausible IRQ handler, or 0 SID writes across the window) — an empty trace is NEVER emitted as if it were a silent tune. **Check the exit code**; don't just parse stderr. Gotcha: a too-short window looks identical to a broken trace (Arkanoid = 0 writes at 5 frames, 460 at 200) — use ≥200 frames before calling a file broken. Source of truth: `tools/sidm2_sid_trace.zig` **in this repo** (rebuild: copy to `C:\Users\mit\Downloads\zig64\src\examples\`, `zig build`, copy `zig-out/bin/sidm2-sid-trace.exe` back — the zig64 copy goes stale).

**RSID escape hatch — the VICE wrapper** (`C:\Users\mit\claude\sid-reference-project\scripts\dev\vsid-trace.js`, a *separate* project): zig64 has **no autonomous VIC/CIA interrupt delivery**, so RSID files that declare `play=$0000` and install their own IRQ are untraceable here — the tracer now says so instead of faking a 0-write trace. `vsid` runs a full emulated C64, so the machine drives the player. **21 of SIDM2's 22 untraceable RSIDs trace under it** (incl. `Broken_Ass` 1068 writes, `Myth` 259, `A_Mind_Is_Born` 100; only `Final_Countdown_BASIC` = 0, plausibly genuine). Cross-validated: on a PSID both tools drive (Stinsen, 16 frames) both report **exactly 90** changed-value writes. Usage: `node vsid-trace.js <file.sid> --frames N --json --changed-only` (`--changed-only` matches this tracer's semantics; vsid otherwise records redundant writes). Gotchas: **vsid exits 1 on normal termination** — check for the dump file, not the exit code; cycle timings are NOT comparable between the tools (~1 frame apart), only the write *sequence* agrees. Not wired into SIDM2. See `docs/players/PLAYBOOK.md`.

**Fidelity harness** (`sidm2/fidelity_common.py`): the shared measurement plumbing every scorer should route through — **do not write a new one**. Two guards that answer different questions, and you need both: `score_pct(ok, tot)` returns **None** (never 100.0/0.0) when `tot == 0` — *were there any frames?* — and `exercised(a, b)` returns False when both series are the same single constant — *did those frames carry information?* The second is not optional: **siddump force-displays every register on its first row** whether the playroutine wrote it or not, so a tune that never filters yields a full-length non-None series of zeroes on both sides and scores a confident 100%. That exact bug was fixed, re-appeared one layer down, and was caught by *running the tool* both times. Five separate copies of the same weighted-accuracy scheme existed in this repo, each independently broken — one scored **two identical captures at 50%**. Also here: an A/B baseline mode (`result_row`/`ab_pair`/`compare_runs`) that refuses on mismatched *measurement* settings but surfaces mismatched *build options* as "the change under test", a dimension registry so a report can generate — not hand-maintain — the list of registers **nothing it measured reads**, and `output_digest` so "no number moved" can be told apart from "the build never changed". A third helper, `shape_agreement`, is the phase-invariant companion for a **swept** register (pulse width, cutoff): movement count + travel, so a sweep that is correct but a few frames late stops reading as a dead engine (`5_Title_Tunes` osc3 pulse 4.5% strict = a -3-frame offset). Necessary, not sufficient — print it beside the strict number, never instead. See `PATTERNS.md` D4/D9.

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
| Matt Gray → Driver 11 | **Driller build only**: sequencer onset + pitch **1513/1513 = 100%** on *plain* instruments over 240 s. Pitch-modulated notes (n=468) are **NOT claimed** — the player rewrites `$d400` every frame there, so onset is vacuously 100%; base-pitch is 65.4% and that residual is the synth side | 🚧 Stage A only (`bin/`, not default); 1 of 55 HVSC files located, `verify()` refuses unknown variants loudly. Stage A knowingly lacks the slide/arp/PWM/drum engine — **it will NOT sound like the original**; timbre is a Stage B claim. Gotchas: PSID `load=0`; `music_init` ignores the accumulator; Tusker's `play=$e002` is under KERNAL ROM. See `docs/players/MATTGRAY.md` |
| DMC (Demo Music Creator, Johannes Bjerregaard) → native driver | **Balloon 77 parts → ONE 400s SF2, wf/pulse 100×3 over the FULL 400s** (n=19996/voice, freq 80.6/100/97.7); Rockbuster ~97/100/100 *on part 1 of 16*. **Every % is window-dependent** (one file reads 100/89/95 @6s, 44/38/39 @20s) — quote the window | 🚧 56/88 build-eligible = a **mode count, NOT accuracy** (an eligible file can still score 39%); all build (`bin/`, not default); see `docs/players/DMC.md` |
| Sound Monitor (Hülsbeck) → native driver | corpus strict sweep **99.25% freq+wf** over **all 27 of 27 parts**. freq+wf = best 2 of 4: pulse 96.67, filter 97.33 ✻ (**doc-carried, not re-aggregated by the current sweep**) | ✅ 11/11 Fun_Fun files build, 11 songs/27 parts (`bin/`, not default); **reproducible from a fresh clone** via tracked `pyscript/soundmonitor_sweep.py`; see `docs/players/SOUNDMONITOR.md` |
| Blackbird / lft → native driver | 16-file v1.2-exact corpus **mean 99.96** vs the validated simulator; **11 of 16 at exactly 100.0**, none below 99.8. NOTE the 16 are **not a chosen subset** — they are **every LFT rip `locate_blackbird` supports** (16 of 61 on disk; the other 45 are unlocatable variants). Glyptodont **162/162 note-ons** | ✅ B1-B25 + E3e/f/g + E4/E5/E6 (`bin/`, not default). Corpus sweep tracked + tested, **reproducible from a fresh clone**; see `docs/players/BLACKBIRD.md` |
| SID Duzz' It (Gallefoss/Tjelta) → Driver 11 (Stage A) | strict onset+pitch medians: A 98.3, D 100, C 86.0, B 74.8, E 50.8, DELTA 89.8 win / 55.5 strict, V 21.8. n: A 50 B 43 C 80 D 18 E 118 DELTA 8 V 6. **Only A+D are unfitted** (C/E/DELTA/V pick a timing model best-of-N) | 🚧 **343 locate → 348 Stage A SF2s → 324 sweep-validated — three different denominators, don't conflate.** "0 failures" = emitted OK, **not** fidelity: 274/324 ship some default instrument data. Native Stage B TODO; see `docs/players/SDI.md` |
| HardTrack Composer (Longhair/Brush) → Driver 11 (Stage A) + native (Stage B) | Sequencer decode only, vs siddump on byte-exact freq registers: **88.7%** where the instrument lets the sequencer own the pitch, **2.6%** where the instrument's wave program drives `$D400/$D401` itself (field-5 bit 7). **Two columns, never averaged** — the second is the unmodelled synth engine. 8/33 files exactly 100.0%; residual is flat across time (no drift) | 🚧 RE + Stage A (`bin/hardtrack_to_sf2.py`) + Stage B (`bin/build_hardtrack_native_song.py`), neither default. **Stage A 91.3% is ABOVE the parser's 88.7% — an artifact, not an improvement** (the original's wave program bends pitch off the table value and misses; Stage A doesn't port that modulation and hits). Compare only in the LOSING direction. 6 of 8 parser-100% files are Stage A 100.0%. The apparent losses are **diagnosed as a systematic +1-frame lag** (68.9% of notes) clipped by the 8-frame window, not lost music — the renders play the identical arpeggio one frame apart. **Root cause: Driver 11's `init` leaves the `$16CC` command byte at `$00`, which its per-frame tick reads as "state not initialised" — so the driver spends its FIRST play call seeding state and EVERY Driver 11 Stage A build in this repo starts one frame late** (`docs/players/DRIVER11.md`; the earlier "template ships `$16CC=$40`" cause is corrected there). Removing that phase puts Zakplus/Hopscotch exactly on the parser's score (never losses). **Over the notes the PARSER resolves, lag-corrected, Stage A retains 99.69%** (16 lost of 5,132) — quote that, not the diluted 91.3%. `$6F` legato (pitch changes WITHOUT restarting the instrument's programs; 24.7% of all note events) was 58% of the losses and is now fixed via a duplicate instrument slot starting at the wave program's SETTLED step: 25→3 lost, plain-note losses unchanged at 18. Of the 16 left, **11 are two instruments failing 100%**, both now explained and both **Stage B material**: Walk_to_Soul's `$62` freezes the wave stepper (notes followed by `$62` lose 7.35% vs 0.26%, 28×), and Ritual_II_tune_2's program returns to base only past the window while the original scores off HardTrack's note-on base-frequency write. Driver 11 has neither mechanism. Three hypotheses were FALSIFIED on the way (cross-pattern gate state; hard-restart flag; wrapper play address). **The window has no plateau — always quote it.** Table addresses are **patched per file**, so everything is recovered by code signature — never by load+constant. 5 of 38 corpus files are refused (wrapped/multi-instance rips). `SID/Shogoon/` is **mixed-player**: 38 of 150 files. The **filter is modelled** (v3.25.0): it is **global, not per-voice** — the engine runs once per frame *after* the voice loop — and `$D416`/`$D417` are byte-exact on 32,967 frames across all 33 files. ⚠️ `$D418` is also 100% but **only 10 of 33 files exercise it**; the rest are withheld by `exercised()`, so quote the file count. `$D415` is never written by this player (0 stores corpus-wide). Five negative controls were run and four break the score (wrap 24.75%, stepper 23.90%, f6/f7 swap 28.34%, `f12==0` routing-clear 48.28%); the fifth — the field-5 bit-4 re-arm gate — **moves nothing**, because only 21 instruments set it and one has a filter, so it stays an unverified reading. The **second player build's 15 files are now seeded per-variable** from each variable's own consumer (no positional table can follow that build — its *code* differs too), freq 99.15% → 99.89%; ablation prices the whole transient at `mode` (1.67 pts) + `freq_hi`/`freq_lo`. Chasing the rest (it was **not** a seeding gap — the other 38 are worth 0.03, measured) found a **bug in the player**: the second build's `$62` handler is `STA $D406,X` where it means `,Y`, so a `$62` on voice 1/2 zeroes part of **voice 1's frequency**. Reproduced, not corrected; 15 files, exactly the second-build set. The out-of-range arp read is **FIXED**: past the 96-note table the player reads its own live RAM, so the model resolves the addresses it can name (`_var_addr_map`) — **layout-seeded population is now exactly 100.00% on frequency (0 of 53,569)**, second build 99.96%; 97 → 18 misses corpus-wide. The last **load+constant** (`vib_depth` at `load+$1C`) is gone: right on 18 files, wrong on 15, and its bytes WERE the per-voice error (`$42/$23/$0b` = +66/+35/+11). Recovered from the vibrato leg that reads it (4 legs, 2 operand pairs, unique 33/33). ⚠️ Open: on build 2 alone, seeding nothing scores 10 vs 18 — recorded, not fitted. **Stage B** (`bin/build_hardtrack_native_song.py`, no new driver — a MoN shim) CAPTURES the synth engine per frame instead of modelling it, which dissolves every Stage A loss class at once. Its residual is **one frame per note that CANNOT match** — the driver holds base pitch on its trigger frame where HardTrack still has the previous note's freq — and the builder counts how many of those carry the SID TEST bit (silent): essentially all. Net of it, Love_tune_2 loses 2/12/20 frames of 5,841 per voice (99.97/99.79/99.66%) over the full 117 s. Quote raw AND audible, never net alone. **Rung 4 listening pass run (v3.25.0)** and it found a real defect no headless metric could: the `$D418` **passband was never captured**, so every render was low-pass (`Love_tune_2` is low+band 100%) — match 0%→100%, centroid −99→−51 Hz. **DMC had the same gap and is also fixed**; FC/SDI were right by luck, Hubbard/SoundMonitor have no passband. Half the brightness gap remains. ⚠️ The waveform lead was **retired**: all those per-register figures were taken at shift 0 but the render sits at **−3** — re-measured there waveform is 100.0/100.0/99.8%, pulse/`$D417`/passband/volume 100%, cutoff 94.6%. Weakest is now **ADSR 88–94%**, systematically HardTrack's pre-note-on SR-zeroing which precedes the capture window; `hard_restart=1` is provably WRONG (the driver's row zeroes AD too, and AD differs on 0/10/20 of 1,397 frames). **Rung 3 SF2II play-test PASSES**: the editor plays our Stage B SF2 **identically to our own render** (100% freq/wf/pulse, all 3 voices, offset 0). Two earlier readings ("tool unreliable", "Stage B fails") were both retracted — a wrong control, then an offset artifact in `bin/sf2ii_vs_real.py`, now **fixed**: its search could not express a NEGATIVE offset (this render leads by 3) and ranked offsets by raw hits rather than match rate. `Love_tune_2` now reads freq 91/93/64%, wf/pulse/ADSR 100% ×3; MoN control byte-identical. ⚠️ The per-voice offset previously prescribed is the WRONG fix — the offset is one startup delay, i.e. global.

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

**On Version Bump**: Add the release entry to `CHANGELOG.md` (the canonical version history — NOT this file; CLAUDE.md stays compact) AND `STORY.md` (the project narrative — append to per-version index; update Eras / deep-tech sections only if a new architectural finding warrants it). Bump `sidm2/__init__.py __version__` + `__build_date__`. Update the Known Limitations table + relevant `docs/` if behavior changed. **Also re-stamp `docs/reference/ACCURACY_MATRIX.md`** — it is named the accuracy source of truth below, so a version bump that skips it leaves the canonical copy stale (it sat at v3.22.0 through the 3.23.0 release because this list did not name it).

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

**Size**: ~25 KB / ~6.3k tokens — this file is loaded into **every** session, so measure it in bytes, not lines. It previously drifted to 32 KB while *staying inside* a ~215-line budget, because prose migrated into table cells; a line count cannot see that. Keep per-player rows to a verdict + caveats + a `docs/players/` link. | **For full docs**: See README.md and docs/
