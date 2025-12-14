#!/usr/bin/env python3
"""
Test enhanced table extraction validation.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.extraction_validator import ExtractionValidator
from sidm2.siddecompiler import TableInfo


def test_complete_laxity_extraction():
    """Test validation of complete Laxity extraction"""

    print("=" * 100)
    print("TEST: COMPLETE LAXITY EXTRACTION VALIDATION")
    print("=" * 100)
    print()

    validator = ExtractionValidator()

    # Mock complete Laxity extraction
    tables = {
        'filter': TableInfo(name='filter', address=0x1A1E, size=128, type='filter'),
        'pulse': TableInfo(name='pulse', address=0x1A3B, size=256, type='pulse'),
        'instrument': TableInfo(name='instrument', address=0x1A6B, size=256, type='instrument'),
        'wave': TableInfo(name='wave', address=0x1ACB, size=256, type='wave'),
    }

    metrics = validator.validate_extraction(tables, 'Laxity NewPlayer v21')

    print(validator.generate_validation_report(metrics))
    print()

    if metrics.overall_quality >= 0.70:
        print("[OK] Complete extraction validated with acceptable quality")
    else:
        print("[WARN] Quality lower than expected")
    print()


def test_incomplete_extraction():
    """Test validation of incomplete extraction"""

    print("=" * 100)
    print("TEST: INCOMPLETE EXTRACTION (MISSING TABLES)")
    print("=" * 100)
    print()

    validator = ExtractionValidator()

    # Only 2 of 4 expected tables
    tables = {
        'filter': TableInfo(name='filter', address=0x1A1E, size=128, type='filter'),
        'pulse': TableInfo(name='pulse', address=0x1A3B, size=256, type='pulse'),
    }

    metrics = validator.validate_extraction(tables, 'Laxity NewPlayer v21')

    print(validator.generate_validation_report(metrics))
    print()

    if metrics.completeness < 0.80 and len(validator.issues) > 0:
        print("[OK] Incomplete extraction correctly identified")
    else:
        print("[FAIL] Should have detected missing tables")
    print()


def test_invalid_addresses():
    """Test validation with invalid addresses"""

    print("=" * 100)
    print("TEST: INVALID TABLE ADDRESSES")
    print("=" * 100)
    print()

    validator = ExtractionValidator()

    # Tables with invalid addresses
    tables = {
        'valid': TableInfo(name='valid', address=0x1000, size=256, type='data'),
        'invalid_out_of_range': TableInfo(name='invalid', address=0x10000, size=256, type='data'),
        'invalid_negative': TableInfo(name='invalid2', address=-1, size=256, type='data'),
    }

    metrics = validator.validate_extraction(tables, 'Unknown')

    print(validator.generate_validation_report(metrics))
    print()

    if metrics.consistency < 1.0 and len(validator.issues) > 0:
        print("[OK] Invalid addresses detected correctly")
    else:
        print("[FAIL] Should have detected invalid addresses")
    print()


def test_overlapping_extraction():
    """Test validation with overlapping tables"""

    print("=" * 100)
    print("TEST: OVERLAPPING TABLES IN EXTRACTION")
    print("=" * 100)
    print()

    validator = ExtractionValidator()

    # Overlapping tables
    tables = {
        'table1': TableInfo(name='table1', address=0x1000, size=256, type='data'),
        'table2': TableInfo(name='table2', address=0x1100, size=128, type='data'),
        'table3': TableInfo(name='table3', address=0x1150, size=128, type='data'),  # Overlaps with table2
    }

    metrics = validator.validate_extraction(tables, 'Unknown')

    print(validator.generate_validation_report(metrics))
    print()

    if metrics.integrity < 1.0 and metrics.critical_count > 0:
        print("[OK] Overlapping tables correctly identified as critical")
    else:
        print("[FAIL] Should have detected overlaps")
    print()


def test_large_extraction():
    """Test validation with unusually large tables"""

    print("=" * 100)
    print("TEST: UNUSUALLY LARGE TABLE")
    print("=" * 100)
    print()

    validator = ExtractionValidator()

    # Very large table
    tables = {
        'normal': TableInfo(name='normal', address=0x1000, size=256, type='data'),
        'huge': TableInfo(name='huge', address=0x2000, size=32768, type='data'),
    }

    metrics = validator.validate_extraction(tables, 'Unknown')

    print(validator.generate_validation_report(metrics))
    print()

    if len(validator.issues) > 0:
        print("[OK] Unusually large table detected")
    else:
        print("[WARN] Should have warned about large table")
    print()


def test_driver11_extraction():
    """Test validation of Driver 11 extraction"""

    print("=" * 100)
    print("TEST: COMPLETE DRIVER 11 EXTRACTION")
    print("=" * 100)
    print()

    validator = ExtractionValidator()

    # Complete Driver 11 extraction
    tables = {
        'sequence': TableInfo(name='sequence', address=0x0903, size=512, type='sequence'),
        'instrument': TableInfo(name='instrument', address=0x0A03, size=256, type='instrument'),
        'wave': TableInfo(name='wave', address=0x0B03, size=256, type='wave'),
        'pulse': TableInfo(name='pulse', address=0x0D03, size=256, type='pulse'),
        'filter': TableInfo(name='filter', address=0x0F03, size=128, type='filter'),
    }

    metrics = validator.validate_extraction(tables, 'Driver 11')

    print(validator.generate_validation_report(metrics))
    print()

    if metrics.completeness >= 0.80:
        print("[OK] Driver 11 extraction validated")
    else:
        print("[FAIL] Driver 11 validation failed")
    print()


if __name__ == "__main__":
    print()
    print("EXTRACTION VALIDATION TEST SUITE")
    print("=" * 100)
    print()

    test_complete_laxity_extraction()
    test_incomplete_extraction()
    test_invalid_addresses()
    test_overlapping_extraction()
    test_large_extraction()
    test_driver11_extraction()

    print("=" * 100)
    print("EXTRACTION VALIDATION TESTS COMPLETE")
    print("=" * 100)
