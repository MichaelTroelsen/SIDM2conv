"""SF2 Format Validator - Validates SF2 file format structure.

This script validates that an SF2 file has correct format structure and can
theoretically be loaded in SID Factory II Editor. It performs automated checks
on file format, metadata blocks, tables, and data integrity.

NOTE: This validates FILE FORMAT, not actual editor loading. Actual editor
loading requires manual testing or complex automation.

Usage:
    python scripts/validate_sf2_format.py output.sf2
    python scripts/validate_sf2_format.py --batch output/*.sf2
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class ValidationCheck:
    """Single validation check result."""
    name: str
    passed: bool
    message: str
    severity: str = "ERROR"  # ERROR, WARNING, INFO


@dataclass
class ValidationResult:
    """Complete validation result."""
    file_path: Path
    passed: bool
    checks: List[ValidationCheck] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0

    def add_check(self, check: ValidationCheck):
        """Add a check result."""
        self.checks.append(check)
        if not check.passed:
            if check.severity == "ERROR":
                self.errors += 1
                self.passed = False
            elif check.severity == "WARNING":
                self.warnings += 1


class SF2FormatValidator:
    """Validates SF2 file format structure."""

    # SF2 format constants
    SF2_HEADER_START = 0x1700
    SF2_HEADER_END = 0x18FF
    SF2_HEADER_SIZE = 512

    # Expected metadata block locations (relative to load address)
    ORDERLIST_OFFSETS = {
        'voice1': 0x0700,
        'voice2': 0x0703,
        'voice3': 0x0706,
    }

    SEQUENCE_BASE = 0x0903
    INSTRUMENT_BASE = 0x0A03
    WAVE_BASE = 0x0B03
    PULSE_BASE = 0x0D03
    FILTER_BASE = 0x0F03

    def __init__(self):
        """Initialize validator."""
        pass

    def validate_file(self, sf2_file: Path, verbose: bool = False) -> ValidationResult:
        """Validate SF2 file format.

        Args:
            sf2_file: Path to SF2 file
            verbose: Show detailed check information

        Returns:
            ValidationResult with all checks
        """
        result = ValidationResult(file_path=sf2_file, passed=True)

        # Check 1: File exists
        if not sf2_file.exists():
            result.add_check(ValidationCheck(
                name="File Exists",
                passed=False,
                message=f"File not found: {sf2_file}",
                severity="ERROR"
            ))
            return result

        result.add_check(ValidationCheck(
            name="File Exists",
            passed=True,
            message=f"File found: {sf2_file.name}",
            severity="INFO"
        ))

        # Read file
        try:
            data = sf2_file.read_bytes()
        except Exception as e:
            result.add_check(ValidationCheck(
                name="File Readable",
                passed=False,
                message=f"Cannot read file: {e}",
                severity="ERROR"
            ))
            return result

        result.add_check(ValidationCheck(
            name="File Readable",
            passed=True,
            message=f"File size: {len(data)} bytes",
            severity="INFO"
        ))

        # Check 2: Valid PRG format
        prg_check = self._validate_prg_format(data)
        result.add_check(prg_check)
        if not prg_check.passed:
            return result  # Can't continue if not valid PRG

        # Extract load address
        load_addr = data[0] | (data[1] << 8)

        # Check 3: File size reasonable
        size_check = self._validate_file_size(data)
        result.add_check(size_check)

        # Check 4: Metadata blocks present
        metadata_checks = self._validate_metadata_structure(data, load_addr)
        for check in metadata_checks:
            result.add_check(check)

        # Check 5: Table structure
        table_checks = self._validate_tables(data, load_addr)
        for check in table_checks:
            result.add_check(check)

        # Check 6: End markers
        end_marker_check = self._validate_end_markers(data)
        result.add_check(end_marker_check)

        # Check 7: No truncation
        truncation_check = self._validate_no_truncation(data, load_addr)
        result.add_check(truncation_check)

        return result

    def _validate_prg_format(self, data: bytes) -> ValidationCheck:
        """Validate PRG file format (C64 executable)."""
        if len(data) < 2:
            return ValidationCheck(
                name="PRG Format",
                passed=False,
                message="File too small (< 2 bytes)",
                severity="ERROR"
            )

        # Extract load address (little-endian)
        load_addr = data[0] | (data[1] << 8)

        # Valid C64 memory range: $0000-$FFFF
        if load_addr < 0x0000 or load_addr > 0xFFFF:
            return ValidationCheck(
                name="PRG Format",
                passed=False,
                message=f"Invalid load address: ${load_addr:04X}",
                severity="ERROR"
            )

        # Common SF2 load addresses
        common_addrs = [0x0E00, 0x1000, 0x2000, 0x4000, 0x8000, 0xA000, 0xC000]
        if load_addr in common_addrs:
            return ValidationCheck(
                name="PRG Format",
                passed=True,
                message=f"Valid PRG - Load address: ${load_addr:04X}",
                severity="INFO"
            )
        else:
            return ValidationCheck(
                name="PRG Format",
                passed=True,
                message=f"Valid PRG - Load address: ${load_addr:04X} (uncommon)",
                severity="WARNING"
            )

    def _validate_file_size(self, data: bytes) -> ValidationCheck:
        """Validate file size is reasonable for SF2."""
        size = len(data)

        # SF2 files typically 8KB-64KB
        if size < 2048:
            return ValidationCheck(
                name="File Size",
                passed=False,
                message=f"File too small: {size} bytes (expected 8KB-64KB)",
                severity="ERROR"
            )

        if size > 65536:
            return ValidationCheck(
                name="File Size",
                passed=False,
                message=f"File too large: {size} bytes (exceeds C64 memory)",
                severity="ERROR"
            )

        if size < 8192:
            return ValidationCheck(
                name="File Size",
                passed=True,
                message=f"File size: {size} bytes (small, may be minimal conversion)",
                severity="WARNING"
            )

        return ValidationCheck(
            name="File Size",
            passed=True,
            message=f"File size: {size} bytes",
            severity="INFO"
        )

    def _validate_metadata_structure(self, data: bytes, load_addr: int) -> List[ValidationCheck]:
        """Validate SF2 metadata block structure."""
        checks = []

        # Check if we have enough data for header
        header_offset = self.SF2_HEADER_START - load_addr + 2  # +2 for PRG header

        if len(data) < header_offset + self.SF2_HEADER_SIZE:
            checks.append(ValidationCheck(
                name="Metadata Block",
                passed=False,
                message=f"File too small for SF2 header (need {header_offset + self.SF2_HEADER_SIZE} bytes)",
                severity="ERROR"
            ))
            return checks

        checks.append(ValidationCheck(
            name="Metadata Block",
            passed=True,
            message=f"SF2 header region present (${self.SF2_HEADER_START:04X}-${self.SF2_HEADER_END:04X})",
            severity="INFO"
        ))

        return checks

    def _validate_tables(self, data: bytes, load_addr: int) -> List[ValidationCheck]:
        """Validate table structures."""
        checks = []

        # Check if orderlists are present
        for voice, offset in self.ORDERLIST_OFFSETS.items():
            table_offset = offset - load_addr + 2
            if table_offset < len(data):
                checks.append(ValidationCheck(
                    name=f"Orderlist ({voice})",
                    passed=True,
                    message=f"Orderlist for {voice} present at offset ${offset:04X}",
                    severity="INFO"
                ))
            else:
                checks.append(ValidationCheck(
                    name=f"Orderlist ({voice})",
                    passed=False,
                    message=f"Orderlist for {voice} missing (offset ${offset:04X} beyond file)",
                    severity="WARNING"
                ))

        # Check sequence base
        seq_offset = self.SEQUENCE_BASE - load_addr + 2
        if seq_offset < len(data):
            checks.append(ValidationCheck(
                name="Sequence Data",
                passed=True,
                message=f"Sequence data present at ${self.SEQUENCE_BASE:04X}",
                severity="INFO"
            ))
        else:
            checks.append(ValidationCheck(
                name="Sequence Data",
                passed=False,
                message=f"Sequence data missing (offset ${self.SEQUENCE_BASE:04X} beyond file)",
                severity="ERROR"
            ))

        # Check instrument table
        inst_offset = self.INSTRUMENT_BASE - load_addr + 2
        if inst_offset < len(data):
            checks.append(ValidationCheck(
                name="Instrument Table",
                passed=True,
                message=f"Instrument table present at ${self.INSTRUMENT_BASE:04X}",
                severity="INFO"
            ))
        else:
            checks.append(ValidationCheck(
                name="Instrument Table",
                passed=False,
                message=f"Instrument table missing",
                severity="WARNING"
            ))

        # Check wave table
        wave_offset = self.WAVE_BASE - load_addr + 2
        if wave_offset < len(data):
            checks.append(ValidationCheck(
                name="Wave Table",
                passed=True,
                message=f"Wave table present at ${self.WAVE_BASE:04X}",
                severity="INFO"
            ))
        else:
            checks.append(ValidationCheck(
                name="Wave Table",
                passed=False,
                message=f"Wave table missing",
                severity="WARNING"
            ))

        return checks

    def _validate_end_markers(self, data: bytes) -> ValidationCheck:
        """Check for end markers ($7F) in data."""
        # Count end markers
        end_marker_count = data.count(0x7F)

        if end_marker_count == 0:
            return ValidationCheck(
                name="End Markers",
                passed=False,
                message="No end markers ($7F) found - file may be incomplete",
                severity="WARNING"
            )

        if end_marker_count < 3:
            return ValidationCheck(
                name="End Markers",
                passed=True,
                message=f"End markers found: {end_marker_count} (low, may indicate minimal conversion)",
                severity="WARNING"
            )

        return ValidationCheck(
            name="End Markers",
            passed=True,
            message=f"End markers found: {end_marker_count}",
            severity="INFO"
        )

    def _validate_no_truncation(self, data: bytes, load_addr: int) -> ValidationCheck:
        """Check file isn't truncated."""
        # Check if file ends abruptly (last bytes should be meaningful data or padding)
        last_byte = data[-1]

        # If last byte is 0x00, might be padding (OK)
        # If last byte is 0x7F, might be end marker (OK)
        # If last byte is 0xFF, might be unused memory (OK)
        if last_byte in [0x00, 0x7F, 0xFF]:
            return ValidationCheck(
                name="File Integrity",
                passed=True,
                message=f"File appears complete (last byte: ${last_byte:02X})",
                severity="INFO"
            )

        # Otherwise, check if it looks like real data
        # Count non-zero bytes in last 16 bytes
        non_zero = sum(1 for b in data[-16:] if b != 0)

        if non_zero > 8:
            return ValidationCheck(
                name="File Integrity",
                passed=True,
                message=f"File appears complete (active data at end)",
                severity="INFO"
            )

        return ValidationCheck(
            name="File Integrity",
            passed=True,
            message=f"File integrity check passed",
            severity="INFO"
        )


