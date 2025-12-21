#!/usr/bin/env python3
"""
Generate comprehensive driver-specific analysis reports.
Shows features, limitations, and conversion implications for each SF2 driver.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_compatibility import SF2CompatibilityAnalyzer, DriverProfile


def generate_driver_feature_report(analyzer: SF2CompatibilityAnalyzer) -> str:
    """Generate detailed feature comparison report"""

    lines = []

    lines.append("=" * 120)
    lines.append("SF2 DRIVER FEATURE COMPARISON REPORT")
    lines.append("=" * 120)
    lines.append("")

    drivers = analyzer.list_drivers()

    # Get all unique features
    all_features = set()
    for driver_name in drivers:
        profile = analyzer.get_driver_profile(driver_name)
        if profile:
            all_features.update(profile.features.keys())

    # Feature support matrix
    lines.append("FEATURE SUPPORT MATRIX:")
    lines.append("-" * 120)

    header = "Feature".ljust(25)
    for driver in sorted(drivers):
        header += f" | {driver:20}"
    lines.append(header)
    lines.append("-" * 120)

    for feature in sorted(all_features):
        row = feature.ljust(25)
        for driver in sorted(drivers):
            profile = analyzer.get_driver_profile(driver)
            if profile and feature in profile.features:
                supported = profile.features[feature].supported
                status = "YES" if supported else "NO"
            else:
                status = "?"
            row += f" | {status:20}"
        lines.append(row)

    lines.append("")
    lines.append("")

    # Detailed feature descriptions per driver
    lines.append("DETAILED FEATURE DESCRIPTIONS:")
    lines.append("-" * 120)
    lines.append("")

    for driver_name in sorted(drivers):
        profile = analyzer.get_driver_profile(driver_name)
        if not profile:
            continue

        lines.append(f"{profile.name} ({profile.version or 'Unknown version'})")
        lines.append("-" * 120)

        for feature_name in sorted(profile.features.keys()):
            feature = profile.features[feature_name]
            status = "SUPPORTED" if feature.supported else "NOT SUPPORTED"
            lines.append(f"  {feature_name:20} [{status:15}]")
            lines.append(f"    Description: {feature.description}")
            if feature.notes:
                lines.append(f"    Notes: {feature.notes}")

        lines.append("")

    lines.append("=" * 120)

    return "\n".join(lines)


def generate_driver_limitations_report(analyzer: SF2CompatibilityAnalyzer) -> str:
    """Generate limitations and caveats report"""

    lines = []

    lines.append("=" * 120)
    lines.append("SF2 DRIVER LIMITATIONS & CAVEATS REPORT")
    lines.append("=" * 120)
    lines.append("")

    drivers = analyzer.list_drivers()

    for driver_name in sorted(drivers):
        profile = analyzer.get_driver_profile(driver_name)
        if not profile:
            continue

        lines.append(f"{profile.name}")
        lines.append("-" * 120)
        lines.append(f"Version: {profile.version or 'Unknown'}")
        lines.append("")

        # Memory requirements
        lines.append("Memory Requirements:")
        for key, value in profile.memory_requirements.items():
            label = key.replace('_', ' ').title()
            if isinstance(value, int):
                lines.append(f"  * {label}: {value} bytes")
            else:
                lines.append(f"  * {label}: {value}")
        lines.append("")

        # Limitations
        lines.append("Known Limitations:")
        if profile.limitations:
            for limitation in profile.limitations:
                lines.append(f"  * {limitation}")
        else:
            lines.append("  * None known")
        lines.append("")

        # Table formats
        lines.append("Table Formats Supported:")
        for table_type, format_desc in profile.table_formats.items():
            lines.append(f"  * {table_type.ljust(15)}: {format_desc}")
        lines.append("")

        # Accuracy
        accuracy_pct = profile.accuracy_estimate * 100
        lines.append(f"Expected Conversion Accuracy: {accuracy_pct:.0f}%")
        lines.append("")
        lines.append("")

    lines.append("=" * 120)

    return "\n".join(lines)


def generate_conversion_guide(analyzer: SF2CompatibilityAnalyzer) -> str:
    """Generate conversion best practices guide"""

    lines = []

    lines.append("=" * 120)
    lines.append("SID TO SF2 CONVERSION GUIDE")
    lines.append("=" * 120)
    lines.append("")

    lines.append("CONVERSION RECOMMENDATIONS BY SOURCE FORMAT:")
    lines.append("-" * 120)
    lines.append("")

    # Laxity conversion recommendations
    lines.append("LAXITY NEWPLAYER V21 SOURCE FILES:")
    lines.append("")
    lines.append("  OPTION 1: Use Custom Laxity Driver")
    lines.append("    Pros:")
    lines.append("      * 70-90% conversion accuracy")
    lines.append("      * Uses original Laxity player code")
    lines.append("      * Full feature preservation")
    lines.append("    Cons:")
    lines.append("      * Requires custom driver installation")
    lines.append("      * Larger resulting SF2 file")
    lines.append("    Recommended for: Maximum accuracy, important compositions")
    lines.append("")

    lines.append("  OPTION 2: Use Driver 11 (Standard SF2)")
    lines.append("    Pros:")
    lines.append("      * Works in all SF2 editors")
    lines.append("      * No custom driver needed")
    lines.append("    Cons:")
    lines.append("      * 1-8% conversion accuracy")
    lines.append("      * Filter format not compatible")
    lines.append("      * Requires manual correction")
    lines.append("    Recommended for: Quick edits, simple compositions")
    lines.append("")

    lines.append("  OPTION 3: Use NP20 (JCH NewPlayer v20)")
    lines.append("    Pros:")
    lines.append("      * Slightly smaller than Driver 11")
    lines.append("      * Good compatibility")
    lines.append("    Cons:")
    lines.append("      * 1-8% conversion accuracy")
    lines.append("      * Limited effect support")
    lines.append("    Recommended for: Space-constrained projects")
    lines.append("")
    lines.append("")

    # Driver 11 conversion recommendations
    lines.append("DRIVER 11 / SF2-EXPORTED SOURCE FILES:")
    lines.append("")
    lines.append("  Best choice: Driver 11")
    lines.append("    * 100% accuracy expected")
    lines.append("    * No conversion needed - use SF2 format directly")
    lines.append("    * Full feature preservation")
    lines.append("")
    lines.append("")

    # Best practices
    lines.append("CONVERSION BEST PRACTICES:")
    lines.append("-" * 120)
    lines.append("")
    lines.append("1. ANALYZE SOURCE FORMAT")
    lines.append("   * Identify player type (Laxity, Driver11, NP20, etc.)")
    lines.append("   * Check for custom features or advanced effects")
    lines.append("   * Review table sizes and memory layout")
    lines.append("")

    lines.append("2. VALIDATE EXTRACTION")
    lines.append("   * Check completeness (all expected tables found)")
    lines.append("   * Verify consistency (valid addresses, no overlaps)")
    lines.append("   * Confirm integrity (data structure is sound)")
    lines.append("")

    lines.append("3. CHOOSE APPROPRIATE DRIVER")
    lines.append("   * If Laxity: Choose Laxity driver for accuracy")
    lines.append("   * If Driver11: Choose Driver 11 (100% compatible)")
    lines.append("   * Consider memory constraints")
    lines.append("   * Consider feature requirements")
    lines.append("")

    lines.append("4. VALIDATE CONVERSION")
    lines.append("   * Generate WAV files and compare")
    lines.append("   * Check register trace output")
    lines.append("   * Verify in multiple players (VICE, siddump, SID2WAV)")
    lines.append("   * Manual correction if needed")
    lines.append("")

    lines.append("5. TEST IN SF2 EDITOR")
    lines.append("   * Load in SID Factory II")
    lines.append("   * Test playback")
    lines.append("   * Verify table editing (if supported)")
    lines.append("   * Check audio quality")
    lines.append("")

    lines.append("")
    lines.append("ACCURACY EXPECTATIONS:")
    lines.append("-" * 120)
    lines.append("")
    lines.append("Source Format             -> Driver 11   -> NP20       -> Laxity Driver")
    lines.append("-" * 120)
    lines.append("Laxity NewPlayer v21      1-8%         1-8%        70-90%")
    lines.append("Driver 11                 100%         ~95%        N/A")
    lines.append("JCH NewPlayer v20         ~95%         100%        N/A")
    lines.append("SF2 Exported              100%         95%         N/A")
    lines.append("")

    lines.append("=" * 120)

    return "\n".join(lines)


def main():
    """Generate all driver analysis reports"""

    analyzer = SF2CompatibilityAnalyzer()

    # Generate features report
    features_report = generate_driver_feature_report(analyzer)
    print(features_report)
    print()
    print()

    # Generate limitations report
    limitations_report = generate_driver_limitations_report(analyzer)
    print(limitations_report)
    print()
    print()

    # Generate conversion guide
    guide = generate_conversion_guide(analyzer)
    print(guide)

    # Save reports to files
    output_dir = Path("docs/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    reports = [
        ("DRIVER_FEATURES_COMPARISON.md", features_report),
        ("DRIVER_LIMITATIONS.md", limitations_report),
        ("CONVERSION_GUIDE.md", guide),
    ]

    for filename, content in reports:
        filepath = output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\nSaved: {filepath}")


if __name__ == "__main__":
    main()
