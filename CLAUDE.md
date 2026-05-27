# CLAUDE.md - AI Assistant Quick Reference

**SIDM2 v3.5.65** | SID→SF2 Converter | C64 Music Tools | Updated 2026-05-27

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

**On Version Bump**: Update `CLAUDE.md` (this file), `CHANGELOG.md`, AND `STORY.md` (the project narrative — append to per-version index; update Eras / deep-tech sections only if a new architectural finding warrants it). Bump `sidm2/__init__.py __version__` + `__build_date__`.

**Debug**: Check `output.txt` → Compare dumps (`siddump_complete.py`) → Compare audio

---

## Version History

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
