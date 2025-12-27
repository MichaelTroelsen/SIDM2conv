#!/usr/bin/env python3
"""Direct binary comparison of two SF2 files."""

import struct
from pathlib import Path


def read_sf2_file(sf2_path):
    """Read SF2 file and return parsed data."""
    with open(sf2_path, 'rb') as f:
        data = f.read()

    load_addr = struct.unpack('<H', data[0:2])[0]
    c64_data = data[2:]

    return {
        'path': sf2_path,
        'size': len(data),
        'load_addr': load_addr,
        'c64_data': c64_data
    }


def compare_files(file1_path, file2_path):
    """Compare two SF2 files."""
    print("="*70)
    print("SF2 BINARY COMPARISON")
    print("="*70)

    file1 = read_sf2_file(file1_path)
    file2 = read_sf2_file(file2_path)

    print(f"\nFile 1: {file1_path.name}")
    print(f"  Size: {file1['size']:,} bytes")
    print(f"  Load address: ${file1['load_addr']:04X}")

    print(f"\nFile 2: {file2_path.name}")
    print(f"  Size: {file2['size']:,} bytes")
    print(f"  Load address: ${file2['load_addr']:04X}")

    # Compare sizes
    if file1['size'] == file2['size']:
        print(f"\nOK: File sizes match: {file1['size']:,} bytes")
    else:
        print(f"\nWARNING: File size mismatch: {file1['size']:,} vs {file2['size']:,} bytes")
        print(f"  Difference: {abs(file1['size'] - file2['size']):,} bytes")

    # Compare load addresses
    if file1['load_addr'] == file2['load_addr']:
        print(f"OK: Load addresses match: ${file1['load_addr']:04X}")
    else:
        print(f"WARNING: Load address mismatch: ${file1['load_addr']:04X} vs ${file2['load_addr']:04X}")

    # Byte-by-byte comparison
    data1 = file1['c64_data']
    data2 = file2['c64_data']

    min_len = min(len(data1), len(data2))
    matches = 0
    differences = []

    for i in range(min_len):
        if data1[i] == data2[i]:
            matches += 1
        else:
            if len(differences) < 20:  # Show first 20 differences
                differences.append({
                    'offset': i,
                    'addr': file1['load_addr'] + i,
                    'byte1': data1[i],
                    'byte2': data2[i]
                })

    accuracy = (matches / min_len) * 100

    print(f"\n{'='*70}")
    print("BYTE-BY-BYTE COMPARISON")
    print(f"{'='*70}")
    print(f"Matching bytes: {matches:,}/{min_len:,} ({accuracy:.2f}%)")

    if differences:
        print(f"\nFirst {len(differences)} differences:")
        for diff in differences:
            print(f"  Offset {diff['offset']:4d} (${diff['addr']:04X}): "
                  f"${diff['byte1']:02X} vs ${diff['byte2']:02X}")

    # Overall result
    print(f"\n{'='*70}")
    print("RESULT")
    print(f"{'='*70}")

    if accuracy == 100.0:
        print("SUCCESS: FILES ARE IDENTICAL!")
    elif accuracy >= 99.9:
        print("OK: Files are virtually identical (>99.9% match)")
    elif accuracy >= 95.0:
        print("WARNING: Files are mostly similar (>95% match)")
    else:
        print("FAIL: Files have significant differences")

    return accuracy


def main():
    """Main comparison."""
    original = Path(r"C:\Users\mit\claude\c64server\SIDM2\learnings\Laxity - Stinsen - Last Night Of 89.sf2")
    converted = Path(r"C:\Users\mit\claude\c64server\SIDM2\output\Stinsens_FINAL.sf2")

    if not original.exists():
        print(f"ERROR: Original file not found: {original}")
        return 1

    if not converted.exists():
        print(f"ERROR: Converted file not found: {converted}")
        return 1

    accuracy = compare_files(original, converted)

    return 0 if accuracy >= 99.0 else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
