"""
Demo script showcasing SIDM2's enhanced logging and error handling.

This script demonstrates:
- Verbosity levels (ERROR, WARNING, INFO, DEBUG)
- Color-coded console output
- Structured JSON logging
- Performance logging
- User-friendly error messages
- Error types and formatting

Usage:
    # Normal mode (INFO level, colored)
    python pyscript/demo_logging_and_errors.py

    # Debug mode (DEBUG level)
    python pyscript/demo_logging_and_errors.py --debug

    # Quiet mode (ERROR only)
    python pyscript/demo_logging_and_errors.py --quiet

    # With file logging
    python pyscript/demo_logging_and_errors.py --log-file logs/demo.log

    # JSON logging
    python pyscript/demo_logging_and_errors.py --log-json --log-file logs/demo.jsonl

Version: 1.0.0
"""

import argparse
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.logging_config import (
    setup_logging,
    get_logger,
    PerformanceLogger,
    log_performance,
    configure_from_args
)
from sidm2 import errors


def demo_logging_levels():
    """Demonstrate different logging levels."""
    logger = get_logger(__name__)

    print("\n" + "="*70)
    print("DEMO 1: Logging Levels")
    print("="*70 + "\n")

    logger.debug("This is a DEBUG message (verbosity 3)")
    logger.info("This is an INFO message (verbosity 2)")
    logger.warning("This is a WARNING message (verbosity 1)")
    logger.error("This is an ERROR message (verbosity 0)")

    print("\nNote: Current verbosity determines which messages are shown")
    print("Try running with --debug, --quiet, or -v/-vv flags\n")


def demo_structured_logging():
    """Demonstrate structured logging with extra fields."""
    logger = get_logger(__name__)

    print("\n" + "="*70)
    print("DEMO 2: Structured Logging (with extra fields)")
    print("="*70 + "\n")

    # Log with custom fields
    logger.info(
        "Processing SID file",
        extra={
            'filename': 'test.sid',
            'file_size': 4096,
            'player_type': 'Laxity NewPlayer v21',
            'driver': 'laxity'
        }
    )

    logger.info(
        "Conversion completed",
        extra={
            'input': 'test.sid',
            'output': 'test.sf2',
            'accuracy': 99.93,
            'duration_seconds': 0.523
        }
    )

    print("\nNote: With --log-json, these extra fields appear in JSON output\n")


def demo_performance_logging():
    """Demonstrate performance logging."""
    logger = get_logger(__name__)

    print("\n" + "="*70)
    print("DEMO 3: Performance Logging")
    print("="*70 + "\n")

    # Method 1: Context manager
    print("Method 1: Context Manager")
    with PerformanceLogger(logger, "Simulated SID parsing"):
        time.sleep(0.3)  # Simulate work

    # Method 2: Decorator
    print("\nMethod 2: Decorator")

    @log_performance("Simulated table extraction")
    def extract_tables():
        time.sleep(0.2)  # Simulate work
        return "tables_extracted"

    result = extract_tables()

    print("\nNote: Duration automatically logged for operations\n")


def demo_error_handling():
    """Demonstrate user-friendly error messages."""
    print("\n" + "="*70)
    print("DEMO 4: User-Friendly Error Messages")
    print("="*70 + "\n")

    print("Example 1: File Not Found Error")
    print("-" * 70)
    try:
        raise errors.FileNotFoundError(
            path="nonexistent.sid",
            context="input SID file"
        )
    except errors.SIDMError as e:
        print(e)

    print("\n" + "="*70)
    print("Example 2: Invalid Input Error")
    print("-" * 70)
    try:
        raise errors.InvalidInputError(
            input_type="SID file",
            value="test.txt",
            expected="valid SID file (PSID/RSID format)",
            got="text file"
        )
    except errors.SIDMError as e:
        print(e)

    print("\n" + "="*70)
    print("Example 3: Configuration Error")
    print("-" * 70)
    try:
        raise errors.ConfigurationError(
            setting='driver',
            value='invalid_driver',
            valid_options=['np20', 'driver11', 'laxity'],
            example='--driver laxity'
        )
    except errors.SIDMError as e:
        print(e)

    print("\n" + "="*70)
    print("Example 4: Conversion Error")
    print("-" * 70)
    try:
        raise errors.ConversionError(
            stage="table extraction",
            reason="Wave table loop marker 0x7E not found",
            input_file="problematic.sid",
            suggestions=[
                "Check if file is a valid Laxity SID: tools/player-id.exe problematic.sid",
                "Try a different driver: --driver driver11 or --driver np20",
                "Enable debug logging: --debug",
                "Report issue with file details"
            ]
        )
    except errors.SIDMError as e:
        print(e)


