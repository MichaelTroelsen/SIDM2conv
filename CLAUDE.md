# CLAUDE.md - AI Assistant Quick Reference

**SIDM2 v3.23.0** | SID→SF2 Converter | C64 Music Tools | Updated 2026-08-09

Converts native Laxity NP21 SID files to SF2 format (100% accuracy). Features: Auto-driver selection, VSID audio export, Batch Analysis (multi-pair comparison), Accuracy Heatmap (4 viz modes), Trace Comparison (tabbed HTML), SF2 Viewer, Conversion Cockpit, SID Inventory (658+ files), Python siddump/SIDwinder, Batch Testing, User Docs, CI/CD (5 workflows), audio-domain listening tooling (feature summary + spectrograms, calibrated), ~2,065 tests

---

## Critical Rules

1. **Keep Root Clean**: ALL .py files in `pyscript/` only. No .py in root.
2. **Run Tests**: `test-all.bat` (7 suites) before committing; `python -m pytest` runs all ~2,065
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
test-all.bat                  # 7 suites (pytest runs all ~2,065)
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

**Audio-domain "listening" (`sidm2/audio_listen.py`)**: the companion to `audio_tightness.py`'s onset timing — whole-file/per-section features (level in dBFS **and** A-weighted dBA, spectral centroid/rolloff, flatness, silence, 12-bin pitch-class **chroma**) plus a 3-panel spectrogram PNG the assistant reads directly. numpy+Pillow only. **Calibrated against the one recorded human verdict** (B13/Glyptodont, `pyscript/calibration_cases.json`, `docs/AUDIO_LISTENING_CALIBRATION.md`) — read that before quoting any of it: onset match has **ordinal sensitivity but no absolute gate** (a 99.8%-register-exact build scores 64.7% against an 85-91% original-vs-itself floor, so any threshold flagging the bad build condemns the good one — use it against a baseline, never as pass/fail, and measure the floor per tune). Of the five features, **A-weighting is the strongest discriminator** (5.4x better separation than raw dBFS), **chroma is a correct null** on a percussive defect, **mel is unproven** on one tune, and **`--windowed`'s verdict is degenerate on original-vs-driver comparisons** — `silence_frac` differs systematically (a driver never reproduces the original's startup silence) and the flat-baseline scoring branch outranges the sigma branch, so silence wins outright; re-rank without it. See the KNOWN LIMITATION block in the module. Four of these five would have shipped a *confidently wrong* number that their own unit test passed; each was caught only by running against real material.

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
| Martin Galway → trace native driver | ~100% | ✅ 40/40 build, 30/40 objectively clean (`bin/`, not default); see `docs/players/GALWAY.md`. NB the **default pipeline's** Galway→Driver 11 path was silently dropping 29 sequences on `Short_Circuit` (128-slot cap) — **fixed 2026-07-30**, it now splits into parts with `output_path` as part 1; other 39 byte-identical |
| ROMUZAK V6.3 → native driver | ~98-100% | ✅ Byte-exact wf/pulse/AD-SR (`bin/`, not default) |
| Maniacs of Noise (Jeroen Tel) → native driver | 100% byte-exact (Hawkeye sub 2/3) on freq/wf/pulse/**cutoff**. `$D418` was scored by NOTHING until 2026-08-07 and was wrong on 3 of 8 targets — now Cybernoid_II 0→99.7%, Hawkeye 82.5→99.9%, Supremacy sub0 0→exact | ✅ Hawkeye + Cybernoid I/II + Myth + Supremacy all build (`bin/`, not default; **Myth needs `bin/build_myth_native_song.py`**, not the generic `build_mon_native_song.py` — it is a relocating compilation with `play=$0000`, so a static parse is a pseudo-parse and the builder's speed-byte gate correctly refuses it). The passband was never captured (builder hardcoded low-pass; the driver could always carry all 3 bits) and the master volume was hardcoded `$0f` (Supremacy sub0/sub1 actually play at 6 and 8). Both fixed. Read older "filter 100%" figures as **cutoff only**. Supremacy `adsr` 2.3%/4.5% on osc2/osc3 **fixed 2026-08-08 → 100%**: the orderlist's `$70-$7F` instrument-base byte was skipped as an inert modifier, so sub0's 3-voice canon played voice 1's envelope on all three voices (one nibble: attack 4 vs 6). freq/wf/pulse byte-identical; only Supremacy uses this orderlist mode; see `docs/players/MON.md` **Cybernoid_II's "register-exact but 71-85% onset-matched = SYNTHESIS on every voice" finding was FALSIFIED 2026-08-08** — it was the metric. Registers really are identical (6 differing siddump lines in 350 frames, all in frames 0-2, all the one-frame `$D418` mode lag at startup that is the whole of the 99.7%). The audio gap is metric noise plus free-running SID phase: two `--delay=0` renders of ONE file differ by `rms(diff)/rms ~ 0.001` yet move a VOICE-ISOLATED onset count 101/88/98 and the match rate across 84-97% (the full mix is stable, 38/38). `audio_tightness_tool` now measures that floor per voice (`--repeat-floor`, default 9) and returns INCONCLUSIVE inside it; see PATTERNS.md F5b. The one real defect it turned up — a one-frame `$D418` mode lag at startup — is **fixed 2026-08-08**: `do_play` wrote the volume/mode byte before `filt_prog_step` produced `F_MODE`, so it published LAST frame's passband (cutoff never had this, `fp_apply` stores `$D415/$D416` itself). Cybernoid_II `$D418` 99.7→**0/350 differing frames**; Hawkeye sub0/2/3, Cybernoid, Supremacy sub0 all unchanged (Cybernoid osc3 freq 95.0 A/B-confirmed pre-existing). The frame-lag half is fixed in **both** the MoN-specific and shared engine (`drivers_src/common/sf2_native_driver.asm`, covering ROMUZAK + Galway). The shared engine's `ora #$0f` hardcode is **confirmed inert 2026-08-08** — traced `$D418` across 2 ROMUZAK + 4 Galway originals, none ever write it at all (frame 0's displayed value is siddump's pre-init bus garbage). No plumbing needed unless a specific file turns up that genuinely writes it; see `docs/players/ROMUZAK.md`. |
| Mainstream MoN / Jeroen Tel (SID/Tel_Jeroen, 179 files) → mon_parser | B1-indirect bucket: **12/24 onset-EXACT** (unchanged), plus **Tel_1 24%→86%** via a new row-tie flag, and **Monitor_Madness_1 2%→75/106, Monitor_Madness_2 3/146→90/146, Trying_Out_2 1/59→41/59** via a `bin/mon_validate.py` calibration fix (see note below). Trying_Out 78%, Zynon_Zak 84%, Bantam 77%, Starball 76%, Alloyrun 61% | 🚧 NEW MoN GENERATION cracked (ab99032): `_locate_b1` + `_voice_blocks_tel`. Same-day `_locate_b1_row_variant` + `_locate_tel_instr_fields`, 4 rounds (orderlist REPEAT/off1/classic-row → row-ctrl off1 → row length-mask read per-file → column-major instrument tables). **Row ctrl bit5 is a TIE flag** (`_tel_row_tie`, disassembly-confirmed via a raw zig64/vsid register trace) — a row can skip its own end-of-note gate-off, holding the SID gate through to the next row so THAT row's fresh waveform write doesn't retrigger the envelope on real hardware. Tel_1's residual was mid-note wave-program gate cycling (genuine Stage-B, hand-traced, not a grammar gap). **The validator itself (`bin/mon_validate.py`) was ALSO miscalibrating 3 files** — their raster-IRQ init primes a voice's waveform register at frame 0, and siddump's `is_first_frame` display rule shows that as a spurious onset; rewrote the offset calibration as a joint brute-force search over offset + a per-voice "drop leading artifact" candidate (first attempt regressed Cybernoid sub1 by dropping unconditionally — fixed by making the drop a search candidate, not a forced step). All signature-gated + disassembly-confirmed; one earlier round caused a real regression mid-session (over-loose proximity match), caught + fixed with a stride-consistency check before shipping — verify against the FULL bucket AND the 5-check byte-exact gate, not just the target file. Remaining: Monitor_Madness_2/Trying_Out_2 not at their theoretical max (validator finds a locally-good, not fully optimal, offset); 85-file no-copy bucket untouched. See `memory/mainstream-mon-tel.md` |
| Rob Hubbard V1 → native driver | pulse 100% (modelled engine, all voices/4 tunes), freq 99.3-100; **filter NOT exercised** (Hubbard never writes cutoff — the old "filter 100%" was 0==0) | ✅ 12 V1 tunes + subsongs (`bin/`, not default); per-instrument pulse engine. ⚠️ Stage A `Kings_of_the_Beach_intro` is **missing music** (needs 153 sequences vs the 128 cap, 25 dropped) and is the one builder that **can't** use the shared windower — its voices have no common time base (orderlists 294/322/14). Open; see `docs/players/HUBBARD.md` |
| Rob Hubbard V2 (Delta class) → native driver | Delta theme freq 100%, wf 85-97% (pessimistic — residual is pure ±1-frame skew); **pulse 100% is CAPTURED, not modelled** (`hp_engine=0`); filter not exercised | 🚧 6 split-songs + Delta + 7 swallow built; swallow-class state-region relocation + spin-class + note-format laggards open; see `docs/players/HUBBARD.md` |
| Jeroen Kimmel (Hubbard-derived) → Driver 11 | **11/12 voice-medians exact 100%** (frame-pitch) | ✅ 4 files / 9 SF2s incl. Radax 6 subtunes; arp+PWM+freq-slide(T0)+drum ported (`bin/`, not default); see `docs/players/KIMMEL.md` |
| Charles Deenen (MoN/Deenen replay) → Driver 11 | 7 clean wins (Ding, B_A_T, LotR, After_the_War, Zamzara all exactly 100/100; Constant_Runner 100/97.7; Astro 77.4/91.5); 10/19 located | 🚧 + 8 freebies at 100% (3 SM shim, 2 Hubbard, 3 MoN-TTWII sub0); per-file tempo + per-voice audio validator; builder REFUSES implausible decodes (`bin/`, not default); see `docs/players/DEENEN.md` |
| Future Composer → native driver | **Stage B: 14/15 corpus voices exactly 100.0% audible pitch, FULL song length** (n 346-2253); sole residual Triangle_Intro v1 83.6%/633fr. The builder's **raw** column (58-100%) understates — FC rests park `$0002` gate-off, inaudible; read both columns with their n | ✅ Stage B shipped 2026-07-30 via a MON shim, **no new driver** (`bin/build_fc_native_song.py`); Stage A (Driver 11) still can't gate long silent intros, Stage B can; see `docs/players/FUTURECOMPOSER.md` |
| Matt Gray → Driver 11 | **Driller build only**: sequencer onset **1513/1513 = 100%**, pitch **1513/1513 = 100%** on *plain* instruments over 240 s. Pitch-modulated notes (n=468) are **NOT claimed** — the player rewrites `$d400` every frame there, so onset is vacuously 100%; base-pitch agreement is 65.4% and that residual is the synth side | 🚧 Stage A only (`bin/`, not default). His OWN from-scratch driver (not Hubbard/Galway-derived), refined **per game** — 1 of 55 HVSC files located; `verify()` refuses unknown variants loudly. Driller's whole 11:05 song is **ONE SF2 file** (R20: the old "memory wall" 2-part split was a retracted, underivable frame ceiling — real capacity is event *density*, 57/128 sequence slots); sequences round-trip byte-exact, and the one-part module **play-tests clean in real SF2II** — **3/3 SURVIVED over 700 s**, editor clock **11:41** = whole song + loop, screenshot-verified, against the 2-part build as an interleaved control. That clears the load/crash hazard only — Stage A is knowingly missing the slide/arp/PWM/drum engine, so it will NOT sound like the original; timbre is a Stage B claim. Gotchas: PSID `load=0`; `music_init` ignores the accumulator (both subtunes play tune 1); Tusker's `play=$e002` is under KERNAL ROM. See `docs/players/MATTGRAY.md` |
| DMC (Demo Music Creator, Johannes Bjerregaard) → native driver | **Balloon 77 parts → ONE 400s SF2, wf/pulse 100×3 over the FULL 400s** (n=19996/voice, freq 80.6/100/97.7); Rockbuster ~97/100/100 *on part 1 of 16*. **Every % is window-dependent** (one file reads 100/89/95 @6s, 44/38/39 @20s) — quote the window | 🚧 56/88 build-eligible = a **mode count, NOT accuracy** (an eligible file can still score 39%); all build (`bin/`, not default); see `docs/players/DMC.md` |
| Sound Monitor (Hülsbeck) → native driver | corpus strict sweep **99.25% freq+wf** over **all 27 of 27 parts** (`pyscript/soundmonitor_sweep.py`, re-derived 2026-07-30 — supersedes the prior 99.23%/26-parts figure). freq+wf = best 2 of 4: pulse 96.67, filter 97.33 ✻ (doc-carried, not yet re-aggregated by the new sweep). 100.0 on every register: Fuck_Off 242s + Dance parts **03/04 only** | ✅ 11/11 Fun_Fun files build, 11 songs/27 parts (`bin/`, not default); **reproducible from a fresh clone** (R21) via tracked `pyscript/soundmonitor_sweep.py` + `test_soundmonitor_sweep.py`. NB the native (Stage B) path was always clean; 2 **Stage A** files were silently missing music via the Driver 11 128-slot cap (`Dance_at_Night_remix` −93 sequences, `Dreamix` −12) — **fixed 2026-07-30**, both now split into 2 parts; a different builder, never touched the 99.25%; see `docs/players/SOUNDMONITOR.md` |
| Blackbird / lft → native driver | 16-file v1.2-exact corpus **mean 99.96** register-accuracy vs the validated simulator; **11 of 16 files at exactly 100.0**, none below 99.8. NOTE the 16 files are not a chosen subset -- they are **every LFT rip `locate_blackbird` supports** (16 of 61 on disk; the other 45 are unlocatable variants). Glyptodont **162/162 note-ons** (0 missing, 0 spurious), arming 100% on every file | ✅ B1-B25 + E3e/E3f/E3g + E4/E5/E6 (`bin/`, not default — same as every other native-driver player here, not a defect). E3f combo fx values were briefly disabled on a since-**falsified** SF2II-crash report (`BB_NO_COMBO=1` disables). E4 (prepare1's byte allowance is forfeited by prepare2) + E5 (a third filter row type: hardware writes `$D418`/`$D417` every frame whatever the cutoff op is, so an ADD row0 must still set mode/res) took `To_Die_For_II` 94.2→98.2→**100.0** and `Revolutions_Delivered` 99.0→**100.0**; E6 (B7 priming and `window_steps` were fighting — a mid-note part boundary re-triggered the wave program and threw away the primed pulse phase) took `Into_the_Unknown` 98.1→**100.0**. Corpus sweep is tracked + tested (`pyscript/blackbird_sweep.py`, `pyscript/blackbird_crash_probe.py`, 34 tests) — **reproducible from a fresh clone**; see `docs/players/BLACKBIRD.md` |
| SID Duzz' It (Gallefoss/Tjelta) → Driver 11 (Stage A) | strict onset+pitch medians: A 98.3, D 100, **C 86.0** (was 66.7), B 74.8, **E 50.8** (was 47.5), **DELTA win 89.8 / strict 55.5** (8 files), V 21.8. n: A 50 B 43 C 80 D 18 E 118 DELTA 8 V 6. **Only A+D are unfitted** (C/E/DELTA/V pick a timing model best-of-N) | 🚧 **343 locate → 348 Stage A SF2s** (343 + 5 subtune), **324 sweep-validated** — three different denominators, don't conflate. "0 failures" = emitted OK, not fidelity: 274/324 ship some default instrument data. **13 files were silently MISSING MUSIC** (needed >128 sequences, the Driver 11 pointer table holds 128, the emitter truncated) — **fixed 2026-07-30**: those now split into parts (343 songs → 358 files), 330 others byte-identical. Verify: `pyscript/sf2_truncation_sweep.py sdi` → 0. C walk decoded + E $Cx trailing-delay fix + E single-store-init gen + DELTA-class play+3 wrapper cracked + multi-subtune (A/C/E) + "sixth layout" wrapper cracked; native Stage B TODO; see `docs/players/SDI.md` |

**Critical**: "SidFactory_II/Laxity" ≠ native Laxity! Check player-id: "SidFactory" = use Driver 11, "Laxity_NewPlayer_V21" = use Laxity driver

**Other**: Only native Laxity NP21 supported by Laxity driver, single subtune only, filter accuracy 100% (Stinsen verified v3.1.4)

---

## Documentation

**Start**: `README.md` | `docs/guides/GETTING_STARTED.md` | `docs/guides/TROUBLESHOOTING.md`

**User Guides** (3,400+ lines): `TUTORIALS.md`, `FAQ.md`, `BEST_PRACTICES.md`, `SF2_VIEWER_GUIDE.md`, `CONVERSION_COCKPIT_USER_GUIDE.md`, `LAXITY_DRIVER_USER_GUIDE.md`, `VALIDATION_GUIDE.md`, `LOGGING_AND_ERROR_HANDLING_GUIDE.md`

**Technical**: `docs/ARCHITECTURE.md`, `docs/COMPONENTS_REFERENCE.md`, `docs/reference/SF2_FORMAT_SPEC.md`, `docs/guides/RETRODEBUGGER_GUIDE.md` (live 6502/C64 debugging via `mcp__retrodebugger__*` — breakpoints, memory read/write, live disassembly, warp-speed fast-forward; use when a static/offline model of a player keeps guessing wrong and you need real CPU ground truth)

**Players (consolidated 2026-07-05)**: `docs/players/PLAYBOOK.md` (**the cross-player porting method** — staged Stage A/B pipeline, size caps, gotchas, new-player checklist), `docs/players/README.md` (support index), per-player docs (`LAXITY`, `GALWAY`, `MON`, `ROMUZAK`, `HUBBARD` + `HUBBARD_V2_PLAN`, `KIMMEL`, `DEENEN`, `DMC`, `SOUNDMONITOR`, `SDI`, `BLACKBIRD`, `FUTURECOMPOSER`, `DRIVER11`, `NP20`, `CLUSTERS`), `PATTERNS.md` (**the RE technique catalog** — cited as D2/D4 below), `NATIVE_DRIVER.md`, `docs/reference/ACCURACY_MATRIX.md` (accuracy source of truth, v3.22.0), `docs/ROADMAP.md` (consolidation/optimization plan)

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
