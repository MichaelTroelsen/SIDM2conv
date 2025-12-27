"""
SF2 Format Compatibility Analysis Module

Analyzes SID files and SID Factory II format compatibility including:
- Driver feature support
- Table format compatibility
- Memory layout requirements
- Conversion accuracy predictions
- Format-specific limitations
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .errors import ConfigurationError


class CompatibilityStatus(Enum):
    """Compatibility status levels"""
    FULL = "FULL"          # 100% compatible
    HIGH = "HIGH"          # 85-99% compatible
    MEDIUM = "MEDIUM"      # 50-84% compatible
    LOW = "LOW"            # 10-49% compatible
    NONE = "NONE"          # 0-9% compatible


@dataclass
class DriverFeature:
    """Describes a driver feature"""
    name: str
    description: str
    supported: bool
    notes: Optional[str] = None


@dataclass
class CompatibilityIssue:
    """Describes a compatibility issue"""
    severity: str  # 'critical', 'high', 'medium', 'low'
    category: str  # 'format', 'feature', 'memory', 'table'
    issue: str
    recommendation: str


@dataclass
class DriverProfile:
    """Profile of an SF2 driver"""
    name: str
    version: Optional[str]
    features: Dict[str, DriverFeature]
    table_formats: Dict[str, str]  # table_type -> format description
    memory_requirements: Dict[str, int]  # 'code_size', 'data_size', 'max_tables'
    limitations: List[str]
    accuracy_estimate: float  # 0.0-1.0 for conversion accuracy


@dataclass
class CompatibilityResult:
    """Result of compatibility analysis"""
    source_format: str
    target_driver: str
    overall_status: CompatibilityStatus
    accuracy_estimate: float  # 0.0-1.0
    compatible_features: int
    total_features: int
    issues: List[CompatibilityIssue]
    recommendations: List[str]

    def __str__(self):
        return (f"{self.source_format} -> {self.target_driver}: "
                f"{self.overall_status.value} "
                f"({self.compatible_features}/{self.total_features} features, "
                f"{self.accuracy_estimate*100:.0f}% accuracy)")


# Known driver profiles for SF2
DRIVER_PROFILES = {
    'Driver11': DriverProfile(
        name='Driver 11',
        version='SF2 Standard',
        features={
            'sequences': DriverFeature('Sequences', 'Sequence playback', True),
            'instruments': DriverFeature('Instruments', 'Instrument definitions', True),
            'wave': DriverFeature('Wave Table', 'Waveform table', True),
            'pulse': DriverFeature('Pulse Table', 'Pulse/PWM control', True),
            'filter': DriverFeature('Filter Table', 'Filter settings', True),
            'arpeggio': DriverFeature('Arpeggio', 'Arpeggio patterns', True),
            'hardrestart': DriverFeature('Hard Restart', 'Gate control', True),
            'effects': DriverFeature('Effects', 'Special effects', True),
            'transpose': DriverFeature('Transpose', 'Note transposition', True),
        },
        table_formats={
            'sequence': '2 bytes per entry',
            'instrument': '8 bytes per entry, 32 max',
            'wave': '2 bytes per entry, 128 max',
            'pulse': '4 bytes per entry, 64 max',
            'filter': '4 bytes per entry, 32 max',
        },
        memory_requirements={
            'code_size': 6656,
            'data_size': 2048,
            'max_tables': 5,
            'min_free': 512,
        },
        limitations=[
            'No Laxity NewPlayer v21 specific features',
            'Filter format incompatible with Laxity',
            'Arpeggio implementation differs from Laxity',
        ],
        accuracy_estimate=1.0,
    ),
    'NP20': DriverProfile(
        name='JCH NewPlayer v20',
        version='NP20',
        features={
            'sequences': DriverFeature('Sequences', 'Sequence playback', True),
            'instruments': DriverFeature('Instruments', 'Instrument definitions', True),
            'wave': DriverFeature('Wave Table', 'Waveform table', True),
            'pulse': DriverFeature('Pulse Table', 'Pulse/PWM control', True),
            'filter': DriverFeature('Filter Table', 'Filter settings', True),
            'arpeggio': DriverFeature('Arpeggio', 'Arpeggio patterns', True),
            'hardrestart': DriverFeature('Hard Restart', 'Gate control', True),
            'effects': DriverFeature('Effects', 'Special effects', False, 'Limited support'),
        },
        table_formats={
            'sequence': '2 bytes per entry',
            'instrument': '8 bytes per entry, 32 max',
            'wave': '2 bytes per entry, 128 max',
            'pulse': '4 bytes per entry, 64 max',
            'filter': '4 bytes per entry, 32 max',
        },
        memory_requirements={
            'code_size': 5376,
            'data_size': 2048,
            'max_tables': 5,
            'min_free': 512,
        },
        limitations=[
            'Smaller code size than Driver 11',
            'Limited effect support',
            'Filter format incompatible with Laxity',
        ],
        accuracy_estimate=0.95,
    ),
    'Laxity': DriverProfile(
        name='Laxity NewPlayer v21',
        version='v21',
        features={
            'sequences': DriverFeature('Sequences', 'Sequence playback', True),
            'instruments': DriverFeature('Instruments', 'Instrument definitions', True),
            'wave': DriverFeature('Wave Table', 'Waveform table', True),
            'pulse': DriverFeature('Pulse Table', 'Pulse/PWM control', True),
            'filter': DriverFeature('Filter Table', 'Filter settings', True),
            'arpeggio': DriverFeature('Arpeggio', 'Arpeggio patterns', True),
            'hardrestart': DriverFeature('Hard Restart', 'Gate control', True),
            'effects': DriverFeature('Effects', 'Advanced effects', True),
            'laxity_filter': DriverFeature('Laxity Filter', 'Advanced filter control', True),
        },
        table_formats={
            'sequence': '2 bytes per entry',
            'instrument': '8 bytes per entry, 32 max',
            'wave': '2 bytes per entry, 128 max (row-major)',
            'pulse': '4 bytes per entry, 64 max (Y*4 indexing)',
            'filter': '4 bytes per entry, 32 max (Y*4 indexing)',
        },
        memory_requirements={
            'code_size': 2500,
            'data_size': 3000,
            'max_tables': 5,
            'min_free': 512,
        },
        limitations=[
            'SF2 format conversion lossy',
            'Filter format unique to Laxity',
            'Advanced effects may not convert',
        ],
        accuracy_estimate=0.70,  # Expected for Laxity->SF2 conversion
    ),
}


class SF2CompatibilityAnalyzer:
    """Analyzes SF2 format compatibility"""

    def __init__(self):
        """Initialize analyzer"""
        self.profiles = DRIVER_PROFILES

    def analyze_compatibility(self,
                             source_format: str,
                             target_driver: str,
                             source_features: Optional[Dict[str, bool]] = None,
                             source_tables: Optional[Dict[str, bool]] = None) -> CompatibilityResult:
        """
        Analyze compatibility between source format and target driver

        Args:
            source_format: Source player format (e.g., 'Laxity', 'Driver11')
            target_driver: Target SF2 driver (e.g., 'Driver11', 'NP20')
            source_features: Dictionary of feature support in source
            source_tables: Dictionary of table types in source

        Returns:
            CompatibilityResult with detailed analysis
        """
        if target_driver not in self.profiles:
            raise ConfigurationError(
                setting='target_driver',
                value=target_driver,
                valid_options=list(self.profiles.keys()),
                example='target_driver: Driver11',
                docs_link='guides/TROUBLESHOOTING.md#driver-configuration'
            )

        profile = self.profiles[target_driver]
        issues = []
        recommendations = []

        # Analyze feature compatibility
        compatible_features = 0
        total_features = len(profile.features)

        for feature_name, feature in profile.features.items():
            if source_features and feature_name in source_features:
                if source_features[feature_name] and feature.supported:
                    compatible_features += 1
                elif not feature.supported:
                    issues.append(CompatibilityIssue(
                        severity='medium',
                        category='feature',
                        issue=f"{feature_name} not supported in {target_driver}",
                        recommendation=f"Manually adjust {feature_name} settings or use different driver"
                    ))
            elif feature.supported:
                compatible_features += 1

        # Analyze table format compatibility
        if source_tables:
            for table_type in source_tables:
                if table_type not in profile.table_formats:
                    issues.append(CompatibilityIssue(
                        severity='high',
                        category='table',
                        issue=f"Table format {table_type} not supported",
                        recommendation=f"Conversion required for {table_type} table"
                    ))

        # Determine overall status and accuracy
        # Check for known incompatibilities
        source_lower = source_format.lower().replace(' ', '')
        target_lower = target_driver.lower().replace(' ', '')

        if 'laxity' in source_lower and 'driver' in target_lower and '11' in target_lower:
            accuracy = 0.08  # Known low conversion accuracy Laxity->Driver11
            issues.append(CompatibilityIssue(
                severity='critical',
                category='format',
                issue='Laxity to Driver 11: Format incompatibility (Laxity filter format not supported)',
                recommendation='Use custom Laxity driver for 70-90% accuracy instead'
            ))
        elif source_lower == target_lower or ('laxity' in source_lower and 'laxity' in target_lower):
            accuracy = 1.0  # Same format
        else:
            accuracy = profile.accuracy_estimate

        # Determine overall status
        if accuracy == 1.0:
            status = CompatibilityStatus.FULL
        elif accuracy >= 0.85:
            status = CompatibilityStatus.HIGH
        elif accuracy >= 0.50:
            status = CompatibilityStatus.MEDIUM
        elif accuracy >= 0.10:
            status = CompatibilityStatus.LOW
        else:
            status = CompatibilityStatus.NONE

        # Generate recommendations
        if not issues:
            recommendations.append(f"{source_format} to {target_driver} is fully compatible")
        else:
            for issue in issues:
                if issue.severity == 'critical':
                    recommendations.append(f"CRITICAL: {issue.recommendation}")
                elif issue.severity == 'high':
                    recommendations.append(f"Recommended: {issue.recommendation}")

        # Add memory recommendations
        if profile.memory_requirements:
            recommendations.append(
                f"Ensure {profile.memory_requirements.get('min_free', 512)} bytes free memory"
            )

        return CompatibilityResult(
            source_format=source_format,
            target_driver=target_driver,
            overall_status=status,
            accuracy_estimate=accuracy,
            compatible_features=compatible_features,
            total_features=total_features,
            issues=issues,
            recommendations=recommendations
        )

    def get_driver_profile(self, driver_name: str) -> Optional[DriverProfile]:
        """Get profile for a specific driver"""
        return self.profiles.get(driver_name)

    def list_drivers(self) -> List[str]:
        """List all supported drivers"""
        return list(self.profiles.keys())

    def compare_drivers(self, drivers: List[str]) -> str:
        """Generate comparison report for multiple drivers"""
        lines = []

        lines.append("=" * 120)
        lines.append("SF2 DRIVER COMPATIBILITY COMPARISON")
        lines.append("=" * 120)
        lines.append("")

        # Feature comparison table
        lines.append("FEATURE SUPPORT MATRIX:")
        lines.append("-" * 120)

        # Get all unique features
        all_features = set()
        for driver in drivers:
            if driver in self.profiles:
                all_features.update(self.profiles[driver].features.keys())

        # Header
        header = "Feature".ljust(20)
        for driver in drivers:
            header += f" | {driver:15}"
        lines.append(header)
        lines.append("-" * 120)

        # Feature rows
        for feature in sorted(all_features):
            row = feature.ljust(20)
            for driver in drivers:
                if driver in self.profiles:
                    if feature in self.profiles[driver].features:
                        supported = self.profiles[driver].features[feature].supported
                        status = "YES" if supported else "NO"
                    else:
                        status = "?"
                    row += f" | {status:15}"
            lines.append(row)

        lines.append("")

        # Memory requirements
        lines.append("MEMORY REQUIREMENTS:")
        lines.append("-" * 120)

        for driver in drivers:
            if driver in self.profiles:
                profile = self.profiles[driver]
                req = profile.memory_requirements
                lines.append(f"{driver}:")
                lines.append(f"  Code Size: {req.get('code_size', 'N/A')} bytes")
                lines.append(f"  Data Size: {req.get('data_size', 'N/A')} bytes")
                lines.append(f"  Min Free Memory: {req.get('min_free', 'N/A')} bytes")
                lines.append("")

        lines.append("=" * 120)

        return "\n".join(lines)

    def generate_compatibility_report(self, result: CompatibilityResult) -> str:
        """Generate detailed compatibility report"""
        lines = []

        lines.append("=" * 100)
        lines.append("SF2 FORMAT COMPATIBILITY REPORT")
        lines.append("=" * 100)
        lines.append("")

        # Summary
        lines.append("SUMMARY:")
        lines.append("-" * 100)
        lines.append(f"Source Format: {result.source_format}")
        lines.append(f"Target Driver: {result.target_driver}")
        lines.append(f"Compatibility: {result.overall_status.value}")
        lines.append(f"Predicted Accuracy: {result.accuracy_estimate*100:.1f}%")
        lines.append(f"Compatible Features: {result.compatible_features}/{result.total_features}")
        lines.append("")

        # Issues
        if result.issues:
            lines.append("COMPATIBILITY ISSUES:")
            lines.append("-" * 100)

            critical = [i for i in result.issues if i.severity == 'critical']
            high = [i for i in result.issues if i.severity == 'high']
            medium = [i for i in result.issues if i.severity == 'medium']
            low = [i for i in result.issues if i.severity == 'low']

            if critical:
                lines.append("CRITICAL:")
                for issue in critical:
                    lines.append(f"  [{issue.category.upper()}] {issue.issue}")
                    lines.append(f"    -> {issue.recommendation}")
                lines.append("")

            if high:
                lines.append("HIGH SEVERITY:")
                for issue in high:
                    lines.append(f"  [{issue.category.upper()}] {issue.issue}")
                    lines.append(f"    -> {issue.recommendation}")
                lines.append("")

            if medium:
                lines.append("MEDIUM SEVERITY:")
                for issue in medium:
                    lines.append(f"  [{issue.category.upper()}] {issue.issue}")
                lines.append("")

            if low:
                lines.append("LOW SEVERITY:")
                for issue in low:
                    lines.append(f"  [{issue.category.upper()}] {issue.issue}")
                lines.append("")

        # Recommendations
        if result.recommendations:
            lines.append("RECOMMENDATIONS:")
            lines.append("-" * 100)
            for rec in result.recommendations:
                lines.append(f"  • {rec}")
            lines.append("")

        # Driver profile
        if result.target_driver in self.profiles:
            profile = self.profiles[result.target_driver]

            lines.append("TARGET DRIVER DETAILS:")
            lines.append("-" * 100)
            lines.append(f"Driver: {profile.name} {profile.version or ''}")
            lines.append(f"Accuracy Estimate: {profile.accuracy_estimate*100:.0f}%")
            lines.append("")

            lines.append("Limitations:")
            for limit in profile.limitations:
                lines.append(f"  • {limit}")
            lines.append("")

        lines.append("=" * 100)

        return "\n".join(lines)
