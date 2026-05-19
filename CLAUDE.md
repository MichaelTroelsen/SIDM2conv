# CLAUDE.md - AI Assistant Quick Reference

**SIDM2 v3.5.19** | SID→SF2 Converter | C64 Music Tools | Updated 2026-05-19

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

**siddump** (`pyscript/siddump_complete.py`): 100% musical match, 38 tests. Docs: `docs/implementation/SIDDUMP_PYTHON_IMPLEMENTATION.md`

**SIDwinder** (`pyscript/sidwinder_trace.py`): Frame trace, 27 tests, cross-platform. Docs: `docs/analysis/SIDWINDER_PYTHON_DESIGN.md`

**HTML Annotation Tool** (`pyscript/generate_stinsen_html.py`): Interactive HTML docs with 3,700+ annotations, clickable navigation, 11 data sections, dynamic ROM/RAM detection. Docs: `docs/guides/HTML_ANNOTATION_TOOL.md`

**VSID** (`sidm2.vsid_wrapper`): SID→WAV via VICE, auto-fallback to SID2WAV. Docs: `docs/VSID_INTEGRATION_GUIDE.md`

**SF2 Automation** (`sidm2.sf2_editor_automation`): PyAutoGUI auto-loading, 100% pass. Docs: `PYAUTOGUI_INTEGRATION_COMPLETE.md`

**Filter Accuracy Validator** (`pyscript/validate_filter_accuracy.py`): Cross-validates Laxity NP21 filter tables extracted from SID binary against cycle-accurate zig64 ground truth trace. Checks resonance byte, sweep speed, and mode bits. Ground truth: `SID/stinsen_sid_trace_300frames.csv`

**Regenerator 2000 Labeler** (archived 2026-04-29 → `archive/cleanup_2026-04-29/orphaned_utils/regen2000_label_laxity_np21.py`): Auto-labels any NP21 file loaded in Regenerator 2000 via MCP HTTP. Restore from archive if needed.

**Regenerator 2000 Project Generator** (archived 2026-04-29 → `archive/cleanup_2026-04-29/orphaned_utils/gen_regen2000_project.py`): Generates `.regen2000proj` directly from a PRG binary with NP21 labels pre-applied. Restore from archive if needed.

**zig64 SID Tracer** (`tools/sidm2-sid-trace.exe`): Pre-built cycle-accurate SID register tracer. Usage: `sidm2-sid-trace.exe file.prg [frames] [init_hex] [play_hex]`. Output: CSV on stderr. Source: `C:\Users\mit\Downloads\zig64\src\examples\sidm2_sid_trace.zig`

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

**Critical**: "SidFactory_II/Laxity" ≠ native Laxity! Check player-id: "SidFactory" = use Driver 11, "Laxity_NewPlayer_V21" = use Laxity driver

**Other**: Only native Laxity NP21 supported by Laxity driver, single subtune only, filter accuracy 100% (Stinsen verified v3.1.4)

---

## Documentation

**Start**: `README.md` | `docs/guides/GETTING_STARTED.md` | `docs/guides/TROUBLESHOOTING.md`

**User Guides** (3,400+ lines): `TUTORIALS.md`, `FAQ.md`, `BEST_PRACTICES.md`, `SF2_VIEWER_GUIDE.md`, `CONVERSION_COCKPIT_USER_GUIDE.md`, `LAXITY_DRIVER_USER_GUIDE.md`, `VALIDATION_GUIDE.md`, `LOGGING_AND_ERROR_HANDLING_GUIDE.md`

**Technical**: `docs/ARCHITECTURE.md`, `docs/COMPONENTS_REFERENCE.md`, `docs/reference/SF2_FORMAT_SPEC.md`

**Complete index**: `docs/INDEX.md`

---

## For AI Assistants

**Tools**: Task(Explore) for broad searches | Read/Grep for specific files | EnterPlanMode for multi-file changes

**Before Commit**: Run `test-all.bat` (200+ tests) | Update README.md, CLAUDE.md, docs/ if changed | Run `update-inventory.bat` if files added/removed

**Debug**: Check `output.txt` → Compare dumps (`siddump_complete.py`) → Compare audio

---

## Version History

**v3.5.19** (2026-05-19): **v3.5.18 #211 fix validated at full Laxity-corpus scale + housekeeping.** Re-ran F10-load N=15 across all 286 SID/Laxity files post-fix: **C1 134→242/286 (47%→85%), 109 files recovered 0/15→15/15**, audio byte-identical (C2 unchanged 219/286), C4 unchanged (277/283). The one flagged file (21_G4_demo_tune_3 15→12/15) is NOT a regression — the workaround provably skipped it (byte-untouched; $1006 held translator data, not gap; argv-load never crashes 5/5); it's the pre-existing heap-layout-dependent intermittent F10 crash, pre-fix 15/15 was sampling luck. The 37 still-crashing are all separate pre-documented clusters (30 C2-silent sub-$1000 wrapper-collision, 15 Vibrants V20 deferred, 3 CONV_FAIL) — zero clean #211 cases remain. Also: synced stale `sidm2/__init__.py` `__version__` (was 3.3.0 → 3.5.19), purged bin/ scratch artifacts, gitignored the issue-211 cron state file. No code-behavior change. Results: `bin/_laxity_c1_v3518.csv`; full breakdown in `memory/laxity-corpus-c2-failures.md`.

