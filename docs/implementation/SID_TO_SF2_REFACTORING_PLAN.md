# sid_to_sf2.py Refactoring Plan

**Goal**: Separate CLI interface from business logic to enable unit testing and coverage tracking

**Status**: APPROVED - Ready for implementation
**Created**: 2025-12-27
**Target**: Phase 1 Test Coverage Initiative

---

## Executive Summary

### Current Problems
1. **Zero coverage tracking** - scripts/sid_to_sf2.py is a script file, coverage tools cannot track it (0.00%)
2. **Difficult unit testing** - 7/24 tests fail due to integration complexity and Mock object issues
3. **Mixed concerns** - CLI code intertwined with business logic (1841 lines in one script)
4. **Violates project structure** - Business logic should be in sidm2/ module, not scripts/

### Proposed Solution
**Create sidm2/conversion_pipeline.py** - New module containing all business logic
**Refactor scripts/sid_to_sf2.py** - Thin CLI wrapper (< 200 lines) that imports from module

### Expected Outcomes
✅ Coverage tracking works (target: > 0%, ideally 50%+)
✅ Tests pass at current or better rate (17/24 → 20+/24)
✅ Better separation of concerns
✅ Easier to test and maintain
✅ No change to CLI behavior (backward compatible)

---

## Architecture Analysis

### Current Structure (scripts/sid_to_sf2.py - 1841 lines)

**CLI Functions** (~200 lines):
- `main()` - Entry point with argparse
- Argument parsing setup
- Logger initialization
- Output formatting for CLI

**Business Logic Functions** (~1600 lines):
- `detect_player_type(filepath)` - Subprocess call to player-id.exe
- `print_success_summary(...)` - Format conversion results
- `analyze_sid_file(...)` - Parse and analyze SID file
- `convert_laxity_to_sf2(...)` - Laxity conversion orchestrator
- `convert_galway_to_sf2(...)` - Galway conversion orchestrator
- `convert_sid_to_sf2(...)` - Main conversion orchestrator
- `convert_sid_to_both_drivers(...)` - Dual driver conversion
- `get_default_config()` - Default configuration

**Dependencies**:
```python
from sidm2.sid_parser import SIDParser
from sidm2.laxity_converter import LaxityConverter
from sidm2.sf2_writer import SF2Writer
from sidm2.driver_selector import DriverSelector
from sidm2.config import ConversionConfig
# ... many more
```

### Target Structure

**sidm2/conversion_pipeline.py** (NEW - ~1600 lines):
```python
"""SID to SF2 conversion pipeline - Business logic module.

This module contains all conversion orchestration and analysis logic,
separated from CLI interface for better testability.

Functions:
    detect_player_type() - Identify SID player format
    analyze_sid_file() - Parse and analyze SID file
    convert_laxity_to_sf2() - Laxity conversion
    convert_galway_to_sf2() - Galway conversion
    convert_sid_to_sf2() - Main conversion
    convert_sid_to_both_drivers() - Dual conversion
    print_success_summary() - Format results
    get_default_config() - Configuration
"""
```

**scripts/sid_to_sf2.py** (REFACTORED - ~200 lines):
```python
"""SID to SF2 converter - Command-line interface.

Thin CLI wrapper that imports business logic from sidm2.conversion_pipeline.
"""
from sidm2.conversion_pipeline import (
    convert_sid_to_sf2,
    convert_sid_to_both_drivers,
    print_success_summary,
    get_default_config,
)

def main():
    """CLI entry point."""
    # Argparse setup
    # Call conversion_pipeline functions
    # Handle output
```

---

## Implementation Plan

### Phase 1: Preparation & Analysis (30 min)

**Step 1.1**: Read scripts/sid_to_sf2.py completely
- [ ] Identify exact line ranges for each function
- [ ] List all imports and dependencies
- [ ] Note global variables/constants
- [ ] Identify any CLI-specific code in business functions

**Step 1.2**: Analyze test dependencies
- [ ] List all functions tested in test_sid_to_sf2_script.py
- [ ] Note all patch decorators and their paths
- [ ] Identify functions that will need import path updates