def demo_all_error_types():
    """Show all error types in quick succession."""
    logger = get_logger(__name__)

    print("\n" + "="*70)
    print("DEMO 5: All Error Types")
    print("="*70 + "\n")

    error_types = [
        ("FileNotFoundError", lambda: errors.FileNotFoundError(
            path="missing.sid", context="SID file"
        )),
        ("InvalidInputError", lambda: errors.InvalidInputError(
            input_type="driver", value="bad_driver"
        )),
        ("MissingDependencyError", lambda: errors.MissingDependencyError(
            dependency="PyQt6", install_command="pip install PyQt6"
        )),
        ("PermissionError", lambda: errors.PermissionError(
            operation="write", path="/protected/file.sf2"
        )),
        ("ConfigurationError", lambda: errors.ConfigurationError(
            setting="verbosity", value=99, valid_options=['0', '1', '2', '3']
        )),
        ("ConversionError", lambda: errors.ConversionError(
            stage="SF2 writing", reason="Invalid template"
        )),
    ]

    for name, error_fn in error_types:
        print(f"\n{name}:")
        print("-" * 70)
        try:
            raise error_fn()
        except errors.SIDMError as e:
            # Just show first 10 lines of error
            error_lines = str(e).split('\n')
            for line in error_lines[:10]:
                print(line)
            print(f"... ({len(error_lines) - 10} more lines)")


def main():
    """Main demonstration function."""
    # Argument parser
    parser = argparse.ArgumentParser(
        description="Demo script for logging and error handling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Normal mode (INFO level, colored)
  python pyscript/demo_logging_and_errors.py

  # Debug mode (DEBUG level)
  python pyscript/demo_logging_and_errors.py --debug

  # Quiet mode (ERROR only)
  python pyscript/demo_logging_and_errors.py --quiet

  # With file logging
  python pyscript/demo_logging_and_errors.py --log-file logs/demo.log

  # JSON logging
  python pyscript/demo_logging_and_errors.py --log-json --log-file logs/demo.jsonl

  # Verbose with file
  python pyscript/demo_logging_and_errors.py -vv --log-file logs/demo.log
        """
    )

    # Logging arguments
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=2,
        help="Increase verbosity (-v=INFO, -vv=DEBUG)"
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help="Quiet mode (errors only)"
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help="Debug mode (maximum verbosity)"
    )
    parser.add_argument(
        '--log-file',
        type=str,
        help="Log to file"
    )
    parser.add_argument(
        '--log-json',
        action='store_true',
        help="Use JSON log format"
    )

    # Demo selection
    parser.add_argument(
        '--demo',
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Run specific demo (1-5, default: all)"
    )

    args = parser.parse_args()

    # Configure logging
    configure_from_args(args)

    logger = get_logger(__name__)

    # Print header
    print("\n" + "="*70)
    print("SIDM2 LOGGING & ERROR HANDLING DEMO")
    print("="*70)
    print(f"\nLogging Configuration:")
    print(f"  Verbosity: {args.verbose} (0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG)")
    print(f"  Quiet: {args.quiet}")
    print(f"  Debug: {args.debug}")
    print(f"  Log File: {args.log_file or 'None (console only)'}")
    print(f"  JSON Format: {args.log_json}")
    print()

    logger.info("Demo script started")

    # Run demos
    if args.demo is None or args.demo == 1:
        demo_logging_levels()

    if args.demo is None or args.demo == 2:
        demo_structured_logging()

    if args.demo is None or args.demo == 3:
        demo_performance_logging()

    if args.demo is None or args.demo == 4:
        demo_error_handling()

    if args.demo == 5:
        demo_all_error_types()

    # Footer
    print("\n" + "="*70)
    print("DEMO COMPLETE")
    print("="*70)
    print("\nFor more information, see:")
    print("  - docs/guides/LOGGING_AND_ERROR_HANDLING_GUIDE.md")
    print("  - sidm2/logging_config.py (v2.0.0)")
    print("  - sidm2/errors.py (v1.0.0)")
    print()

    logger.info("Demo script completed")

    return 0


if __name__ == '__main__':
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
