# Error Message Improvement Guide

**Purpose**: Guide for improving error messages to be more user-friendly and actionable

**Version**: 1.0
**Date**: 2025-12-27
**Related**: Track 4.2 - Improve Error Messages

---

## Overview

This guide provides patterns and examples for improving error messages in the SIDM2 codebase.

**Current State** (as of Track 4.2):
- **449 total issues** identified across 47 files
- **24 generic exceptions** (medium priority) - being replaced
- **216 bare logger errors** (low priority) - need suggestions
- **156 missing doc links** (low priority) - need documentation
- **52 missing alternatives** (low priority) - need fallback options

**Goals**:
1. Replace generic exceptions with rich error classes
2. Add actionable suggestions to all errors
3. Link to relevant documentation
4. Provide alternative approaches when possible

---

## Error Classification

### 1. User-Facing Errors (High Priority)

**Examples**:
- File not found
- Invalid configuration
- Conversion failures
- Permission denied

**Pattern**: Use rich error classes from `sidm2/errors.py`

### 2. Developer Errors (Medium Priority)

**Examples**:
- Invalid API usage
- Missing dependencies
- Configuration errors

**Pattern**: Informative messages with examples

### 3. Internal Errors (Low Priority)

**Examples**:
- Unexpected exceptions
- Data validation failures

**Pattern**: Technical details + troubleshooting steps

---

## Improvement Patterns

### Pattern 1: Replace Generic Exceptions

**Before**:
```python
if self.validation_level not in ['strict', 'normal', 'permissive']:
    raise ValueError(f"Invalid validation level: {self.validation_level}")
```

**After**:
```python
from sidm2.errors import ConfigurationError

if self.validation_level not in ['strict', 'normal', 'permissive']:
    raise ConfigurationError(
        setting='validation_level',
        value=self.validation_level,
        valid_options=['strict', 'normal', 'permissive'],
        example='validation_level: normal',
        docs_link='guides/TROUBLESHOOTING.md#configuration-errors'
    )
```

**Benefits**:
- ✅ Clear error category (Configuration Error)
- ✅ Shows valid options
- ✅ Provides example usage
- ✅ Links to documentation
- ✅ Color-coded terminal output

---

### Pattern 2: Enhance Logger Errors

**Before**:
```python
logger.error(f"Failed to generate {driver_type} version: {e}")
```

**After**:
```python
logger.error(
    f"Failed to generate {driver_type} version: {e}\n"
    f"  Suggestion: Try a different driver with --driver driver11\n"
    f"  See: docs/guides/TROUBLESHOOTING.md#conversion-failures"
)
```

**Alternative** (for critical errors):
```python
try:
    generate_output(driver_type)
except Exception as e:
    raise ConversionError(
        stage=f'{driver_type} generation',
        reason=str(e),
        input_file=input_path,
        suggestions=[
            f'Try a different driver: --driver driver11',
            'Enable debug logging: --debug',
            'Check input file format'
        ]
    )
```

---

### Pattern 3: Add Documentation Links

**Before**:
```python
logger.warning(f"Player type detection failed: {e}")
```

**After**:
```python
logger.warning(
    f"Player type detection failed: {e}\n"
    f"  This may affect accuracy. Using safe default driver.\n"
    f"  To override: Use --driver laxity or --driver driver11\n"
    f"  See: https://github.com/MichaelTroelsen/SIDM2conv/blob/master/docs/guides/DRIVER_SELECTION_GUIDE.md"
)
```

---

### Pattern 4: Provide Alternatives

**Before**:
```python
if not os.path.exists(siddump_exe):
    logger.error(f"Siddump exe not found: {siddump_exe}")
    return None
```

**After**:
```python
if not os.path.exists(siddump_exe):
    logger.error(
        f"Siddump exe not found: {siddump_exe}\n"
        f"  Alternative 1: Use Python siddump instead (slower but always available)\n"
        f"    python pyscript/siddump_complete.py input.sid -t30\n"
        f"  Alternative 2: Download siddump.exe from tools/ directory\n"
        f"  Alternative 3: Skip validation with --no-validate"
    )
    # Fall back to Python implementation
    logger.info("Falling back to Python siddump implementation")
    return use_python_siddump(sid_path, duration)
```

---

### Pattern 5: File Not Found Errors

**Before**:
```python
if not os.path.exists(input_path):
    raise FileNotFoundError(f"File not found: {input_path}")
```