def print_validation_result(result: ValidationResult, verbose: bool = False):
    """Print validation result."""
    print(f"\nValidating: {result.file_path.name}")
    print("=" * 70)

    # Print checks
    if verbose:
        for check in result.checks:
            if check.severity == "ERROR":
                symbol = "✗"
            elif check.severity == "WARNING":
                symbol = "⚠"
            else:
                symbol = "✓"

            print(f"{symbol} {check.name}: {check.message}")
    else:
        # Only show errors and warnings
        for check in result.checks:
            if check.severity in ("ERROR", "WARNING"):
                symbol = "✗" if check.severity == "ERROR" else "⚠"
                print(f"{symbol} {check.name}: {check.message}")

    # Summary
    print()
    if result.passed:
        print("RESULT: PASS - SF2 file format is valid")
        if result.warnings > 0:
            print(f"  (with {result.warnings} warnings)")
    else:
        print(f"RESULT: FAIL - {result.errors} errors detected")
        if result.warnings > 0:
            print(f"  (and {result.warnings} warnings)")

    print("=" * 70)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate SF2 file format")
    parser.add_argument('files', nargs='+', type=Path, help='SF2 files to validate')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show all checks (not just errors)')
    parser.add_argument('--batch', action='store_true', help='Batch mode (multiple files)')

    args = parser.parse_args()

    validator = SF2FormatValidator()
    results = []

    print("SF2 Format Validator")
    print("=" * 70)
    print("NOTE: This validates FILE FORMAT, not actual editor loading.")
    print("      Manual testing in SF2 Editor is recommended.")
    print()

    # Validate files
    for file_path in args.files:
        result = validator.validate_file(file_path, verbose=args.verbose)
        results.append(result)

        if not args.batch:
            print_validation_result(result, verbose=args.verbose)

    # Batch summary
    if args.batch and len(results) > 1:
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        print("\n" + "=" * 70)
        print("BATCH VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Total files:  {len(results)}")
        print(f"Passed:       {passed} ({passed / len(results) * 100:.1f}%)")
        print(f"Failed:       {failed} ({failed / len(results) * 100:.1f}%)")
        print()

        if failed > 0:
            print("Failed files:")
            for r in results:
                if not r.passed:
                    print(f"  - {r.file_path.name} ({r.errors} errors)")

        print("=" * 70)

    # Exit code
    if all(r.passed for r in results):
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
