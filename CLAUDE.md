# CLAUDE.md - AI Assistant Quick Reference

**SIDM2 v3.20.0** | SID→SF2 Converter | C64 Music Tools | Updated 2026-07-12

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

**zig64 SID Tracer** (`tools/sidm2-sid-trace.exe`): Pre-built cycle-accurate SID register tracer. Usage: `sidm2-sid-trace.exe file.prg [frames] [init_hex] [play_hex] [subtune]`. Pass init/play (from the PSID header) + subtune for non-Laxity files (e.g. Galway); defaults are $1000/$1003/0. Output: CSV on stderr. Source: `C:\Users\mit\Downloads\zig64\src\examples\sidm2_sid_trace.zig` (rebuild: `zig build`).

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
| Future Composer → Driver 11 | trace-validated | 🚧 Stage A only, `$1800` variant; native driver TODO |
| DMC (Demo Music Creator, Johannes Bjerregaard) → native driver | Rockbuster ~97/100/100; Balloon 77 parts → ONE 400s SF2 (wf/pulse 100×3, step-grid) | 🚧 **56/88 onset-eligible**, all build (`bin/`, not default); bundle-bound files keep high part counts; see `docs/players/DMC.md` |
| Sound Monitor (Hülsbeck) → native driver | corpus strict sweep 99.23% freq+wf (global-delay, EVERY part); Dance parts 2-6 + Fuck_Off 242s at 100.0 every register; 11 songs/27 parts | ✅ 11/11 Fun_Fun files build (`bin/`, not default); see `docs/players/SOUNDMONITOR.md` |
| SID Duzz' It (Gallefoss/Tjelta) → Driver 11 (Stage A) | strict onset+pitch medians: A 98.3, D 100, C 66.7, B 74.8, E 57.8, V 21.8 (249 validated) | 🚧 254 Stage A SF2s (0 failures, `bin/`, not default); native Stage B TODO; see `docs/players/SDI.md` |

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

**On Version Bump**: Update `CLAUDE.md` (this file), `CHANGELOG.md`, AND `STORY.md` (the project narrative — append to per-version index; update Eras / deep-tech sections only if a new architectural finding warrants it). Bump `sidm2/__init__.py __version__` + `__build_date__`.

**Debug**: Check `output.txt` → Compare dumps (`siddump_complete.py`) → Compare audio

---

## Version History

**v3.20.0** (2026-07-12): **The SDI pitch-carrier campaign — six variants decoded, 254 Stage A SF2s, the knowledge base ships.** SDI STRICT CAMPAIGN (user: "complete the SDI first"): **variant D wfprg RESTING-PITCH port** ($13E5 walk: 3-byte rows, $FE parks on the last row = the sustained pitch, bit7=abs) → **12 D files 100.0 STRICT** (Another_Day 81→100, Banana 69→100, Culture_Mix 62→100) + the $ff track byte = LOOP not stop (Sveitser_Ost 69.5→99.2); **variant E row-0 pitch** (byte-verified 2_Young $EE1F: the set-instrument tail applies f[z0[sound]] ON the note-on frame; $c0-$ef arp records REDIRECT the sound — $F566 = ad+1) + per-file STRICT-agreement timing calibration (Kirby 16.5→71.0 from calibration alone); **variant V** — the "multispeed VE-2x/4x" files were FALSE D LOCATES (play=$0000 wrapper drives a 3-JMP module 2x/4x; module seq-row read byte-identical to D's track read → V dispatches BEFORE D): full tracker engine decoded ($40-byte state blocks, per-seq length-in-ticks, per-note instrument in the fx byte, octave-nibble pitch), 0.0 → windowed 65-91; **variant C wfprg located but GATED** (onset apply regressed Bahbar 94.3→81.4 — walk phase differs per sub-class, needs emulation). **Final corpus map** (249 validated, win/strict medians): A 98.3/98.3, D 100/100, C 98/67, B 89/75, E 72/58, V 70/22. **Stage A: 254 SF2s, 0 failures** (out/sdi_sf2/). New docs/players/SDI.md. KNOWLEDGE BASE (user: "do 1 and 2"): **docs/players/PATTERNS.md** (the technique catalog — named mechanisms/diagnostics/failure classes with symptom→exploit→sightings; the pitch-carrying instrument = 5 independent finds) + **sidm2/player_idioms.py** (knowledge as CODE: find_pattern/scan_freq_tables/follow_immediate_poke/bounded_init, tests lock each idiom against corpus files; sdi_parser consumes it). 1529+ tests green.

**v3.19.0** (2026-07-11): **Residual pockets + part-bloat levers + the Gallefoss/SDI arc opens.** SM POCKET FIXES (crown-jewel byte-verified each): no pulse streams for pulse_tie engines (Dance part03 v0 pulse **4.0→100.0** — the drift detector false-positived on ±1-frame splits of the SAME PW reset); grid-aligned part bounds + exact frame bounds in labels (sweeps parsing rounded seconds strict-collapse on grid content); **FM LOOPS** (periodic vibrato past FM_CAP loops instead of freezing — Dreamix_Two v1 88.3→98.3); **reversal-aware filter drives** (fast envelopes swallowed embedded re-attacks in one "jump run" — Dance filter 33.6→**100.0**). Honest classification: remaining v2 pulse "misses" have ZERO gated mismatches (idle-PWM, silent). PART-BLOAT LEVERS: **DMC STEP-GRID** (Balloon **77 parts → ONE 400s SF2**, wf/pulse 100×3; collapses sequence-bound files; bundle-bound files unchanged — Alf 40 parts at bundles 50-62/63 = the known DMC diversity boundary; DMC corpus 1135→~944 files); **SM STRUCTURAL ARPS** (row-header chord tables → looping semitone FM programs; Fuck_Off 906 arp notes = 99.97% strict whole-song; fixed the VACUOUS arp-acceptance tolerance for short notes — drum sections had played garbage steps); **SM PULSE CANONICALS** (unroll-guarded lossless; Dance 9→8 parts AND parts 1-6 healed to 100.0 flat). **SM corpus final: 11 songs / 27 parts, 99.23% corpus strict freq+wf.** GALLEFOSS/SDI OPENED ON THE PLAYER'S OWN SOURCE: extracted the commented SDI 2.1 source (1994 lines, c1541+petcat from the user-staged d64s → bin/SIDDuzz/extracted/) — feature-flag assembly (explains the rip clusters), track/seq byte formats, column-major zN instrument tables, waveform/pulse/arp/filter/tempo programs all mapped first-pass (memory gallefoss-sdi-player.md). 1524 tests green.

**v3.18.0** (2026-07-11): **THE INSTRUMENT-CAP OPTIMIZER (user directive) — fewer parts AND higher fidelity, plus two blindness-class bug finds.** User insight measured true: per-note capture manufactures artificial instrument variety (Dance part 1: 10 source instruments -> 31 slots). Three register-exact-guarded transforms: (1) **RELEASE_WF driver feature** — gated-off frames write the instrument's release wf (poked IRELWF = SM rec[8]) VERBATIM instead of program&$fe; `_rel_split` moves duration-positioned release tails into gate-off rows -> programs collapse to the duration-independent body (RELEASE_WF=0 proven BYTE-IDENTICAL via Hawkeye sub2, twice). (2) First-row boundary-bleed normalization (gate-clear frame 0 -> the note's own wf; 1-frame class). (3) **Dynamic filter-drive routing** — SM switches filter routing per section; drives credited to the voice the $D417 bits point at ON the attack frame + tie events drive-eligible + same-pitch filter ties at observed re-attacks (Dance part-8 window: 32->14 slots, filter 247->60 rows). **BUG FIND 1 (shipped in v3.17.0): grid-part inter-voice desync** — SMShim.frame_to_tick identity made every grid part >=2 start ALL voices at row 0; Dance part05 28-65% freq -> **100.0 every register every voice** after the fix; masked by part01-only sweeps + per-voice-delay tooling (LESSON: later parts need GLOBAL-delay metrics). **BUG FIND 2: DMC within-frame blindness** — audit found 24/88 DMC files retriggering OFF+ON in one play call; the missed onsets also FAILED the agreement gate -> whole files on tick-grid fallback. Balloon part01: wf 0/70/36 pulse 1/0/95 -> **wf 100/100/92 pulse 100/100/100**; within_frame now the DMC default (DMC_WF=0 reverts; gate still protects multispeed). **SM corpus: 11 songs / 28 parts** (was 32), corpus-wide strict sweep (global delay, EVERY part) **99.08% freq+wf**, WAV RMS 0.92-1.05. New diagnostics: INSTR_DECOMPOSE=1 (pre-cluster slot decomposition), bin/_dmc_wf_audit.py, bin/_opt_sweep_corpus.py. 1524 tests green.

