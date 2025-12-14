# Martin Galway SID to SF2 Converter - Implementation Plan

**Status**: Pre-Implementation (Baseline Testing Complete)
**Priority**: High-Impact Feature Addition
**Effort**: 112 hours (3-4 weeks)
**Risk Level**: Medium (Mitigated by strict testing)

---

## 🔴 CRITICAL BACKWARD COMPATIBILITY CONSTRAINT

**RULE #1**: NO breaking changes to Laxity functionality
**RULE #2**: All code additions must be in isolated modules
**RULE #3**: Every phase must pass backward compatibility tests
**RULE #4**: Baseline tests established and MUST continue passing

### Baseline Testing Status
- **Date Established**: 2025-12-14
- **Test File**: `scripts/test_laxity_baseline.py`
- **Current Status**: ✅ **10/10 PASSING**
- **Laxity Modules Verified**: 5 modules, all importable
- **Conversion API Verified**: All methods callable
- **SF2 Output Verified**: All files valid

**This baseline must not change.**

---

## Architecture: Modular Isolation

### Laxity Implementation (EXISTING - DO NOT MODIFY)
```
sidm2/
├── laxity_parser.py         ← Laxity-specific parsing
├── laxity_analyzer.py       ← Laxity-specific analysis
├── laxity_converter.py      ← Laxity-specific conversion
└── (other shared modules)
```

### Martin Galway Implementation (NEW - ISOLATED)
```
sidm2/
├── martin_galway_analyzer.py        ← NEW: Galway-specific analyzer
├── galway_memory_analyzer.py        ← NEW: Galway memory patterns
├── galway_table_extractor.py        ← NEW: Galway table extraction
├── galway_format_converter.py       ← NEW: Format conversion
├── galway_table_builder.py          ← NEW: Runtime table building
└── (existing shared modules - NO CHANGES)
```

### Shared/Modified Modules (MINIMAL CHANGES ONLY)
```
sidm2/
├── enhanced_player_detection.py     ← Already has Galway support (update only if needed)
└── player_base.py                   ← Register Galway analyzer (add 5-10 lines)

scripts/
├── sid_to_sf2.py                    ← Add Galway routing (add 15-20 lines)
└── (new batch converters for Galway)
```

---

## Phase Breakdown with Testing

### PHASE 1: Foundation & Registry (6-8 hours)
**Goal**: Infrastructure for Galway support without touching Laxity

**Tasks**:
1. Create `MartinGalwayAnalyzer` class
2. Register with player detection system
3. Implement RSID/PSID detection
4. Add file tracking system
5. Create minimal logging

**Code Changes**:
- NEW: `sidm2/martin_galway_analyzer.py` (400-500 lines)
- MODIFY: `sidm2/player_base.py` (+5 lines)
- MODIFY: `sidm2/enhanced_player_detection.py` (+5 lines)

**Testing Before Proceeding**:
```bash
# Run baseline - must still pass 10/10
python scripts/test_laxity_baseline.py

# Test Galway detection only
python -c "
from sidm2.enhanced_player_detection import EnhancedPlayerDetector
d = EnhancedPlayerDetector()
from pathlib import Path
p, c = d.detect_player(Path('Galway_Martin/Arkanoid.sid'))
assert 'Martin' in p, f'Expected Martin, got {p}'
print(f'[OK] Detected as {p}')
"
```

**Go/No-Go Gate**:
- ✅ Baseline tests still pass? Continue
- ❌ Any Laxity tests failed? STOP - revert changes

---

### PHASE 2: Memory Analysis (10-12 hours)
**Goal**: Understand Martin Galway memory layout

**Tasks**:
1. Implement memory pattern scanner
2. Create heuristic table finders
3. Build address conflict detector
4. Generate analysis reports
5. Create game signature database

**Code Changes**:
- NEW: `sidm2/galway_memory_analyzer.py` (600+ lines)
- NEW: Signature database (JSON)

**Testing Before Proceeding**:
```bash
# Run baseline - must still pass 10/10
python scripts/test_laxity_baseline.py

# Test Galway analysis on subset
python -c "
from sidm2.galway_memory_analyzer import GalwayMemoryAnalyzer
analyzer = GalwayMemoryAnalyzer('Galway_Martin/Arkanoid.sid')
results = analyzer.analyze()
print(f'[OK] Analyzed {len(results)} patterns')
"
```

**Decision Point After Phase 2**:
- Analyze first 10 files completely
- Success: >= 8/10 memory patterns identified
- Continue: Proceed to Phase 3
- Failure: Reduce scope to 20 most similar files

---

### PHASE 3: Table Extraction (14-18 hours)
**Goal**: Extract music tables with fallback strategies

