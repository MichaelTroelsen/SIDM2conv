# Error Message Style Guide

Guidelines for writing user-friendly error messages in the SIDM2 project.

**Version**: v2.5.0
**Last Updated**: 2025-12-21
**For**: Contributors and developers

---

## Overview

Good error messages help users solve problems themselves, reducing support burden and improving user experience. This guide provides standards for all error messages in the SIDM2 project.

### Goals

1. **Self-Service**: 80% of users should be able to resolve errors without help
2. **Clarity**: Users should understand what went wrong and why
3. **Actionability**: Every error should include specific steps to fix it
4. **Consistency**: All errors follow the same structure

---

## Error Message Structure

All error messages in SIDM2 follow this standard structure:

```
ERROR: [Clear Error Title]

What happened:
  [Brief explanation of what went wrong]

Why this happened:
  • [Common cause 1]
  • [Common cause 2]
  • [Common cause 3]

How to fix:
  1. [Primary solution with specific command]
  2. [Alternative solution]
  3. [Fallback solution]

Alternative:  (optional)
  [Alternative approach if fixes don't work]

Need help?
  * Documentation: [link to specific guide section]
  * Issues: https://github.com/MichaelTroelsen/SIDM2conv/issues
  * README: https://github.com/MichaelTroelsen/SIDM2conv#readme

Technical details:  (optional)
  [Debugging information for advanced users]
```

---

## Using Error Classes

### Available Error Types

The `sidm2.errors` module provides 6 specialized error classes:

| Error Class | Use For | Example |
|-------------|---------|---------|
| `FileNotFoundError` | Missing files/directories | Input SID file not found |
| `InvalidInputError` | Invalid/corrupted data | Corrupted SID file format |
| `MissingDependencyError` | Missing modules/tools | Laxity converter not installed |
| `PermissionError` | Access denied issues | Cannot write output file |
| `ConfigurationError` | Invalid settings | Unknown driver type |
| `ConversionError` | Conversion failures | Table extraction failed |

### Basic Usage

```python
from sidm2 import errors

# File not found
if not os.path.exists(input_path):
    raise errors.FileNotFoundError(
        path=input_path,
        context="input SID file",
        suggestions=[
            "Check the file path: python scripts/sid_to_sf2.py --help",
            "Use absolute path instead of relative",
            "List files: ls SID/"
        ],
        docs_link="guides/TROUBLESHOOTING.md#1-file-not-found-issues"
    )

# Invalid input
if magic_bytes != b'PSID':
    raise errors.InvalidInputError(
        input_type="SID file",
        value=filepath,
        expected="PSID or RSID format",
        got=f"Unknown magic bytes: {magic_bytes.hex()}",
        suggestions=[
            "Verify file is a valid SID file",
            "Re-download from HVSC or csdb.dk",
            "Check file size (should be > 124 bytes)"
        ]
    )

# Missing dependency
if not LAXITY_CONVERTER_AVAILABLE:
    raise errors.MissingDependencyError(
        dependency="sidm2.laxity_converter",
        install_command="pip install -e .",
        alternatives=[
            "Use standard drivers instead:",
            "  python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11"
        ]
    )

# Configuration error
if driver not in available_drivers:
    raise errors.ConfigurationError(
        setting="driver",
        value=driver,
        valid_options=available_drivers,
        example="python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity"
    )

# Conversion error
try:
    extract_tables(sid_data)
except Exception as e:
    raise errors.ConversionError(
        stage="table extraction",
        reason=str(e),
        input_file=input_path,
        suggestions=[
            "Check player type: tools/player-id.exe input.sid",
            "Try different driver: --driver driver11",
            "Enable verbose logging: --verbose"
        ]
    )

# Permission error
try:
    with open(output_path, 'wb') as f:
        f.write(data)
except OSError:
    raise errors.PermissionError(
        operation="write",
        path=output_path
    )
```

### Convenience Functions

For quick error raising:

```python
from sidm2.errors import file_not_found, invalid_input

# Quick file not found
if not os.path.exists(path):
    raise file_not_found(path, "SID file")

# Quick invalid input
if not validate(value):
    raise invalid_input("configuration", value, expected="number", got="string")
```

