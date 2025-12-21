# SIDM2 Project Roadmap

**Strategic direction and future improvements**

**Date**: 2025-12-21
**Version**: 2.1
**Status**: 🎯 Active Roadmap

---

## Overview

This roadmap focuses on improving the SIDM2 converter from its current **99.93% accuracy** baseline to production-ready quality and expanded format support.

**Current State** (v2.5.2):
- ✅ Laxity NewPlayer v21: 99.93% frame accuracy
- ✅ SF2-exported SIDs: 100% accuracy (perfect roundtrip)
- ✅ Complete validation system with CI/CD
- ✅ Cleanup and project maintenance system
- ✅ Professional error handling system (v2.5.2)
- ✅ SF2 Viewer GUI with visualization and playback (v2.4.0)
- ✅ Documentation consolidation and optimization (v2.3.0-v2.3.1)
- ✅ Comprehensive test coverage (130+ tests, 100% pass rate)
- ⚠️ Filter accuracy: 0% (format not yet converted)
- ⚠️ Voice 3: Untested (no test files available)

**Vision**: Universal C64 music converter with near-perfect accuracy across all player formats.

---

## Priority Framework

| Priority | Meaning | Timeframe |
|----------|---------|-----------|
| **P0** | Critical - fixes production blockers | Immediate |
| **P1** | High value - key features | This quarter |
| **P2** | Medium value - improvements | Next quarter |
| **P3** | Low value - nice to have | Backlog |

---

## Track 1: Laxity Driver Perfection (P1)

**Goal**: 99.93% → 100% accuracy

### 1.1: Implement Filter Format Conversion (P1)

**Current**: Filters not converted (0% accuracy)
**Target**: Full filter support with proper format translation

**Tasks**:
1. Analyze Laxity filter table format
   - Document filter table structure (see Wave Table Fix as example)
   - Compare with SF2 filter format
   - Identify format differences
2. Implement filter format converter
   - Create conversion algorithm
   - Test on files with filter effects
   - Validate filter accuracy
3. Update Laxity driver with filter injection
   - Integrate filter conversion into `sidm2/sf2_writer.py`
   - Add filter-specific pointer patches
   - Update table injection logic

**Effort**: 8-12 hours
**Expected Impact**: +0.05% accuracy (filters rarely used)
**Success Criteria**: Filter effects sound identical to original

**Files Modified**:
- `sidm2/sf2_writer.py` (add filter conversion)
- `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md` (document approach)

---

### 1.2: Test Voice 3 Support (P2)

**Current**: Voice 3 untested (no test files)
**Target**: Verify voice 3 works correctly

**Tasks**:
1. Find or create Laxity files using voice 3
2. Test conversion with 3-voice music
3. Verify all 3 voices render correctly
4. Fix any voice 3-specific issues

**Effort**: 4-6 hours
**Expected Impact**: Confidence in full 3-voice support
**Success Criteria**: 3-voice files convert at 99.93%+ accuracy

---

### 1.3: Optimize Register Write Accuracy (P1)

**Current**: 99.93% frame accuracy (507/507 register writes on test files)
**Target**: 100% frame accuracy

**Investigation**:
1. Analyze the 0.07% discrepancy
   - Which registers differ?
   - Which frames show mismatches?
   - Pattern in discrepancies?
2. Identify root cause
   - Timing issues?
   - Table lookup differences?
   - Edge case handling?
3. Implement fix

**Effort**: 6-8 hours
**Expected Impact**: 99.93% → 100% accuracy
**Success Criteria**: Perfect register write match on all test files

---

## Track 2: Additional Player Format Support (P2)

**Goal**: Expand beyond Laxity NewPlayer v21

### 2.1: Add JCH NewPlayer v20 Support (P2)

**Current**: NP20 driver exists but accuracy unknown
**Target**: NP20 files convert at >95% accuracy

**Approach**: Use same Extract & Wrap method as Laxity driver

**Tasks**:
1. Extract NP20 player from reference SID
2. Analyze memory layout and tables
3. Create relocation script
4. Write SF2 wrapper
5. Generate header blocks
6. Test on NP20 files
7. Measure accuracy

**Effort**: 30-40 hours (similar to Laxity driver)
**Expected Impact**: Support for second most common format
**Success Criteria**: >95% accuracy on NP20 test files

**Files Created**:
- `drivers/np20/` (new directory)
- `sidm2/np20_parser.py` (if needed)

---

### 2.2: Player Format Auto-Detection (P1)

**Current**: Manual `--driver` flag required
**Target**: Automatic player detection and driver selection

**Tasks**:
1. Enhance `tools/player-id.exe` usage
2. Create driver selection logic
3. Map player IDs to drivers
4. Auto-select best driver per file
5. Fallback to generic driver
6. Add user override option

