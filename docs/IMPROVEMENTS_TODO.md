# SIDM2 Improvements & TODO List

**Created**: 2025-12-22
**Reconciled**: 2026-08-20 against v3.27.0 — every item below was checked against the
current tree (file/function existence, `git log`, `CHANGELOG.md`), not against its own
checkbox. Items confirmed shipped were removed; each is listed under "Closed since
2025-12-22" with the commit/evidence that closed it. What remains below is what a
tree-check on 2026-08-20 could not find implemented.
**Status**: Active tracking of remaining improvement suggestions
**Related**: See `docs/ROADMAP.md` for strategic planning

---

## Open Items

### CC-7: Configuration Import/Export
**Priority**: P3 (Low - advanced feature)
**Status**: ❌ Not Started (confirmed 2026-08-20: no "Export Config"/"Import Config"
controls or JSON config export/import in `pyscript/cockpit_widgets.py` or
`pyscript/conversion_cockpit_gui.py`; `load_settings`/`save_settings` there only
persist window geometry and recent-file paths via `QSettings`, not pipeline config)
**Effort**: 2-3 hours

**Tasks**:
- [ ] Export config to JSON file
- [ ] Import config from JSON file
- [ ] Add "Export Config" / "Import Config" buttons
- [ ] Validate imported config
- [ ] Handle version compatibility

**Files to modify**:
- `pyscript/conversion_cockpit_gui.py` (add import/export)
- `pyscript/pipeline_config.py` (JSON serialization)

---

### CC-6b: Remaining UI Polish Items
**Priority**: P3 (Low - aesthetic)
**Status**: 🔄 Partially open (CC-6 itself shipped — see Closed section — but these
three sub-items were never implemented; confirmed 2026-08-20, no match for keyboard
shortcuts, tooltips, or a dark-mode toggle in `pyscript/conversion_cockpit_gui.py` or
`pyscript/cockpit_styles.py`)

**Tasks**:
- [ ] Add keyboard shortcuts (Ctrl+O, Ctrl+S, F5, Esc)
- [ ] Add tooltips to all controls
- [ ] Add dark mode option

---

### DOC-1: Conversion Cockpit Screenshots
**Priority**: P2 (Medium - better docs)
**Status**: ❌ Not Started (confirmed 2026-08-20: no `docs/screenshots/` directory,
no `.png` files anywhere under `docs/`)
**Effort**: 1-2 hours

**Tasks**:
- [ ] Take screenshots of all 5 tabs
- [ ] Create ASCII art representations (for terminal viewing)
- [ ] Add to user guide
- [ ] Add to README.md
- [ ] Show before/after conversion examples

**Files to modify**:
- `docs/guides/CONVERSION_COCKPIT_USER_GUIDE.md`
- `README.md`
- `docs/screenshots/` (new directory)

---

### DOC-2: Demo Video Tutorial
**Priority**: P3 (Low - nice to have)
**Status**: ❌ Not Started (confirmed 2026-08-20: no video link or reference in
README.md or the user guide)
**Effort**: 2-4 hours
**Roadmap**: Track 4.3 (video tutorials)

**Tasks**:
- [ ] Record Conversion Cockpit usage demo
- [ ] Show file selection and configuration
- [ ] Demonstrate batch conversion
- [ ] Review results and accuracy
- [ ] Edit and publish to YouTube
- [ ] Link from README.md

**Reference**: Already tracked in `docs/ROADMAP.md` Track 4.3

---

### DOC-3: API Documentation Generation
**Priority**: P3 (Low - developer docs)
**Status**: ❌ Not Started (confirmed 2026-08-20: no Sphinx `conf.py` anywhere in the
tree, no generated API reference)
**Effort**: 6-8 hours
**Roadmap**: Track 5.2

**Tasks**:
- [ ] Add docstrings to all public functions
- [ ] Set up Sphinx documentation
- [ ] Generate API reference
- [ ] Host on GitHub Pages
- [ ] Link from README.md

**Reference**: Already tracked in `docs/ROADMAP.md` Track 5.2

---

### INFRA-1: Automated Performance Testing
**Priority**: P3 (Low - optimization baseline)
**Status**: ❌ Not Started (confirmed 2026-08-20: no `scripts/benchmark_performance.py`,
no `performance-tests.yml`; the 5 CI workflows in `.github/workflows/` are
`ci.yml`, `test.yml`, `validation.yml`, `batch-testing.yml`,
`conversion-cockpit-tests.yml` — none benchmark or track performance over versions)
**Effort**: 4-6 hours

**Tasks**:
- [ ] Create performance benchmark suite
- [ ] Measure conversion time per file
- [ ] Measure memory usage
- [ ] Track performance over versions
- [ ] Add to CI/CD pipeline
- [ ] Generate performance reports

---

### INFRA-2: Package as Standalone Binary
**Priority**: P3 (Low - distribution improvement)
**Status**: ❌ Not Started (confirmed 2026-08-20: no PyInstaller reference in
`requirements.txt`, README.md, or CLAUDE.md; no standalone binaries or GitHub Releases
artifacts referenced anywhere in the repo)
**Effort**: 8-12 hours
**Roadmap**: Quick Win Q3

