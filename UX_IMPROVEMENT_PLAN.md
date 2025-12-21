# User Experience Improvement Plan

**Focus**: Improve error messages and user guidance
**Effort**: 6-8 hours
**Priority**: P2 (High value)
**Date**: 2025-12-21

---

## Current State Analysis

### Error Message Audit Results

**Files with error handling**:
- scripts/: 15 files
- sidm2/: 19 files
- Total: 34 files with error handling

### Common Error Patterns Found

#### 1. Generic Errors (No Context)
```python
# Current
raise FileNotFoundError(f"Input file not found: {input_path}")

# Problem: User doesn't know what to do next
```

#### 2. Technical Errors (No User-Friendly Explanation)
```python
# Current
raise RuntimeError("Laxity converter not available. Ensure sidm2.laxity_converter is installed.")

# Problem: User doesn't know HOW to install it
```

#### 3. Missing Troubleshooting Hints
```python
# Current
raise ValueError(f"Invalid or corrupted SID file: {e}")

# Problem: User doesn't know WHY it's invalid or what to try
```

#### 4. No Documentation Links
```python
# Current
raise IOError(f"Output file already exists (use --overwrite or config.output.overwrite=true): {output_path}")

# Problem: User doesn't know which option to use or where to learn more
```

---

## Error Categories

### Category 1: File Not Found Errors
**Current issues**:
- No suggestions for common typos
- No check for similar filenames
- No guidance on file paths

**Examples**:
- Input SID file not found
- Template file not found
- Configuration file not found

### Category 2: Invalid Input Errors
**Current issues**:
- No explanation of WHY input is invalid
- No common causes listed
- No validation guidance

**Examples**:
- Invalid SID file format
- Corrupted file
- Unsupported player format

### Category 3: Missing Dependencies Errors
**Current issues**:
- No installation instructions
- No version requirements
- No troubleshooting for failed imports

**Examples**:
- Laxity converter not available
- External tools missing
- Python modules not installed

### Category 4: Permission/Access Errors
**Current issues**:
- No permission troubleshooting
- No Windows vs Linux guidance
- No alternative solutions

**Examples**:
- Cannot create output directory
- Cannot write output file
- Permission denied reading file

### Category 5: Configuration Errors
**Current issues**:
- No examples of correct configuration
- No validation of config values
- No defaults suggested

**Examples**:
- Invalid driver type
- Unknown configuration option
- Conflicting settings

### Category 6: Conversion Errors
**Current issues**:
- No diagnosis of root cause
- No partial success handling
- No recovery suggestions

**Examples**:
- Conversion failed
- Extraction failed
- Packing failed

---

## Improved Error Message Format

### Template Structure

```
ERROR: [Clear Error Title]

What happened:
  [Brief explanation of what went wrong]

Why this happened:
  [Common causes, root cause if known]

How to fix:
  1. [Primary solution]
  2. [Alternative solution]
  3. [Fallback solution]

Need help?
  → Documentation: [link to relevant docs]
  → Troubleshooting: [link to troubleshooting guide]
  → GitHub Issues: https://github.com/MichaelTroelsen/SIDM2conv/issues
```

### Example: File Not Found

**Before**:
```
FileNotFoundError: Input file not found: SID/song.sid
```

**After**:
```
ERROR: Input SID File Not Found

What happened:
  Could not find the SID file: SID/song.sid

Why this happened:
  • File path may be incorrect
  • File may have been moved or deleted
  • Wrong current directory

How to fix:
  1. Check the file path: python scripts/sid_to_sf2.py --help
  2. Use absolute path: python scripts/sid_to_sf2.py C:/full/path/to/song.sid
  3. List files: ls SID/ (or dir SID\ on Windows)

Similar files found:
  • SID/song2.sid
  • SID/songs.sid

Need help?
  → Quick Start: docs/guides/LAXITY_DRIVER_USER_GUIDE.md
  → Issues: https://github.com/MichaelTroelsen/SIDM2conv/issues
```

### Example: Invalid SID File

**Before**:
```
InvalidSIDFileError: Invalid SID file magic: ABCD
```

**After**:
```
ERROR: Invalid SID File Format

What happened:
  The file is not a valid SID file (found magic bytes: ABCD)

Why this happened:
  • File is not a SID file (wrong format)
  • File is corrupted or incomplete
  • File downloaded incorrectly

Valid SID file formats:
  ✓ PSID (PlaySID format)
  ✓ RSID (RealSID format)

How to fix:
  1. Check file type: file song.sid
  2. Re-download from source (HVSC, csdb.dk)
  3. Use player-id tool: tools/player-id.exe song.sid

Need help?
  → SID Format Spec: docs/reference/format-specification.md
  → Supported Formats: README.md#supported-formats
  → Issues: https://github.com/MichaelTroelsen/SIDM2conv/issues
```

