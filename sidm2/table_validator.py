"""
Table Size Validation Module

Provides comprehensive validation for extracted table sizes including:
- Size boundary checking
- Overlap detection
- Suspicious configuration warnings
- Memory layout verification
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation warnings"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ValidationIssue:
    """A validation issue found during table analysis"""
    severity: ValidationSeverity
    table_name: str
    issue_type: str
    message: str
    table_address: Optional[int] = None
    table_size: Optional[int] = None
    expected_size: Optional[int] = None

    def __str__(self):
        return f"[{self.severity.value}] {self.table_name}: {self.message}"


@dataclass
class TableValidationResult:
    """Results of table validation"""
    is_valid: bool
    tables_checked: int
    issues_found: List[ValidationIssue]
    warnings: List[ValidationIssue]
    errors: List[ValidationIssue]
    critical: List[ValidationIssue]

    @property
    def passed(self) -> bool:
        """Returns True if all checks passed (no critical or errors)"""
        return self.is_valid and len(self.errors) == 0 and len(self.critical) == 0


# Known table sizes for different player formats
KNOWN_TABLE_SIZES = {
    # Laxity NewPlayer v21 formats
    'laxity_instruments': 256,  # 8 bytes × 32 entries
    'laxity_wave': 256,         # 2 bytes × 128 entries or 4 bytes × 64 entries
    'laxity_pulse': 256,        # 4 bytes × 64 entries
    'laxity_filter': 128,       # 4 bytes × 32 entries
    'laxity_arpeggio': 256,     # 2 bytes × variable

    # Driver 11 / SF2 formats
    'driver11_sequence': 512,   # 256 entries × 2 bytes
    'driver11_instrument': 256, # 32 entries × 8 bytes
    'driver11_wave': 256,       # 128 entries × 2 bytes
    'driver11_pulse': 256,      # 64 entries × 4 bytes
    'driver11_filter': 128,     # 32 entries × 4 bytes

    # Generic expected ranges
    'instrument': (128, 512),
    'wave': (128, 512),
    'pulse': (128, 512),
    'filter': (64, 256),
    'sequence': (256, 2048),
    'arpeggio': (64, 512),
}


class TableValidator:
    """Validates extracted table sizes and configurations"""

    def __init__(self):
        """Initialize validator"""
        self.issues: List[ValidationIssue] = []

    def validate_tables(self,
                       tables: Dict[str, 'TableInfo'],
                       player_type: Optional[str] = None,
                       memory_end: int = 0xFFFF) -> TableValidationResult:
        """
        Validate extracted tables for consistency and correctness

        Args:
            tables: Dictionary of TableInfo objects (from extract_tables)
            player_type: Optional player type for format-specific validation
            memory_end: Upper memory boundary (default: $FFFF)

        Returns:
            TableValidationResult with all findings
        """
        self.issues = []
        warnings = []
        errors = []
        critical = []

        # Validate each table individually
        for table_name, table_info in tables.items():
            self._validate_single_table(table_name, table_info, errors, warnings)

        # Cross-table validation
        self._validate_table_overlaps(tables, errors, critical)
        self._validate_memory_boundaries(tables, memory_end, errors, warnings)
        self._validate_table_ordering(tables, errors, warnings)

        # Player-type specific validation
        if player_type:
            self._validate_player_format(tables, player_type, warnings, errors)

        # Categorize all issues
        all_issues = errors + warnings + critical
        for issue in all_issues:
            if issue.severity == ValidationSeverity.ERROR:
                errors.append(issue)
            elif issue.severity == ValidationSeverity.CRITICAL:
                critical.append(issue)
            elif issue.severity == ValidationSeverity.WARNING:
                warnings.append(issue)

        # Overall result
        is_valid = len(critical) == 0 and len(errors) == 0
        passed = is_valid

        return TableValidationResult(
            is_valid=passed,
            tables_checked=len(tables),
            issues_found=all_issues,
            warnings=warnings,
            errors=errors,
            critical=critical
        )

    def _validate_single_table(self,
                              table_name: str,
                              table_info,
                              errors: List[ValidationIssue],
                              warnings: List[ValidationIssue]):
        """Validate a single table for basic issues"""

        # Check if address is valid
        if table_info.address is None:
            errors.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                table_name=table_name,
                issue_type="MISSING_ADDRESS",
                message="Table address not specified",
            ))
            return

        # Check if address is in valid C64 memory range
        if table_info.address < 0x0000 or table_info.address > 0xFFFF:
            errors.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                table_name=table_name,
                issue_type="INVALID_ADDRESS",
                message=f"Address ${table_info.address:04X} outside C64 memory range",
                table_address=table_info.address
            ))
            return

        # Check if address is in reserved areas
        if 0x0000 <= table_info.address <= 0x001F:
            warnings.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                table_name=table_name,
                issue_type="RESERVED_AREA",
                message=f"Address ${table_info.address:04X} is in zero-page reserved area",
                table_address=table_info.address
            ))

        if 0xD000 <= table_info.address <= 0xDFFF:
            warnings.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                table_name=table_name,
                issue_type="SID_CHIP_AREA",
                message=f"Address ${table_info.address:04X} overlaps with SID chip registers",
                table_address=table_info.address
            ))

        # Check size if available
        if table_info.size is not None:
            if table_info.size < 0:
                errors.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    table_name=table_name,
                    issue_type="NEGATIVE_SIZE",
                    message=f"Table size is negative: {table_info.size}",
                    table_address=table_info.address,
                    table_size=table_info.size
                ))
            elif table_info.size == 0:
                warnings.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    table_name=table_name,
                    issue_type="ZERO_SIZE",
                    message="Table size is zero",
                    table_address=table_info.address,
                    table_size=0
                ))
            elif table_info.size > 16384:  # 16KB is unusual
                warnings.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    table_name=table_name,
                    issue_type="EXCESSIVE_SIZE",
                    message=f"Table size is very large: {table_info.size} bytes",
                    table_address=table_info.address,
                    table_size=table_info.size
                ))

            # Check if table fits in memory
            table_end = table_info.address + table_info.size - 1
            if table_end > 0xFFFF:
                errors.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    table_name=table_name,
                    issue_type="EXCEEDS_MEMORY",
                    message=f"Table extends beyond C64 memory (ends at ${table_end:05X})",
                    table_address=table_info.address,
                    table_size=table_info.size
                ))

    def _validate_table_overlaps(self,
                                tables: Dict[str, 'TableInfo'],
                                errors: List[ValidationIssue],
                                critical: List[ValidationIssue]):
        """Check for overlapping table regions"""

        table_list = list(tables.items())

        for i, (name1, table1) in enumerate(table_list):
            if table1.address is None or table1.size is None:
                continue

            end1 = table1.address + table1.size

            for name2, table2 in table_list[i+1:]:
                if table2.address is None or table2.size is None:
                    continue

                end2 = table2.address + table2.size

                # Check for overlap
                if not (end1 <= table2.address or end2 <= table1.address):
                    # Tables overlap
                    overlap_start = max(table1.address, table2.address)
                    overlap_end = min(end1, end2)
                    overlap_size = overlap_end - overlap_start

                    critical.append(ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        table_name=f"{name1} <-> {name2}",
                        issue_type="TABLE_OVERLAP",
                        message=f"Tables overlap by {overlap_size} bytes at ${overlap_start:04X}-${overlap_end:04X}",
                        table_address=overlap_start,
                        table_size=overlap_size
                    ))

    def _validate_memory_boundaries(self,
                                   tables: Dict[str, 'TableInfo'],
                                   memory_end: int,
                                   errors: List[ValidationIssue],
                                   warnings: List[ValidationIssue]):
        """Check if tables respect memory boundaries"""

        for table_name, table_info in tables.items():
            if table_info.address is None:
                continue

            # Check against upper boundary
            if table_info.address > memory_end:
                errors.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    table_name=table_name,
                    issue_type="EXCEEDS_BOUNDARY",
                    message=f"Table at ${table_info.address:04X} exceeds memory boundary ${memory_end:04X}",
                    table_address=table_info.address
                ))

            # Warn if too close to boundary
            if table_info.size and table_info.address + table_info.size > memory_end - 256:
                warnings.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    table_name=table_name,
                    issue_type="CLOSE_TO_BOUNDARY",
                    message=f"Table approaches memory boundary (ends at ${table_info.address + table_info.size:04X})",
                    table_address=table_info.address,
                    table_size=table_info.size
                ))

    def _validate_table_ordering(self,
                                tables: Dict[str, 'TableInfo'],
                                errors: List[ValidationIssue],
                                warnings: List[ValidationIssue]):
        """Check if tables are in logical order"""

        # Sort tables by address
        sorted_tables = sorted(
            [(name, info) for name, info in tables.items() if info.address],
            key=lambda x: x[1].address
        )

        # Check for unusual gaps or ordering
        for i in range(len(sorted_tables) - 1):
            name1, table1 = sorted_tables[i]
            name2, table2 = sorted_tables[i + 1]

            if table1.size:
                end1 = table1.address + table1.size
                gap = table2.address - end1

                # Warn about very large gaps
                if gap > 4096:  # > 4KB gap is unusual
                    warnings.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        table_name=f"{name1} -> {name2}",
                        issue_type="LARGE_GAP",
                        message=f"Large gap of {gap} bytes between tables",
                        table_address=end1,
                        table_size=gap
                    ))

    def _validate_player_format(self,
                               tables: Dict[str, 'TableInfo'],
                               player_type: str,
                               warnings: List[ValidationIssue],
                               errors: List[ValidationIssue]):
        """Validate tables based on detected player format"""

        player_type_lower = player_type.lower()

        if 'laxity' in player_type_lower:
            self._validate_laxity_tables(tables, errors, warnings)
        elif 'driver11' in player_type_lower or 'driver 11' in player_type_lower:
            self._validate_driver11_tables(tables, errors, warnings)

    def _validate_laxity_tables(self,
                               tables: Dict[str, 'TableInfo'],
                               errors: List[ValidationIssue],
                               warnings: List[ValidationIssue]):
        """Validate Laxity-specific table configuration"""

        expected_tables = {'filter', 'pulse', 'instrument', 'wave'}
        found_tables = {info.type for info in tables.values() if info.type}

        for expected in expected_tables:
            if expected not in found_tables:
                warnings.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    table_name=f"laxity_{expected}",
                    issue_type="MISSING_TABLE",
                    message=f"Expected {expected} table not found in Laxity format"
                ))

        # Validate Laxity memory layout expectations
        # Typically: instruments ~$1A6B, wave ~$1ACB, pulse ~$1A3B, filter ~$1A1E
        for table_name, table_info in tables.items():
            if table_info.type == 'instrument' and (table_info.address < 0x1900 or table_info.address > 0x1B00):
                warnings.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    table_name=table_name,
                    issue_type="UNEXPECTED_LOCATION",
                    message=f"Instrument table at ${table_info.address:04X}, expected ~$1A6B",
                    table_address=table_info.address
                ))

    def _validate_driver11_tables(self,
                                 tables: Dict[str, 'TableInfo'],
                                 errors: List[ValidationIssue],
                                 warnings: List[ValidationIssue]):
        """Validate Driver 11 / SF2-specific table configuration"""

        expected_tables = {'sequence', 'instrument', 'wave', 'pulse', 'filter'}
        found_tables = {info.type for info in tables.values() if info.type}

        for expected in expected_tables:
            if expected not in found_tables:
                warnings.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    table_name=f"driver11_{expected}",
                    issue_type="MISSING_TABLE",
                    message=f"Expected {expected} table not found in Driver 11 format"
                ))

        # Driver 11 tables typically start at specific offsets
        for table_name, table_info in tables.items():
            if table_info.type == 'sequence':
                # Sequences usually at $0903 for Driver 11
                if table_info.address not in (0x0903, 0x0A03, 0x0B03, 0x0C03):
                    warnings.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        table_name=table_name,
                        issue_type="UNUSUAL_OFFSET",
                        message=f"Sequence table at unusual address ${table_info.address:04X}",
                        table_address=table_info.address
                    ))

    def generate_report(self, result: TableValidationResult) -> str:
        """Generate a detailed validation report"""

        lines = []
        lines.append("=" * 80)
        lines.append("TABLE VALIDATION REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Summary
        lines.append("SUMMARY:")
        lines.append("-" * 80)
        lines.append(f"Tables Checked: {result.tables_checked}")
        lines.append(f"Status: {'PASSED' if result.passed else 'FAILED'}")
        lines.append(f"Total Issues: {len(result.issues_found)}")
        lines.append(f"  - Critical: {len(result.critical)}")
        lines.append(f"  - Errors: {len(result.errors)}")
        lines.append(f"  - Warnings: {len(result.warnings)}")
        lines.append("")

        # Critical issues
        if result.critical:
            lines.append("CRITICAL ISSUES:")
            lines.append("-" * 80)
            for issue in result.critical:
                lines.append(f"  {issue}")
            lines.append("")

        # Errors
        if result.errors:
            lines.append("ERRORS:")
            lines.append("-" * 80)
            for issue in result.errors:
                lines.append(f"  {issue}")
            lines.append("")

        # Warnings
        if result.warnings:
            lines.append("WARNINGS:")
            lines.append("-" * 80)
            for issue in result.warnings:
                lines.append(f"  {issue}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)
