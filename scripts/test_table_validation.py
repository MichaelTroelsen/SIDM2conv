#!/usr/bin/env python3
"""
Test the table size validation functionality.
Validates table extraction and size checking on known SID files.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.siddecompiler import SIDdecompilerAnalyzer, TableInfo
from sidm2.table_validator import TableValidator


def test_basic_validation():
    """Test basic table validation with mock tables"""

    print("=" * 80)
    print("TESTING BASIC TABLE VALIDATION")
    print("=" * 80)
    print()

    # Create mock tables
    tables = {
        'filter_table': TableInfo(
            name='filter_table',
            address=0x1A1E,
            size=128,
            type='filter'
        ),
        'pulse_table': TableInfo(
            name='pulse_table',
            address=0x1A3B,
            size=256,
            type='pulse'
        ),
        'instrument_table': TableInfo(
            name='instrument_table',
            address=0x1A6B,
            size=256,
            type='instrument'
        ),
        'wave_table': TableInfo(
            name='wave_table',
            address=0x1ACB,
            size=256,
            type='wave'
        ),
    }

    validator = TableValidator()
    result = validator.validate_tables(tables, player_type='Laxity NewPlayer v21')

    print(validator.generate_report(result))
    print()

    if result.passed:
        print("[OK] Basic validation passed!")
    else:
        print("[FAIL] Basic validation found issues")
        for issue in result.issues_found:
            print(f"     - {issue}")
    print()


def test_overlapping_tables():
    """Test overlap detection"""

    print("=" * 80)
    print("TESTING OVERLAP DETECTION")
    print("=" * 80)
    print()

    # Create overlapping tables
    tables = {
        'table1': TableInfo(
            name='table1',
            address=0x1000,
            size=256,
            type='data'
        ),
        'table2': TableInfo(
            name='table2',
            address=0x1100,
            size=128,
            type='data'
        ),
        'table3': TableInfo(
            name='table3',
            address=0x1150,  # Overlaps with table2
            size=64,
            type='data'
        ),
    }

    validator = TableValidator()
    result = validator.validate_tables(tables)

    print(validator.generate_report(result))
    print()

    if len(result.critical) > 0:
        print("[OK] Overlap detected correctly!")
        for issue in result.critical:
            print(f"     - {issue}")
    else:
        print("[FAIL] Overlap not detected")
    print()


def test_boundary_violations():
    """Test memory boundary violations"""

    print("=" * 80)
    print("TESTING MEMORY BOUNDARY VIOLATIONS")
    print("=" * 80)
    print()

    # Create tables exceeding boundaries
    tables = {
        'normal_table': TableInfo(
            name='normal_table',
            address=0x2000,
            size=256,
            type='data'
        ),
        'exceeds_table': TableInfo(
            name='exceeds_table',
            address=0xFF00,
            size=512,  # Exceeds 0xFFFF boundary
            type='data'
        ),
    }

    validator = TableValidator()
    result = validator.validate_tables(tables, memory_end=0xFFFF)

    print(validator.generate_report(result))
    print()

    if len(result.errors) > 0:
        print("[OK] Boundary violation detected!")
        for issue in result.errors:
            print(f"     - {issue}")
    else:
        print("[FAIL] Boundary violation not detected")
    print()


def test_siddecompiler_integration():
    """Test integration with SIDdecompiler"""

    print("=" * 80)
    print("TESTING SIDDECOMPILER INTEGRATION")
    print("=" * 80)
    print()

    analyzer = SIDdecompilerAnalyzer()

    # Create mock tables
    tables = {
        'filter': TableInfo(
            name='filter',
            address=0x1A1E,
            size=128,
            type='filter'
        ),
        'pulse': TableInfo(
            name='pulse',
            address=0x1A3B,
            size=256,
            type='pulse'
        ),
    }

    try:
        result = analyzer.validate_tables(tables, 'Laxity NewPlayer v21')
        report = analyzer.validate_and_report(tables, 'Laxity NewPlayer v21')

        print("Validation Result:")
        print(f"  Status: {'PASSED' if result.passed else 'FAILED'}")
        print(f"  Tables Checked: {result.tables_checked}")
        print(f"  Issues: {len(result.issues_found)}")
        print()

        print("Generated Report:")
        print(report)
        print()

        print("[OK] SIDdecompiler integration works!")

    except Exception as e:
        print(f"[FAIL] Integration test failed: {e}")
    print()


def test_driver11_validation():
    """Test Driver 11 specific validation"""

    print("=" * 80)
    print("TESTING DRIVER 11 VALIDATION")
    print("=" * 80)
    print()

    # Create Driver 11 style tables
    tables = {
        'sequence': TableInfo(
            name='sequence',
            address=0x0903,
            size=512,
            type='sequence'
        ),
        'instrument': TableInfo(
            name='instrument',
            address=0x0A03,
            size=256,
            type='instrument'
        ),
        'wave': TableInfo(
            name='wave',
            address=0x0B03,
            size=256,
            type='wave'
        ),
    }

    validator = TableValidator()
    result = validator.validate_tables(tables, player_type='Driver 11')

    print(validator.generate_report(result))
    print()

    if result.passed:
        print("[OK] Driver 11 validation passed!")
    else:
        print("[FAIL] Driver 11 validation found issues")
    print()


if __name__ == "__main__":
    print()
    print("TABLE VALIDATION TEST SUITE")
    print("=" * 80)
    print()

    test_basic_validation()
    test_overlapping_tables()
    test_boundary_violations()
    test_siddecompiler_integration()
    test_driver11_validation()

    print("=" * 80)
    print("TABLE VALIDATION TESTS COMPLETE")
    print("=" * 80)