**v3.13.1** (2026-07-05): **Docs-only consolidation release — the cross-player knowledge base.** New `docs/players/PLAYBOOK.md` (the consolidated porting method: staged RE→Stage A→Stage B→Stage C pipeline, technique catalog, SF2II caps, fidelity ladder, all gotchas, new-player checklist), `docs/players/MON.md` (Hawkeye/Cybernoid/Myth/Supremacy — was undocumented despite being the v3.13.0 headline), `docs/players/CLUSTERS.md` (DRAX/Stinsen/Beast/Angular/2000AD/Wizax/V20). Rewritten to v3.13 state: `docs/reference/ACCURACY_MATRIX.md` (was v3.1.1), `docs/ROADMAP.md` (prioritized optimization plan: unify the 3-copy native driver, shared native-build + fidelity libs incl. the `_semi()` reference-freq drift, registry-wire the bin/ players, universal trace-first fallback toward "any SID → 99%/100% editable"), `README.md` (stale 3.6.0/3.2.1 headers + false limitations), `docs/INDEX.md` (players tree indexed, ~12 dead links fixed), `docs/players/README.md`. No code changes (version constant only).

**v3.17.0** (2026-07-10): **Sound Monitor (Chris Hülsbeck '86) — the seventh from-scratch player, full arc in ONE day.** The 11-file Fun_Fun `$C000/$C475` cluster ("MUSICMASTER" driver, byte-identical player at a fixed load → hardcoded table addresses, no relocation). `sidm2/soundmonitor_parser.py` (ROW model w/ 8-bit wraparound; per-row bar/transpose tables; complete data-flag map incl. `$10` glide; the **chord-arp bank inside the row-header record**; 24-byte sounds) onset-validated **99.9% corpus-wide**. Stage A `bin/soundmonitor_to_sf2.py` → editable Driver-11, **32/33 voices note-accurate** (gotcha locked by test: **runtime Driver 11 can't parse `$90-$9F` tie bytes** — editor-only feature, emitting them desyncs playback). Stage B `bin/build_soundmonitor_native_song.py` (SMShim → shared MoN engine): onset-aligned + legato A/B + **FM_CAP-gated TIE SPLITS** (Fuck_Off osc2 66.6→**100** strict freq/wf) — **Final_Luv = whole 161s song in ONE part, 98.1-99.9 skew-tolerant every register, filter 99.9**; 11 songs / 52 parts. Engine finds: `$CB65` = the ARPEGGIO engine (not digi); `$C31B` = the triangle-PWM engine (dispatcher Y=2/9/16 → pulse regs); REST writes the sound record's byte-8 RELEASE WAVEFORM (gated release = voices legato through rests). New `docs/players/SOUNDMONITOR.md`; 12 tests; memory `soundmonitor-player.md`. 1524 tests green.

**v3.16.0** (2026-07-10): **The part-reduction + fidelity-truth campaign — fewer files per song across every native player, and the analyser that finds its own fixes.** User goal: reduce SF2 parts per song (each subtune = its own file is fine). Root cause MEASURED: ~95% of splits = the 64-slot `$c0-$ff` (FM,pulse) **bundle** channel; Phase-0 decompose showed Hubbard FM is structural (24 shapes/song — pulse drives its explosion) while DMC is diverse in both axes (clustering = proven dud). Levers shipped: (1) **pulse_canon** per-instrument pulse canonical — **Commando 45→4 parts, Monty 22→4, Chimera 76→12, byte-exact**; gated to `hp_engine` builds after proving it LOSSY for captured-pulse classes (Shockway osc3 pulse 0.3→100 with it off; MoN opt-in `MON_PULSE_CANON=1`). (2) **Track bit7 TRANSPOSE generation decoded** (3 ROM-verified encodings) — the parser had read them as pattern numbers 128+ → garbage → **Shockway 638 parts of repeats → 21** (Star_Paws 188→10, Auf_W 274→43); + span-sanity guard, split pulse-speed table (`lay.pulsespeed_tbl`), the class's self-modifying-rails pulse engine decoded (fetch-frame step + fx-arp re-fetch = the documented residual). (3) Builders **auto-prune stale parts**. Hubbard corpus → **529 files**. **Fidelity**: the **wave REST-TAIL fix** (capture extends across rests; cap 96→256) — **Supremacy sub1 94.3→99.9 every register, Cybernoid II part01 100×3, Cybernoid I wf/pulse 100**, crown jewel intact. **DMC 33→41 eligible** (state-copy/staged-emit/ADC-vibrato/interleaved-track generations) + the full-song per-voice **legato A/B** (Dreaming osc3 39→90, guaranteed non-regressing). **Analyser** (`bin/mon_part_fidelity.py`): per-voice delay, **skew-vs-content classification** (Supremacy sub2 osc2 = 47.7 strict / 100.0 skew-tolerant = audibly exact), **mismatch-cluster report** (it localized the rest-tail fix), part-loop auto-cap. **Infra**: `docs/SF2.md` build index + `pyscript/gen_sf2_index.py`; **CI security scan green after 199 red runs** (8 live bandit findings repaired, archive/ excluded). Sound Monitor arc opened (11-file `$C000/$C475` Fun_Fun cluster; ROMUZAK's `SOUNDMONITOR_CNV` = the reference). 1512 tests green. Analysis: `docs/analysis/PART_REDUCTION_PLAN.md`.

