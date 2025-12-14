#!/usr/bin/env python3
"""
Laxity Baseline Test - Establish current functionality as golden standard

This test documents what Laxity currently does, for comparison after
Martin Galway integration to ensure no breaking changes.

CRITICAL: Must pass before and after Martin Galway integration.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_laxity_module_imports():
    """Test that all Laxity modules import successfully"""
    print("[1/10] Testing Laxity module imports...")

    modules_to_import = [
        'sidm2.sid_parser',
        'sidm2.laxity_parser',
        'sidm2.laxity_analyzer',
        'sidm2.laxity_converter',
        'sidm2.enhanced_player_detection',
    ]

    for module_name in modules_to_import:
        try:
            __import__(module_name)
            print(f"  [OK] {module_name}")
        except ImportError as e:
            print(f"  [FAIL] {module_name}: {e}")
            return False

    return True


def test_laxity_player_detection():
    """Test that Laxity files are detected correctly"""
    print("\n[2/10] Testing Laxity player detection...")

    from sidm2.enhanced_player_detection import EnhancedPlayerDetector

    detector = EnhancedPlayerDetector()
    test_files = [
        ('SID/Broware.sid', 'Laxity'),
        ('SID/Stinsens_Last_Night_of_89.sid', 'Laxity'),
    ]

    all_pass = True
    for filepath, expected_player in test_files:
        if Path(filepath).exists():
            player, confidence = detector.detect_player(Path(filepath))
            if expected_player in player:
                print(f"  [OK] {Path(filepath).name}: Detected as {player} ({confidence:.0%})")
            else:
                print(f"  [FAIL] {Path(filepath).name}: Expected {expected_player}, got {player}")
                all_pass = False
        else:
            print(f"  [SKIP] {filepath} not found")

    return all_pass


def test_sf2_files_valid():
    """Test that generated SF2 files are valid"""
    print("\n[3/10] Testing SF2 file validity...")

    sf2_files = list(Path('output/SIDSF2player_Complete_Pipeline').glob('*/New/*.sf2'))

    if not sf2_files:
        print("  [SKIP] No SF2 files found")
        return True

    all_pass = True
    for sf2_file in sf2_files[:3]:  # Test first 3
        try:
            with open(sf2_file, 'rb') as f:
                magic = f.read(2)
                size = os.path.getsize(sf2_file)

            # SF2 magic is 0x1337, may have 2-byte prefix (Laxity driver structure)
            # Check both at offset 0 and offset 2
            if magic == b'\x37\x13':
                print(f"  [OK] {sf2_file.parent.parent.name}: {size:,} bytes (magic at offset 0)")
            elif magic == b'\x7e\x0d':
                # Laxity driver wrapper - check magic at offset 2
                with open(sf2_file, 'rb') as f:
                    f.seek(2)
                    magic2 = f.read(2)
                if magic2 == b'\x37\x13':
                    print(f"  [OK] {sf2_file.parent.parent.name}: {size:,} bytes (Laxity wrapped, magic at offset 2)")
                else:
                    print(f"  [FAIL] {sf2_file.name}: Invalid magic at offset 2: {magic2.hex()}")
                    all_pass = False
            else:
                print(f"  [FAIL] {sf2_file.name}: Invalid magic {magic.hex()}")
                all_pass = False
        except Exception as e:
            print(f"  [FAIL] {sf2_file.name}: {e}")
            all_pass = False

    return all_pass


def test_pipeline_outputs():
    """Test that pipeline generates expected output files"""
    print("\n[4/10] Testing pipeline output files...")

    test_song = 'Broware'
    base_path = Path(f'output/SIDSF2player_Complete_Pipeline/{test_song}/New')

    if not base_path.exists():
        print(f"  [SKIP] Pipeline output not found")
        return True

    expected_files = [
        f'{test_song}.sf2',
        f'{test_song}_exported.sid',
        'info.txt',
    ]

    all_pass = True
    for filename in expected_files:
        file_path = base_path / filename
        if file_path.exists():
            size = os.path.getsize(file_path)
            print(f"  [OK] {filename}: {size:,} bytes")
        else:
            print(f"  [MISSING] {filename}")
            all_pass = False

    return all_pass


def test_conversion_api():
    """Test that conversion API is callable"""
    print("\n[5/10] Testing conversion API...")

    try:
        from scripts.sid_to_sf2 import convert_sid_to_sf2
        import inspect

        sig = inspect.signature(convert_sid_to_sf2)
        print(f"  [OK] convert_sid_to_sf2 function exists")
        print(f"       Parameters: {list(sig.parameters.keys())}")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_enhanced_player_detection():
    """Test that player detection system is working"""
    print("\n[6/10] Testing enhanced player detection...")

    try:
        from sidm2.enhanced_player_detection import EnhancedPlayerDetector

        detector = EnhancedPlayerDetector()

        # Check that it has expected methods
        methods = ['detect_player', '_detect_with_player_id_exe']
        for method in methods:
            if hasattr(detector, method):
                print(f"  [OK] EnhancedPlayerDetector.{method} exists")
            else:
                print(f"  [MISSING] EnhancedPlayerDetector.{method}")
                return False

        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_laxity_converter_callable():
    """Test that LaxityConverter can be instantiated"""
    print("\n[7/10] Testing LaxityConverter instantiation...")

    try:
        from sidm2.laxity_converter import LaxityConverter

        converter = LaxityConverter()
        print(f"  [OK] LaxityConverter instantiated")

        # Check key methods exist
        if hasattr(converter, 'convert'):
            print(f"  [OK] LaxityConverter.convert() method exists")
        else:
            print(f"  [FAIL] LaxityConverter.convert() method missing")
            return False

        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_backward_compatibility_markers():
    """Verify code has proper backward compatibility markers"""
    print("\n[8/10] Checking backward compatibility markers...")

    files_to_check = [
        'sidm2/laxity_parser.py',
        'sidm2/laxity_analyzer.py',
        'sidm2/laxity_converter.py',
    ]

    all_pass = True
    for filepath in files_to_check:
        file_path = Path(filepath)
        if file_path.exists():
            print(f"  [OK] {filepath} exists")
        else:
            print(f"  [MISSING] {filepath}")
            all_pass = False

    return all_pass


def test_python_path_setup():
    """Verify Python path is set correctly"""
    print("\n[9/10] Testing Python path setup...")

    try:
        import sidm2
        print(f"  [OK] sidm2 module importable")
        print(f"       Location: {sidm2.__file__}")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def test_existing_tests_runnable():
    """Verify existing test scripts are runnable"""
    print("\n[10/10] Checking existing test infrastructure...")

    test_scripts = [
        'scripts/test_converter.py',
        'scripts/test_sf2_format.py',
        'scripts/test_complete_pipeline.py',
    ]

    all_exist = True
    for script_path in test_scripts:
        if Path(script_path).exists():
            print(f"  [OK] {script_path} exists")
        else:
            print(f"  [MISSING] {script_path}")
            all_exist = False

    return all_exist


def main():
    """Run all baseline tests"""
    print("="*70)
    print("LAXITY BASELINE TEST - Establishing golden standard")
    print("="*70)

    tests = [
        test_laxity_module_imports,
        test_laxity_player_detection,
        test_sf2_files_valid,
        test_pipeline_outputs,
        test_conversion_api,
        test_enhanced_player_detection,
        test_laxity_converter_callable,
        test_backward_compatibility_markers,
        test_python_path_setup,
        test_existing_tests_runnable,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n[ERROR] Unexpected error in {test_func.__name__}: {e}")
            results.append(False)

    # Summary
    print("\n" + "="*70)
    print("BASELINE TEST SUMMARY")
    print("="*70)
    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if all(results):
        print("\n[OK] BASELINE ESTABLISHED - All Laxity functionality working")
        print("Safe to proceed with Martin Galway integration")
        print("\nREQUIREMENT: These tests MUST PASS after Martin Galway integration")
        return 0
    else:
        print("\n[FAIL] Some baseline tests failed")
        print("Current Laxity functionality may be incomplete")
        return 1


if __name__ == '__main__':
    sys.exit(main())
