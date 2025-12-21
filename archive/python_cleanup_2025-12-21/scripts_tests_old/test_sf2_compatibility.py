#!/usr/bin/env python3
"""
Test SF2 format compatibility analysis.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_compatibility import SF2CompatibilityAnalyzer, CompatibilityStatus


def test_laxity_to_driver11():
    """Test Laxity to Driver 11 compatibility (known low)"""

    print("=" * 100)
    print("TEST: LAXITY TO DRIVER 11 COMPATIBILITY")
    print("=" * 100)
    print()

    analyzer = SF2CompatibilityAnalyzer()

    # Analyze Laxity to Driver 11
    result = analyzer.analyze_compatibility(
        source_format='Laxity NewPlayer v21',
        target_driver='Driver11',
        source_features={
            'sequences': True,
            'instruments': True,
            'wave': True,
            'pulse': True,
            'filter': True,
            'laxity_filter': True,
        }
    )

    print(analyzer.generate_compatibility_report(result))
    print()

    # Expected: Low compatibility due to format differences
    if result.overall_status in [CompatibilityStatus.LOW, CompatibilityStatus.NONE]:
        print("[OK] Laxity->Driver11 correctly identified as low compatibility")
    else:
        print(f"[WARN] Expected LOW compatibility, got {result.overall_status.value}")
    print()


def test_driver11_to_driver11():
    """Test Driver 11 to Driver 11 (should be perfect)"""

    print("=" * 100)
    print("TEST: DRIVER 11 TO DRIVER 11 (SAME FORMAT)")
    print("=" * 100)
    print()

    analyzer = SF2CompatibilityAnalyzer()

    result = analyzer.analyze_compatibility(
        source_format='Driver 11',
        target_driver='Driver11'
    )

    print(analyzer.generate_compatibility_report(result))
    print()

    if result.overall_status == CompatibilityStatus.FULL and result.accuracy_estimate == 1.0:
        print("[OK] Same format conversion correctly identified as FULL compatible")
    else:
        print(f"[FAIL] Expected FULL (100%), got {result.overall_status.value} ({result.accuracy_estimate*100:.0f}%)")
    print()


def test_laxity_to_laxity():
    """Test Laxity to Laxity (perfect format match)"""

    print("=" * 100)
    print("TEST: LAXITY TO LAXITY (SAME FORMAT)")
    print("=" * 100)
    print()

    analyzer = SF2CompatibilityAnalyzer()

    result = analyzer.analyze_compatibility(
        source_format='Laxity',
        target_driver='Laxity'
    )

    print(analyzer.generate_compatibility_report(result))
    print()

    if result.accuracy_estimate >= 0.7:
        print("[OK] Laxity->Laxity has high estimated accuracy")
    else:
        print(f"[WARN] Expected high accuracy, got {result.accuracy_estimate*100:.0f}%")
    print()


def test_driver_comparison():
    """Test driver comparison"""

    print("=" * 100)
    print("TEST: DRIVER COMPARISON")
    print("=" * 100)
    print()

    analyzer = SF2CompatibilityAnalyzer()

    comparison = analyzer.compare_drivers(['Driver11', 'NP20', 'Laxity'])
    print(comparison)
    print()

    print("[OK] Driver comparison generated")
    print()


def test_get_driver_profile():
    """Test getting driver profile"""

    print("=" * 100)
    print("TEST: GET DRIVER PROFILE")
    print("=" * 100)
    print()

    analyzer = SF2CompatibilityAnalyzer()

    profile = analyzer.get_driver_profile('Driver11')

    if profile:
        print(f"Driver Profile: {profile.name}")
        print(f"Version: {profile.version}")
        print(f"Features Supported: {sum(1 for f in profile.features.values() if f.supported)}/{len(profile.features)}")
        print(f"Code Size: {profile.memory_requirements.get('code_size')} bytes")
        print()
        print("[OK] Driver profile retrieved successfully")
    else:
        print("[FAIL] Driver profile not found")
    print()


def test_list_drivers():
    """Test listing available drivers"""

    print("=" * 100)
    print("TEST: LIST AVAILABLE DRIVERS")
    print("=" * 100)
    print()

    analyzer = SF2CompatibilityAnalyzer()

    drivers = analyzer.list_drivers()
    print(f"Available Drivers: {len(drivers)}")
    for driver in sorted(drivers):
        profile = analyzer.get_driver_profile(driver)
        print(f"  - {driver:15} ({profile.name})")
    print()

    if len(drivers) >= 3:
        print("[OK] Found expected number of drivers")
    else:
        print(f"[WARN] Expected at least 3 drivers, found {len(drivers)}")
    print()


def test_laxity_to_np20():
    """Test Laxity to NP20 compatibility"""

    print("=" * 100)
    print("TEST: LAXITY TO NP20 COMPATIBILITY")
    print("=" * 100)
    print()

    analyzer = SF2CompatibilityAnalyzer()

    result = analyzer.analyze_compatibility(
        source_format='Laxity NewPlayer v21',
        target_driver='NP20'
    )

    print(analyzer.generate_compatibility_report(result))
    print()

    print(f"[INFO] Accuracy estimate: {result.accuracy_estimate*100:.0f}%")
    print()


if __name__ == "__main__":
    print()
    print("SF2 COMPATIBILITY ANALYSIS TEST SUITE")
    print("=" * 100)
    print()

    test_laxity_to_driver11()
    test_driver11_to_driver11()
    test_laxity_to_laxity()
    test_driver_comparison()
    test_get_driver_profile()
    test_list_drivers()
    test_laxity_to_np20()

    print("=" * 100)
    print("SF2 COMPATIBILITY TESTS COMPLETE")
    print("=" * 100)
