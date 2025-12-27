# Test File Recommendations

**Purpose**: Guide for selecting diverse Laxity SID test files for the test suite
**Date**: 2025-12-27
**Analysis**: Based on automated analysis of 286 Laxity SID files

---

## Analysis Summary

**Total Files Analyzed**: 286 Laxity NewPlayer v21 SID files

### Voice Usage Distribution
- **3-voice files**: 232 (81%) - Excellent 3-voice test coverage available
- **2-voice files**: 34 (12%)
- **1-voice files**: 18 (6%)

### Filter Usage
- **Files with filter**: 286 (100%) - ALL Laxity files use filters

### File Size Distribution
- **Large files (>10KB)**: 23 files
- **Medium files (5-10KB)**: 49 files
- **Small files (<5KB)**: 214 files
- **Tiny files (<1KB)**: 2 files

---

## Recommended Test Files

### Core Test Files (Currently Used)
These files are already in the test suite and should remain:

1. **Stinsens_Last_Night_of_89.sid** (7,182 bytes)
   - 3-voice, 100% filter usage
   - Well-known tune, proven conversion accuracy
   - Used in accuracy validation (100% frame accuracy achieved)

2. **Broware.sid** (6,267 bytes)
   - 3-voice, 100% filter usage
   - Used in accuracy validation
   - 507/507 frames perfect match

3. **Aids_Trouble.sid** (11,385 bytes)
   - 3-voice, 100% filter usage
   - Confirmed filter data (32% non-zero filter values)
   - Used in Voice 3 validation
   - Used in filter conversion validation

---

## Recommended Additions

### Category 1: 3-Voice with Heavy Filter Usage
Add these to expand 3-voice and filter test coverage:

1. **Alliance.sid** (5,167 bytes)
   - 3-voice, 100% filter usage
   - Medium size, good complexity

2. **Basics.sid** (2,998 bytes)
   - 3-voice, 100% filter usage
   - Small size, simpler structure

3. **Galax_it_y.sid** (2,110 bytes)
   - 3-voice, 100% filter usage
   - Small size, edge case testing

**Justification**: Expands 3-voice test coverage beyond current 3 files. Adds variety in file sizes and complexity.

---

### Category 2: Large Complex Files
Add these to test performance and edge cases:

1. **Aviator_Arcade_II.sid** (34,904 bytes) ⭐ **HIGHEST PRIORITY**
   - 3-voice, 99.6% filter usage
   - Largest file in collection (3x bigger than average)
   - Tests conversion performance limits
   - Tests memory allocation limits

2. **No_Way.sid** (19,666 bytes)
   - 3-voice, 99.6% filter usage
   - Large file, complex structure
   - Tests sequence/instrument extraction

**Justification**: Tests conversion on large, complex files. Validates performance optimizations (Track 3.7). Ensures no size-related bugs.

---

### Category 3: Small Simple Files
Add these to test minimal files and edge cases:

1. **Repeat_me.sid** (400 bytes) ⭐ **HIGHEST PRIORITY**
   - 3-voice, 99.6% filter usage
   - **Smallest file in collection**
   - Tests minimal valid file structure
   - Edge case: very short sequences/tables

2. **Twone_Five.sid** (673 bytes)
   - 3-voice, 99.6% filter usage
   - Very small file
   - Tests sparse data structures

**Justification**: Tests lower bounds of file size. Validates minimal table extraction. Ensures no assumptions about minimum data sizes.

---

### Category 4: 2-Voice Files
Add these to test non-3-voice scenarios:

1. **Ruff_Scale.sid** (23,772 bytes)
   - **2-voice only**, 99.6% filter usage
   - Large 2-voice file
   - Tests voice 3 handling when unused

2. **System.sid** (23,772 bytes)
   - **2-voice only**, 99.6% filter usage
   - Large 2-voice file (different tune than Ruff_Scale)
   - Tests voice 3 edge cases

**Justification**: Most test files are 3-voice. Need 2-voice coverage to ensure voice 3 is properly handled when unused.

---

### Category 5: 1-Voice Files
Add these to test single-voice edge cases:

1. **Stormlord_2.sid** (20,146 bytes)
   - **1-voice only**, 99.6% filter usage
   - Large but single-voice
   - Tests extreme case: voices 2+3 completely unused

**Justification**: Tests extreme edge case where only voice 1 is active. Validates that voices 2+3 are properly handled as silent.

---

## Prioritized Addition Plan

### Phase 1: High Priority (Add Now)
1. **Aviator_Arcade_II.sid** - Largest file (34KB)
2. **Repeat_me.sid** - Smallest file (400 bytes)
3. **Stormlord_2.sid** - 1-voice edge case

