"""
Demo/test script for the new error handling module.

This script demonstrates all the new error types and their output.
Run this to see how errors will look to users.

Usage:
    python test_errors_demo.py
"""

import os
import sys

# Add sidm2 to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sidm2 import errors


def demo_file_not_found():
    """Demonstrate FileNotFoundError with similar file suggestions."""
    print("\n" + "="*70)
    print("DEMO 1: File Not Found Error")
    print("="*70)

    try:
        raise errors.FileNotFoundError(
            path="SID/song.sid",
            context="input SID file",
            suggestions=[
                "Check the file path: python scripts/sid_to_sf2.py --help",
                "Use absolute path instead of relative",
                "List files: ls SID/ (or dir SID\\ on Windows)"
            ],
            docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md"
        )
    except errors.SIDMError as e:
        print(e)


def demo_invalid_input():
    """Demonstrate InvalidInputError for corrupted files."""
    print("\n" + "="*70)
    print("DEMO 2: Invalid Input Error")
    print("="*70)

    try:
        raise errors.InvalidInputError(
            input_type="SID file",
            value="corrupted_file.sid",
            expected="PSID or RSID format",
            got="Unknown magic bytes: ABCD",
            suggestions=[
                "Verify file is a valid SID file: file song.sid",
                "Re-download from HVSC or csdb.dk",
                "Use player-id tool: tools/player-id.exe song.sid",
                "Check file size (should be > 124 bytes)"
            ],
            docs_link="reference/format-specification.md"
        )
    except errors.SIDMError as e:
        print(e)


def demo_missing_dependency():
    """Demonstrate MissingDependencyError with install instructions."""
    print("\n" + "="*70)
    print("DEMO 3: Missing Dependency Error")
    print("="*70)

    try:
        raise errors.MissingDependencyError(
            dependency="sidm2.laxity_converter",
            install_command="pip install -e .",
            alternatives=[
                "Use standard drivers instead:",
                "  python scripts/sid_to_sf2.py song.sid output.sf2 --driver driver11",
                "",
                "Note: Standard drivers have 1-8% accuracy for Laxity files",
                "      (vs 99.93% with Laxity driver)"
            ],
            docs_link="README.md#installation"
        )
    except errors.SIDMError as e:
        print(e)


def demo_permission_error():
    """Demonstrate PermissionError with platform-specific hints."""
    print("\n" + "="*70)
    print("DEMO 4: Permission Error")
    print("="*70)

    try:
        raise errors.PermissionError(
            operation="write",
            path="output/protected_folder/output.sf2",
            docs_link="README.md#troubleshooting"
        )
    except errors.SIDMError as e:
        print(e)


def demo_configuration_error():
    """Demonstrate ConfigurationError with valid options."""
    print("\n" + "="*70)
    print("DEMO 5: Configuration Error")
    print("="*70)

    try:
        raise errors.ConfigurationError(
            setting="driver",
            value="invalid_driver",
            valid_options=["driver11", "driver12", "driver13", "driver14", "driver15", "driver16", "np20", "laxity"],
            example="python scripts/sid_to_sf2.py song.sid output.sf2 --driver laxity",
            docs_link="reference/DRIVER_REFERENCE.md"
        )
    except errors.SIDMError as e:
        print(e)


def demo_conversion_error():
    """Demonstrate ConversionError with diagnosis."""
    print("\n" + "="*70)
    print("DEMO 6: Conversion Error")
    print("="*70)

    try:
        raise errors.ConversionError(
            stage="table extraction",
            reason="Failed to locate instrument table in SID memory",
            input_file="SID/unknown_player.sid",
            suggestions=[
                "Check player format: tools/player-id.exe SID/unknown_player.sid",
                "Try different driver: --driver driver11",
                "Enable verbose logging: --verbose",
                "This file may use an unsupported player format"
            ],
            docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md#troubleshooting"
        )
    except errors.SIDMError as e:
        print(e)


def demo_custom_error():
    """Demonstrate custom error using base class."""
    print("\n" + "="*70)
    print("DEMO 7: Custom Error (Base Class)")
    print("="*70)

    try:
        raise errors.SIDMError(
            message="Custom Operation Failed",
            what_happened="The custom operation could not be completed",
            why_happened=[
                "Reason 1: Something went wrong",
                "Reason 2: Another thing failed",
                "Reason 3: Unexpected condition"
            ],
            how_to_fix=[
                "Try this first",
                "If that doesn't work, try this",
                "As a last resort, do this"
            ],
            alternatives=[
                "Alternative approach 1",
                "Alternative approach 2"
            ],
            docs_link="README.md",
            technical_details="Stack trace or debug info would go here"
        )
    except errors.SIDMError as e:
        print(e)


def demo_convenience_functions():
    """Demonstrate convenience functions for raising errors."""
    print("\n" + "="*70)
    print("DEMO 8: Convenience Functions")
    print("="*70)

    print("Example 1: Quick file not found")
    print("-" * 70)
    try:
        raise errors.file_not_found("missing.sid", "SID file")
    except errors.SIDMError as e:
        print(e)

    print("\n" + "-" * 70)
    print("Example 2: Quick invalid input")
    print("-" * 70)
    try:
        raise errors.invalid_input("configuration", "bad_value", expected="number", got="string")
    except errors.SIDMError as e:
        print(e)


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print(" SIDM2 ERROR HANDLING MODULE - DEMONSTRATION")
    print("="*70)
    print("\nThis demonstrates the new user-friendly error messages.")
    print("Each error includes:")
    print("  • Clear explanation of what happened")
    print("  • Why it happened (common causes)")
    print("  • How to fix it (step-by-step)")
    print("  • Documentation links")
    print("  • Alternative approaches")
    print("\n" + "="*70)

    demos = [
        demo_file_not_found,
        demo_invalid_input,
        demo_missing_dependency,
        demo_permission_error,
        demo_configuration_error,
        demo_conversion_error,
        demo_custom_error,
        demo_convenience_functions
    ]

    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\nUnexpected error in demo: {e}")

    print("\n" + "="*70)
    print(" END OF DEMONSTRATION")
    print("="*70)
    print("\nTo use these errors in your code:")
    print("  from sidm2.errors import FileNotFoundError, ConfigurationError, etc.")
    print("\nSee sidm2/errors.py for full API documentation.")
    print("\n")


if __name__ == "__main__":
    main()