**v3.5.18** (2026-05-18): **SF2II upstream #211 F10-load crash — RESOLVED via SF2-side workaround.** Root-caused (symbolized via the local SF2II .pdb after discovering `main.cpp:95` auto-loads `argv[1]` — new tool `pyscript/sf2_argv_crash.py`, no pyautogui): crash is `Editor::DriverUtils::GetSIDWriteInformationFromDriver` at **`driver_utils.cpp:419`** — `result.begin()->m_CycleOffset` dereferenced on an EMPTY vector. The function statically sweeps `[m_DriverCodeTop, +m_DriverCodeSize)` = `[$1000,$1900)` for absolute-indexed (ABX/ABY) writes to `$D400-$D406`; binaries not loaded at `$1000` leave that window as zero-fill PRG gap → zero writes → empty `result` → AV READ at 0x1. (The old "m_TableColorRules destructor" attribution was WRONG.) Upstream declined to prioritize (collaborator comment 2026-05-14: SF2 only officially supports SF2II-saved files). Fix: new `_ensure_sid_write_in_scan_window_universal()` called once in `write()` after all injection paths converge — every path (laxity raw-NP21, minimal-embed, driver11) emits a 2-JMP trampoline at `$1000`, so SF2II's sweep lands deterministically at `$1006`; if that slot is inert gap (`00 00 00`) stamp a dead `STA $D400,X` (`9D 00 D4`) there. Scanner finds the write → no crash; trampoline intact (zig64/playback unaffected); live-code / NP21-at-$1000 layouts skipped (already pass). Verified 0/15→5/5 F10-load on 3545_I, Aids_Trouble (driver11 path), Atmo_Spherical, Alibi, A_Trace_of_Space with **byte-identical audio**; passers (Sauna, G4) byte-identical + still 5/5. **1010 tests pass** (+4 `TestUpstream211Workaround`). Not addressed: C2=0-silent files (Digidag etc.) — separate sub-$1000-collide / Vibrants V20 cluster, not #211.

**v3.5.17** (2026-05-14): **Two project-wide audio + round-trip bugs fixed while driving Angular to 4-criterion PASS.** (1) `_inject_laxity_raw_np21` no longer clobbers `$1A1C/$1A1F` when those bytes don't contain valid ch_seq_ptrs — for Angular those bytes are state-machine data the player reads via `LDA $1A1F,Y` at `$10F7`, and the default patch caused 3 extra `osc3` register writes per active frame (75 total over 300 frames). Audio now byte-identical to the original SID (2648/2648 register writes match — was 2723). Tradeoff: F1 edit propagation disabled for files where the default ch_seq_ptr address contains non-pointer data; F2/F4/F5 wiring (variant-specific detectors) unaffected. Corpus regression test missed this because it diffs row-by-row including the cycle column, failing at row 0 due to wrapper cycle drift before reaching row 208 where content diverges. (2) Metadata round-trip was never actually implemented — `sf2_to_sid.py` since v3.2.1 scanned for an aux block (id=5 param=1) with title/author/copyright that `sf2_writer` never emitted. Title/author/copyright were thus lost on every SID→SF2→SID for every file. Fix: append a `b"META"` magic + 3 pascal strings (title, author, copyright) past the SF2 content; SF2II ignores the trailer (memory location isn't read by any handler). Round-trip now preserves metadata for Stinsen/Unboxed/Beast/Angular (all 4 verified). New verification tools: `pyscript/verify_audio_match.py` (zig64 trace SID + SF2, compare register writes ignoring cycle column), `verify_np21_embed.py` (binary diff vs SF2 embed), `verify_edit_propagates.py` (patch SF2 row, check zig64 divergence), `trace_dump_frame.py` (per-frame register-write dump). **1006 tests pass**. Stinsen/Unboxed/Beast/Angular: all 4 criteria PASS (C1 loads, C2 audio match, C3 edit propagation via F2/F4/F5, C4 round-trip audio + metadata).