**v3.15.0** (2026-07-09): **DMC (Demo Music Creator) — Johannes Bjerregaard, the sixth from-scratch native player, and a format that unlocks hundreds of HVSC tunes.** DMC (the DMC4 Player, Brian/Graffity '91) is one of the most-used C64 editors ever, so a parser generalises far beyond the `SID/JohannesBjerregaard/` corpus (88 files, ~all Bjerregaard — Blue_Monday_88/Billie_Jean/Domino_Dancing covers + DMC_Demo_IV). Ground truth: the DMC4 editor (`~/Downloads/dmc4editor11_win64.zip`; disks in `bin/DMC/`). Format RE'd from **Balloon.sid** (Track→Sector→Sound; `sidm2/dmc_parser.py`, relocation-safe signature-located tables — the player relocates to many load addresses like Hubbard V2; dominant fingerprint init+$440/play+$3). Model: **Track** (orderlist, `$FF` loop/`$FE` end) → **Sector** (pattern; command byte dur=low5/bit5 flag/bit6=2 effect bytes/bit7=sound, `(cmd&$E0)==$C0`=REST, `$FF` ends) → **Sound** (8-byte instrument `$1500`: AD/SR/PW-init/PW-rails/PW-speed/vibrato/filter/flags; classic DMC PWM sweep). **Freq table** `$135F` interleaved lo/hi. **The DMC signature = the WAVETABLE** (`$1A00` arp / `$1B00` waveform, advanced 1 step/frame → fast per-frame arp; `$1A00` byte = `$80|note` absolute, `$7E/$7F` loop): the freq-table row is the wavetable value, so DMC plays notes far above its own table via octave shift. Parser+decoder: **29/43 main-player files ≥90%** per-voice onsets (the correct metric — a single global phase undercounts because voices trigger a few frames apart). `measure_onsets` = siddump CPU + `$D012` raster fake, records every per-voice `$D404` gate-rise = exact onsets. Native Stage B (`bin/build_dmc_native_song.py`, DMCShim → the shared MoN pipeline): **onset-aligned** mode (fpt=1, one note per emulated gate-rise, pitch = trace-resolved absolute semitone via full-range PAL) triggers on the true frame so the FM capture reproduces the arp **in phase** — **Rockbuster freq 65→97, wf 87→100, pulse 100/100/100**. 21/43 files onset-eligible (incl. several decode-FAIL variants — onset-align is decode-independent for pitch/timing), most 2/3 voices 90–100%. 6 DMC tests green. **Open:** per-voice **adaptive** base-note resolution for fast-arp voices (a 1-frame arp attack spike at onset+1 traps the fixed-frame `_sem` resolver — Wanna_Get_Sick osc1 @33%, Omega_Force_One); multispeed/self-IRQ variants (Chase); the 0%-variant track signature. **Dead ends** (do not retry): the wavetable-arp *semitone* model regresses (DMC's freq table isn't PAL → the Hz-delta onset-aligned capture is strictly more exact); global tick→frame schedule; pitch-step/debounced onset detection; minimal-embed SF2 (crashes SF2II). New doc `docs/players/DMC.md`; memory `johannes-bjerregaard-player.md`. Hubbard shipped v3.14.0.

**v3.14.0** (2026-07-08): **Rob Hubbard — the fifth from-scratch native player, and it was TWO formats.** Ground truth: Anthony McSweeney's commented Monty disassembly (C=Hacking #5, `docs/analysis/hubbard/chacking5_monty_disassembly.txt`). Parser `sidm2/hubbard_parser.py` (relocation-safe signatures, V1+V2), Stage A `bin/hubbard_to_sf2.py`, Stage B `bin/build_hubbard_native_song.py` (reuses the shared MoN native builder/driver). **V1** (~12 tunes + subsongs — Monty/Commando/Zoids/Gremlins/Master_of_Magic/One_Man/Last_V8+C128/Geoff_Capes/Crazy_Comets/Chimera/5_Title_Tunes/Gerry): **pulse + freq + filter 100%** via the **per-instrument HP pulse engine** (the ROM's pulsework re-implemented in the driver — pulse is exact by construction; classic bounce + fast-PWM, load-image-seeded counters, `HPMAP` slot→instrument). Three ear-caught / VICE-dump-found fixes: no-release (bit5) chains are **ties** not retriggers (2-frame bass chop); ADSR re-arms **on** the fetch frame; compilation rips (`5_Title_Tunes` = 5 embedded players → module-windowed signatures + init-flag module map); looping-ostinato track expansion. **V2** (Delta class, incremental deltas — split lo/hi song tables, the **fractional-tempo swallow counter** → poked `TEMPO_SWALLOW` driver flag, 4-byte-porta/1-byte-rest/no-fetch note format, repeat-count tracks, pulse-resets-per-fetch): **Delta** (the theme is PSID **song 12/13**, caught by the user) plays freq/pulse/filter **100%** (wf 85-96%); 6 split-songs files built. Infra: the **vacuous-100.0** fidelity bug fixed+guarded (a `secs=0` window measured a *silent* SF2 as perfect); play-routine **spin class** routed through the siddump CPU with a raster fake (a batch-killing 3-hour replay → 27 s); `bin/hubbard_build_all.py` corpus runner (sequential, timeout-proof). **Open:** the V2 **swallow-class state-region overlap** (`$16CC-$1702` — filter programs spill; 7 files decode 100% but don't assemble), 3 spin-class timeouts, ~7 note-format/speed laggards (IK+/Thundercats/Tarzan/Mega_Apocalypse/Knucklebusters/Game_Killer), 6 no-signature files. New doc `docs/players/HUBBARD.md`; memory `hubbard-player-re.md`. ~19 tunes build, ~28 decode ≥95%.

**v3.13.0** (2026-06-29): **Three new players land — Future Composer, ROMUZAK, and Hawkeye/Maniacs-of-Noise (Jeroen Tel) — each SID→SF2, the last two with from-scratch NATIVE SF2 drivers that load in stock SID Factory II.** All Stage-B work reuses the shared trace-driven native-driver pipeline first built for Galway (`bin/build_*_native_song.py` + `bin/build_*_driver_full.py` + per-frame fidelity metric). (1) **Future Composer** ("The Beat-Machine" V4.1): format fully RE'd from `Triangle_Intro.sid` (`sidm2/fc_parser.py` + `bin/fc_to_sf2.py`, 4 tests); Stage-A Driver-11 transpiler is trace-validated (every V2 melody note matches siddump). Handles the `$1800` player variant (5/20 Fun_Fun files); other load addresses need player-base detection. (2) **ROMUZAK V6.3** (Oliver Blasnik): Stage-A Driver-11 transpiler **plus** a from-scratch native SF2 driver (`drivers_src/romuzak/`) reaching note/orderlist-exact + **byte-exact waveform/pulse/AD-SR (~98–100%)** on both Fun_Fun tunes; deterministic validator `bin/romuzak_native_validate.py`; loads+plays in stock SF2II. (3) **Hawkeye / Maniacs of Noise** (the headline): MoN two-level orderlist→pattern engine RE'd (`sidm2/mon_parser.py`, frame-exact: SPLIT freq table lo `$8337`/hi `$8396`, `$FE`=song-end, `$FF`=loop, `$40-$5F`=pattern-repeat counter, 8-byte instrument records `$860C`). Stage A (`bin/mon_to_sf2.py`) → editable Driver-11 SF2, **GUI-confirmed sub 2 & 3** (sub3 28/28 onsets, sub2 174/174, all EXACT). Stage B native driver (`drivers_src/mon/`, `bin/build_mon_native_song.py`, `bin/mon_fidelity.py`): **subtunes 2 AND 3 = freq + waveform + pulse + FILTER ALL 100% BYTE-EXACT on all 3 voices, full song length, single editable SF2 each.** Mechanism: per-note (FM, pulse) bundles via the `$c0-$ff` command channel (slides+arps, drop delta[0] for the 1-frame `pr_note` hold); per-note WAVE programs as distinct instruments (gate envelope); global resonant FILTER restarted per note by a flag-`$40` instrument. For the dense ~6.4-min main theme (subtune 0, ~6000 notes > the 64-bundle/32-instrument/$D000 caps): **greedy nearest-merge clustering** + **window-splitting** (13×30s parts, `py -3 bin/build_mon_native_song.py SID 0 30`) — each part ~100% pitch/waveform/pulse, filter ~75% (window-boundary seam, open). 9 mon tests green. Status/handoff: `whats-next.md`; memory `hawkeye-mon-player-re.md`, `romuzak-player-re.md`, `future-composer-player.md`. Also this cycle: `siddump_complete.py` gained `--bits` bit-field column mode + `--written` write-precision mode.

**v3.12.0** (2026-06-22): **The ENTIRE 40-tune Galway corpus now builds — 37 trace-faithful + 3 near, 0 blocked (was 4/40 validated) — plus editable chord-arp wave tables.** Three advances (trace-driven path only; all in `bin/build_galway_trace_song.py` + `bin/build_galway_native_song.py` + the zig64 tracer). (1) **`play=$0000` self-installed-IRQ tracing** (unblocks the last 6: Arkanoid, Arkanoid alt-drums, Game Over, Combat School, MicroProse Soccer V1 + intro). These tunes' INIT installs its own IRQ (a RASTER handler at the hardware vector `$FFFE` with `$01=$35` banking the KERNAL out, OR the KERNAL `CINV $0314`) and **never RTSes** (it CLIs + spins) → the old init+play trace got nothing AND `c64.call(init)` hung. New tracer path (`tools/sidm2_sid_trace.zig`, rebuilt **ReleaseFast**): bounded INIT until the vector installs, derive the handler from whichever vector changed, then drive each frame by **simulating a 6502 IRQ** (push return-PC=`$FFF0` + status, jump to handler, halt when it RTIs to an RTS sentinel) with a per-frame step cap so a quirky handler can't hang. The real speed fix was `detect_multispeed`: shortcut `play=0 → 1` (raster = 1 play/frame; INIT never RTSes so the CIA-timer probe otherwise spun py65 ~60s/build). Combat School's music is **subtune 1** (PSID default 0 is a sparse jingle); MPS V1 uses the KERNAL path, the rest hardware. All 6 → FAITHFUL ~100% in 3-4s. (2) **Chord arpeggios → the editable WAVE table** (`GALWAY_ARP_WAVE`, default on). Arps were buried in the driver-internal FM (invisible/uneditable); now a discrete-semitone arp (≥2 levels, span≥2, both directions, **on-grid** — frequencies sit on exact semitones, detrended by the note's own detune; wide vibratos sit ~0.5 off-grid → stay in FM) is emitted as a per-instrument wave program (`waveform,semitone` rows + `$7f` loop), the FM goes flat, and the instrument key gains the arp. Loss-free (same freqtable lookups), and **editing the wave column changes playback** (`wave_step`). Pre-scan budgets the 256-row table (adopt the most-common arps, rare → FM); `gen_includes_song` dedups identical programs. Terra Cresta `0-3-7-12` chords now visible/editable; Terra Cresta → 100% on every register in real SF2II (was CHECK). (3) **Nearest-merge `(fm,pulse)` bundle clustering** (dense tunes — Rambo's 95 bundles > the 64-entry `$c0-$ff` command channel; SF2II allows one command index/row so FM+pulse can't be independent channels). Replaces the old contour-quantising `fmq` (which at high coarseness merged a downward slide INTO a flat vibrato → phantom pitch slide). New `cluster_bundles`: keep every bundle exact, greedily merge the two MOST-similar (FM-contour L1, count-weighted so the loss hits the fewest notes, hard FM-distance cap so a slide is never merged into a vibrato) until ≤63; **pulse-audibility-aware** — a tie's EMPTY pulse and a saw/tri note's pulse are don't-care, so those merge free and the loss lands where it's inaudible. Full Rambo: freq ~99/100/98, osc2 (the pulse-heavy voice) pulse 33%→**95%**, osc3 (saw) 100%. **SF2II-validated set now 5** (added Rambo). Batch → `out/galway_sf2/`. 87 galway tests green. Full status: `docs/players/GALWAY.md`.