**Tasks**:
- [ ] Set up PyInstaller
- [ ] Create Windows executable
- [ ] Create macOS app bundle
- [ ] Create Linux AppImage
- [ ] Test on fresh systems
- [ ] Add to GitHub Releases

**Reference**: Already tracked in `docs/ROADMAP.md` Quick Win Q3

---

## Closed since 2025-12-22 (verified, not just checked-off)

These shipped and were removed from the open list above; kept here only as a pointer
to what closed them, in case a future audit needs the trail.

- **IA-1** Test Conversion Cockpit with Real Files — `pyscript/test_cockpit_real_files.py`
  exists on disk; cockpit backend is exercised by the current test suite.
- **IA-2** Update README with Conversion Cockpit — README.md has a "Conversion Cockpit
  (v2.6)" section and a GUI usage block; confirmed present 2026-08-20.
- **IA-3** Tag v2.6.0 Release — `git tag -l v2.6.0` returns the tag; confirmed present.
- **CC-1** Concurrent File Processing — `pyscript/conversion_executor.py` exists with
  the described thread-pool machinery.
- **CC-2** Embedded Dashboard View — dashboard integration present in
  `pyscript/conversion_cockpit_gui.py`.
- **CC-3** Batch History — `pyscript/batch_history_manager.py` (BatchHistoryManager
  class, load/save/delete/clear entry points) and `pyscript/cockpit_history_widgets.py`
  both exist and are populated.
- **CC-4** Export Batch Reports — `pyscript/report_generator.py` (BatchReportGenerator)
  and `sidm2/report_generator.py` (ReportGenerator) both exist, with
  `pyscript/test_report_generator.py` covering them. (The two sub-items this task
  itself left unchecked — PDF export via ReportLab, Chart.js accuracy charts — were
  explicitly scoped as future enhancements, not part of the CC-4 deliverable; neither
  exists on disk, so if ever revived they belong as a new backlog item, not a reopened
  CC-4.)
- **CC-5** Progress Estimation Based on History — `pyscript/progress_estimator.py`
  (ProgressEstimator, add_timing/load_timings/save_timings) and
  `pyscript/executor_with_progress.py` both exist.
- **CC-6** UI Polish & Icons (core deliverable) — `pyscript/cockpit_styles.py`
  (470+ lines, ColorScheme/IconGenerator/StyleSheet) exists and is wired into
  `pyscript/conversion_cockpit_gui.py`. Three sub-items (shortcuts/tooltips/dark mode)
  were never done — carried forward above as **CC-6b**, not closed.
- **BF-1** SF2 Packer Pointer Relocation Bug — commit `b1a2df0` exists; `is_code=False`
  is present at the described data-section sites in `sidm2/sf2_packer.py`.
- **BF-2** Conversion Cockpit QScrollArea Import — commit `677d812` exists.
- **AI-1** Implement Filter Format Conversion — commit `22c94c1` exists; the Y*4→direct
  index conversion (`direct_idx = next_idx // 4 if next_idx % 4 == 0 ...`) is present
  in `sidm2/table_extraction.py`.
- **AI-2** Test Voice 3 Support — investigation scripts exist
  (`pyscript/find_voice3_files.py`, `pyscript/check_voice_usage.py`); superseded in
  practice by the multi-player corpus work documented in `docs/reference/ACCURACY_MATRIX.md`.
- **AI-3** Optimize Register Write Accuracy — `_frames_match` exists in
  `sidm2/accuracy.py` at the frame-comparison call site described.
- **TEST-1** Conversion Cockpit Unit Tests Expansion — cockpit test files exist and
  run as part of `test-all.bat`.
- **TEST-2** Expand Overall Test Coverage — target was "200+ tests with edge cases";
  the current suite has **2,325 `def test_*` functions** (`grep -rn "def test_"
  pyscript/test_*.py | wc -l`), matching CLAUDE.md's "~2,300 tests" figure and far
  exceeding the original target, even though the original per-area checklist
  (Laxity driver / filter format / Voice 3 / integration / error-handling tests) was
  never individually ticked off — the growth subsumed it.
- **CC (af73287 commit reference for CC-2), 9d027bf (v2.6.0 tag commit)** — both
  commits confirmed present via `git cat-file -e`.

---

## Notes

**Cross-References**:
- Strategic planning: `docs/ROADMAP.md`
- Archived improvements: `docs/archive/2025-12-14/IMPROVEMENT_PLAN_FINAL_STATUS.md`
- Bug tracking: GitHub Issues (when created)

**Maintenance**:
- Re-run this reconciliation against the tree (not against checkboxes) before trusting
  this file as a candidate open-task list.

**Version**: 2.0 (reconciled)
**Reconciled against**: SIDM2 v3.27.0
**Last Updated**: 2026-08-20
**Owner**: SIDM2 Project