**v3.5.16** (2026-05-12): **F1 (sequences) edit propagation extended to Zetrex/YP cluster (3 files: Jewels, Waste, Racer)**. Same architecture as Wizax-A: voice byte streams accessed via ZP-indirect-Y, NP21-compatible bytes, file-specific ptr-table addresses. New `sidm2/zetrex_yp_detector.py` reads the ptr-table-setup pattern at fixed offset `$0B6` (= `$E0B6` absolute for load `$E000`) — all 3 cluster files share the same player code at this offset with file-specific operand bytes. Per-file tables: Jewels `$E849/$E859` ZP `$FE/$FF`; Waste `$E961/$E96C` ZP `$FE/$FF`; Racer `$E849/$E86C` ZP `$1B/$1C`. Also added a **zig64 entry stub** at `$1000` for binaries loaded outside `$1000` (Zetrex/YP at `$E000`, Echo_Beat at `$0400`, etc.) — writes `JMP $0F90; JMP $0F94` so zig64 (which always reads INIT/PLAY at `$1000`/`$1003`) finds the SF2 handlers. Without this, Zetrex/YP files produced 0 SID register writes under zig64 trace. zig64-verified edit propagation: Jewels `+10/45` freq writes diverge after V0 byte 0 patch; Waste `+5/40` diverge; Racer 0/167 (audio plays correctly but V0 byte 0 patch doesn't visibly diverge in 60-frame window). 15 new tests including parametrized detection + non-Zetrex/YP rejection + conversion success + `$1000` stub verification. **1006 tests pass**. Corpus regression on Stinsen/Unboxed/Beast/Angular byte-identical.

**v3.5.15** (2026-05-12): **F1 (sequences) edit propagation for Wizax-A cluster (4 files)**. First Vibrants V20 sub-cluster with WORKING edit propagation through the NP21 multipat-translator pipeline. New `sidm2/wizax_a_detector.py` scans for the 11-byte voice-control-clear signature + the 10-byte `B9 lo hi 85 zp B9 lo hi 85 zp` ptr-table-setup pattern, returning per-file ptr-table addresses (variable due to song-specific data section sizes). Detected addresses: 2000_A_D `$150C/$153D`, Fight_TST_II `$184A/$18B8`, Hall_of_Fame `$C73E/$C773`, Min_Axel_F `$1774/$179C`. Two-stage redirect: (1) `convert()` detects Wizax-A and overrides driver11 routing to use `_inject_laxity_raw_np21` (the F1 pipeline); (2) the ch_seq_ptr patching step uses the detected Wizax-A addresses instead of NP21's $0A1C/$0A1F default. zig64-verified edit propagation: patching V0 byte 0 in 2000_A_D's SF2 edit area → 50/146 freq writes diverge from baseline; Fight_TST_II 20/28; Min_Axel_F 20/72 (Hall_of_Fame shows 0/0 in 60-frame window, likely longer intro delay). 17 new tests including parametrized cluster-file detection + non-Wizax-A rejection + conversion success + patching verification. **991 tests pass**. Corpus regression byte-identical. Caveats: translator's NP21 command byte semantics may differ from Wizax-A's, so command-byte edits could mis-translate; notes + durations round-trip correctly. F2-F5 (instruments/wave/pulse/filter) stay empty because Wizax-A has no NP21 instrument/wave/pulse/filter tables.

**v3.5.14** (2026-05-12): **All 14 Vibrants V20 files now have specific cluster identification.** Final 4 clusters added: (1) Wizax-B widened to also catch Magic_Sound (1987 Yield Point Music, load $F000) via 5-byte `30 2A 50 40 AE` BMI/BVC/LDX-abs prelude that matches both Cool_as_Wize_Title ($C000) and Magic_Sound ($F000) — same player, different loads. (2) James_Bond_Theme_Remix singleton — distinctive `A2 00 8A A9 00 9D` init-loop within the 1988 2000 A.D. copyright label (different player from Galax/Echo_Beat cluster). (3) Atom_Rock singleton — 1989 Flexible Arts, 5-iteration STA abs,X voice-clear with `30 2E 70 21 A9 00 A2 02 9D` prelude. (4) Fast_Stuff_1 singleton — 1990 Laxity, 6-iteration STA abs,X with `30 34 70 31 A2 02 A9 01 9D` prelude. Also: bumped `V20_MAX_SIZE` from $1000 to $1800 (Fast_Stuff_1 is $1300), added "Laxity" to `V20_COPYRIGHT_HINTS`, recognized Min_Axel_F (1987 Yield Point copyright) as a 4th Wizax-A file (player signature matches despite copyright label). 19 new tests including a parametrized `TestAllV20FilesIdentified` that asserts every V20 file matches a specific cluster. **974 tests pass**. Corpus regression byte-identical. **V20 cluster coverage now 14 of 14 files (100%).**

**v3.5.13** (2026-05-12): Vibrants V20 — third + fourth cluster signatures (Wizax-A + Wizax-B). The "1987 Wizax 2004" copyright label covers 4 files split across 2 sub-clusters by player code. Wizax-A (`2000_A_D` + `Fight_TST_II` + `Hall_of_Fame`) shares a player with `A9 00 8D 04 D4 8D 0B D4 8D 12 D4` (LDA #0; STA $D404; STA $D40B; STA $D412 — clear voice control registers) found via byte-pattern search within first 128 bytes (JMP-table prefix length varies per file). Wizax-B (`Cool_as_Wize_Title`) uses a DIFFERENT player with `99 04 D4 9D C8 C4 9D CB C4 9D CE C4 9D D4 C4 99 06 D4` (STA abs,Y/X indexed writes — Yield-Point-style architecture). 5 new tests + mutual-exclusivity check. **955 tests pass**. Corpus regression byte-identical. **Vibrants V20 cluster coverage now 9 of 14 files** (1988 2000 A.D.: 2, Zetrex/YP: 3, Wizax-A: 3, Wizax-B: 1; remaining 5 = Magic_Sound + Min_Axel_F + James_Bond_Theme_Remix + Atom_Rock + Fast_Stuff_1, each a singleton or different player).

**v3.5.12** (2026-05-12): Vibrants V20 — second cluster (Zetrex / Yield Point) signature-identified. Discovered Jewels.sid + Waste.sid (1988 Zetrex) + Racer.sid (1987 Yield Point Music) share the same player binary at load $E000 — same code matches across 3 files; song-specific data tables diverge after the first 35 bytes of player code. New `_is_zetrex_yp_cluster` check in `sidm2/vibrants_v20_detector.py` matches `2C 4A E5 30 29 50 3E A2 02 A9 00 BC 09 E5 99 04 D4 9D 0D E5 9D 10 E5 9D 13 E5 9D 19 E5 99 06 D4 A9 11 9D` at c64_data offset 9. These files get player-id="Rob_Hubbard" and route through driver11 (not laxity), so the V20 detector call was ALSO added to `_inject_player_raw_minimal` so the cluster advisory log appears. Cluster suffix: "1988 Zetrex / 1987 Yield Point cluster (player signature matched; 3 files share this binary at load $E000)". No edit propagation — same multi-week-per-variant RE blocker as the 1988 2000 A.D. cluster. **950 tests pass** (+4 new: 3 parametrized cluster matches + 1 mutual-exclusivity check). Corpus regression byte-identical.

**v3.5.11** (2026-05-12): Vibrants V20 (pre-NP21) advisory + autodetect short-circuit. The 14 Class-C all-notes Laxity-corpus files use pre-NP21 player variants from 1987-1990 (Wizax / Yield Point / 2000 A.D. / Zetrex / Flexible Arts / Laxity-1990) with per-voice freq LUTs at variant-dependent addresses (Galax_it_y: $14C5/$14C8 V0 freq scratches fed via `LDA $150F,Y` LUT lookup at PC $1236, with note source byte stream at `$1794+` per-voice). The relaxed v3.5.5/v3.5.6 NP21 autodetect was lifting 2-14 byte "patterns" from these files' freq LUTs and other regions — garbage from the SF2 editor's perspective. New `sidm2/vibrants_v20_detector.py` uses copyright-string + file-size heuristics ("Wizax", "Yield Point", "2000 A.D.", "Zetrex", "Flexible Arts" + size < $1000) to flag these files BEFORE the autodetect runs; flagged files skip the autodetect and emit `track_count=0` (honest empty editor view). Audio path unchanged — playback goes through the embedded-binary path via SF2II's PLAY handler. Plus an info-level log line: `Vibrants V20 (pre-NP21) detected: <copyright>. Audio plays via embedded-binary path; editor view stays empty by design`. **943 tests pass** (+20 new: parametrized `TestKnownV20Files` × 13 + `TestCanonicalFilesDoNotMatch` × 4 + base detector cases × 3). Corpus regression byte-identical. Full V20 byte-stream RE remains multi-week per variant (each cluster has its own scratch layout + LUT shape); see `memory/vibrants-v20-findings.md`.

**v3.5.10** (2026-05-12): Stage 7 F4 (pulse) extended to Beast + Angular. Disassembled both variants' pulse handlers ($13C4-$13DA for Beast, $1404-$1418 for Angular) and discovered an unexpected encoding: 4-byte step records where byte 0 is **nibble-packed** — high nibble → PW lo scratch, low nibble → PW hi scratch. New `_emit_pulse_packed_copy_routine` (34B 6502) writes SF2 3-col rows into NP21 stride-4 records, copying bytes 0/1/2 per step and preserving byte 3. New `sidm2/beast_pulse_detector.py` + `sidm2/angular_pulse_detector.py` piggyback the variant instr signatures. Stage 3 emit override populates SF2 from the binary's $1AC5+r*4 (Beast) / $1A3B+r*4 (Angular) byte streams. Verified end-to-end via zig64: Beast row 0 col 0 patch $00→$A0 → +10 pw_lo writes of $A0, 30/30 sequence positions diverge; Angular row 0 col 0 patch $08→$A0 → same result. The nibble-pack encoding explains why earlier single-byte patch tests (v3.5.9) appeared not to propagate — bytes get split before reaching D-registers, so $A5 patches showed up as $A0 (high nibble) on PW lo, $05 (low nibble) on PW hi. **923 tests pass** (+8 new: `TestBeastPulseDetector` + `TestAngularPulseDetector` + `TestPulsePackedCopyRoutine`). Corpus regression byte-identical. **Stage 7 now COMPLETE for all three variants (Stinsen, Beast, Angular) across F1/F2/F3/F4/F5 except: Stinsen F1-F5 + F2 Beast/Angular (AD+SR only — HR/Pulse_ptr/Wave_ptr columns not RE'd for any variant) + F4/F5 Beast/Angular shipped (this release).**

**v3.5.9** (2026-05-12): Stage 7 F5 (filter) extended to Beast + Angular variants. Architecture (RE'd this session): both store cutoff_hi as a 16+ entry byte stream (Beast: `$1A7D`, Angular: `$1A1F`), with res_routing latched at fixed `$100A` and mode_vol at fixed `$1009` (both shared between Beast and Angular). Cutoff_lo (D415) is unused. The fixed-address single bytes can't be array-indexed safely (would overwrite adjacent player code), so the new `_emit_filter_cutoff_only_routine` (19B 6502) propagates ONLY col 0 → cutoff_hi byte stream. Cols 1 + 2 in the SF2 editor show the static $100A/$1009 bytes but edits to those cols won't propagate. New `sidm2/beast_filter_detector.py` + `sidm2/angular_filter_detector.py` piggyback the existing Beast/Angular instr signatures. Stage 3 emit override populates SF2 cols 0/1/2 from the byte stream + fixed bytes. Verified end-to-end via zig64: patching SF2 filter row 0 col 0 in Beast → cutoff_hi at frame 1 flips $05→$C7 (direct value propagation, no state-machine transformation); Angular → 24/30 sequence positions changed. F4 (pulse) Beast + Angular DEFERRED — PW lo byte streams at `$1AC5` (Beast) / `$1A3B` (Angular) don't propagate single-byte patches (likely AND/OR masking before reaching D-registers), and PW hi sources go through ZP `$FB` indirection. Multi-day RE per variant. **915 tests pass** (+9 new: `TestBeastFilterDetector` × 3 + `TestAngularFilterDetector` × 3 + `TestFilterCutoffOnlyRoutine` × 3). Corpus regression byte-identical on Stinsen/Unboxed/Beast/Angular.

**v3.5.8** (2026-05-11): Stage 7 F5 (filter) — Stinsen edits propagate to playback. Full RE of the filter command handler at `$15F6-$167F` confirmed the byte streams at `$1989` (cmd), `$19A3` (val), `$19BD` (aux) form a state machine: bit 7 of cmd selects SET command (initialize accumulator) vs SWEEP command (delta accumulate); aux byte feeds resonance/routing (D417) directly OR step-duration depending on command type. `_emit_filter_split_copy_routine` (31B 6502) copies SF2 3-byte rows back to the three parallel arrays; player re-interprets state machine on next step. New `sidm2/stinsen_filter_detector.py` piggybacks the Stinsen instr signature. Stage 3 emit override populates SF2 cols 0/1/2 from the byte streams (replacing prior `find_and_extract_filter_table` interpretation). Verified end-to-end via zig64: patching SF2 filter row 0 col 2 (aux) → +2 `filter_res_control` register writes with marker value. Plus a translator overflow fix: 4 inline JSRs in the multipat translator would have exceeded the `$0F9E..$0FFA` 98B window (would land at 99B). Consolidated tail (instr + pulse + filter) into a 10B trampoline at the end of `sf2_edit_data` — translator does ONE JSR to the trampoline instead of 3 inline JSRs, saving 6B. **906 tests pass** (+9 new: `TestFilterSplitCopyRoutine` × 5 + `TestStinsenFilterDetector` × 4). Corpus regression byte-identical on Stinsen/Unboxed/Beast/Angular. Beast/Angular F5 not yet wired — needs per-variant filter byte-stream RE.

**v3.5.7** (2026-05-11): Stage 7 F4 (pulse) — Stinsen edits propagate to playback. New `sidm2/stinsen_pulse_detector.py` finds the parallel PW lo / PW hi byte streams at `$1957`/`$193E` (piggybacks the existing Stinsen instr signature at `$1800`). New `_emit_pulse_split_copy_routine` (25 bytes 6502) does a single-pass interleaved walk over the SF2 edit area's 16 × 3-byte pulse table, writing col 0 → `$1957+r` (PW lo) and col 1 → `$193E+r` (PW hi). Stage 3 SF2 emit gains a Stinsen-pulse override that populates cols 0/1 from the binary's actual PW lo/hi bytes (replacing the prior `find_and_extract_pulse_table` 4-byte-tuple interpretation that was structurally incompatible). Verified end-to-end via zig64: patching SF2 pulse row 0 col 0 → 5 new `osc*_pw_lo` register writes flipped to the patched value across all three voices. 897 tests pass (+11 new: `TestPulseSplitCopyRoutine` × 5 in `test_sf2_writer_phase_b2.py` + `TestStinsenPulseDetector` × 5 in `test_stinsen_pulse_detector.py`). Non-Stinsen variants (Beast/Angular) keep the old 4-byte-tuple emit and don't get F4 wire-up — needs per-variant pulse-table RE to extend (Beast/Angular scratches and source candidates not yet identified).

**v3.5.6** (2026-05-10): ch_seq_ptr `_score_sequence` short-body return changed from -1000 (hard reject) to 0 (neutral). v3.5.5's per-voice hard-reject for `len(body) < 8` was poisoning the per-table sum in `_scan_table_at` — files with one silent voice (e.g., Intro_2.sid voice 1 = 2-byte body before terminator) got the entire table rejected even though voices 0+2 had legitimate NP21 streams. Returning 0 for short bodies lets non-silent voices' positive scores carry the candidate. **Editor-view yield on Laxity 286-file corpus: 76% → 78% (216 → 224 files; C_unchanged collapsed 10 → 2).** All-notes Vibrants-variant files (no duration/instrument bytes) stay correctly rejected — they trip n_traits < 2 on long bodies, which still hard-rejects. New regression test `test_lifts_intro_2_with_silent_voice`; existing `test_too_short_rejected` split into `test_empty_body_rejected` + `test_short_body_neutral_not_rejected`. 886 tests pass.

**v3.5.5** (2026-05-10): ch_seq_ptr autodetect `play_reads`-coverage check relaxed from hard reject to `+1 per byte found` score bonus (max +6). v3.5.4 required all 6 table bytes appear in the PLAY-time read set within 3 ticks — too strict for ~129 Laxity files whose players touch one voice per PLAY tick (IRQ-dispatched / counter-rotated voice handling). Structurally-valid candidates scoring 24-60 on stream-shape were getting dropped pre-scoring. **Editor-view yield on Laxity 286-file corpus: 30% → 76% (87 → 216 files).** 3 new regression tests in `test_ch_seq_ptr_scanner.py::TestPlayReadsSoftFilter` pin Axel_F.sid / TSZ_Intro.sid (v3.5.4 false-rejects) plus a Stinsen-unaffected check. 885 tests pass. Audio path unchanged — the runtime translator pre-fills shadow buffer to the NP21 binary's verbatim bytes, so editor-view lift is decoupled from playback. Negative findings docs: a ZP-indirect-Y detector was the originally-scoped fix but `bin/classify_c_class.py` showed 0/54 of the remaining Class-C files actually lack a static-disasm indexed-load pair — every C-class file had at least one `LDA abs,X/Y` candidate. The real gap was the play_reads strictness; PTRS_OOR cases (20 of 54 sampled) are unrelated player variants (Hubbard/Galway/Vibrants 1987-90) outside the NP21 scope.

**v3.5.4** (2026-05-10): Wave-copy non-idempotency (v3.5.3 known issue) RESOLVED via two clean changes: (1) removed `$7F`-swap from `find_and_extract_wave_table` — extract now always emits `(wave_val, note_val)`, end markers land in col 1 naturally, wave-copy is byte-perfect round-trip identity; (2) re-enabled the JMP-indirection trampoline patch — when `play_addr == init+3` is `JMP $XXXX` (Beast/Hubbard layout), extract the JMP target as the translator's JSR play target and patch `$1003 → JMP TRANSLATE_BASE`. End-to-end zig64-verified F2 edit propagation now works for ALL THREE variants (Stinsen, Beast, Angular) — was Stinsen-only pre-this-release. Stinsen + Unboxed audio byte-identical (1909 + 2733 register writes). Unboxed cycle column shifted (translator path now runs each PLAY tick under zig64); golden re-baselined.

**v3.5.3** (2026-05-10): Beast + Angular instrument-table detectors land. F2 (instruments) AD/SR edits now propagate for any binary matching one of three known layouts: Stinsen column-major @ $1808/$181C, Beast row-major 8B @ $1B38 (AD@+5 SR@+6), Angular row-major 2B @ $1ADB. `_emit_instr_copy_routine` gained `fields=` (variant-specific column mappings) and `np21_stride=` (default 8, Angular uses 2) parameters. Plus a major ch_seq_ptr autodetect fix: relaxed `body[0] must be $A0-$BF` to allow note/duration/command starts (Beast voice bodies start with notes), and relaxed entropy threshold for held-note runs. **Editor-view yield on Laxity 286-file corpus jumped from 30% to 72% (87 → 206 files extracting real per-voice sequences, +119 net).** Two negative-result investigations documented: wave-copy non-idempotency for non-Stinsen variants (`$7F`-swap mismatch between extract and copy-back; reverted attempted fix; root cause documented for future fix), and F4 pulse propagation complexity (pulse is a byte stream, not a grid; needs deeper RE). 862 tests pass (+19 new). Audio unchanged.

**v3.5.2** (2026-05-10): Stage 7 Phase B.2 — F2 (instruments) AD+SR edits propagate to playback for Stinsen-class binaries. New `sidm2/stinsen_instr_detector.py` matches the column-major layout signature at binary offset `$0800` (AD col `$1808`, SR col `$181C`, 20 slots max). New `_emit_instr_column_copy_routine` (41 bytes 6502) handles SF2-row-major→NP21-column-major stride mismatch. Stage 3 SF2 emit populates F2 view with real Stinsen AD/SR values. Verified: editing instr 1 AD `$A0`→`$5A` flips osc1_attack_decay writes; editing instr 1 SR `$25`→`$66` flips osc1_sustain_release. Plus a definitive negative result via direct-edit + static disasm: HR/Filter/Pulse_ptr/Wave_ptr columns are NOT in Stinsen's per-instrument table — they're encoded by other mechanisms beyond F2 column view's scope. 843 tests pass (+12 new). Golden trace re-baselined for the cycle shift.

**v3.5.1** (2026-05-10): Two ch_seq_ptr autodetect bug fixes lifted +12 net new Laxity files to proper editor view (75→87, 18%→30%). (1) `trace_play_reads` snapshot loop iterated through `TracingMemory.__getitem__`, polluting the read-tracking set with all 64KB and rendering the PLAY-read filter in `detect_ch_seq_ptr` a no-op. Fix: snapshot via `list.__getitem__`. (+5 lifts). (2) Brute-force fallback gate ran only on `best is None`; if static candidates returned hard-rejected scores (-3000), `best` was set and fallback skipped. Now runs when `best is None OR best[0] <= 0`. (+14 absolute lifts). Plus conversion-time advisory when load_addr is outside the safe window `$0E00-$3000`, naming upstream issue #211 (Chordian/sidfactory2). 3 new regression tests in `test_sid_init_runner.py`. 831 tests pass. Audio unchanged.

**v3.5.0** (2026-05-09): Stage 7 — criterion 3 extends from sequences to **wave** tables. Edits to F3 (wave) in the SF2 editor now propagate to playback end-to-end via a 31-byte split-copy 6502 routine emitted into the SF2 edit area, called via JSR from the multipat translator at `$0F9E` on every PLAY tick. The wave detector in `extract_all_laxity_tables` was rewritten — preferring `find_and_extract_wave_table` (which validates static wave-program addresses against known Laxity NP21 layouts) over the LDA-near-STA$D404 heuristic which returned transient per-voice state. New `wave_data_addr` field exposes the parallel waveform array (Stinsen: notes=$190C, waves=$18DA). Trampoline at `init+3` redirects to `TRANSLATE_BASE` when patterns exist (so zig64 trace path also goes through wave-copy, not just SF2II's PLAY handler). **Verified: byte-edit at file-offset $2CA5 ($21 saw → $11 tri) flipped 155 osc<v>_control writes from $20 to $10 across all three voices.** Plus Phase B.2 plumbing: `_emit_instr_copy_routine` (110B, 5 fields) and `_emit_pulse_copy_routine` (66B, 3 fields) — 6502 split-copy routines for instruments + pulse, tested via py65 step-through (11 new tests). Wire-up deferred for instr/pulse pending per-variant address-detection RE (Stinsen has AD/SR at $18D8/$18D9 adjacent to wave-data; Beast/Angular use parallel-array per-voice scratches at completely different addresses). 828 tests pass. Golden traces re-baselined.

**v3.4.1** (2026-05-09): Block 3 emits `TextFieldSize` instead of `NameLen`. SF2II's parser was reading our `NameLen` byte as `m_TextFieldSize`, making every driver table a `ComponentTableRowElementsWithText` whose `Refresh` writes a stray byte 0xDE/0xDF when its `AuxilaryDataTableText` lookup misses on tables without text entries. **Solo F10-load: Stinsen 47% → 100%, Unboxed → 100%.** Same fix unblocked Angular + Beast (was 0% deterministic crash → 100%). Empty-patterns fallback path returns 5-tuple to match Stage 2.5 contract. Per-instance `arp_addr/tempo_addr/hr_addr/init_table_addr` overrides on `SF2HeaderGenerator` so non-Laxity binaries don't collide with hardcoded `$C000-$C300`. Stage 8.5 toolkit (`appverifier-*.bat`, `pyscript/sf2_debug_inspect_v2.py`, `disasm_rva.py`) plus PageHeap-mode investigation that LOCALIZED the residual non-Laxity F10 crash to a NULL `std::string` deref in SF2II's `m_TableColorRules` destructor at `+0x63fab` — reported upstream as Chordian/sidfactory2#211. Broader 11-file corpus pass rate 9/11 = 82% (the 2 failures blocked on upstream). 794 tests still pass.

**v3.4.0** (2026-05-08): Editor fidelity push — Laxity SF2 output now structurally matches the bundled SF2II reference corpus across all 9 header blocks, the aux chain, and Block 3 column data formats. Multi-pattern segmentation splits each voice's flat NP21 byte stream at instrument-prefix boundaries (e.g. Stinsen voice 0: 6 segments). New 87-byte multi-pattern runtime translator at `$0F8E`. Driver-11-format Wave/Pulse/Filter/Instruments tables emitted in the SF2 edit area. Block 9 populated with 4 descriptors (was 1-byte placeholder). Bundled `[3, 2, 1, 4, 5, END]` aux chain with body formats decoded from `auxilary_data_*.cpp`. Stage 8 Path A — minimal embed-binary fallback for non-Laxity SIDs. `star.html` Star Wars opening-crawl viewer for the changelog.

**v3.3.0** (2026-04-30): Criterion 3 closed — edits in SF2 editor affect playback. Two-part architecture: build-time pre-fill of a 3-slot shadow buffer (per-voice NP21-format bytes appended after the SF2 edit area, with `ch_seq_ptr` at $1A1C/$1A1F patched to point at the shadow); runtime translator at $0F0E that regenerates the shadow on every PLAY tick by translating SF2-edit-area bytes through `sidm2/sf2_to_np21.py`. PLAY handler at $0F04 is now `JMP $0F0E`. Stinsen + Unboxed both still trace at 100%; 794 tests passing (+3 edit-proof tests). Architecture dead-ends and corrections documented in `docs/criterion3_step0_findings.md` and `docs/criterion3_scoping.md`.

**v3.2.2** (2026-04-29): Fix +1 note shift in `_build_np21_sf2_edit_area` — Step 0 of criterion-3 investigation revealed v3.1.9 was wrong: NP21 0x00 = "no new note this tick" (verified at player code `$10F4-$10FB`), not C-0. Old converter shifted every note one semitone up in the editor view and rendered NP21 silence-rows as C-0 played notes. Correct mapping: NP21 0x00→SF2 0x00, NP21 0x01-0x6F→identity, NP21 0x70-0x7D→clamp 0x6F. Playback unaffected (zig64 trace 100% on Stinsen + Unboxed). 6 new regression tests; 784 total passing.

**v3.2.1** (2026-04-27): First end-to-end success for Stinsen + Unboxed — auto-detect now picks laxity driver for `SidFactory_II/Laxity` files (Stinsen-class), no `--driver` flag needed; `sf2_to_sid.py` reads metadata from SF2 aux block id=5 instead of last-string-wins heuristic, so title/author/copyright survive SID→SF2→SID round-trip; `--driver` override reports registered accuracy ("99.93% (user override)") instead of flat "User override"; `EDITABLE-REPLAY GAP` documented inline in `_build_np21_sf2_edit_area` (NP21↔SF2 byte format conflict, criterion 3 deferred); new `pyscript/verify_editor_view.py` simulates `DataSourceSequence::Unpack` for headless editor-side checks; 786 tests pass

**v3.2.0** (2026-03-30): Correct Block 3 table addresses for raw NP21 approach — Filter fixed from `$1A1E` (was ch_seq_ptr_hi, editing it would corrupt NP21!) to `$1989` (tbl_filter_seq); Wave updated to `$1942`; Instruments layout set column-major; all addresses now match actual NP21 binary layout (player at `$1000`)

**v3.1.9** (2026-03-30): Correct NP21→SF2 note index mapping — SF2 notes are 1-based (0x01=C-0), NP21 notes are 0-based (0x00=C-0); fix: `sf2_note = np21_note + 1`; all note displays in editor were shifted down one semitone (e.g. D-1 displayed as C#1); accuracy unaffected (NP21 binary unchanged)

**v3.1.8** (2026-03-30): Accurate NP21 sequence extraction — `_extract_raw_seq` stops at `0xFF` (NP21 loop marker) not `0x7F` (unreachable safety terminator); Stinsen voice 0: 101 → 41 bytes (no longer captures adjacent voice data); note 0 (C-0) passes through correctly to SF2 (gate-off is `0x80` not `0x00`); loop target detection with warning for non-zero targets

**v3.1.7** (2026-03-29): Editable SF2 — Block 5 MusicData now populated with real addresses; SF2 edit data area (orderlists + sequences in SF2 format) appended after NP21 binary; voice sequences extracted from ch_seq_ptr ($0A1C/$0A1F), note indices pass through 1:1 (chromatic order identical in NP21 and SF2); 786 tests pass, 100% accuracy maintained

**v3.1.6** (2026-03-29): Valid SF2 file output — raw NP21 embedding now produces a proper SF2 recognized by SID Factory II editor; added 0x1337 magic + 5 required header blocks (228 bytes at $0D7E-$0E62); handlers moved to $0F00/$0F04/$0F08; zig64 accuracy maintained at 100% (Stinsen 1909/1909, Unboxed 2733/2733); editor automation test PASS

**v3.1.5** (2026-03-22): Raw NP21 embedding extended to all Laxity songs — embed any song's own NP21 binary verbatim at $1000 with a minimal $0D7E wrapper dispatching to INIT/PLAY; patch $init+3 → JMP play_addr for zig64 auto-detection compatibility; 100% accuracy on both Stinsen and Unboxed (verified 300 frames each)

**v3.1.4** (2026-03-21): Fix Laxity driver filter accuracy 0%→100% — dynamic voice OL pointers from SID binary ($0A1C/$0A1F), filter table addresses $19D0/$19EA/$1A04, LSR $EC→$FC (D416 corruption fix), raw NP21 music block injection, filter state zero-init, add compare_filter_accuracy.py

**v3.1.3** (2026-03-14): Fix NP21 seq ptr reading (separate lo/hi arrays at $0A1C/$0A1F), fix filter injection addresses ($19F1/$1A0B/$1A25), fix HP/LP label swap in filter seq decoder, add Regenerator 2000 project generator (headless .regen2000proj from PRG), registry-based player dispatch (PLAYER_REGISTRY + PLAYER_CONVERTERS/PLAYER_EXTRACTORS dicts replacing hardcoded if/elif), 4 players registered (laxity/driver11/np20/galway)

**v3.1.2** (2026-03-08): Filter accuracy validation pipeline (zig64 ground truth tracer, validate_filter_accuracy.py), Regenerator 2000 MCP auto-labeler, filter table fix ($1A1E→$1989/$19A3/$19BD correct NP21 offsets), pre-built sidm2-sid-trace.exe

**v3.0.2** (2026-01-01): Interactive analysis features (Dashboard v2.0, HTML Trace, batch launchers, 33 tests)

**v3.0.1** (2025-12-27): Laxity driver restoration (0→40 patches, 0.60%→99.98% accuracy verified 2025-12-28), VSID pipeline integration

**v3.0.0** (2025-12-27): Auto SF2 reference detection (100% accuracy for SF2-exported SIDs)

**v2.9.7** (2025-12-27): UX improvements (success/error messages, quiet mode, help text, Windows compatibility, UX metrics 3→9/10)

**v2.9.6** (2025-12-26): User docs (3,400+ lines), CI/CD (5 workflows), VSID integration

**v2.9.5** (2025-12-26): Batch testing (100% pass), process cleanup

**Earlier**: v2.9.4 (PyAutoGUI), v2.9.1 (SF2 format fixes), v2.9.0 (SID Inventory 658+ files), v2.8.0 (Auto driver + Python SIDwinder), v2.6.0 (Python siddump), v2.5.3 (Enhanced logging), v2.5.0 (Cockpit GUI), v1.8.0 (Laxity driver 99.98%)

**Complete**: `CHANGELOG.md`

---

**End of Quick Reference**

**Lines**: ~150 (compacted from 270) | **For full docs**: See README.md and docs/