**v3.11.0** (2026-06-21): **Full-fidelity, full-length WIZBALL — the default Galway tune now plays ~100% on every SID register in stock SF2II.** v3.10.0 fixed Ocean Loader but left the default Wizball tune benched (its trace extracted only ~2 notes/voice). Two fixes. (1) **Legato note extraction** (`sidm2/galway_trace_extract.py`, commit `3bb2829`): Wizball's default tune is fully LEGATO (every voice holds the gate and changes pitch via the player), so the gate-based detector collapsed each voice to ~1-2 notes; new `_legato_splits` recovers the melody by settled-pitch change (split notes tagged `tie=True`), applied only to legato voices. Driver gained tie handling (`pn_tied`: `$90-$9f` `$10` bit = tie → pitch change, no re-gate, pulse free-runs). 30s build → pulse 64/10/8% → 99%. (2) **16-bit pulse pointer** (commit `9a2f697`): at full length the lead's pulse fell to ~19% (freq/wave/AD-SR already 100%) because the driver's PULSE table was capped at 256 rows by an 8-bit index, but the 135s song needs ~573 rows. Fix: convert the pulse engine to **FM's 16-bit pointer** — `pulse_step` walks a ROW-major PULSETAB (3 bytes/entry, `$7f`=freeze) via per-voice `PPTR`, no cap; emitter lays distinct programs row-major after FMTAB with per-command `IPULSE_LO/HI`. Gotcha: `pptr` ZP at `$ea/$eb` collided with `vhold[1]/vhold[2]` → voices 1/2 silent; moved to `$b9`. Build: pulse is per-GATE-REGION (driver resets per gate-on, free-runs across ties), length-proportional row budget, `PULSE_TABLE_ROWS` 256→1024, legato tunes auto-use TEMPO=multispeed (1 row/video frame — frame-accurate pulse resets; tempo 8 drops to 92%, tempo 2 = same sound 2× rows, tempo 4 = sweet spot). **Real-SF2II result (full 135s default Wizball): osc1 100/100/100/100, osc2 99/100/99/100, osc3 100/100/99/100; 120s window 96-100%.** Ocean Loader unchanged at 100/100/100/100 (shared driver/emitter re-verified). 87 galway tests green. Tradeoff: pulse table now driver-internal row-major → no longer an editable SF2II table (playback faithful). Still NOT the default `convert_galway_to_sf2` (lives in `bin/`). Out: `out/Wizball_full.sf2`.