**After**:
```python
from sidm2.errors import FileNotFoundError as SIDMFileNotFoundError

if not os.path.exists(input_path):
    raise SIDMFileNotFoundError(
        path=str(input_path),
        context='input SID file',
        docs_link='guides/TROUBLESHOOTING.md#file-not-found-issues'
    )
```

**Benefits**:
- ✅ Suggests similar files automatically
- ✅ Shows absolute path
- ✅ Provides directory listing command
- ✅ Explains common causes

---

## Rich Error Classes

### Available Classes (from `sidm2/errors.py`)

1. **FileNotFoundError**
   - Use for: Missing files
   - Auto-features: Similar file suggestions
   - Example: Input SID not found

2. **InvalidInputError**
   - Use for: Invalid file formats, corrupted data
   - Fields: `input_type`, `value`, `expected`, `got`
   - Example: Invalid SID magic bytes

3. **MissingDependencyError**
   - Use for: Missing tools, modules
   - Fields: `dependency`, `install_command`
   - Example: Missing siddump.exe

4. **PermissionError**
   - Use for: Access denied errors
   - Auto-features: Platform-specific suggestions
   - Example: Cannot write output file

5. **ConfigurationError**
   - Use for: Invalid config values
   - Fields: `setting`, `value`, `valid_options`, `example`
   - Example: Invalid driver type

6. **ConversionError**
   - Use for: Conversion failures
   - Fields: `stage`, `reason`, `input_file`
   - Example: SF2 generation failed

### Error Class Template

```python
from sidm2.errors import SIDMError

class MyCustomError(SIDMError):
    """Custom error for specific failure mode"""

    def __init__(self, context: str, details: str, **kwargs):
        super().__init__(
            message=f"Operation Failed: {context}",
            what_happened=f"The operation failed because: {details}",
            why_happened=[
                "Reason 1",
                "Reason 2",
                "Reason 3"
            ],
            how_to_fix=[
                "Step 1: Do this",
                "Step 2: Then do that",
                "Step 3: Finally check"
            ],
            docs_link='guides/TROUBLESHOOTING.md#my-section',
            alternatives=[
                "Alternative approach 1",
                "Alternative approach 2"
            ],
            technical_details=kwargs.get('tech_details')
        )
```

---

## Quick Reference

### When to Use Each Pattern

| Situation | Use | Priority |
|-----------|-----|----------|
| User error (file not found, bad config) | Rich error class | **High** |
| Conversion failure | ConversionError | **High** |
| Warning about issue | logger.warning + suggestion | Medium |
| Internal error | logger.error + context | Medium |
| Debug information | logger.debug | Low |

### Error Message Checklist

- [ ] Error type is clear (what went wrong)
- [ ] Explanation provided (why it happened)
- [ ] Actionable suggestion (how to fix)
- [ ] Documentation link (where to learn more)
- [ ] Alternative approach (if available)
- [ ] Example or valid options (when relevant)

---

## Examples by Module

### config.py - Configuration Errors

```python
from sidm2.errors import ConfigurationError

# Invalid setting value
if value not in valid_values:
    raise ConfigurationError(
        setting='setting_name',
        value=value,
        valid_options=valid_values,
        example='setting_name: default_value'
    )
```

### sid_parser.py - File Validation Errors

```python
from sidm2.errors import InvalidInputError

# Invalid file format
if magic != b'PSID':
    raise InvalidInputError(
        input_type='SID file',
        value=str(input_path),
        expected='PSID or RSID magic bytes',
        got=f'{magic}',
        suggestions=[
            'Verify file is a valid SID file',
            'Check file extension (.sid)',
            'Try opening in a SID player first'
        ]
    )
```

### converter.py - Conversion Errors

```python
from sidm2.errors import ConversionError

# Conversion stage failure
try:
    result = extract_music_data()
except Exception as e:
    raise ConversionError(
        stage='Music Data Extraction',
        reason=f'Failed to extract: {str(e)}',
        input_file=str(input_path),
        suggestions=[
            'Check if file uses supported player format',
            'Try different driver: --driver laxity',
            'Enable verbose logging: --verbose'
        ]
    )
```

---

## Migration Strategy

### Phase 1: Critical User-Facing Errors (High Priority)

