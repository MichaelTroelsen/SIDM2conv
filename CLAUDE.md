# CLAUDE.md - AI Assistant Quick Reference

**SIDM2 v3.5.4** | SID→SF2 Converter | C64 Music Tools | Updated 2026-05-10

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