**Step 1.3**: Check for circular import risks
- [ ] Verify no sidm2/* modules import from scripts/
- [ ] Confirm safe to add new sidm2/conversion_pipeline.py
- [ ] Plan import order

**Deliverable**: Analysis document with line ranges and import map

### Phase 2: Create New Module (45 min)

**Step 2.1**: Create sidm2/conversion_pipeline.py
```bash
# Create new file
touch sidm2/conversion_pipeline.py
```

**Step 2.2**: Copy module header
- [ ] Module docstring (comprehensive)
- [ ] Copyright/license if applicable
- [ ] Import statements (all dependencies)

**Step 2.3**: Extract business logic functions (in order)
1. [ ] `detect_player_type(filepath: str) -> str`
2. [ ] `print_success_summary(...) -> None`
3. [ ] `analyze_sid_file(...) -> ExtractedData`
4. [ ] `convert_laxity_to_sf2(...) -> bool`
5. [ ] `convert_galway_to_sf2(...) -> bool`
6. [ ] `convert_sid_to_sf2(...) -> None`
7. [ ] `convert_sid_to_both_drivers(...) -> Dict`
8. [ ] `get_default_config() -> ConversionConfig`

**Step 2.4**: Copy supporting code
- [ ] Constants (LAXITY_CONVERTER_AVAILABLE, etc.)
- [ ] Type hints and imports
- [ ] Helper functions if any

**Step 2.5**: Add module-level features
- [ ] `__all__` export list
- [ ] Module-level logger setup
- [ ] Version/author metadata if needed

**Deliverable**: sidm2/conversion_pipeline.py with all business logic

### Phase 3: Refactor CLI Script (30 min)

**Step 3.1**: Backup original
```bash
cp scripts/sid_to_sf2.py scripts/sid_to_sf2.py.backup
```

**Step 3.2**: Simplify scripts/sid_to_sf2.py
- [ ] Keep only imports needed for CLI
- [ ] Add import from sidm2.conversion_pipeline
- [ ] Remove all business logic functions (now imported)
- [ ] Update main() to call imported functions
- [ ] Verify < 250 lines (target < 200)

**Step 3.3**: Update function calls in main()
```python
# Before:
result = convert_sid_to_sf2(input_path, output_path)

# After (same - but imported):
from sidm2.conversion_pipeline import convert_sid_to_sf2
result = convert_sid_to_sf2(input_path, output_path)
```

**Step 3.4**: Test CLI still works
```bash
# Quick smoke test
python scripts/sid_to_sf2.py --help
```

**Deliverable**: Simplified scripts/sid_to_sf2.py (thin wrapper)

### Phase 4: Update Tests (45 min)

**Step 4.1**: Update test imports
Change in pyscript/test_sid_to_sf2_script.py:
```python
# OLD:
script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts')
sys.path.insert(0, script_dir)
from sid_to_sf2 import detect_player_type, ...

# NEW:
from sidm2.conversion_pipeline import (
    detect_player_type,
    print_success_summary,
    analyze_sid_file,
    convert_laxity_to_sf2,
    convert_galway_to_sf2,
    convert_sid_to_sf2,
)
```

**Step 4.2**: Update all patch decorators
```python
# OLD:
@patch('sid_to_sf2.SIDParser')
@patch('sid_to_sf2.LaxityConverter')
@patch('sid_to_sf2.DriverSelector')

# NEW:
@patch('sidm2.conversion_pipeline.SIDParser')
@patch('sidm2.conversion_pipeline.LaxityConverter')
@patch('sidm2.conversion_pipeline.DriverSelector')
```

Use search & replace:
```python
# Find: @patch\('sid_to_sf2\.
# Replace: @patch('sidm2.conversion_pipeline.
```

**Step 4.3**: Run tests
```bash
python -m pytest pyscript/test_sid_to_sf2_script.py -v
```
- [ ] Count passing/failing
- [ ] Note any new errors

**Step 4.4**: Fix import-related failures
- [ ] Missing imports
- [ ] Incorrect patch paths
- [ ] Module not found errors

**Deliverable**: Updated tests with correct import paths

### Phase 5: Verify Coverage (15 min)

**Step 5.1**: Run coverage test
```bash
python -m pytest pyscript/test_sid_to_sf2_script.py \
  --cov=sidm2.conversion_pipeline \
  --cov-report=term-missing
```

**Step 5.2**: Verify non-zero coverage
- [ ] Coverage should be > 0% (NOT 0.00%)
- [ ] Target: 30-50% or higher
- [ ] Identify uncovered lines

**Step 5.3**: Document baseline coverage
```
Expected output:
----------- coverage: -----------
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
sidm2/conversion_pipeline.py       XXX    YYY    ZZ%    lines...
---------------------------------------------------------------
TOTAL                              XXX    YYY    ZZ%
```

**Deliverable**: Coverage report showing measurable coverage

### Phase 6: Integration Testing (20 min)

**Step 6.1**: Test real CLI usage
```bash
# Test basic conversion
python scripts/sid_to_sf2.py test.sid output.sf2

# Test with driver selection
python scripts/sid_to_sf2.py test.sid output.sf2 --driver laxity

# Test quiet mode
python scripts/sid_to_sf2.py test.sid output.sf2 -q

# Test help
python scripts/sid_to_sf2.py --help
```

**Step 6.2**: Verify batch files still work
```bash
sid-to-sf2.bat test.sid output.sf2
```

**Step 6.3**: Test error handling
```bash
# Non-existent file
python scripts/sid_to_sf2.py nonexistent.sid output.sf2

# Invalid format
python scripts/sid_to_sf2.py invalid.txt output.sf2
```

**Deliverable**: Confirmation that CLI behavior is unchanged

### Phase 7: Full Test Suite (10 min)

**Step 7.1**: Run complete test suite
```bash
test-all.bat
```

**Step 7.2**: Check for regressions
- [ ] All previous tests still passing?
- [ ] No new failures introduced?
- [ ] Total test count unchanged?

**Step 7.3**: Fix any regressions
- [ ] Identify root cause
- [ ] Apply fixes
- [ ] Re-run tests

**Deliverable**: test-all.bat passes with no regressions

### Phase 8: Documentation (15 min)

**Step 8.1**: Update CLAUDE.md
```markdown
## Project Structure
- sidm2/ - Core package
  - conversion_pipeline.py - Conversion orchestration (NEW)
  - laxity_converter.py - Laxity conversion
  - ...
```

**Step 8.2**: Update README.md
- [ ] Mention new module if architecture section exists
- [ ] Update any references to script structure

**Step 8.3**: Update architecture docs
- [ ] docs/ARCHITECTURE.md - Add conversion_pipeline
- [ ] docs/COMPONENTS_REFERENCE.md - Document new module API

**Step 8.4**: Create migration notes
- [ ] Document import path changes for developers
- [ ] Note backward compatibility maintained

**Deliverable**: Updated documentation

### Phase 9: Commit (10 min)

**Step 9.1**: Review all changes
```bash
git status
git diff sidm2/conversion_pipeline.py
git diff scripts/sid_to_sf2.py
git diff pyscript/test_sid_to_sf2_script.py
```

**Step 9.2**: Commit atomically
```bash
git add sidm2/conversion_pipeline.py
git add scripts/sid_to_sf2.py
git add pyscript/test_sid_to_sf2_script.py
git add docs/

git commit -m "refactor: Separate CLI from business logic in sid_to_sf2

Extract all conversion business logic to new sidm2/conversion_pipeline.py
module, reducing scripts/sid_to_sf2.py to thin CLI wrapper.

BREAKING CHANGE for test imports (internal only):
- Tests now import from sidm2.conversion_pipeline instead of sid_to_sf2
- No user-facing changes - CLI behavior identical

Benefits:
- Enable coverage tracking (was 0.00%, now measurable)
- Better separation of concerns
- Easier unit testing
- Follows project structure (business logic in sidm2/)

Changes:
- NEW: sidm2/conversion_pipeline.py (~1600 lines)
  * detect_player_type()
  * analyze_sid_file()
  * convert_laxity_to_sf2()
  * convert_galway_to_sf2()
  * convert_sid_to_sf2()
  * convert_sid_to_both_drivers()
  * print_success_summary()
  * get_default_config()

- REFACTOR: scripts/sid_to_sf2.py (~200 lines)
  * Now thin CLI wrapper
  * Imports from conversion_pipeline
  * main() and argparse only

- UPDATE: pyscript/test_sid_to_sf2_script.py
  * Import from sidm2.conversion_pipeline
  * Update patch decorators
  * Tests: 17/24 passing → ZZ/24 passing
  * Coverage: 0.00% → XX.X%

- UPDATE: docs/
  * CLAUDE.md - New module structure
  * README.md - Updated architecture
  * ARCHITECTURE.md - conversion_pipeline docs

Tested:
- Unit tests: XX/24 passing (YY% coverage)
- Integration: CLI behavior verified unchanged
- Full suite: test-all.bat passes

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Deliverable**: Clean atomic commit

---

## Risk Mitigation

### Risk 1: Breaking CLI Behavior
**Impact**: High - Users depend on CLI
**Probability**: Low - We're only moving code, not changing it
**Mitigation**:
- Keep scripts/sid_to_sf2.py as entry point
- Thoroughly test CLI before committing
- Maintain exact same argument parsing

**Test Plan**:
- [ ] Run all CLI examples from README
- [ ] Test all batch file wrappers
- [ ] Verify error messages unchanged
- [ ] Check exit codes

### Risk 2: Import Errors / Circular Imports
**Impact**: High - Code won't run
**Probability**: Low - sidm2/ modules don't import from scripts/
**Mitigation**:
- Verify import graph before starting
- Test imports immediately after creating module
- Use try/except during development

**Test Plan**:
- [ ] `python -c "import sidm2.conversion_pipeline"`
- [ ] Check for circular import warnings
- [ ] Run python with `-v` to see import order

### Risk 3: Test Failures Increase
**Impact**: Medium - Need to fix before committing
**Probability**: Medium - Import path changes are tricky
**Mitigation**:
- Update imports incrementally
- Run tests after each change
- Have rollback plan (git stash)

**Test Plan**:
- [ ] Run tests after updating imports
- [ ] Run tests after updating patches
- [ ] Track test count at each step

### Risk 4: Coverage Still Zero
**Impact**: Medium - Main goal not achieved
**Probability**: Low - Module files are trackable
**Mitigation**:
- Test coverage on simple module first
- Verify pytest-cov works with sidm2/
- Check coverage config in pytest.ini

**Test Plan**:
- [ ] Test coverage on sidm2/laxity_parser.py first
- [ ] Verify coverage reporting works
- [ ] Check module is being imported

### Risk 5: Merge Conflicts
**Impact**: Low - This is new work
**Probability**: Low - Working on feature branch
**Mitigation**:
- Work in isolation
- Complete in single session
- Commit atomically

---

## Success Criteria

### Must Have ✅
- [ ] sidm2/conversion_pipeline.py exists with all business logic
- [ ] scripts/sid_to_sf2.py is < 250 lines
- [ ] Tests pass at ≥ 17/24 (maintain or improve)
- [ ] Coverage > 0% (measurable)
- [ ] CLI behavior unchanged (backward compatible)
- [ ] test-all.bat passes
- [ ] Documentation updated

### Should Have 🎯
- [ ] Coverage ≥ 30%
- [ ] Tests pass at ≥ 20/24
- [ ] scripts/sid_to_sf2.py < 200 lines
- [ ] No new linting errors
- [ ] Clean git history

### Nice to Have 🌟
- [ ] Coverage ≥ 50%
- [ ] Tests pass at 24/24
- [ ] Improved error messages
- [ ] Additional test cases for uncovered code

---

## Timeline Estimate

| Phase | Duration | Tasks |
|-------|----------|-------|
| 1. Preparation | 30 min | Analysis, planning |
| 2. Create Module | 45 min | Extract business logic |
| 3. Refactor CLI | 30 min | Thin wrapper |
| 4. Update Tests | 45 min | Import paths, patches |
| 5. Verify Coverage | 15 min | Run coverage tests |
| 6. Integration Test | 20 min | CLI behavior verification |
| 7. Full Test Suite | 10 min | Regression check |
| 8. Documentation | 15 min | Update docs |
| 9. Commit | 10 min | Git commit |
| **TOTAL** | **3h 40min** | **9 phases** |

**Buffer**: +30 min for unexpected issues
**Total with buffer**: ~4 hours

---

## Rollback Plan

If anything goes wrong:

**Option 1: Git Reset** (if uncommitted)
```bash
git checkout scripts/sid_to_sf2.py
git checkout pyscript/test_sid_to_sf2_script.py
rm sidm2/conversion_pipeline.py
```

**Option 2: Git Revert** (if committed)
```bash
git revert HEAD
```

**Option 3: Git Stash** (work in progress)
```bash
git stash save "WIP: sid_to_sf2 refactoring"
```

---

## Next Steps After Completion

Once refactoring is complete and tests are passing:

1. **Fix remaining 7 test failures** - Now easier with module structure
2. **Increase coverage to 50%+** - Add tests for uncovered code
3. **Extract more functions** - Further modularization if needed
4. **Complete Phase 1** - Move to other modules
5. **Document patterns** - Use as template for future refactoring

---

## References

- **Current test results**: 17/24 passing (70.8%), 0.00% coverage
- **Project structure rules**: docs/guides/ROOT_FOLDER_RULES.md
- **Phase 1 initiative**: GitHub Issue #4
- **SIDM2 architecture**: docs/ARCHITECTURE.md

---

**Status**: APPROVED - Ready for implementation
**Assigned**: Claude Sonnet 4.5
**Priority**: High (Phase 1 blocker)
**Complexity**: Medium-High

---

_Plan created: 2025-12-27_
_Estimated completion: Same day (4 hours)_
