# Logging and Error Handling Guide

**Complete guide to SIDM2's logging system and error handling**

**Version**: 2.0.0
**Date**: 2025-12-21

---

## Overview

SIDM2 provides two comprehensive systems for better user experience and debugging:

1. **Enhanced Logging System** (v2.0.0)
   - Verbosity levels (0-3)
   - Color-coded console output
   - Structured JSON logging
   - File logging with rotation
   - Performance metrics logging

2. **User-Friendly Error Messages** (v1.0.0)
   - Clear explanations of what went wrong
   - Common causes and solutions
   - Documentation links
   - Similar file suggestions
   - Platform-specific guidance

---

## Table of Contents

1. [Logging System](#logging-system)
   - [Quick Start](#quick-start)
   - [Verbosity Levels](#verbosity-levels)
   - [Color Output](#color-output)
   - [File Logging](#file-logging)
   - [Structured Logging](#structured-logging)
   - [Performance Logging](#performance-logging)
   - [CLI Integration](#cli-integration)
2. [Error Handling](#error-handling)
   - [Error Types](#error-types)
   - [Error Format](#error-format)
   - [Using Errors](#using-errors)
   - [Custom Errors](#custom-errors)
3. [Examples](#examples)
4. [Best Practices](#best-practices)
5. [Troubleshooting](#troubleshooting)

---

## Logging System

### Quick Start

**Basic Usage:**
```python
from sidm2.logging_config import setup_logging, get_logger

# Setup logging (INFO level by default)
setup_logging()

# Get logger for your module
logger = get_logger(__name__)

# Log messages
logger.info("Processing SID file")
logger.warning("Missing optional data")
logger.error("Conversion failed")
logger.debug("Detailed debug info")
```

**CLI Usage:**
```bash
# Normal mode (INFO level)
python scripts/sid_to_sf2.py input.sid output.sf2

# Verbose mode (DEBUG level)
python scripts/sid_to_sf2.py input.sid output.sf2 --debug

# Quiet mode (ERROR only)
python scripts/sid_to_sf2.py input.sid output.sf2 --quiet

# With file logging
python scripts/sid_to_sf2.py input.sid output.sf2 --log-file logs/conversion.log
```

---

### Verbosity Levels

SIDM2 supports 4 verbosity levels:

| Level | Value | Includes | Use Case |
|-------|-------|----------|----------|
| **ERROR** | 0 | Errors only | Production, quiet mode |
| **WARNING** | 1 | Warnings + Errors | Normal operation |
| **INFO** | 2 | Info + Warnings + Errors | Default, verbose mode |
| **DEBUG** | 3 | Everything | Development, debugging |

**Setting Verbosity:**

```python
from sidm2.logging_config import setup_logging

# Method 1: Direct verbosity level
setup_logging(verbosity=2)  # INFO level

# Method 2: Convenience flags
setup_logging(quiet=True)    # verbosity=0 (ERROR)
setup_logging(debug=True)    # verbosity=3 (DEBUG)

# Method 3: Dynamic change
from sidm2.logging_config import set_verbosity
set_verbosity(3)  # Switch to DEBUG at runtime
```

**Example Output:**

```
# INFO level (verbosity=2)
2025-12-21 10:30:15 [    INFO] sidm2.sid_parser:145 - Parsing SID file: test.sid
2025-12-21 10:30:15 [    INFO] sidm2.sf2_writer:203 - Writing SF2 file: output.sf2

# DEBUG level (verbosity=3)
2025-12-21 10:30:15 [   DEBUG] sidm2.sid_parser:112 - Header loaded: PSID v2
2025-12-21 10:30:15 [   DEBUG] sidm2.sid_parser:125 - Load address: 0x1000
2025-12-21 10:30:15 [    INFO] sidm2.sid_parser:145 - Parsing SID file: test.sid

# ERROR level (verbosity=0 - quiet)
2025-12-21 10:30:15 [   ERROR] sidm2.sf2_writer:220 - Failed to write SF2 file
```

---

### Color Output

**Automatic Color Detection:**
- Colors enabled when output is a terminal
- Disabled when redirected to file
- Can be manually controlled

**Color Scheme:**
- 🔴 **ERROR** - Red
- 🟡 **WARNING** - Yellow
- 🔵 **INFO** - Cyan
- ⚪ **DEBUG** - Grey
- 🟥 **CRITICAL** - Bold Red

**Controlling Colors:**
```python
from sidm2.logging_config import setup_logging

# Enable colors (default for terminals)
setup_logging(use_colors=True)

# Disable colors (useful for redirected output)
setup_logging(use_colors=False)

# Automatic detection (default)
setup_logging()  # Colors auto-enabled if terminal
```

---

### File Logging

**Basic File Logging:**
```python
from sidm2.logging_config import setup_logging

# Log to file
setup_logging(
    verbosity=2,
    log_file='logs/sidm2.log'
)
```

**Log Rotation:**
```python
from sidm2.logging_config import setup_logging

# Rotating file handler (10 MB max, 3 backups)
setup_logging(
    verbosity=2,
    log_file='logs/sidm2.log',
    max_file_size=10 * 1024 * 1024,  # 10 MB
    backup_count=3
)

# Files created:
# - logs/sidm2.log (current)
# - logs/sidm2.log.1 (previous)
# - logs/sidm2.log.2 (older)
# - logs/sidm2.log.3 (oldest)
```

**Multiple Log Files:**
```python
from sidm2.logging_config import setup_logging, add_file_handler
import logging

# Setup main logging
setup_logging(verbosity=2, log_file='logs/main.log')

# Add error-only log
add_file_handler('logs/errors.log', level=logging.ERROR)

# Add debug log
add_file_handler('logs/debug.log', level=logging.DEBUG)
```

---

### Structured Logging

**JSON Output:**

Structured logging outputs each log entry as a JSON object, ideal for log aggregation tools (ELK stack, Splunk, etc.).

```python
from sidm2.logging_config import setup_logging

# Enable JSON logging
setup_logging(
    verbosity=2,
    structured=True,
    log_file='logs/sidm2.jsonl'
)
```

**Example Output:**
```json
{"timestamp": "2025-12-21T10:30:15.123456", "level": "INFO", "logger": "sidm2.sid_parser", "module": "sid_parser", "line": 145, "function": "parse_file", "message": "Parsing SID file: test.sid", "file": "test.sid", "size": 4096}
{"timestamp": "2025-12-21T10:30:15.234567", "level": "INFO", "logger": "sidm2.sf2_writer", "module": "sf2_writer", "line": 203, "function": "write_file", "message": "Writing SF2 file: output.sf2", "duration_seconds": 0.523}
```

**Custom Fields:**
```python
logger = get_logger(__name__)
logger.info(
    "File processed successfully",
    extra={
        'filename': 'test.sid',
        'file_size': 4096,
        'conversion_time': 0.523,
        'driver': 'laxity'
    }
)
```

---

### Performance Logging

**Context Manager:**
```python
from sidm2.logging_config import get_logger, PerformanceLogger

logger = get_logger(__name__)

with PerformanceLogger(logger, "SID file conversion"):
    # Your code here
    convert_sid_to_sf2(input_file, output_file)

# Output:
# [INFO] Starting: SID file conversion
# [INFO] Completed: SID file conversion (duration_seconds: 0.523, status: success)
```

**Decorator:**
```python
from sidm2.logging_config import get_logger, log_performance

@log_performance("SID file parsing")
def parse_sid_file(path: str):
    # Parsing code
    return sid_data

# Automatically logs:
# [INFO] Starting: SID file parsing
# [INFO] Completed: SID file parsing (duration_seconds: 0.142, status: success)
```

**Error Handling:**
```python
with PerformanceLogger(logger, "Risky operation"):
    # If this raises an exception
    risky_operation()

# Output:
# [INFO] Starting: Risky operation
# [ERROR] Failed: Risky operation (duration_seconds: 0.05, status: failed, exception: "File not found")
```

---

### CLI Integration

**ArgumentParser Integration:**

```python
import argparse
from sidm2.logging_config import configure_from_args

# Create parser
parser = argparse.ArgumentParser(description="SID to SF2 converter")
parser.add_argument('input', help="Input SID file")
parser.add_argument('output', help="Output SF2 file")

# Add logging arguments
parser.add_argument('-v', '--verbose', action='count', default=2,
                   help="Increase verbosity (-v=INFO, -vv=DEBUG)")
parser.add_argument('-q', '--quiet', action='store_true',
                   help="Quiet mode (errors only)")
parser.add_argument('--debug', action='store_true',
                   help="Debug mode (maximum verbosity)")
parser.add_argument('--log-file', type=str,
                   help="Log to file")
parser.add_argument('--log-json', action='store_true',
                   help="Use JSON log format")

args = parser.parse_args()

# Configure logging from args (one line!)
configure_from_args(args)

# Now use logging
logger = get_logger(__name__)
logger.info(f"Converting {args.input} to {args.output}")
```

**Usage Examples:**
```bash
# Default (INFO level)
python script.py input.sid output.sf2

# Verbose (DEBUG level)
python script.py input.sid output.sf2 -v

# Extra verbose (DEBUG level)
python script.py input.sid output.sf2 -vv

# Quiet (ERROR only)
python script.py input.sid output.sf2 -q

# Debug mode
python script.py input.sid output.sf2 --debug

# With log file
python script.py input.sid output.sf2 --log-file logs/conversion.log

# JSON logging
python script.py input.sid output.sf2 --log-json --log-file logs/conversion.jsonl
```

---

## Error Handling

### Error Types

SIDM2 provides 6 specialized error classes:

1. **FileNotFoundError** - File not found with similar file suggestions
2. **InvalidInputError** - Invalid input with validation guidance
3. **MissingDependencyError** - Missing dependencies with install instructions
4. **PermissionError** - Permission issues with platform-specific fixes
5. **ConfigurationError** - Invalid configuration with valid options
6. **ConversionError** - Conversion failures with recovery suggestions

---

### Error Format

All SIDM2 errors follow this rich format:

```
ERROR: Error Title

What happened:
  Detailed explanation of what went wrong

Why this happened:
  • Possible cause 1
  • Possible cause 2
  • Possible cause 3

How to fix:
  1. Step-by-step solution 1
  2. Step-by-step solution 2
  3. Step-by-step solution 3

Alternative:
  • Alternative approach 1
  • Alternative approach 2

Need help?
  * Documentation: https://github.com/.../docs/...
  * Issues: https://github.com/.../issues
  * README: https://github.com/...#readme

Technical details:
  Additional debugging information
```

---

### Using Errors

**Import:**
```python
from sidm2 import errors
# or
from sidm2.errors import FileNotFoundError, InvalidInputError
```

**Example 1: File Not Found**
```python
from sidm2.errors import FileNotFoundError
import os

if not os.path.exists(input_path):
    raise FileNotFoundError(
        path=input_path,
        context="input SID file"
    )
```

**Output:**
```
ERROR: Input Sid File Not Found

What happened:
  Could not find the input SID file: test.sid

Why this happened:
  • File path may be incorrect or contains typos
  • File may have been moved or deleted
  • Working directory may be wrong
  • Using relative path when absolute is needed

How to fix:
  1. Check the file exists: ls test.sid (or dir test.sid on Windows)
  2. Use absolute path: C:\Users\...\test.sid
  3. List directory contents: ls ./ (or dir .\ on Windows)
  4. Check current directory: pwd (or cd on Windows)

Alternative:
  Similar files found in the same directory:
    • test2.sid
    • test_old.sid
    • sample.sid

Need help?
  * Documentation: https://github.com/.../docs/guides/TROUBLESHOOTING.md#1-file-not-found-issues
  * Issues: https://github.com/.../issues
  * README: https://github.com/...#readme

Technical details:
  Full path checked: C:\Users\...\test.sid
```

**Example 2: Invalid Input**
```python
from sidm2.errors import InvalidInputError

if file_size < 64:
    raise InvalidInputError(
        input_type="SID file",
        value=input_path,
        expected="at least 64 bytes",
        got=f"{file_size} bytes"
    )
```

**Example 3: Conversion Error**
```python
from sidm2.errors import ConversionError

try:
    extract_tables(sid_data)
except Exception as e:
    raise ConversionError(
        stage="table extraction",
        reason=str(e),
        input_file=input_path,
        suggestions=[
            "Try a different driver: --driver driver11",
            "Check player type: tools/player-id.exe input.sid",
            "Enable debug logging: --debug"
        ]
    )
```

**Example 4: Configuration Error**
```python
from sidm2.errors import ConfigurationError

valid_drivers = ['np20', 'driver11', 'laxity']

if driver not in valid_drivers:
    raise ConfigurationError(
        setting='driver',
        value=driver,
        valid_options=valid_drivers,
        example='--driver laxity'
    )
```

---

### Custom Errors

**Creating Custom Error Classes:**

```python
from sidm2.errors import SIDMError

class TableValidationError(SIDMError):
    """
    Custom error for table validation failures.
    """

    def __init__(self, table_name: str, issue: str):
        super().__init__(
            message=f"Invalid {table_name} Table",
            what_happened=f"The {table_name} table failed validation: {issue}",
            why_happened=[
                f"{table_name} table is corrupted",
                f"{table_name} table has invalid format",
                "Extraction logic has a bug"
            ],
            how_to_fix=[
                "Check SID file integrity",
                "Try re-downloading the SID file",
                "Report issue with file details"
            ],
            docs_link="guides/TROUBLESHOOTING.md",
            technical_details=f"Table: {table_name}, Issue: {issue}"
        )
```

**Using Custom Errors:**
```python
if not validate_wave_table(wave_data):
    raise TableValidationError(
        table_name="wave",
        issue="loop marker 0x7E not found"
    )
```

---

## Examples

### Example 1: Complete Logging Setup

```python
"""
Example script with complete logging and error handling.
"""
import argparse
from pathlib import Path
from sidm2.logging_config import configure_from_args, get_logger, PerformanceLogger
from sidm2 import errors

def main():
    # Argument parser
    parser = argparse.ArgumentParser(description="SID to SF2 converter")
    parser.add_argument('input', help="Input SID file")
    parser.add_argument('output', help="Output SF2 file")
    parser.add_argument('-v', '--verbose', action='count', default=2)
    parser.add_argument('-q', '--quiet', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--log-file', type=str)
    parser.add_argument('--log-json', action='store_true')

    args = parser.parse_args()

    # Configure logging
    configure_from_args(args)

    # Get logger
    logger = get_logger(__name__)

    try:
        # Validate input
        input_path = Path(args.input)
        if not input_path.exists():
            raise errors.FileNotFoundError(
                path=str(input_path),
                context="input SID file"
            )

        # Process with performance logging
        logger.info(f"Starting conversion: {args.input} → {args.output}")

        with PerformanceLogger(logger, "SID to SF2 conversion"):
            # Your conversion code here
            result = convert_file(input_path, args.output)

        logger.info(
            "Conversion completed successfully",
            extra={'input': args.input, 'output': args.output, 'accuracy': result.accuracy}
        )

    except errors.SIDMError as e:
        # SIDM errors already have rich formatting
        logger.error(str(e))
        return 1

    except Exception as e:
        # Wrap unexpected errors
        logger.exception("Unexpected error occurred")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())
```

### Example 2: Module with Logging

```python
"""
Example module showing logging best practices.
"""
from sidm2.logging_config import get_logger, log_performance
from sidm2 import errors

# Module logger
logger = get_logger(__name__)

@log_performance("SID file parsing")
def parse_sid_file(path: str):
    """Parse SID file with logging."""
    logger.debug(f"Opening file: {path}")

    try:
        with open(path, 'rb') as f:
            data = f.read()

        logger.debug(f"Read {len(data)} bytes", extra={'size': len(data)})

        # Parsing logic
        header = parse_header(data)
        logger.info("Header parsed successfully", extra={'version': header.version})

        return header

    except FileNotFoundError:
        raise errors.FileNotFoundError(path=path, context="SID file")

    except Exception as e:
        logger.error(f"Failed to parse file: {e}")
        raise errors.ConversionError(
            stage="file parsing",
            reason=str(e),
            input_file=path
        )

def parse_header(data: bytes):
    """Parse SID header."""
    logger.debug("Parsing header")

    # Header parsing logic
    if len(data) < 64:
        raise errors.InvalidInputError(
            input_type="SID file",
            value=f"{len(data)} bytes",
            expected="at least 64 bytes",
            got=f"{len(data)} bytes"
        )

    # ... more parsing ...

    return header
```

---

## Best Practices

### Logging

1. **Use appropriate levels:**
   - `ERROR` - Failures that prevent operation
   - `WARNING` - Issues that don't prevent operation
   - `INFO` - Important milestones and results
   - `DEBUG` - Detailed diagnostic information

2. **Add context with extra fields:**
   ```python
   logger.info(
       "File converted",
       extra={'input': input_file, 'size': file_size, 'duration': duration}
   )
   ```

3. **Use performance logging for expensive operations:**
   ```python
   with PerformanceLogger(logger, "table extraction"):
       extract_tables(sid_data)
   ```

4. **Log at module boundaries:**
   - Function entry/exit (DEBUG level)
   - Major operations (INFO level)
   - Errors and warnings appropriately

5. **Don't log sensitive information:**
   - Avoid logging passwords, API keys, etc.
   - Sanitize file paths if needed

### Error Handling

1. **Use specific error types:**
   ```python
   # Good
   raise errors.FileNotFoundError(path=path, context="SID file")

   # Bad
   raise Exception("File not found")
   ```

2. **Provide actionable suggestions:**
   ```python
   raise errors.ConversionError(
       stage="table extraction",
       reason="missing wave table",
       suggestions=[
           "Check if file is a valid Laxity SID",
           "Try --driver driver11",
           "Enable debug logging: --debug"
       ]
   )
   ```

3. **Include documentation links:**
   ```python
   raise errors.InvalidInputError(
       input_type="driver",
       value=driver,
       docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md#driver-selection"
   )
   ```

4. **Preserve exception chains:**
   ```python
   try:
       risky_operation()
   except Exception as e:
       raise errors.ConversionError(...) from e
   ```

---

## Troubleshooting

### Colors Not Working

**Problem**: Colors not showing in terminal

**Solutions:**
1. Check if output is redirected: `python script.py > output.txt` (no colors)
2. Use `--no-color` flag if terminal doesn't support ANSI codes
3. On Windows, install ANSICON or use Windows Terminal

### Log File Not Created

**Problem**: Log file not being created

**Solutions:**
1. Check directory exists: `mkdir logs/`
2. Check permissions: `ls -la logs/` or `icacls logs\`
3. Check log_file path is absolute or relative to working directory

### Too Much/Too Little Logging

**Problem**: Wrong verbosity level

**Solutions:**
```bash
# Too much: reduce verbosity
python script.py -q  # Quiet mode (errors only)

# Too little: increase verbosity
python script.py -v   # Verbose (INFO)
python script.py -vv  # Very verbose (DEBUG)
python script.py --debug  # Debug mode
```

### JSON Logs Not Valid

**Problem**: JSON logs have invalid format

**Solutions:**
1. Use `.jsonl` extension (JSON Lines format - one JSON object per line)
2. Each line is valid JSON, but file is not a JSON array
3. Parse line-by-line:
   ```python
   with open('logs/sidm2.jsonl') as f:
       for line in f:
           log_entry = json.loads(line)
   ```

---

## Summary

**Logging System v2.0.0:**
- ✅ 4 verbosity levels (0-3)
- ✅ Color-coded console output
- ✅ Structured JSON logging
- ✅ File logging with rotation
- ✅ Performance metrics logging
- ✅ Easy CLI integration

**Error Handling v1.0.0:**
- ✅ 6 specialized error types
- ✅ Rich formatted messages
- ✅ Troubleshooting guidance
- ✅ Documentation links
- ✅ Platform-specific help
- ✅ Similar file suggestions

**Resources:**
- Module: `sidm2/logging_config.py` (v2.0.0, 482 lines)
- Module: `sidm2/errors.py` (v1.0.0, 614 lines)
- Guide: `docs/guides/ERROR_MESSAGE_STYLE_GUIDE.md`
- Guide: `docs/guides/TROUBLESHOOTING.md`

---

**Version**: 2.0.0
**Last Updated**: 2025-12-21
**Status**: ✅ Production Ready