**Effort**: 4-6 hours
**Expected Impact**: Better user experience, fewer errors
**Success Criteria**: Correct driver selected 95%+ of time

**Files Modified**:
- `scripts/sid_to_sf2.py` (add auto-detection)
- `sidm2/player_detection.py` (new module)

---

## Track 3: Quality and Stability (P1-P2)

**Goal**: Production-ready reliability

### 3.1: Fix SF2 Packer Pointer Relocation Bug (P2)

**Current**: 17/18 files fail SIDwinder disassembly
**Impact**: Medium (files play correctly, only affects debugging)

**Tasks**:
1. Complete investigation (started in old improvement plan)
2. Compare working vs broken file patterns
3. Identify missing relocation cases
4. Fix `sidm2/sf2_packer.py`
5. Verify all 18 files disassemble

**Effort**: 8-12 hours
**Expected Impact**: Better debugging capability
**Success Criteria**: 18/18 files disassemble successfully

**Files Modified**:
- `sidm2/sf2_packer.py` (fix relocation logic)

---

### 3.2: Expand Test Coverage (P2)

**Current**: 69 converter tests, 12 format tests, 19 pipeline tests
**Target**: 150+ tests with edge cases

**Focus Areas**:
1. Laxity driver tests (new)
   - Test all table types
   - Test pointer patching
   - Test edge cases
2. Format conversion tests
   - Filter format (when implemented)
   - Voice 3 scenarios
3. Integration tests
   - Multi-file batch conversion
   - Error handling
   - Invalid input handling

**Effort**: 12-16 hours
**Expected Impact**: Fewer regressions, faster development
**Success Criteria**: >80% code coverage

**Files Created**:
- `scripts/test_laxity_driver.py` (new test suite)
- `scripts/test_edge_cases.py` (edge case tests)

---

### 3.3: Performance Optimization (P3)

**Current**: Conversion time unknown, likely acceptable
**Target**: Optimize for batch processing

**Tasks**:
1. Profile conversion pipeline
2. Identify bottlenecks
3. Optimize slow operations
4. Add progress indicators
5. Enable parallel processing

**Effort**: 8-12 hours
**Expected Impact**: Faster batch conversions
**Success Criteria**: 2x speed improvement

---

## Track 4: User Experience (P2-P3)

**Goal**: Make tool more accessible and easier to use

### 4.1: Create GUI Application (P3)

**Current**: Command-line only
**Target**: Simple desktop GUI for non-technical users

**Features**:
- File selection dialog
- Drag-and-drop support
- Conversion progress bar
- Preview audio player
- Batch conversion
- Settings management

**Technology**: Python + tkinter (built-in) or PyQt

**Effort**: 40-60 hours
**Expected Impact**: Broader user base
**Success Criteria**: Non-technical users can convert files

---

### 4.2: Improve Error Messages (P2)

**Current**: Technical error messages
**Target**: User-friendly error messages with suggestions

**Tasks**:
1. Audit all error messages
2. Categorize error types
3. Write clear, actionable messages
4. Add troubleshooting hints
5. Link to documentation

**Effort**: 6-8 hours
**Expected Impact**: Reduced user confusion
**Success Criteria**: Users can self-resolve common issues

---

### 4.3: Create Video Tutorials (P3)

**Content**:
1. Quick Start (5 min)
2. Batch Conversion (10 min)
3. Troubleshooting (15 min)
4. Advanced Features (20 min)

**Effort**: 16-20 hours
**Expected Impact**: Lower barrier to entry

---

## Track 5: Documentation (P2-P3)

**Goal**: Comprehensive, accessible documentation

### 5.1: User Guide (P2)

**Current**: Technical documentation for developers
**Target**: User-friendly guide for musicians

**Sections**:
1. Getting Started
2. Converting Your First File
3. Understanding Accuracy Reports
4. Troubleshooting Common Issues
5. Advanced Options
6. FAQ

**Effort**: 12-16 hours
**Files Created**: `docs/guides/USER_GUIDE.md`

---

### 5.2: API Documentation (P3)

**Current**: Code comments only
**Target**: Complete API documentation with examples

**Tasks**:
1. Document all public modules
2. Add docstrings to all functions
3. Create usage examples
4. Generate API reference

**Tools**: Sphinx or similar

**Effort**: 20-24 hours

---

## Track 6: Integration and Ecosystem (P3)

**Goal**: Integrate with C64 music ecosystem

### 6.1: HVSC Integration (P3)

**High Voltage SID Collection** integration

**Features**:
- Batch convert HVSC subsets
- Preserve metadata
- Generate statistics
- Create compatibility matrix

**Effort**: 16-20 hours

---

### 6.2: SID Factory II Editor Integration (P3)

**Goal**: Seamless workflow with SF2 editor

**Features**:
- One-click import to SF2
- Export from SF2 to SID
- Preserve editing session data
- Plugin or script for SF2