**Tasks**:
1. Implement table extraction engine
2. Create format converters (Galway → SF2)
3. Build validation layer
4. Create per-game templates
5. Implement fallback strategies

**Code Changes**:
- NEW: `sidm2/galway_table_extractor.py` (800+ lines)
- NEW: `sidm2/galway_format_converter.py` (400+ lines)
- NEW: Template library (JSON)

**Testing Before Proceeding**:
```bash
# Run baseline - must still pass 10/10
python scripts/test_laxity_baseline.py

# Test extraction on 5 files
for f in Galway_Martin/Arkanoid.sid Galway_Martin/Broware.sid ...; do
  python scripts/test_galway_extraction.py $f
done
```

**Decision Point After Phase 3**:
- Extract tables from first 20 files
- Success: >= 14/20 with confidence > 70%
- Continue: Proceed to driver implementation
- Failure: Accept lower accuracy targets

---

### PHASE 4: Driver Implementation (18-24 hours)
**Goal**: Create SF2 driver with Martin Galway player

**Tasks**:
1. Analyze Galway player code
2. Extract relocatable player code
3. Create SF2 wrapper assembly
4. Build relocation script
5. Generate driver binary

**Code Changes**:
- NEW: `G5/drivers/galway/galway_driver.asm` (1500+ lines)
- NEW: `G5/drivers/galway/build_galway_driver.py` (300+ lines)
- NEW: `G5/drivers/galway/sf2driver_galway_00.prg` (binary)

**Testing Before Proceeding**:
```bash
# Run baseline - must still pass 10/10
python scripts/test_laxity_baseline.py

# Test driver assembly
python G5/drivers/galway/build_galway_driver.py
# Verify binary created and valid

# Test driver on one file
python scripts/sid_to_sf2.py Galway_Martin/Arkanoid.sid output/test_galway.sf2 --driver galway
# Verify SF2 created successfully
```

**Decision Point After Phase 4**:
- Driver builds without errors?
- One file plays correctly?
- Success: Continue
- Failure: Use standard Driver 11 instead (skip Phases 4-5, accept lower accuracy)

---

### PHASE 5: Runtime Table Building (12-16 hours)
**Goal**: Dynamically adapt driver to different Galway variants

**Tasks**:
1. Design runtime table builder
2. Create game signature matching
3. Implement adaptive init routine
4. Build fallback strategies

**Code Changes**:
- NEW: `sidm2/galway_table_builder.py` (600+ lines)
- NEW: Game signature database (JSON)

**Testing Before Proceeding**:
```bash
# Run baseline - must still pass 10/10
python scripts/test_laxity_baseline.py

# Test runtime building
python scripts/test_galway_runtime_tables.py

# Verify no crashes on table injection
```

---

### PHASE 6: Conversion Integration (10-12 hours)
**Goal**: Wire everything together

**Tasks**:
1. Update main converter routing
2. Implement batch conversion
3. Add validation pipeline
4. Create reporting system

**Code Changes**:
- MODIFY: `scripts/sid_to_sf2.py` (+20-30 lines)
- NEW: `scripts/convert_galway_collection.py` (300+ lines)
- NEW: `scripts/validate_galway_conversions.py` (400+ lines)

**Testing Before Proceeding**:
```bash
# Run baseline - must PASS 10/10
python scripts/test_laxity_baseline.py

# Test batch conversion (all 40 files)
python scripts/convert_galway_collection.py

# Verify no crashes, all files processed
```

---

### PHASE 7: Manual Refinement (16-20 hours)
**Goal**: Fix remaining issues

**Tasks**:
1. Manual review of low-confidence files
2. Fix per-game issues
3. Update template library
4. Round-trip validation
5. SID Factory II editor verification

**Testing**:
```bash
# Run baseline - MUST PASS 10/10
python scripts/test_laxity_baseline.py

# Run Galway validation
python scripts/validate_galway_conversions.py
```

---

### PHASE 8: Documentation & Release (8 hours)
**Goal**: Complete and release

**Tasks**:
1. Write user guide
2. Update README/CLAUDE.md
3. Create developer docs
4. Version bump
5. Final validation

**Testing**:
```bash
# FINAL: Run baseline - MUST PASS 10/10
python scripts/test_laxity_baseline.py

# FINAL: Run all tests
python scripts/test_converter.py
python scripts/test_sf2_format.py
```

---

## Testing Strategy: Continuous Backward Compatibility

### Mandatory Baseline Tests (Must pass at every gate)
```bash
# Test 1: Laxity baseline (10 tests)
python scripts/test_laxity_baseline.py
# MUST: 10/10 passing

# Test 2: Existing converter tests
python scripts/test_converter.py
# MUST: All Laxity tests still passing

# Test 3: Existing pipeline tests
python scripts/test_complete_pipeline.py
# MUST: Pipeline outputs unchanged
```

