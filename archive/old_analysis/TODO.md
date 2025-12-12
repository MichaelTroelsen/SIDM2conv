# SIDM2 Project TODO

**Last Updated**: 2025-12-07
**Version**: 0.7.1
**Status**: Implementation Phase - Ready to Execute

---

## Quick Status

**Current State**:
- Version: 0.7.1
- Documentation: Consolidated (46 → 25 files)
- Scripts: Organized in scripts/ folder
- Validation Tools: Exist but ecosystem broken

**Accuracy**:
- SF2-originated files: 100% (17/17 files)
- Laxity-originated files: Variable (1-5% typical)
- Overall: 68% at 100%, 32% needing improvement

**Critical Blockers**:
1. ❌ SIDwinder trace broken (patches applied, not rebuilt)
2. ❌ Packer relocation bug (17/18 files fail disassembly)
3. ❌ No validation dashboard (can't track progress)

---

## PRIORITY 0: Fix Validation Ecosystem (THIS WEEK)

**Goal**: Unblock all validation and improvement work

### P0.1: Rebuild SIDwinder with Trace Patches ⚠️ CRITICAL

**Problem**: Trace patches applied to source but executable not rebuilt

**Tasks**:
- [ ] Open Visual Studio Developer Command Prompt
- [ ] Navigate to: `C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6`
- [ ] Run: `build.bat`
- [ ] Copy `build\Release\SIDwinder.exe` to `tools/`
- [ ] Test: `tools/SIDwinder.exe -trace=test.txt SID/Angular.sid`
- [ ] Verify: test.txt contains register writes (not empty)

**Effort**: 2 hours
**Success**: Trace files contain actual data
**Blocks**: Pipeline step 6, register validation

**Reference**: [docs/guides/SIDWINDER_GUIDE.md](docs/guides/SIDWINDER_GUIDE.md#rebuilding-sidwinder)

### P0.2: Fix Packer Pointer Relocation Bug ⚠️ CRITICAL

**Problem**: 17/18 exported SIDs fail disassembly with "Execution at $0000"

**Investigation Approach**:
1. Compare working file (Cocktail_to_Go_tune_3) vs broken (Angular)
2. Disassemble both original SIDs (verify both work)
3. Disassemble exported working SID (verify works)
4. Attempt exported broken SID (fails at $0000)
5. Compare pointer patterns
6. Trace packer relocation on both
7. Identify failing addressing mode/pattern

**Tasks**:
- [ ] Create `scripts/compare_packer_relocations.py` analysis script
- [ ] Analyze working file pointer patterns
- [ ] Analyze broken file pointer patterns
- [ ] Identify root cause (likely jump table or indirect addressing)
- [ ] Fix relocation logic in `sidm2/sf2_packer.py`
- [ ] Test on all 18 files
- [ ] Verify: 18/18 files disassemble successfully

**Effort**: 4-8 hours
**Success**: All files disassemble without errors
**Blocks**: Pipeline step 9, debugging capability

**Reference**: [docs/analysis/CONSOLIDATION_INSIGHTS.md](docs/analysis/CONSOLIDATION_INSIGHTS.md#2-the-packer-bug-is-a-critical-validation-blocker)

### P0.3: Verify Validation Ecosystem Works

**Tasks**:
- [ ] Run complete pipeline on all 18 files
- [ ] Verify steps 6 and 9 complete successfully
- [ ] Verify trace files contain data
- [ ] Verify all files disassemble
- [ ] Update pipeline success metrics
- [ ] Document validation workflow

**Effort**: 1 hour
**Success**: Complete pipeline 18/18 files, all 14 outputs

---

## PRIORITY 1: Implement Semantic Conversion (THIS MONTH)

**Goal**: Fix the 32% failure rate by addressing Laxity→SF2 semantic gaps

### P1.1: Implement Gate Inference Algorithm

**Problem**: Laxity has implicit gates, SF2 requires explicit (+++ / ---)

**Tasks**:
- [ ] Analyze Laxity gate patterns in test files
- [ ] Design gate inference algorithm
- [ ] Implement in `sidm2/sequence_extraction.py`
- [ ] Add unit tests for gate inference
- [ ] Validate on 10 Laxity files
- [ ] Measure accuracy improvement

**Effort**: 6 hours
**Expected Impact**: +10-15% accuracy on Laxity files
**Files**: `sidm2/sequence_extraction.py`, `scripts/test_converter.py`

### P1.2: Implement Command Decomposition

**Problem**: Laxity super commands (multi-param) need SF2 simple commands

**Tasks**:
- [ ] Document all Laxity super commands
- [ ] Create decomposition mapping table
- [ ] Implement decomposition logic
- [ ] Handle parameter extraction
- [ ] Validate command accuracy
- [ ] Measure improvement

**Effort**: 8 hours
**Expected Impact**: +5-10% accuracy
**Files**: `sidm2/sequence_extraction.py`, `sidm2/command_mapping.py` (new)

### P1.3: Implement Instrument Transposition

**Problem**: Laxity row-major 8×8 vs SF2 column-major 32×6

**Tasks**:
- [ ] Analyze current instrument extraction
- [ ] Implement proper transposition
- [ ] Add padding with defaults
- [ ] Validate instrument parameters
- [ ] Test on all file types
- [ ] Measure improvement

**Effort**: 4 hours
**Expected Impact**: +5% accuracy
**Files**: `sidm2/instrument_extraction.py`

### P1.4: Create Semantic Conversion Test Suite

**Tasks**:
- [ ] Test cases for gate inference
- [ ] Test cases for command decomposition
- [ ] Test cases for instrument transposition
- [ ] Add reference outputs
- [ ] Implement regression tests
- [ ] Integrate into CI/CD

**Effort**: 4 hours
**Files**: `scripts/test_semantic_conversion.py` (new)

---

## PRIORITY 2: Systematize Validation (THIS QUARTER)

**Goal**: Track progress and prevent regressions

### P2.1: Create Validation Dashboard

**Purpose**: Single view of all metrics

**Tasks**:
- [ ] Create dashboard generator script
- [ ] Parse pipeline validation results
- [ ] Calculate aggregate metrics
- [ ] Generate HTML with charts (overall, by file type, top issues)
- [ ] Run after each pipeline execution
- [ ] Commit to repo

**Effort**: 6 hours
**Files**: `scripts/generate_dashboard.py` (new), `output/validation_dashboard.html`

### P2.2: Implement Regression Tracking

**Purpose**: Track accuracy over time

**Tasks**:
- [ ] Create validation history tracker
- [ ] Store results per version in JSON
- [ ] Generate trend charts
- [ ] Flag regressions (accuracy drops)
- [ ] Integrate with dashboard
- [ ] Run on every release

**Effort**: 4 hours
**Files**: `validation_history.json` (new), `scripts/track_validation_history.py` (new)

### P2.3: Automate Validation on Commits

**Purpose**: Catch issues early

**Tasks**:
- [ ] Add validation to CI/CD pipeline
- [ ] Quick validation (10 files) on PR
- [ ] Full validation on merge
- [ ] Post results as PR comment
- [ ] Block merge if accuracy drops >5%
- [ ] Update dashboard automatically

**Effort**: 4 hours
**Files**: `.github/workflows/test.yml`, `scripts/ci_validation.py` (new)

---

## PRIORITY 3: Documentation & Knowledge

### P3.1: Create Laxity→SF2 Rosetta Stone

**Purpose**: Definitive semantic mapping guide

**Tasks**:
- [ ] Document gate handling algorithm
- [ ] Complete command mapping table
- [ ] Step-by-step table transformations
- [ ] Known edge cases and workarounds

**Effort**: 6 hours
**Files**: `docs/guides/LAXITY_TO_SF2_GUIDE.md` (new)

### P3.2: Document Solutions (Ongoing)

**Purpose**: Capture fixes for future reference

**Tasks**:
- [ ] Create `docs/solutions/` directory
- [ ] Document each fix with problem/cause/solution/tests
- [ ] Update after implementing each fix

**Effort**: 1 hour per fix
**Files**: `docs/solutions/*.md` (as needed)

---

## QUICK WINS (Do Anytime)

### Q1: Add .gitignore for Temp Files
```bash
# Add to .gitignore:
temp/
*.log
*.cfg
tools/trace.bin
tools/mit*
pipeline_run_*.log
```
**Effort**: 5 minutes

### Q2: Clean Up Old Index
```bash
rm docs/INDEX_OLD.md
```
**Effort**: 1 minute

### Q3: Update README Documentation Links

Update README.md to reference new docs structure.

**Effort**: 10 minutes

---

## Success Metrics

### Phase 1: Validation Ecosystem (Week 1)
- [x] Documentation consolidated
- [x] Scripts organized
- [ ] SIDwinder trace working
- [ ] 18/18 files disassemble
- [ ] Complete pipeline 100% success

### Phase 2: Conversion Quality (Month 1)
- [ ] Gate inference implemented
- [ ] Command decomposition implemented
- [ ] Instrument transposition improved
- [ ] Laxity accuracy: 45% → 85%
- [ ] Average accuracy: 68% → 90%

### Phase 3: Systematic Validation (Quarter 1)
- [ ] Validation dashboard live
- [ ] Regression tracking active
- [ ] Automated CI validation
- [ ] Version-over-version metrics
- [ ] Progress visibility achieved

---

## Timeline

**Week 1** (2025-12-08 to 2025-12-14):
- Focus: P0 (Validation Ecosystem)
- Goal: All tools working

**Weeks 2-3** (2025-12-15 to 2025-12-28):
- Focus: P1 (Semantic Conversion)
- Goal: Laxity quality improved

**Week 4** (2025-12-29 to 2026-01-04):
- Focus: P2 (Systematize)
- Goal: Dashboard and tracking

**Ongoing**:
- P3: Document solutions
- Quick wins: As time permits

---

## Current Focus

**TODAY**: Review improvement plan and consolidation insights

**THIS WEEK**:
1. Rebuild SIDwinder (P0.1)
2. Fix packer bug (P0.2)
3. Verify ecosystem (P0.3)

**BLOCKERS**: None - all tools and knowledge available

---

## References

**New Knowledge Documents**:
- [Consolidation Insights](docs/analysis/CONSOLIDATION_INSIGHTS.md) - Meta-analysis findings
- [Improvement Plan](docs/IMPROVEMENT_PLAN.md) - Detailed action plan
- [Technical Analysis](docs/analysis/TECHNICAL_ANALYSIS.md) - Consolidated tech docs

**Guides**:
- [SIDwinder Guide](docs/guides/SIDWINDER_GUIDE.md) - Tool integration
- [Validation Guide](docs/guides/VALIDATION_GUIDE.md) - How to validate
- [Documentation Index](docs/INDEX.md) - All documentation

**Core Docs**:
- [README.md](README.md) - User guide
- [CLAUDE.md](CLAUDE.md) - AI assistant guide
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines

---

**Status**: Ready for implementation
**Next Action**: Start P0.1 (Rebuild SIDwinder)
**Owner**: SIDM2 Project