**v3.10.0** (2026-06-20): **Full-fidelity, full-length Galway — the trace-driven native-driver build now reproduces a 9-minute Ocean Loader at ~100% on EVERY SID register in stock SF2II.** v3.9.0's converter keyed each instrument on `(waveform,AD,SR,FM-shape)`, cramming timbre×slide into the one 32-slot table; on Ocean Loader 1 (~6.6min, ~8000 notes) that forced slide-clustering (one note's slide reused for a whole cluster) → pitch corruption. Fix: **decouple the per-note synth program from the instrument.** The sequence command channel `$c0-$ff` (previously a skipped no-op) now selects a per-note BUNDLE of (FM slide + pulse-width envelope); the instrument carries timbre only → Ocean fits **18 instruments + 32 bundles**, no clustering. Driver (`drivers_src/galway/galway_driver.asm`): `pr_skipcmd`→`pr_setprog` sets `VIFM`+`VIPULSE` from per-command `IFM`/`IPULSE` tables; `set_instr_v` no longer sets FM/pulse; `do_init` defaults to program 0. Also a **1-frame FM-trigger fix** (`pr_note` now holds base pitch on the trigger frame via `FM_CNT=1`+`FM_OFF=0` — the driver had applied the first slide delta a frame early, ahead of the real SID). `bin/build_galway_native_song.py` `gen_includes_song` builds per-command FM+pulse tables (dedup + pulse truncated ≤256 rows, new `IPULSE` stride-64 table). `bin/build_galway_trace_song.py` adds the bundle builder, a note end-clamp (long tails no longer push the next note late), and a **PSID export** (`out/galway_trace_song.sid`, init=$1000/play=$1003) so the native driver renders to WAV. **The fidelity-measuring "listen" tool `bin/sf2ii_vs_real.py`** diffs an instrumented SF2II's actual per-frame SID output vs the real SID per voice (freq/waveform/pulse/AD-SR) — it exposed the pulse gap (was 71/8/13%) the pitch-only headless metric missed. **Real-SF2II result: osc1 100/100/100/100, osc2 100/100/99/100, osc3 100/100/100/100.** Memory wall ($D000) caps one SF2 at ~27650 play-calls (9.19min). Still NOT the default `convert_galway_to_sf2` (lives in `bin/`). 87 galway tests green. Plan: `docs/analysis/GALWAY_SF2_DRIVER_PLAN.md`.

**v3.9.0** (2026-05-30): **Stage B2 — the native Galway driver is now a FULL standard table-driven SF2 driver (wave + pulse + filter all editable AND driving playback).** Where v3.8.0 played Wizball with hand-tuned synth shortcuts (single waveform byte, pulse-width in an instrument column, empty pulse/filter editor tables), v3.9.0 ports the real Driver-11 table interpreters into `drivers_src/galway/galway_driver.asm`: `wave_step` (2-col wave programs: waveform+semitone, `$7f` jump), `pulse_step` (3-col `8X` set / `0X` add / `7f` jump), `filt_prog_step` (global filter: `9Y YY RB` set passband/cutoff/res/bitmask, `0X` add-to-cutoff, `7f` jump; started by an instrument flag `$40`). Per-voice/global program state lives in scratch RAM `$1800+`. Spec RE'd → `docs/analysis/DRIVER11_TABLE_FORMATS.txt`. `bin/build_galway_native_song.py` now emits **standard-format** wave/pulse/filter tables + real instrument column pointers (AD/SR/Flags/Filter/Pulse/Wave) + instrument **names** (id=4 TableText aux). Each table verified BYTE-FOR-BYTE against the real Wizball SID (waveform `$41`; pulse `$800 +8/frame`; filter `D417 $F1`/`D418 $1F`/cutoff `$89→$78`). **User-confirmed in SF2II: all three tables render as programs AND editing a table changes playback; instrument list populated.** Two crash classes fixed earlier this cycle: SF2II's 1024-event `Unpack` overflow (cap sequences by unpacked-event count) and a freqtable/`$16cc-$1702` state-region overlap (pin freqtable at `$1710` + build guard in `assemble()`). 6502 gotchas logged: `STY abs,x` is invalid (use `STA abs,x`); long routines overflow `bpl`/`bne` range (use near-branch + `jmp`). 81 galway tests green. **Still NOT the default `convert_galway_to_sf2`** (lives in `bin/` scripts) — wiring it in is the next milestone; faithful per-frame FM and full-length songs remain. Plan: `docs/analysis/GALWAY_SF2_DRIVER_PLAN.md`.