**Effort**: ~30 minutes
**Impact**: Tests size extremes (400 bytes → 34KB) and voice extremes (1-voice → 3-voice)

---

### Phase 2: Medium Priority (Add Soon)
1. **Alliance.sid** - 3-voice, medium size
2. **Ruff_Scale.sid** - 2-voice, large
3. **Basics.sid** - 3-voice, small

**Effort**: ~30 minutes
**Impact**: Expands voice usage coverage (1/2/3 voices) and size variety

---

### Phase 3: Nice to Have (Add Later)
1. **No_Way.sid** - Large complex file
2. **Galax_it_y.sid** - Small 3-voice
3. **System.sid** - 2-voice alternative
4. **Twone_Five.sid** - Very small file

**Effort**: ~30 minutes
**Impact**: Comprehensive test coverage across all dimensions

---

## Test Coverage Goals

### Current Coverage (3 files)
- ✅ 3-voice: 100% (3/3)
- ⚠️ 2-voice: 0% (0/3)
- ⚠️ 1-voice: 0% (0/3)
- ✅ Filter: 100% (3/3)
- ⚠️ Size range: 6-11KB (narrow)

### After Phase 1 (6 files)
- ✅ 3-voice: 67% (4/6)
- ✅ 2-voice: 0% (0/6)
- ✅ 1-voice: 17% (1/6)
- ✅ Filter: 100% (6/6)
- ✅ Size range: 400 bytes - 34KB (wide) ⭐

### After Phase 2 (9 files)
- ✅ 3-voice: 67% (6/9)
- ✅ 2-voice: 11% (1/9)
- ✅ 1-voice: 11% (1/9)
- ✅ Filter: 100% (9/9)
- ✅ Size range: 400 bytes - 34KB (comprehensive)

### After Phase 3 (13 files)
- ✅ 3-voice: 62% (8/13)
- ✅ 2-voice: 15% (2/13)
- ✅ 1-voice: 8% (1/13)
- ✅ Filter: 100% (13/13)
- ✅ Size range: 400 bytes - 34KB (excellent variety)

---

## Implementation Guide

### Step 1: Create Test File Directory (Optional)
If you want to organize test files separately:

```bash
mkdir -p tests/fixtures/laxity
cp Laxity/Aviator_Arcade_II.sid tests/fixtures/laxity/
cp Laxity/Repeat_me.sid tests/fixtures/laxity/
cp Laxity/Stormlord_2.sid tests/fixtures/laxity/
```

### Step 2: Update Test Suite
Add test cases using these files:

```python
# pyscript/test_diverse_files.py
import unittest
from pathlib import Path

class TestDiverseFiles(unittest.TestCase):
    """Test diverse Laxity files for edge cases"""

    def test_largest_file(self):
        """Test largest file (34KB)"""
        result = convert_laxity_file("Laxity/Aviator_Arcade_II.sid")
        self.assertIsNotNone(result)

    def test_smallest_file(self):
        """Test smallest file (400 bytes)"""
        result = convert_laxity_file("Laxity/Repeat_me.sid")
        self.assertIsNotNone(result)

    def test_one_voice_file(self):
        """Test 1-voice only file"""
        result = convert_laxity_file("Laxity/Stormlord_2.sid")
        self.assertIsNotNone(result)
```

### Step 3: Document in Test Suite
Update `docs/guides/VALIDATION_GUIDE.md` with new test files list.

### Step 4: Run Tests
```bash
python pyscript/test_diverse_files.py -v
```

---

## Analysis Tool

The analysis was performed using:
```bash
python pyscript/analyze_test_candidates.py
```

This tool analyzes all 286 Laxity files and categorizes them by:
- Voice usage (1/2/3 voices active)
- Filter usage (frames with non-zero filter values)
- File size (bytes)

Output saved to: `test_candidates_analysis.txt`

---

## Notes

1. **Filter Usage**: ALL Laxity files have 100% filter usage, so any file is good for filter testing
2. **Voice 3 Coverage**: 81% of files use 3 voices, so finding 3-voice files is easy
3. **Size Extremes**: Range from 400 bytes to 34KB provides excellent edge case coverage
4. **File Availability**: All files are already in the `Laxity/` directory

---

## Success Criteria

- ✅ Test files cover 1-voice, 2-voice, and 3-voice scenarios
- ✅ Test files cover size range from <1KB to >30KB
- ✅ Test files all include filter usage (100% coverage)
- ✅ Test suite validates edge cases (minimal files, maximal files)
- ✅ Performance testing includes large complex files

---

**End of Test File Recommendations**
