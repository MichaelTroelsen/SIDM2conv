# CLAUDE.md - AI Assistant Quick Reference

**SIDM2 v3.1.3** | SID→SF2 Converter | C64 Music Tools | Updated 2026-03-14

Converts native Laxity NP21 SID files to SF2 format (99.93-100% accuracy). Features: Auto-driver selection, VSID audio export, Batch Analysis (multi-pair comparison), Accuracy Heatmap (4 viz modes), Trace Comparison (tabbed HTML), SF2 Viewer, Conversion Cockpit, SID Inventory (658+ files), Python siddump/SIDwinder, Batch Testing, User Docs (4,300+ lines), CI/CD (5 workflows), 200+ tests

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
python pyscript/quick_disasm.py file.sid                     # Disassemble
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

**Regenerator 2000 Labeler** (`pyscript/regen2000_label_laxity_np21.py`): Auto-labels any NP21 file loaded in Regenerator 2000 via MCP HTTP. Run: `python pyscript/regen2000_label_laxity_np21.py --port 3000`

**Regenerator 2000 Project Generator** (`pyscript/gen_regen2000_project.py`): Generates `.regen2000proj` directly from a PRG binary with all NP21 labels pre-applied (no running Regenerator needed). Run: `python pyscript/gen_regen2000_project.py [--prg FILE] [--out FILE]`. Load headlessly: `regenerator2000.exe file.regen2000proj --headless --mcp-server --mcp-port 3000`

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

**Other**: Only native Laxity NP21 supported by Laxity driver, single subtune only, 0% filter accuracy

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
