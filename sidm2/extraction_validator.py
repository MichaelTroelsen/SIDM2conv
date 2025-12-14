"""
Enhanced Table Extraction Validation System

Provides comprehensive validation for SID table extraction including:
- Table integrity checking
- Extraction completeness verification
- Data consistency validation
- Accuracy metrics
- Extraction quality reporting
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re


@dataclass
class ExtractionQualityMetrics:
    """Metrics for table extraction quality"""
    completeness: float      # 0.0-1.0: percentage of expected tables found
    consistency: float       # 0.0-1.0: consistency of table data
    integrity: float         # 0.0-1.0: data integrity check results
    accuracy_estimate: float # 0.0-1.0: estimated conversion accuracy
    warnings_count: int
    errors_count: int
    critical_count: int

    @property
    def overall_quality(self) -> float:
        """Calculate overall quality score"""
        return (self.completeness * 0.3 +
                self.consistency * 0.3 +
                self.integrity * 0.4)


@dataclass
class ExtractionValidationIssue:
    """An issue found during extraction validation"""
    severity: str  # 'critical', 'error', 'warning', 'info'
    category: str  # 'completeness', 'consistency', 'integrity', 'format'
    table_name: str
    issue: str
    details: Optional[str] = None


class ExtractionValidator:
    """Validates table extraction from SID files"""

    def __init__(self):
        """Initialize validator"""
        self.issues: List[ExtractionValidationIssue] = []

    def validate_extraction(self,
                          tables: Dict,
                          player_type: str,
                          asm_file: Optional[Path] = None) -> ExtractionQualityMetrics:
        """
        Validate extracted tables

        Args:
            tables: Dictionary of extracted tables
            player_type: Detected player type
            asm_file: Optional path to assembly file for detailed validation

        Returns:
            ExtractionQualityMetrics with validation results
        """
        self.issues = []

        # Check completeness
        completeness = self._validate_completeness(tables, player_type)

        # Check consistency
        consistency = self._validate_consistency(tables)

        # Check integrity
        integrity = self._validate_integrity(tables, asm_file)

        # Estimate accuracy based on extraction quality
        accuracy = self._estimate_accuracy(player_type, completeness, consistency, integrity)

        # Categorize issues
        critical = [i for i in self.issues if i.severity == 'critical']
        errors = [i for i in self.issues if i.severity == 'error']
        warnings = [i for i in self.issues if i.severity == 'warning']

        return ExtractionQualityMetrics(
            completeness=completeness,
            consistency=consistency,
            integrity=integrity,
            accuracy_estimate=accuracy,
            warnings_count=len(warnings),
            errors_count=len(errors),
            critical_count=len(critical)
        )

    def _validate_completeness(self, tables: Dict, player_type: str) -> float:
        """Validate that expected tables are present"""

        # Define expected tables per player type
        expected_tables = {
            'laxity': {'filter', 'pulse', 'instrument', 'wave'},
            'driver11': {'sequence', 'instrument', 'wave', 'pulse', 'filter'},
            'np20': {'sequence', 'instrument', 'wave', 'pulse', 'filter'},
        }

        player_lower = player_type.lower()
        expected = expected_tables.get(player_lower, set())

        if not expected:
            return 1.0  # Unknown player, can't validate

        # Find which tables are present
        found_types = set()
        for table_name, table_info in tables.items():
            if hasattr(table_info, 'type') and table_info.type:
                found_types.add(table_info.type.lower())

        # Calculate completeness
        if expected:
            found_count = len(found_types & expected)
            completeness = found_count / len(expected)
        else:
            completeness = 0.5  # Default if unknown

        # Report missing tables
        missing = expected - found_types
        for missing_type in missing:
            self.issues.append(ExtractionValidationIssue(
                severity='warning',
                category='completeness',
                table_name=missing_type,
                issue=f"Expected {missing_type} table not found",
                details=f"Player type {player_type} typically has {missing_type} table"
            ))

        return completeness

    def _validate_consistency(self, tables: Dict) -> float:
        """Validate that extracted data is consistent"""

        consistency_score = 1.0

        # Check each table
        for table_name, table_info in tables.items():
            # Validate table has required attributes
            if not hasattr(table_info, 'address') or table_info.address is None:
                self.issues.append(ExtractionValidationIssue(
                    severity='error',
                    category='consistency',
                    table_name=table_name,
                    issue='Table address missing',
                    details='All tables must have valid addresses'
                ))
                consistency_score *= 0.8

            # Validate address is reasonable
            if hasattr(table_info, 'address'):
                addr = table_info.address
                if not (0x0000 <= addr <= 0xFFFF):
                    self.issues.append(ExtractionValidationIssue(
                        severity='error',
                        category='consistency',
                        table_name=table_name,
                        issue=f'Invalid address ${addr:05X}',
                        details='Address must be within C64 memory range'
                    ))
                    consistency_score *= 0.5

            # Validate size if present
            if hasattr(table_info, 'size') and table_info.size:
                size = table_info.size
                if size <= 0:
                    self.issues.append(ExtractionValidationIssue(
                        severity='error',
                        category='consistency',
                        table_name=table_name,
                        issue=f'Invalid size {size}',
                        details='Table size must be positive'
                    ))
                    consistency_score *= 0.8

                if size > 16384:
                    self.issues.append(ExtractionValidationIssue(
                        severity='warning',
                        category='consistency',
                        table_name=table_name,
                        issue=f'Unusually large size {size}',
                        details='Table size over 16KB is unusual'
                    ))
                    consistency_score *= 0.9

        return max(0.0, consistency_score)

    def _validate_integrity(self, tables: Dict, asm_file: Optional[Path] = None) -> float:
        """Validate data integrity"""

        integrity_score = 1.0

        # Check for table overlaps (already done in another validator, but check here too)
        table_list = [(name, info) for name, info in tables.items()
                     if hasattr(info, 'address') and hasattr(info, 'size')]

        for i, (name1, info1) in enumerate(table_list):
            if not (hasattr(info1, 'address') and hasattr(info1, 'size')):
                continue

            end1 = info1.address + info1.size

            for name2, info2 in table_list[i+1:]:
                if not (hasattr(info2, 'address') and hasattr(info2, 'size')):
                    continue

                end2 = info2.address + info2.size

                # Check for overlap
                if not (end1 <= info2.address or end2 <= info1.address):
                    self.issues.append(ExtractionValidationIssue(
                        severity='critical',
                        category='integrity',
                        table_name=f"{name1} + {name2}",
                        issue='Tables overlap in memory',
                        details=f'{name1} and {name2} occupy same memory region'
                    ))
                    integrity_score *= 0.1

        # Validate against disassembly if available
        if asm_file and asm_file.exists():
            integrity_score = self._validate_against_disassembly(tables, asm_file, integrity_score)

        return max(0.0, integrity_score)

    def _validate_against_disassembly(self, tables: Dict, asm_file: Path, base_score: float) -> float:
        """Validate tables against disassembly"""

        try:
            with open(asm_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Look for table references in disassembly
            found_references = 0
            expected_references = len(tables)

            for table_name in tables.keys():
                # Look for table name or references in assembly
                if table_name.lower() in content.lower():
                    found_references += 1

            # Adjust integrity based on found references
            if expected_references > 0:
                reference_ratio = found_references / expected_references
                return base_score * max(0.5, reference_ratio)

        except Exception as e:
            # Can't validate, return base score
            pass

        return base_score

    def _estimate_accuracy(self,
                          player_type: str,
                          completeness: float,
                          consistency: float,
                          integrity: float) -> float:
        """Estimate conversion accuracy based on extraction quality"""

        # Base accuracy depends on player type
        player_lower = player_type.lower()

        if 'laxity' in player_lower:
            base_accuracy = 0.70  # Laxity conversion is inherently lower
        elif 'driver' in player_lower or 'np20' in player_lower:
            base_accuracy = 0.95  # Driver formats are more compatible
        else:
            base_accuracy = 0.50  # Unknown format

        # Apply extraction quality penalties
        extraction_quality = (completeness * 0.3 + consistency * 0.3 + integrity * 0.4)

        accuracy = base_accuracy * extraction_quality

        return min(1.0, max(0.0, accuracy))

    def generate_validation_report(self, metrics: ExtractionQualityMetrics) -> str:
        """Generate detailed validation report"""

        lines = []

        lines.append("=" * 100)
        lines.append("TABLE EXTRACTION VALIDATION REPORT")
        lines.append("=" * 100)
        lines.append("")

        # Summary metrics
        lines.append("QUALITY METRICS:")
        lines.append("-" * 100)
        lines.append(f"Completeness:      {metrics.completeness*100:6.1f}%  (expected tables found)")
        lines.append(f"Consistency:       {metrics.consistency*100:6.1f}%  (data validity)")
        lines.append(f"Integrity:         {metrics.integrity*100:6.1f}%  (no overlaps, valid ranges)")
        lines.append(f"Overall Quality:   {metrics.overall_quality*100:6.1f}%")
        lines.append(f"Accuracy Estimate: {metrics.accuracy_estimate*100:6.1f}%")
        lines.append("")

        # Issue summary
        lines.append("ISSUES FOUND:")
        lines.append("-" * 100)
        lines.append(f"Critical: {metrics.critical_count}")
        lines.append(f"Errors:   {metrics.errors_count}")
        lines.append(f"Warnings: {metrics.warnings_count}")
        lines.append("")

        # Issue details
        if self.issues:
            lines.append("ISSUE DETAILS:")
            lines.append("-" * 100)

            # Group by severity
            critical_issues = [i for i in self.issues if i.severity == 'critical']
            error_issues = [i for i in self.issues if i.severity == 'error']
            warning_issues = [i for i in self.issues if i.severity == 'warning']

            if critical_issues:
                lines.append("CRITICAL:")
                for issue in critical_issues:
                    lines.append(f"  [{issue.category.upper()}] {issue.table_name}")
                    lines.append(f"    -> {issue.issue}")
                    if issue.details:
                        lines.append(f"    -> Details: {issue.details}")
                lines.append("")

            if error_issues:
                lines.append("ERRORS:")
                for issue in error_issues:
                    lines.append(f"  [{issue.category.upper()}] {issue.table_name}")
                    lines.append(f"    -> {issue.issue}")
                lines.append("")

            if warning_issues:
                lines.append("WARNINGS:")
                for issue in warning_issues:
                    lines.append(f"  [{issue.category.upper()}] {issue.table_name}")
                    lines.append(f"    -> {issue.issue}")
                lines.append("")

        # Recommendations
        lines.append("RECOMMENDATIONS:")
        lines.append("-" * 100)

        if metrics.critical_count > 0:
            lines.append("  • Critical issues detected - extraction may be invalid")
            lines.append("  • Review table addresses and ensure no overlaps")

        if metrics.completeness < 0.80:
            lines.append("  • Some expected tables are missing")
            lines.append("  • This may reduce conversion accuracy")

        if metrics.accuracy_estimate < 0.50:
            lines.append("  • Low accuracy estimate - manual review recommended")
            lines.append("  • Consider alternative conversion methods")

        if metrics.warnings_count > 0:
            lines.append("  • Review warnings for potential issues")

        if metrics.overall_quality >= 0.80:
            lines.append("  • Extraction quality is good - proceed with conversion")

        lines.append("")
        lines.append("=" * 100)

        return "\n".join(lines)