**Effort**: 20-30 hours (requires SF2 editor knowledge)

---

## Quick Wins (Do Anytime)

### Q1: Add More Test Files (P2)
- Collect diverse Laxity SIDs
- Add files with filters
- Add 3-voice files
- Expand test coverage

**Effort**: 2-4 hours

---

### Q2: Improve Logging (P2)
- Add debug logging
- Structured log format
- Log rotation
- Verbosity levels

**Effort**: 4-6 hours

---

### Q3: Package as Binary (P2)
- Create standalone executables
- Windows, macOS, Linux builds
- No Python installation required
- Use PyInstaller or similar

**Effort**: 8-12 hours

---

## Success Metrics

### Short Term (3 months)
- ✅ Laxity driver: 99.93% → 100% accuracy
- ✅ Filter support implemented
- ✅ Packer bug fixed
- ✅ 150+ tests
- ✅ User guide published

### Medium Term (6 months)
- ✅ NP20 driver operational (>95% accuracy)
- ✅ Auto-detection working
- ✅ GUI application released
- ✅ 200+ tests

### Long Term (12 months)
- ✅ Multiple player formats supported
- ✅ HVSC integration
- ✅ SF2 editor integration
- ✅ Community adoption

---

## Timeline

### Q1 2026 (Jan-Mar)
**Priority**: Track 1 (Laxity Perfection) + Track 3 (Quality)

**Goals**:
- Implement filter support
- Achieve 100% accuracy
- Fix packer bug
- Expand tests to 150+

**Estimated Effort**: 40-50 hours

---

### Q2 2026 (Apr-Jun)
**Priority**: Track 2 (NP20 Support) + Track 4 (UX)

**Goals**:
- NP20 driver operational
- Auto-detection working
- Improved error messages
- User guide published

**Estimated Effort**: 50-60 hours

---

### Q3 2026 (Jul-Sep)
**Priority**: Track 4 (GUI) + Track 5 (Docs)

**Goals**:
- GUI application released
- API documentation complete
- Video tutorials published

**Estimated Effort**: 70-90 hours

---

### Q4 2026 (Oct-Dec)
**Priority**: Track 6 (Integration)

**Goals**:
- HVSC integration
- SF2 editor integration
- Community engagement

**Estimated Effort**: 40-50 hours

---

## Risk Mitigation

### Risk: Filter format more complex than expected
**Mitigation**: Time-box to 16 hours, if not resolved, document limitation and defer

### Risk: NP20 driver effort exceeds estimate
**Mitigation**: Reuse Laxity driver patterns, ask for help if stuck >30 hours

### Risk: GUI development takes too long
**Mitigation**: Start with minimal viable GUI, iterate based on feedback

### Risk: Community adoption slow
**Mitigation**: Focus on quality over features, engage C64 music communities early

---

## Community Engagement

### Target Audiences
1. **C64 Musicians** - Create new music in SF2
2. **Game Developers** - Convert SID music for games
3. **Preservationists** - Convert HVSC to editable format
4. **Researchers** - Study C64 music formats

### Engagement Strategies
1. Release announcements on csdb.dk
2. Demo videos on YouTube
3. Posts on Lemon64 forums
4. GitHub Discussions for feedback
5. Discord/Slack communities

---

## Maintenance

### Regular Activities
- **Weekly**: Review issues, answer questions
- **Monthly**: Update roadmap based on progress
- **Quarterly**: Major release with changelog
- **Yearly**: Roadmap review and planning

### Version Strategy
- **Major (X.0.0)**: New player format support
- **Minor (1.X.0)**: New features, significant improvements
- **Patch (1.0.X)**: Bug fixes, minor tweaks

---

## References

- [Archived Improvement Plan](archive/2025-12-14/IMPROVEMENT_PLAN_FINAL_STATUS.md) - Previous roadmap (completed)
- [Laxity Driver User Guide](guides/LAXITY_DRIVER_USER_GUIDE.md) - User-facing guide
- [Laxity Driver Technical Reference](reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md) - Technical reference
- [CHANGELOG.md](../CHANGELOG.md) - Version history
- [CONTRIBUTING.md](../CONTRIBUTING.md) - How to contribute

---

## Next Actions

**Immediate (This Week)**:
1. Review this roadmap
2. Prioritize Track 1 items
3. Start filter format analysis
4. Create GitHub issues for P1 tasks

**This Month**:
1. Implement filter support (1.1)
2. Investigate 100% accuracy (1.3)
3. Expand test coverage (3.2)

**This Quarter**:
1. Complete Track 1 (Laxity Perfection)
2. Fix packer bug (3.1)
3. Publish user guide (5.1)

---

**Document Status**: 🎯 Active Roadmap
**Review Frequency**: Monthly
**Owner**: SIDM2 Project
**Last Updated**: 2025-12-14
**Version**: 2.0