### Galway-Specific Tests (Must pass before each phase)
```bash
# Phase 1 gate: Galway detection
python -m pytest scripts/test_galway_detection.py

# Phase 2 gate: Memory analysis
python -m pytest scripts/test_galway_memory_analysis.py

# Phase 3 gate: Table extraction
python -m pytest scripts/test_galway_table_extraction.py

# Phase 4 gate: Driver implementation
python -m pytest scripts/test_galway_driver.py

# Phase 6 gate: Integration
python -m pytest scripts/test_galway_integration.py

# Phase 7 gate: Full validation
python scripts/validate_galway_conversions.py
```

### CI/CD Integration
```yaml
# Before each commit:
1. Run test_laxity_baseline.py
2. Run test_converter.py (Laxity tests only)
3. Run test_complete_pipeline.py
4. If any fail: REVERT CHANGES immediately
```

---

## Risk Mitigation

### Risk 1: Break Laxity Functionality
**Probability**: Medium (modular approach reduces risk)
**Mitigation**:
- Strict baseline testing at every phase
- No modifications to Laxity code
- Modular architecture with clear boundaries
- Revert strategy if tests fail

**Decision**: STOP and revert if baseline test fails

### Risk 2: Format Too Heterogeneous
**Probability**: Low (initial analysis shows patterns)
**Mitigation**:
- Phase 2 validates approach on first 10 files
- Go/No-Go gate after Phase 2
- Template library reduces manual work
- Can reduce scope if needed

**Decision**: After Phase 2 analysis, decide on scope (40 files vs. 20 files)

### Risk 3: Implementation Takes Too Long
**Probability**: Medium (complexity depends on format variation)
**Mitigation**:
- Baseline: 112 hours estimate
- Phases 1-6: 60 hours (core functionality)
- Phases 7-8: 52 hours (refinement and docs)
- Can skip Phase 4-5 and use Driver 11 if needed

**Decision**: After Phase 6, decide on full vs. basic support

### Risk 4: Driver Doesn't Work
**Probability**: Low (proven architecture from Laxity)
**Mitigation**:
- Phase 4 has go/no-go gate
- Fallback: Use standard Driver 11 (accept 1-8% accuracy)
- Can accept playback-only vs. full editor support

**Decision**: After Phase 4, decide on driver support level

---

## Go/No-Go Decision Points

### Gate 1: After Phase 1 (Day 1)
```
✅ IF: Baseline tests pass 10/10 AND Galway detection works
→ PROCEED to Phase 2

❌ IF: Baseline tests fail
→ REVERT ALL CHANGES, investigate
```

### Gate 2: After Phase 2 (Day 3-4)
```
✅ IF: Memory patterns identified for >= 8/10 files
→ PROCEED to Phase 3

⚠️ IF: Memory patterns found for 5-7/10 files
→ REDUCE scope to 20 files, proceed to Phase 3

❌ IF: Memory patterns found for < 5/10 files
→ RECONSIDER approach (too heterogeneous)
```

### Gate 3: After Phase 3 (Day 7)
```
✅ IF: Tables extracted from >= 14/20 files with confidence > 70%
→ PROCEED to Phase 4

⚠️ IF: Tables extracted from 10-13/20 files
→ ACCEPT lower accuracy targets, proceed

❌ IF: Tables extracted from < 10/20 files
→ STOP, document limitations
```

### Gate 4: After Phase 4 (Day 10)
```
✅ IF: Driver builds, plays at least 1 file correctly
→ PROCEED to Phase 5-6

⚠️ IF: Driver complex, consider using Driver 11 instead
→ Skip Phase 4-5, use standard driver (1-8% accuracy acceptable)

❌ IF: Driver implementation fails
→ USE DRIVER 11 FALLBACK
```

### Gate 5: After Phase 6 (Day 12-14)
```
✅ IF: All 40 files convert, >= 30 with confidence > 70%
→ PROCEED to Phase 7

⚠️ IF: 25-29 files with confidence > 70%
→ PROCEED with reduced scope or requirements

❌ IF: < 25 files with confidence > 70%
→ EVALUATE: Continue Phase 7 or release as-is
```

### Final Gate: After Phase 8
```
✅ IF: Laxity baseline tests still pass 10/10
→ RELEASE v2.1.0 with Martin Galway support

❌ IF: Baseline tests fail
→ REVERT all changes, fix issues, retry
```

---

## Code Organization