### Example: Missing Dependency

**Before**:
```
RuntimeError: Laxity converter not available. Ensure sidm2.laxity_converter is installed.
```

**After**:
```
ERROR: Laxity Driver Not Available

What happened:
  The Laxity driver module could not be loaded

Why this happened:
  • Module sidm2.laxity_converter not found
  • Installation incomplete
  • Python path not configured

How to fix:
  1. Check installation: python -c "import sidm2.laxity_converter"
  2. Reinstall package: pip install -e .
  3. Verify files exist: ls sidm2/laxity_converter.py

Alternative:
  Use standard drivers instead:
    python scripts/sid_to_sf2.py song.sid output.sf2 --driver driver11

Note: Standard drivers have 1-8% accuracy for Laxity files
      (vs 99.93% with Laxity driver)

Need help?
  → Installation Guide: README.md#installation
  → Driver Reference: docs/reference/DRIVER_REFERENCE.md
  → Issues: https://github.com/MichaelTroelsen/SIDM2conv/issues
```

---

## Implementation Plan

### Phase 1: Create Error Helper Module (2 hours)

**Create `sidm2/errors.py`**:
- Custom exception classes with rich formatting
- Helper functions for common error patterns
- Documentation link generator
- Similar file finder for FileNotFound errors

**Classes**:
```python
class SIDMError(Exception):
    """Base exception with rich formatting"""

class FileNotFoundError(SIDMError):
    """File not found with suggestions"""

class InvalidInputError(SIDMError):
    """Invalid input with validation help"""

class MissingDependencyError(SIDMError):
    """Missing dependency with install instructions"""

class ConversionError(SIDMError):
    """Conversion failed with diagnosis"""
```

**Features**:
- Automatic documentation link generation
- Colorized terminal output (optional)
- Structured error data for logging
- User-friendly formatting

### Phase 2: Update Core Modules (3 hours)

**Priority files to update**:
1. `scripts/sid_to_sf2.py` - Main converter (highest priority)
2. `sidm2/sid_parser.py` - SID file parsing
3. `sidm2/sf2_writer.py` - SF2 writing
4. `sidm2/sf2_packer.py` - Packing
5. `scripts/sf2_to_sid.py` - Export

**Update pattern**:
```python
# Before
if not os.path.exists(input_path):
    raise FileNotFoundError(f"Input file not found: {input_path}")

# After
from sidm2.errors import FileNotFoundError as SIDMFileNotFoundError

if not os.path.exists(input_path):
    raise SIDMFileNotFoundError(
        path=input_path,
        context="input SID file",
        suggestions=[
            "Check file path with --help",
            "Use absolute path",
            "List files: ls SID/"
        ],
        docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md"
    )
```

### Phase 3: Add Troubleshooting Guide (1 hour)

**Create `docs/guides/TROUBLESHOOTING.md`**:
- Common errors and solutions
- Platform-specific issues (Windows/Mac/Linux)
- Debug mode instructions
- FAQ section
- Links from error messages

**Sections**:
1. File Not Found Issues
2. Invalid SID Files
3. Missing Dependencies
4. Conversion Failures
5. Permission Problems
6. Performance Issues

### Phase 4: Update Tests (1 hour)

**Test error messages**:
- Verify error message format
- Test documentation links
- Validate suggestions
- Check colorization

**Add tests**:
- `scripts/test_error_messages.py`
- Test each error category
- Verify helpful output

### Phase 5: Documentation (1 hour)

**Update existing docs**:
- README.md - Add troubleshooting section
- CONTRIBUTING.md - Error message guidelines
- Each guide - Add common errors section

**Create new docs**:
- docs/guides/TROUBLESHOOTING.md
- Error message style guide

---

## Success Criteria

### User Experience

✅ Users can self-resolve 80% of common issues
✅ Error messages include actionable suggestions
✅ Documentation links are provided
✅ Alternative solutions are suggested

### Technical Quality

✅ Consistent error format across codebase
✅ All errors include troubleshooting hints
✅ Error classes properly categorized
✅ Tests validate error output

### Metrics

**Measure**:
- GitHub issues for "how do I fix..." questions
- User support requests
- Documentation page views

**Target**:
- 50% reduction in support questions
- 80% of errors include documentation links
- 100% of file errors suggest alternatives

---

## Quick Wins

### Immediate Improvements (30 min each)