---

## Writing Guidelines

### 1. Error Titles

**DO**:
- Use clear, specific titles
- Use title case or sentence case consistently
- Be concise (3-6 words)

```python
# Good
"Input SID File Not Found"
"Invalid Driver Configuration"
"Laxity Converter Not Available"

# Bad
"Error"
"Something went wrong"
"File not found error occurred while trying to read"
```

**DON'T**:
- Use generic titles
- Include technical jargon
- Make titles too long

### 2. What Happened Section

**DO**:
- State exactly what failed
- Include the problematic value/path
- Be specific and factual

```python
# Good
what_happened = "Could not find the input SID file: SID/song.sid"
what_happened = "The driver 'invalid' is not recognized"
what_happened = "Permission denied while trying to write: /protected/output.sf2"

# Bad
what_happened = "File error"
what_happened = "Something is wrong with your configuration"
what_happened = "An unexpected error occurred"
```

**DON'T**:
- Be vague or generic
- Blame the user
- Use technical error codes alone

### 3. Why This Happened Section

**DO**:
- List 3-5 common causes
- Order from most to least common
- Use simple, clear language

```python
# Good
why_happened = [
    "File path may be incorrect or contains typos",
    "File may have been moved or deleted",
    "Working directory may be wrong",
    "Using relative path when absolute is needed"
]

# Bad
why_happened = [
    "ENOENT error code 2",
    "Filesystem node does not exist in directory tree",
    "Path resolution failed during syscall"
]
```

**DON'T**:
- Use technical jargon
- List rare edge cases
- Include more than 5 items

### 4. How to Fix Section

**DO**:
- Provide 2-4 specific, actionable steps
- Include actual commands to run
- Order from easiest to most complex
- Number the steps (1, 2, 3...)

```python
# Good
how_to_fix = [
    "Check the file path: python scripts/sid_to_sf2.py --help",
    "Use absolute path: python scripts/sid_to_sf2.py C:\\full\\path\\to\\file.sid output.sf2",
    "List files in directory: dir SID\\ (or ls SID/ on Mac/Linux)"
]

# Bad
how_to_fix = [
    "Fix the path",
    "Try again",
    "Check your configuration",
    "Read the documentation",
    "Search online for solutions"
]
```

**DON'T**:
- Be vague ("check your settings")
- Provide too many options (>4)
- Omit actual commands

### 5. Alternative Solutions

**DO**:
- Suggest workarounds when available
- Show performance/accuracy trade-offs
- Provide fallback methods

```python
# Good
alternatives = [
    "Use standard drivers instead:",
    "  python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11",
    "",
    "Note: Standard drivers have 1-8% accuracy for Laxity files",
    "      (vs 99.93% with Laxity driver)"
]

# Bad
alternatives = [
    "Try something else",
    "Use a different approach"
]
```

**DON'T**:
- Leave alternatives vague
- Omit trade-off information
- Suggest alternatives without examples

### 6. Documentation Links

**DO**:
- Link to specific section of docs
- Use troubleshooting guide for common issues
- Provide multiple help sources

```python
# Good - Specific section
docs_link = "guides/TROUBLESHOOTING.md#1-file-not-found-issues"
docs_link = "guides/TROUBLESHOOTING.md#3-missing-dependencies"

# Good - General guide
docs_link = "guides/LAXITY_DRIVER_USER_GUIDE.md#troubleshooting"

# Bad - No context
docs_link = "README.md"
docs_link = "docs/"
```

**DON'T**:
- Link to entire README
- Use broken/outdated links
- Omit documentation links

### 7. Technical Details

**DO**:
- Include debug information
- Show full paths checked
- Add platform/version info

```python
# Good
technical_details = f"Full path checked: {os.path.abspath(path)}"
technical_details = f"Platform: {sys.platform}, Python: {sys.version}"
technical_details = f"Stage: {stage}, Reason: {reason}"

# Bad
technical_details = None  # Omitting helpful info
technical_details = str(e)  # Just exception string
```

**DON'T**:
- Include sensitive data (passwords, API keys)
- Show raw stack traces (use --verbose for that)
- Omit context information

---

## Best Practices

### Use Appropriate Error Type