### New Modules (Completely Isolated)
```
sidm2/
├── martin_galway_analyzer.py       - Main analyzer
├── galway_memory_analyzer.py       - Memory pattern detection
├── galway_table_extractor.py       - Table extraction engine
├── galway_format_converter.py      - Format conversion
└── galway_table_builder.py         - Runtime table building

scripts/
├── convert_galway_collection.py    - Batch converter
├── validate_galway_conversions.py  - Validation pipeline
└── test_galway_*.py                - Unit tests

G5/drivers/galway/
├── galway_driver.asm               - Driver assembly
├── build_galway_driver.py          - Build script
└── sf2driver_galway_00.prg         - Compiled driver

docs/
├── MARTIN_GALWAY_GUIDE.md          - User guide
├── GALWAY_IMPLEMENTATION.md        - Technical details
└── GALWAY_CONVERSION_RESULTS.md    - Results report
```

### Minimal Modifications (5-10 lines per file)
```
sidm2/enhanced_player_detection.py
  - Already has Galway detection (verify it works)

sidm2/player_base.py
  - Register MartinGalwayAnalyzer (5 lines)

scripts/sid_to_sf2.py
  - Add Galway routing logic (15-20 lines)
```

### No Modifications to Laxity Code
```
sidm2/laxity_parser.py       - UNCHANGED
sidm2/laxity_analyzer.py     - UNCHANGED
sidm2/laxity_converter.py    - UNCHANGED
```

---

## Success Criteria

### Minimum (Viable)
- ✅ All 40 files convert without crashes
- ✅ Laxity baseline tests pass 10/10 (no breaking changes)
- ✅ >= 25 Martin Galway files have confidence > 70%
- ✅ Audio quality acceptable (correlation > 0.7)
- ✅ Round-trip accuracy >= 60%

### Target (Good)
- ✅ All 40 files convert without crashes
- ✅ Laxity baseline tests pass 10/10 (no breaking changes)
- ✅ >= 35 Martin Galway files have confidence > 70%
- ✅ Audio quality good (correlation > 0.8)
- ✅ Round-trip accuracy >= 70%
- ✅ Documentation complete

### Stretch (Excellent)
- ✅ All 40 files convert without crashes
- ✅ Laxity baseline tests pass 10/10 (no breaking changes)
- ✅ >= 40 Martin Galway files have confidence > 75%
- ✅ Audio quality excellent (correlation > 0.9)
- ✅ Round-trip accuracy >= 80%
- ✅ Full SF2 editor integration working
- ✅ User documentation and examples complete

---

## Rollback Plan

**If anything breaks Laxity functionality**:

```bash
# 1. Identify which commit broke it
git log --oneline | head -20

# 2. Revert to last known good state
git revert <commit_hash>

# 3. Verify baseline passes
python scripts/test_laxity_baseline.py

# 4. Investigate root cause
# 5. Fix with targeted changes
# 6. Retest before proceeding
```

**Revert Strategy**:
- All Martin Galway code in isolated modules
- One commit to revert if needed
- No Laxity code modified
- Laxity functionality completely preserved

---

## Timeline

| Phase | Duration | Cumulative | Status |
|-------|----------|-----------|--------|
| Setup & Tests | 1 day | 1 day | ✅ COMPLETE |
| Phase 1: Foundation | 1 day | 2 days | Ready |
| Phase 2: Memory Analysis | 1.5 days | 3.5 days | Pending |
| Phase 3: Extraction | 2 days | 5.5 days | Pending |
| **Gate 1: Scope decision** | - | 5.5 days | - |
| Phase 4: Driver | 2.5 days | 8 days | Pending |
| Phase 5: Runtime | 2 days | 10 days | Pending |
| Phase 6: Integration | 1.5 days | 11.5 days | Pending |
| **Gate 2: Validation** | - | 11.5 days | - |
| Phase 7: Refinement | 2.5 days | 14 days | Pending |
| Phase 8: Release | 1 day | 15 days | Pending |
| **TOTAL** | **14 days** | **15 days** | - |

**Realistic**: 3-4 weeks part-time, 2 weeks full-time

---

## Critical Rules (NON-NEGOTIABLE)

1. ✅ **Baseline tests must pass 10/10 at every gate**
2. ✅ **No modifications to Laxity code**
3. ✅ **All new code in isolated modules**
4. ✅ **Go/No-Go gates at each phase**
5. ✅ **Rollback plan if tests fail**
6. ✅ **Documentation of all changes**
7. ✅ **Final validation before release**

---

**Status**: Ready to begin Phase 1
**Baseline**: ✅ 10/10 tests passing
**Laxity**: ✅ Fully functional and verified
**Martin Galway**: Ready for implementation with strict safety guarantees