1. **Add similar file finder** to FileNotFoundError
2. **Add driver comparison** to missing dependency errors
3. **Add validation examples** to invalid input errors
4. **Add platform detection** to permission errors
5. **Add config examples** to configuration errors

---

## Example Implementation

### sidm2/errors.py (Partial)

```python
"""
User-friendly error messages with troubleshooting guidance.

This module provides enhanced exception classes that include:
- Clear error explanations
- Common causes
- Step-by-step solutions
- Documentation links
- Alternative approaches
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
import difflib

class SIDMError(Exception):
    """Base exception for SIDM2 converter with rich formatting."""

    def __init__(
        self,
        message: str,
        what_happened: Optional[str] = None,
        why_happened: Optional[List[str]] = None,
        how_to_fix: Optional[List[str]] = None,
        docs_link: Optional[str] = None,
        alternatives: Optional[List[str]] = None
    ):
        self.message = message
        self.what_happened = what_happened
        self.why_happened = why_happened or []
        self.how_to_fix = how_to_fix or []
        self.docs_link = docs_link
        self.alternatives = alternatives or []
        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format error message with troubleshooting guidance."""
        lines = [f"\nERROR: {self.message}\n"]

        if self.what_happened:
            lines.append(f"What happened:")
            lines.append(f"  {self.what_happened}\n")

        if self.why_happened:
            lines.append(f"Why this happened:")
            for reason in self.why_happened:
                lines.append(f"  • {reason}")
            lines.append("")

        if self.how_to_fix:
            lines.append(f"How to fix:")
            for i, solution in enumerate(self.how_to_fix, 1):
                lines.append(f"  {i}. {solution}")
            lines.append("")

        if self.alternatives:
            lines.append(f"Alternative:")
            for alt in self.alternatives:
                lines.append(f"  {alt}")
            lines.append("")

        if self.docs_link:
            repo_url = "https://github.com/MichaelTroelsen/SIDM2conv"
            lines.append(f"Need help?")
            lines.append(f"  → Documentation: {self.docs_link}")
            lines.append(f"  → Issues: {repo_url}/issues\n")

        return "\n".join(lines)


class FileNotFoundError(SIDMError):
    """File not found error with suggestions for similar files."""

    def __init__(
        self,
        path: str,
        context: str = "file",
        suggestions: Optional[List[str]] = None,
        docs_link: Optional[str] = None
    ):
        # Find similar files
        similar = self._find_similar_files(path)

        what_happened = f"Could not find the {context}: {path}"

        why_happened = [
            "File path may be incorrect",
            "File may have been moved or deleted",
            "Wrong current directory"
        ]

        how_to_fix = suggestions or [
            "Check the file path",
            f"Use absolute path: {os.path.abspath(path)}",
            f"List files in directory"
        ]

        alternatives = None
        if similar:
            alternatives = ["Similar files found:"] + [f"  • {f}" for f in similar[:5]]

        super().__init__(
            message=f"{context.title()} Not Found",
            what_happened=what_happened,
            why_happened=why_happened,
            how_to_fix=how_to_fix,
            docs_link=docs_link or "README.md#usage",
            alternatives=alternatives
        )

    @staticmethod
    def _find_similar_files(path: str, threshold: float = 0.6) -> List[str]:
        """Find files with similar names in the same directory."""
        try:
            directory = os.path.dirname(path) or "."
            filename = os.path.basename(path)

            if not os.path.exists(directory):
                return []

            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

            # Find similar filenames using difflib
            matches = difflib.get_close_matches(filename, files, n=5, cutoff=threshold)

            return [os.path.join(directory, m) for m in matches]
        except Exception:
            return []
```

---

## Timeline

**Total effort**: 6-8 hours

| Phase | Time | Status |
|-------|------|--------|
| Phase 1: Error Helper Module | 2 hours | Pending |
| Phase 2: Update Core Modules | 3 hours | Pending |
| Phase 3: Troubleshooting Guide | 1 hour | Pending |
| Phase 4: Update Tests | 1 hour | Pending |
| Phase 5: Documentation | 1 hour | Pending |

**Start**: After approval
**Target completion**: Same day (if focused session)

---

## Next Steps

1. **Get approval** for implementation plan
2. **Create sidm2/errors.py** module
3. **Update sid_to_sf2.py** as pilot implementation
4. **Test with real error scenarios**
5. **Rollout to remaining modules**
6. **Create troubleshooting guide**
7. **Update documentation**

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

**Status**: Ready for implementation
**Priority**: P2 (High value, 6-8 hours)
**Impact**: Immediate user experience improvement
