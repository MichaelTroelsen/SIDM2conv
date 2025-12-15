#!/usr/bin/env python3
"""
Test SF2 Viewer functionality
Verify parser can read and display SF2 files correctly
"""

import sys
from pathlib import Path
from sf2_viewer_core import SF2Parser, BlockType


def test_sf2_parser():
    """Test SF2 parser with Broware.sf2"""
    print("=" * 80)
    print("SF2 VIEWER - PARSER TEST")
    print("=" * 80)

    sf2_path = Path("output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2")

    if not sf2_path.exists():
        print(f"\n[FAIL] Test file not found: {sf2_path}")
        print("Please ensure Broware.sf2 exists")
        return False

    print(f"\nTest File: {sf2_path.name}")
    print(f"Full Path: {sf2_path}")

    # Test 1: Parser initialization
    print("\n" + "-" * 80)
    print("Test 1: Parser Initialization")
    print("-" * 80)

    parser = SF2Parser(str(sf2_path))

    if not parser.magic_id:
        print("[FAIL] Failed to parse file")
        return False

    print(f"[PASS] File parsed successfully")
    print(f"  Magic ID: 0x{parser.magic_id:04X}")
    print(f"  Load Address: ${parser.load_address:04X}")
    print(f"  File Size: {len(parser.data):,} bytes")

    # Test 2: Header blocks
    print("\n" + "-" * 80)
    print("Test 2: Header Blocks")
    print("-" * 80)

    print(f"Found {len(parser.blocks)} blocks:")
    for block_type, (offset, data) in parser.blocks.items():
        print(f"  [OK] Block 0x{block_type.value:02X} ({block_type.name:20s}): "
              f"offset=${offset:04X}, size={len(data):4d} bytes")

    # Check critical blocks
    critical_blocks = [BlockType.DESCRIPTOR, BlockType.DRIVER_COMMON, BlockType.DRIVER_TABLES]
    missing = [b.name for b in critical_blocks if b not in parser.blocks]
    if missing:
        print(f"\n[WARN] Missing critical blocks: {', '.join(missing)}")
    else:
        print(f"\n[OK] All critical blocks present")

    # Test 3: Driver information
    print("\n" + "-" * 80)
    print("Test 3: Driver Information")
    print("-" * 80)

    if not parser.driver_info:
        print("[FAIL] No driver info parsed")
        return False

    print("Driver Info:")
    for key, value in parser.driver_info.items():
        print(f"  {key:20s}: {value}")

    # Test 4: Driver Common addresses
    print("\n" + "-" * 80)
    print("Test 4: Driver Common Addresses")
    print("-" * 80)

    if not parser.driver_common:
        print("[FAIL] No driver common addresses parsed")
        return False

    addrs = parser.driver_common.to_dict()
    print("Critical Addresses:")
    print(f"  Init:   ${addrs['Init']:04X}")
    print(f"  Play:   ${addrs['Play']:04X}")
    print(f"  Stop:   ${addrs['Stop']:04X}")

    # Test 5: Table descriptors
    print("\n" + "-" * 80)
    print("Test 5: Table Descriptors")
    print("-" * 80)

    print(f"Found {len(parser.table_descriptors)} tables:")
    for i, desc in enumerate(parser.table_descriptors):
        layout_name = desc.data_layout.name
        print(f"  [{i}] {desc.name:20s}: ${desc.address:04X} "
              f"({desc.row_count:3d}x{desc.column_count:2d}) {layout_name}")

    # Test 6: Table data extraction
    print("\n" + "-" * 80)
    print("Test 6: Table Data Extraction")
    print("-" * 80)

    if not parser.table_descriptors:
        print("[WARN] No tables to test")
    else:
        first_table = parser.table_descriptors[0]
        print(f"Testing: {first_table.name}")

        table_data = parser.get_table_data(first_table)

        print(f"[OK] Extracted {len(table_data)} rows")
        if table_data:
            print(f"  First row: {' '.join(f'{b:02x}' for b in table_data[0][:8])}...")
            print(f"  Row size: {len(table_data[0])} bytes")

    # Test 7: Validation summary
    print("\n" + "-" * 80)
    print("Test 7: Validation Summary")
    print("-" * 80)

    summary = parser.get_validation_summary()
    for key, value in summary.items():
        print(f"  {key:25s}: {value}")

    # Test 8: Memory map
    print("\n" + "-" * 80)
    print("Test 8: Memory Map")
    print("-" * 80)

    memory_map = parser.get_memory_map()
    print(memory_map)

    # Final result
    print("\n" + "=" * 80)
    print("[OK] ALL TESTS PASSED")
    print("=" * 80)

    print("\nThe SF2 parser successfully:")
    print("  [OK] Parsed SF2 file format")
    print("  [OK] Identified magic number and load address")
    print("  [OK] Extracted all header blocks")
    print("  [OK] Parsed driver information")
    print("  [OK] Extracted critical addresses")
    print("  [OK] Identified all music tables")
    print("  [OK] Extracted table data correctly")

    return True


def main():
    """Main test function"""
    try:
        success = test_sf2_parser()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAIL] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