Choose the most specific error class:

```python
# File operations
if not os.path.exists(path):
    raise errors.FileNotFoundError(...)  # NOT generic Exception

# Invalid data
if not validate_format(data):
    raise errors.InvalidInputError(...)  # NOT ValueError

# Missing modules
if not module_available:
    raise errors.MissingDependencyError(...)  # NOT ImportError

# Permission issues
if access_denied:
    raise errors.PermissionError(...)  # NOT IOError

# Bad configuration
if invalid_setting:
    raise errors.ConfigurationError(...)  # NOT ValueError

# Conversion failures
if conversion_failed:
    raise errors.ConversionError(...)  # NOT RuntimeError
```

### Platform-Specific Guidance

Provide platform-appropriate commands:

```python
# Good - Platform-aware
suggestions = [
    "List files: dir SID\\ (Windows) or ls SID/ (Mac/Linux)",
    "Check permissions: File Properties → Security (Windows) or ls -la (Mac/Linux)"
]

# Better - Auto-detect platform
if sys.platform == 'win32':
    suggestions = ["List files: dir SID\\"]
else:
    suggestions = ["List files: ls SID/"]
```

### Progressive Disclosure

Start simple, provide depth:

```python
# Good - Simple first, then details
how_to_fix = [
    "1. Verify file exists: dir SID\\yourfile.sid",  # Simple
    "2. Use absolute path: python scripts/... C:\\full\\path\\to\\file.sid ...",  # More detail
    "3. Check working directory: cd (shows current directory)"  # Advanced
]

# Bad - Too much detail upfront
how_to_fix = [
    "1. Execute filesystem stat syscall to verify inode existence in directory tree structure"
]
```

### Consistent Tone

Maintain professional, helpful tone:

```python
# Good - Helpful, factual
"Could not find the input SID file"
"The driver type is not recognized"
"Permission denied while trying to write"

# Bad - Casual or blaming
"Oops! Can't find your file!"
"You entered an invalid driver"
"You don't have permission to do that"
```

---

## Testing Error Messages

All new error messages should be tested:

```python
# Test file: scripts/test_error_messages.py

class TestMyNewError(unittest.TestCase):
    def test_my_error_structure(self):
        """Test MyNewError has proper structure."""
        error = errors.MyNewError(param="value")
        msg = str(error)

        # Verify structure
        self.assertIn("ERROR:", msg)
        self.assertIn("What happened:", msg)
        self.assertIn("How to fix:", msg)
        self.assertIn("Need help?", msg)

        # Verify content
        self.assertIn("expected content", msg)
        self.assertIn("troubleshooting guide", msg)

    def test_my_error_can_be_caught(self):
        """Test MyNewError can be caught properly."""
        with self.assertRaises(errors.MyNewError):
            raise errors.MyNewError(param="value")
```

Run tests:
```bash
python scripts/test_error_messages.py
```

---

## Examples

### Example 1: File Not Found

```python
from sidm2 import errors

def load_sid_file(filepath):
    """Load a SID file with proper error handling."""
    if not os.path.exists(filepath):
        raise errors.FileNotFoundError(
            path=filepath,
            context="input SID file",
            suggestions=[
                "Check the file path: python scripts/sid_to_sf2.py --help",
                "Use absolute path instead of relative",
                f"List files in directory: dir {os.path.dirname(filepath) or '.'}"
            ],
            docs_link="guides/TROUBLESHOOTING.md#1-file-not-found-issues"
        )

    with open(filepath, 'rb') as f:
        return f.read()
```

**Output**:
```
ERROR: Input Sid File Not Found

What happened:
  Could not find the input SID file: SID/missing.sid

Why this happened:
  • File path may be incorrect or contains typos
  • File may have been moved or deleted
  • Working directory may be wrong
  • Using relative path when absolute is needed

How to fix:
  1. Check the file path: python scripts/sid_to_sf2.py --help
  2. Use absolute path instead of relative
  3. List files in directory: dir SID

Alternative:
  Similar files found in the same directory:
    • SID\song.sid
    • SID\test.sid

Need help?
  * Documentation: https://github.com/.../TROUBLESHOOTING.md#1-file-not-found-issues
  * Issues: https://github.com/MichaelTroelsen/SIDM2conv/issues
  * README: https://github.com/MichaelTroelsen/SIDM2conv#readme

Technical details:
  Full path checked: C:\Users\...\SIDM2\SID\missing.sid
```