**Target**: 24 generic exceptions
**Time**: 2-3 hours
**Focus**:
- config.py configuration errors ✅ (4/24 complete)
- scripts/sid_to_sf2.py conversion errors ✅ (1/24 complete)
- File I/O errors
- Permission errors

### Phase 2: Logger Error Enhancement (Medium Priority)

**Target**: Top 50 logger.error calls
**Time**: 2-3 hours
**Focus**:
- Add suggestions to bare errors
- Link to documentation
- Provide context and next steps

### Phase 3: Documentation Links (Low Priority)

**Target**: 156 missing doc links
**Time**: 1-2 hours
**Focus**:
- Add TROUBLESHOOTING.md links
- Link to relevant guides
- Create anchor links for sections

### Phase 4: Alternative Suggestions (Low Priority)

**Target**: 52 missing alternatives
**Time**: 1 hour
**Focus**:
- Provide fallback options
- Suggest workarounds
- Offer different approaches

---

## Testing Error Messages

### Manual Testing

```bash
# Test configuration error
python -c "from sidm2.config import DriverConfig; c = DriverConfig(); c.default_driver = 'invalid'; c.validate()"

# Test file not found
python scripts/sid_to_sf2.py nonexistent.sid output.sf2

# Test conversion error
python scripts/sid_to_sf2.py corrupted.sid output.sf2 --verbose
```

### Expected Output

Good error messages should:
1. **Identify the problem** - Clear error type and message
2. **Explain why** - Common causes listed
3. **Show how to fix** - Step-by-step solutions
4. **Link to help** - Documentation and support
5. **Use color** - Terminal color coding (if supported)

Example output:
```
ERROR: Invalid Configuration: default_driver

What happened:
  Invalid configuration for 'default_driver': invalid

Why this happened:
  • 'invalid' is not a valid option for 'default_driver'
  • Configuration file may be outdated
  • Typo in configuration value
  • Using incompatible settings together

How to fix:
  1. Use one of: driver11, np20, laxity
  2. Example: default_driver: laxity
  3. Check configuration file syntax
  4. Refer to documentation for valid options
  5. Use default configuration to test

Alternative:
  Valid options:
    • driver11
    • np20
    • laxity

Need help?
  * Documentation: https://github.com/MichaelTroelsen/SIDM2conv/blob/master/docs/guides/LAXITY_DRIVER_USER_GUIDE.md
  * Issues: https://github.com/MichaelTroelsen/SIDM2conv/issues
  * README: https://github.com/MichaelTroelsen/SIDM2conv#readme

Technical details:
  Setting: default_driver, Value: invalid
```

---

## Tools and Automation

### Error Message Audit Tool

```bash
# Run audit
python pyscript/audit_error_messages.py

# Generate report
python pyscript/audit_error_messages.py --output report.md

# Check progress
grep -r "from sidm2.errors import" --include="*.py" sidm2/ scripts/ | wc -l
```

### Find Remaining Issues

```bash
# Find generic exceptions
grep -r "raise ValueError\|raise RuntimeError\|raise IOError" --include="*.py" sidm2/ scripts/

# Find bare logger errors
grep -r "logger.error\|logger.warning" --include="*.py" sidm2/ scripts/ | grep -v "See:\|Try:\|Check:"

# Find missing doc links
grep -r "raise.*Error" --include="*.py" sidm2/ | grep -v "docs_link\|TROUBLESHOOTING"
```

---

## Best Practices

### DO ✅

- Use rich error classes for user-facing errors
- Provide actionable suggestions
- Link to documentation
- Show valid options for configuration
- Include examples
- Use color-coded output
- Provide alternatives when available
- Explain technical jargon

### DON'T ❌

- Use generic exceptions for user errors
- Show stack traces without context
- Use technical jargon without explanation
- Omit suggestions or next steps
- Forget documentation links
- Leave users without alternatives
- Assume users know internal details

---

## Success Metrics

**Track 4.2 Goals**:
- ✅ Replace 24 generic exceptions → **5/24 complete (21%)**
- 🔄 Improve 50+ logger errors → **In progress**
- 📋 Add 50+ doc links → **Planned**
- ✅ Create improvement guide → **Complete**

**Overall Progress**:
- Total issues: 449
- Resolved: ~10 (2%)
- In progress: Track 4.2
- Target: User-friendly errors across all modules

---

**Document Version**: 1.0
**Last Updated**: 2025-12-27
**Author**: Claude Sonnet 4.5 (Track 4.2 - Error Message Improvement)