**v3.8.0** (2026-05-30): **Stage B milestone — a from-scratch NATIVE Galway SF2 driver that loads in stock SID Factory II and plays a real Galway tune.** Where Stage A (v3.7.0) transposed Galway onto Driver 11, Stage B authors a purpose-built driver (6502 + descriptor, no SF2II changes needed — it's data-driven). Delivered: B0 descriptor-format RE (`docs/analysis/SF2_DRIVER_BINARY_FORMAT.md`); B1 toolchain (64tass) + skeleton that loads; B2/B3 full SF2-format sequencer in 6502 (`drivers_src/galway/galway_driver.asm`: 3 voices, orderlist chaining, packed sequences, durations, per-instrument ADSR+waveform, transpose); B4 `bin/build_galway_native_song.py` → **Wizball plays through the native driver** (15 patterns, parses as "Galway"/3 tracks, headless-verified); B5-start pulse-width modulation. A "6510 emulation exceeded cycle window" load bug was self-diagnosed via the in-repo `bin/SIDFactoryII.exe --skip-intro` (parse log + screenshots) + a py65 model of SF2II's RTS-suspend mechanism, fixed with a parser anti-runaway guard. Build: `bin/build_galway_driver_full.py` (test pattern) / `build_galway_native_song.py` (real SID). **NOT yet the default `convert_galway_to_sf2`** (still Stage A Driver 11 transpile); faithful FM/PM `SOUNDn` synth + full-length songs remain. 61 galway tests green. Plan: `docs/analysis/GALWAY_SF2_DRIVER_PLAN.md`.

**v3.7.0** (2026-05-29): **Galway → EDITABLE Driver 11 SF2 (Stage A of the native-driver plan).** Replaces the v3.6.x embed default: instead of embedding the original player (audio-only, editor display-only), `convert_galway_to_sf2` now transpiles the 1st-gen bytecode-extracted score onto a real **Driver 11** SF2 — the editor edits the tables and Driver 11 plays them (edits affect playback). New `sidm2/galway_to_driver11.py` (mapping → `GalwayDriver11Song` IR: pitch = PAL-table index+1; tempo = GCD of common durations; per-instrument AD/SR + `PINIT` pulse width) + `sidm2/galway_driver11_emitter.py` (packed-sequence format ported from SF2II `datasource_sequence.cpp`; overwrites the `Driver 11 Test - Arpeggio.sf2` template; column-major tables; long-track segmentation; aux rebuild + `$0FFB` repoint). Embed remains the fallback (`config.galway_mode`). **User-confirmed in SF2II: opens, shows notes + instruments, plays via F1 — notes/pitch/timing correct.** Two silent-playback bugs fixed during the GUI test (pulse voices need a pulse-width program; HR/flags defaults). **Known limit → Stage B:** timbre approximated (pulse/FM/filter *modulation* lives in Galway's per-frame synth, not static tables); Stage B will author a native Galway SF2 driver. Plan: `docs/analysis/GALWAY_SF2_DRIVER_PLAN.md` + `GALWAY_TO_DRIVER11_MAPPING.md`. 1357 → 1389 tests. Retired the fictional "88-96%" accuracy figure.

**v3.6.3** (2026-05-28): **Galway SF2 now PLAYS in SID Factory II + shows instruments.** Two fixes from a real SF2II load-test (it loaded but was silent with no instruments): (1) the minimal-embed INIT handler now bakes the subtune into A (`LDA #subtune; JSR init; RTS`) — SF2II calls INIT with A=0, but many rips (Galway/Wizball) leave subtune 0 silent (the music is subtune 3); handler layout shifted (INIT 6 bytes, PLAY +6, STOP +10). (2) `build_placeholder_edit_area` + `build_minimal_embed_sf2` now accept `instruments` and populate the Driver-11 instrument table (`[AD,SR,HR,Filter,Pulse,Wave]`) + wave table (waveform char) so the editor's F2 view shows real instruments (display-only — audio still comes from the embedded player). Verified via cycle-accurate trace through the INIT handler with A=0 → plays subtune 3; Wizball.sf2 shows 5 instruments. 1357 tests.

**v3.6.2** (2026-05-28): **Galway conversion WIRED — `convert_galway_to_sf2` now produces a real, working SF2.** Replaced the lossy table-remap stub (`GalwayConversionIntegrator`) with: embed the real player (audio, via `minimal_embed_builder` — now accepts `voice_streams`) + populate the editor view from the 1st-gen extractor (notes + control flow + instruments). Also resolves the PSID embedded load address (Galway rips ship `load=0` with the real load word as the first 2 data bytes — previously unhandled, which broke both embed placement and recovery). Verified: generated `Wizball.sf2` plays cycle-accurately (frame-0 osc1 $1F1F/AD$06/SR$FA/ctrl$41 matches the original) AND carries 1127 notes / 5 instruments in the editor; Terra_Cresta 2800 notes / 9 instruments. Galway driver registry description/accuracy updated. 1364 → 1365 tests (+1 end-to-end). **Galway now works** (audio + 1st-gen editor view); Hubbard is next.

**v3.6.1** (2026-05-28): **Martin Galway 1st-gen editor extractor — built + validated, NOT yet wired into conversion.** New `sidm2/galway_1stgen_detector.py` (deterministic detector, 3 dispatch variants indirect/indexed/masked, relocation-safe), `galway_1stgen_extractor.py` (channel-PC recovery via init-emulation + subtune sweep, 17/21 corpus; bytecode flattener resolving Call/Ret/For/Next/Jmp/CT/JT with per-file empirically-probed opcode lengths, 36/51 voices desync-free; Vlm+FLoad instrument decode; `galway_to_voice_streams` → SF2 orderlists/sequences), and `galway_trace.py` (universal instrument palette from a cycle-accurate trace). Engine RE'd from Martin Galway's own source (github.com/MartinGalway/C64_music). **Validation unblocked**: rebuilt the zig64 tracer (`tools/sidm2-sid-trace.exe`) to accept `init/play/subtune` so Galway files trace cycle-accurately; instrument extraction confirmed against it (Wizball/Terra_Cresta all played instruments captured). `sid_init_runner.run_init` gained a `subtune` arg. The stub `convert_galway_to_sf2` is NOT yet replaced — final SF2-emission wiring is next. 1314 → 1364 tests (+50). Engine map: `docs/analysis/GALWAY_1STGEN_ENGINE.md`.

**v3.5.70** (2026-05-28): DRAX instrument-table BASE confirmed = detector operand − 2 (byte 0 = AD, byte 1 = SR), verified across all 6 cluster files (4 DRAX + 2 Laxity-G4) via a per-file backward dataflow trace from the fixed `STA $D40x,Y` output writes (robust to the file-specific $18xx scratch addresses). Detector now exposes `instrument_table_addr` (= operand − 2) + `note_ctrl_read_operand`; instr0 AD/SR are all sane SID envelopes. 1312 → 1314 tests (+2). Discipline note: generalized only AFTER per-file confirmation (the earlier one-file generalizations were the v3.5.67/68 mislabels).

**v3.5.69** (2026-05-28): **DRAX $1B8A identity RESOLVED — it's the instrument table.** Via py65 clean disasm: Y for the $1B8A field reads comes from $18C8,X = `instrument*8` (set on the $A0-$BF set-instrument command at $11A9; `& $1F` → up to 32 instruments; never per-frame incremented). So 8-byte records indexed by instrument → instrument table, not a wave table. (First trace chased the wrong scratch $18B9 = note-index; py65 showed the real source $18C8.) `drax_record_table_detector` docs + memory updated; it's the DRAX F2 (instrument) anchor. Per-field record semantics still partial. Detector behavior unchanged (docs-only release). 1312 tests.

**v3.5.68** (2026-05-28): **Correction of the v3.5.67 mislabel.** Fuller disassembly showed $1B8A (Dreams) is an 8-byte STRUCTURED-RECORD table (same Y reads fields at +0..+4), NOT the flat single-byte wave table v3.5.67 claimed. The +0 field IS a packed note(low nibble)+ctrl(high 2 bits) byte (that decode was real), but the table is 8-byte records, and its wave-vs-instrument identity is unresolved. Renamed `np21_packed_wave_detector` → `drax_record_table_detector` (`detect_drax_record_table`, `DraxRecordTableLayout.record_table_addr`); the locator still correctly finds the table base across all 4 DRAX files. Memory note corrected with the lesson (confirm record stride before claiming a table's format). 1312 tests (unchanged count; module renamed).

**v3.5.67** (2026-05-28): DRAX/NP21-G4 packed-wave detector checkpoint. *(Superseded by v3.5.68 — the "wave table" label was wrong; see below.)* The 4 SID/ root "None wired" files (Colorama/Delicate/Dreams/Omniphunk) are Thomas Mogensen (DRAX) NP21-fork players sharing one codebase; their wave table is SINGLE-BYTE packed (low nibble=note offset, high 2 bits=waveform), which `find_wave_table_from_player_code` (built for 2-byte rows) misses. New `sidm2/np21_packed_wave_detector.py` locates it via the read-path signature (`B9 lo hi; TAY; AND #$0F; … TYA; AND #mask`) — RE-verified addresses Colorama $1BDD, Delicate $1C51, Dreams $1B8A, Omniphunk $1B73. FALLBACK-only (the idiom also appears at pulse/filter sites in Beast/Angular). Detector + 9 tests; NOT wired into conversion yet (extractor + F3 write-back are the next steps). See `memory/drax-np21-cluster-re.md`. 1303 → 1312 tests.

**v3.5.66** (2026-05-27): xhigh-effort `/code-review` sweep — 14 of 15 findings fixed. Highlights: narrowed `except Exception:` → `(ImportError, AttributeError)` in low_load + np21_edit_area_builder 2000 A.D. detection (would have caught a future v3.5.63-class regression); added `TableExtractionError` to the laxity narrowed-except tuple (preserves graceful fallback for malformed binaries); strip leading $A0 segment-marker from v2k SF2 sequence body (editor no longer shows spurious "set instrument 0" before each pattern); pat_idx≥128 cap in placeholder + np21_edit_area_builder (prevents silent orderlist aliasing); pattern_ptr table-size bound in extractor; high_load_layout 2000 A.D. detection wired (parallel to low_load); ol_steps + pairs caps now count every iteration; dead negative-transpose clamp removed; stale docstrings updated. New `requirements-dev.txt` lists pyflakes as a real dev dep. Stage 7 tests now also check OUTPUT BYTES (log-message rewording can't hide regressions). 1301 → 1303 tests (+2 net: +3 byte-signature, -1 duplicate).

**v3.5.65** (2026-05-27): Pyflakes-based undefined-name gate + 5 real bug fixes it surfaced. `pyscript/test_pyflakes_undefined.py` runs pyflakes against `sidm2/` and asserts zero "undefined name" findings. Bugs caught and fixed: (1) `conversion_pipeline.py:244` `List` → `list` (typing.List not imported), (2) `galway_table_extractor.py:122` typo `table_name` → `effect_name`, (3) `sid_player.py:143,150` typo `sid_path` → `filepath`, (4) `laxity_raw_np21_builder.py:774,779` two stray `self.data` references the v3.5.54 refactor missed (silently swallowed by `except Exception`; the ch_seq_ptr safety gate has been bypassed for ALL files since), (5) `table_validator.py` missing `TableInfo` import (`TYPE_CHECKING` block — siddecompiler imports table_validator). 1300 → 1301 tests (+1).

**v3.5.64** (2026-05-27): Defensive regression tests for the v3.5.63 bug class. New `pyscript/test_stage7_emissions.py` (11 tests): exercises full conversion for Stinsens/Beast/Angular and asserts each Stage 7 routine emits + the table-address detection block doesn't fail + the v3.5.63-bugged symbol is importable. Also narrowed the bare `except Exception` in `laxity_raw_np21_builder.py` to `(ValueError, IndexError, KeyError, struct.error)` so NameError/ImportError/AttributeError propagate. 1289 → 1300 tests (+11).

**v3.5.63** (2026-05-27): **Fix: F3 wave-split-copy import bug — restored for 13/17 SID/ root files**. `extract_all_laxity_tables` was used at `laxity_raw_np21_builder.py:267` but not imported at module top (regression from v3.5.54 Phase 19 extraction). A bare `except Exception` silently caught the `NameError`, leaving `np21_note_binary_addr`/`np21_wave_data_binary_addr` as None → wave-copy emission skipped. Stinsens back to all-5 columns wired. Audio still 286/286 PASS (gate NOPs problematic emissions).

**v3.5.62** (2026-05-27): Per-pattern transpose for 2000 A.D. cluster — orderlist command handler decoded (`AND #$1F; STA $XXEF,X`). Each orderlist iteration's transpose applied to its sub-pattern's notes. Echo_Beat's V0 sub-patterns now show +12/+15/+10/+8 semitone shifts visually. 2000 A.D. cluster RE fully drained. 1284 → 1289 tests (+5: orderlist transpose).

**v3.5.61** (2026-05-27): Chromatic note display for 2000 A.D. cluster — `byte_2 + 1` shift maps the player's 0-based semitone encoding to NP21's 1-based ($01=C-0). Verified via freq LUT decode at load+$10F (standard PAL chromatic table). Per-pattern transpose commands still deferred (would shift absolute pitches). 1280 → 1284 tests (+4: 4 chromatic mapping).

**v3.5.60** (2026-05-27): 2000 A.D. cluster complete — Echo_Beat editor F1 view now populated via the low_load path. `placeholder_edit_area.build_placeholder_edit_area` accepts optional `voice_streams` to emit real orderlists+sequences (segmented at $A0 markers); low_load_layout threads `psid_copyright` and runs the 2000 A.D. detector before falling through to placeholder. 1272 → 1280 tests (+8: 6 populated-placeholder + 2 low-load integration).

**v3.5.59** (2026-05-27): 2000 A.D. cluster extractor + wire-in — Galax_it_y editor F1 view populated. Pattern_ptr table dynamically located (v3.5.58 hardcoded `load+$788` was Galax-only — Echo_Beat is at `load+$629`). Echo_Beat editor deferred (low_load path). Notes emit as raw bytes (freq LUT decode deferred). 1263 → 1272 tests (+9). Corpus 286/286 C2+C4 audio — zero regressions.

**v3.5.58** (2026-05-26): 1988 2000 A.D. cluster RE'd + detector shipped (Echo_Beat + Galax_it_y share player; James_Bond is separate despite same copyright). 18 extracted modules, 1263 tests. Extractor/wire-in deferred to v3.5.59 — see `memory/vibrants-2000ad-cluster-re.md`.

**v3.5.57** (2026-05-26): Audio-verified 100% via zig64 byte-identical trace. Crosswords fixed via `skip_aux=True` on high_load_layout (file was overflowing 64K with empty-named TableText aux padding).

**v3.5.56** (2026-05-26): Echo_Beat recovered → 286/286 (100%). LOAD_BASE floor lowered $0500→$0100 (SF2II parses from disk before emulation; pre-emulation header bytes can be clobbered safely). Zero remaining CONV_FAILs.

**v3.5.55** (2026-05-26): High-load alternate layout — Crosswords + Magic_Sound recovered. New `sidm2/high_load_layout.py` places edit area BEFORE high-load binaries. 17 modules, 6649L extracted, 193 unit tests.

**v3.5.54** (2026-05-25): Phase 19 — `_inject_laxity_raw_np21` (940L) extracted to `sidm2/laxity_raw_np21_builder.py`. sf2_writer.py 1633→710L (cumulative -88% since v3.5.27). Decomposition functionally complete (8.7:1 extracted:monolith ratio).

**v3.5.53** (2026-05-25): Phase 18 — driver11 template dispatcher + diagnostic moved to `driver11_section_injectors.py`; orphan `_inject_silent_stub` removed.

**v3.5.52** (2026-05-25): Phase 17 — 7 more `_inject_*_table` methods batch-moved to `driver11_section_injectors.py`. sf2_writer.py 1954→1703L.

**v3.5.51** (2026-05-25): Phase 16 — aux chain assembly + $0FFB pointer injection added to `sf2_aux_bodies.py`. sf2_writer.py under 2000L for first time.

**v3.5.0–v3.5.50**: 15-phase refactor decomposition of `sf2_writer.py` (5832→710L) into 16 modules (`np21_codegen`, `audio_gate`, `universal_211_workaround`, `sf2_diagnostics`, `low_load_layout`, `sf2_aux_bodies`, `sf2_parser`, `sf2_metadata_trailer`, `placeholder_edit_area`, `sf2_template_finder`, `driver11_table_helpers`, `driver11_section_injectors`, `laxity_music_data_injector`, `np21_edit_area_builder`, `minimal_embed_builder`). Plus: V20 cluster recovery (v3.5.26 Wizax/Zetrex-YP V20-gate +20 files; v3.5.27 #211 Digidag fallback; v3.5.28-30 Twone_Five/Dark_Fun/SFd1; v3.5.31 init+3 patch safety +4 files including assumed-deferred Alliance+Racer; v3.5.32-33 zig64 audio gate + wave-copy NOP revert; v3.5.34 clean high-load errors; v3.5.35 Block 2 native redirect Exorcist_preview). Sub-$1000 cluster (v3.5.20-25 30/31 files recovered via alternate low-load layout). SF2II #211 fix (v3.5.18 universal `STA $D400,X` stamp at $1006 — F10 47%→85%). Stage 7 F1-F5 edit propagation (v3.5.0-16 across Stinsen/Beast/Angular/Wizax-A/Zetrex-YP variants). ch_seq_ptr autodetect tuning (v3.5.1-6 editor-view yield 18%→78%).

**v3.4.x** (2026-05-08–09): Editor fidelity push — Block 3 emits `TextFieldSize` instead of `NameLen` (Stinsen+Unboxed solo F10-load 47%→100%; commit 04f5829). Multi-pattern segmentation, Driver-11-format tables in SF2 edit area, bundled aux chain `[3,2,1,4,5,END]`, Stage 8 Path A minimal embed-binary fallback.

**v3.3.0** (2026-04-30): Criterion 3 closed — edits in SF2 editor affect playback. Build-time pre-fill of 3-slot shadow buffer (ch_seq_ptr at $1A1C/$1A1F patched) + runtime translator at $0F0E regenerating shadow per PLAY tick via `sidm2/sf2_to_np21.py`.

**v3.2.x** (2026-03-30–04-29): v3.2.2 fix +1 note shift (NP21 0x00 = "no new note", not C-0). v3.2.1 first end-to-end success for Stinsen+Unboxed; SF2→SID metadata via aux block id=5. v3.2.0 correct Block 3 table addresses (Filter $1989, Wave $1942, Instruments column-major).

**v3.1.x** (2026-03-08–30): v3.1.9 NP21→SF2 note index mapping (1-based vs 0-based). v3.1.8 accurate NP21 sequence extraction (stop at 0xFF loop marker). v3.1.7 editable SF2 (Block 5 populated, edit data area appended). v3.1.6 valid SF2 (0x1337 magic + 5 header blocks). v3.1.5 raw NP21 embedding all Laxity songs. v3.1.4 fix Laxity filter accuracy 0%→100%. v3.1.3 PLAYER_REGISTRY dispatch + Regenerator 2000 project generator. v3.1.2 filter accuracy validation pipeline + zig64 ground truth tracer.

**v3.0.x** (2025-12-27–2026-01-01): v3.0.2 interactive analysis (Dashboard v2.0, HTML Trace). v3.0.1 Laxity driver restoration 0.60%→99.98%. v3.0.0 auto SF2 reference detection.

**v2.x**: v2.9.7 UX improvements. v2.9.6 user docs (3,400+ lines), CI/CD. v2.9.5 batch testing. v2.9.4 PyAutoGUI. v2.9.1 SF2 format fixes. v2.9.0 SID Inventory 658+ files. v2.8.0 Auto driver + Python SIDwinder. v2.6.0 Python siddump. v2.5.3 Enhanced logging. v2.5.0 Cockpit GUI. v1.8.0 Laxity driver 99.98%.

**Complete**: `CHANGELOG.md`

---

**End of Quick Reference**

**Lines**: ~220 (compacted from 342) | **For full docs**: See README.md and docs/