### Example 2: Invalid Configuration

```python
from sidm2 import errors

def validate_driver(driver_type, available_drivers):
    """Validate driver type with helpful error."""
    if driver_type not in available_drivers:
        raise errors.ConfigurationError(
            setting="driver",
            value=driver_type,
            valid_options=available_drivers,
            example="python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity",
            docs_link="reference/DRIVER_REFERENCE.md"
        )
```

### Example 3: Conversion Failure

```python
from sidm2 import errors

def convert_sid_to_sf2(input_path, output_path):
    """Convert with detailed error handling."""
    try:
        # Attempt conversion
        data = extract_tables(input_path)
        write_sf2(output_path, data)
    except Exception as e:
        raise errors.ConversionError(
            stage="table extraction",
            reason=str(e),
            input_file=input_path,
            suggestions=[
                "Check player type: tools/player-id.exe " + input_path,
                "Try different driver: --driver driver11",
                "Enable verbose logging: --verbose",
                "Report issue with file details"
            ],
            docs_link="guides/TROUBLESHOOTING.md#4-conversion-failures"
        )
```

---

## Checklist for New Errors

Before submitting code with new error messages:

- [ ] Used appropriate error class from `sidm2.errors`
- [ ] Provided clear "What happened" description
- [ ] Listed 3-5 common causes in "Why this happened"
- [ ] Included 2-4 specific, actionable fixes with commands
- [ ] Added alternatives if applicable
- [ ] Linked to specific troubleshooting guide section
- [ ] Included technical details for debugging
- [ ] Tested error can be raised and caught
- [ ] Added test case to `test_error_messages.py`
- [ ] Verified message length is reasonable (100-2000 chars)
- [ ] Used consistent tone and formatting
- [ ] Provided platform-specific guidance if needed

---

## Common Mistakes to Avoid

### ❌ Don't Use Generic Exceptions

```python
# Bad
raise Exception("File not found")
raise ValueError("Invalid input")
raise RuntimeError("Conversion failed")

# Good
raise errors.FileNotFoundError(path=filepath, context="SID file")
raise errors.InvalidInputError(input_type="SID file", value=filepath)
raise errors.ConversionError(stage="conversion", reason="...")
```

### ❌ Don't Be Vague

```python
# Bad
raise errors.FileNotFoundError(
    path=filepath,
    suggestions=["Check your files", "Try again"]
)

# Good
raise errors.FileNotFoundError(
    path=filepath,
    suggestions=[
        "Verify file exists: dir " + filepath,
        "Use absolute path: C:\\full\\path\\to\\file.sid",
        "List directory contents: dir SID\\"
    ]
)
```

### ❌ Don't Omit Context

```python
# Bad
if error:
    raise errors.ConversionError(stage="conversion", reason="failed")

# Good
if error:
    raise errors.ConversionError(
        stage="table extraction",
        reason=f"Cannot locate instrument table at expected address {hex(addr)}",
        input_file=input_path,
        suggestions=[
            "Check player type: tools/player-id.exe " + input_path,
            "Try different driver: --driver driver11"
        ]
    )
```

### ❌ Don't Skip Documentation Links

```python
# Bad
raise errors.FileNotFoundError(path=filepath)  # Uses default link

# Good
raise errors.FileNotFoundError(
    path=filepath,
    docs_link="guides/TROUBLESHOOTING.md#1-file-not-found-issues"
)
```

---

## References

- **Error Module**: `sidm2/errors.py` - Implementation
- **Test Suite**: `scripts/test_error_messages.py` - 34 tests
- **Troubleshooting Guide**: `docs/guides/TROUBLESHOOTING.md` - User-facing documentation
- **Demo Script**: `test_errors_demo.py` - All error examples

---

**Document Version**: v2.5.0
**Last Updated**: 2025-12-21
**Related**: `CONTRIBUTING.md`, `sidm2/errors.py`, `TROUBLESHOOTING.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
