#!/usr/bin/env python3
"""Test script to validate SF2PlayerParser on multiple SID files."""

import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sidm2.sf2_player_parser import SF2PlayerParser, PSIDHeader, ExtractedData

def test_file(sid_path: str, sf2_reference: str = None) -> dict:
    """Test parsing a single SID file."""
    result = {
        'path': sid_path,
        'name': os.path.basename(sid_path),
        'size': os.path.getsize(sid_path),
        'success': False,
        'header': None,
        'extraction': None,
        'error': None
    }

    try:
        parser = SF2PlayerParser(sid_path, sf2_reference)

        # Parse header
        header = parser.parse_sid_header()
        result['header'] = {
            'magic': header.magic,
            'version': header.version,
            'data_offset': header.data_offset,
            'load_addr': f"${header.load_address:04X}",
            'init_addr': f"${header.init_address:04X}",
            'play_addr': f"${header.play_address:04X}",
            'name': header.name,
            'author': header.author,
            'copyright': header.copyright,
        }

        # Extract data
        extracted = parser.extract()
        result['extraction'] = {
            'instruments': len(extracted.instruments),
            'wave_table_size': len(extracted.wavetable),
            'pulse_table_size': len(extracted.pulsetable),
            'filter_table_size': len(extracted.filtertable),
            'sequences_count': len(extracted.sequences),
            'orderlists_count': len(extracted.orderlists),
        }

        result['success'] = True

    except Exception as e:
        result['error'] = str(e)

    return result

def main():
    """Test all SID files in SIDSF2player folder."""
    sidsf2_folder = Path(__file__).parent / "SIDSF2player"

    if not sidsf2_folder.exists():
        print(f"ERROR: {sidsf2_folder} not found")
        return

    # Find all SID files
    sid_files = list(sidsf2_folder.glob("*.sid"))
    sf2_files = list(sidsf2_folder.glob("*.sf2"))

    print(f"Found {len(sid_files)} SID files and {len(sf2_files)} SF2 files")
    print("=" * 70)

    # Use first SF2 file as reference if available
    sf2_reference = str(sf2_files[0]) if sf2_files else None
    if sf2_reference:
        print(f"Using SF2 reference: {os.path.basename(sf2_reference)}")
        print("=" * 70)

    # Test each SID file
    results = []
    for sid_file in sorted(sid_files):
        print(f"\nTesting: {sid_file.name}")
        print("-" * 50)

        # Test without SF2 reference first
        result_no_ref = test_file(str(sid_file), None)

        # Test with SF2 reference if available
        result_with_ref = None
        if sf2_reference:
            result_with_ref = test_file(str(sid_file), sf2_reference)

        # Print header info
        if result_no_ref['header']:
            h = result_no_ref['header']
            print(f"  Header: {h['magic']} v{h['version']}")
            print(f"  Load: {h['load_addr']}, Init: {h['init_addr']}, Play: {h['play_addr']}")
            print(f"  Name: {h['name']}")
            print(f"  Author: {h['author']}")

        # Print extraction results
        print(f"\n  Extraction without SF2 reference:")
        if result_no_ref['extraction']:
            e = result_no_ref['extraction']
            print(f"    Instruments: {e['instruments']}")
            print(f"    Wave table: {e['wave_table_size']} bytes")
            print(f"    Pulse table: {e['pulse_table_size']} bytes")
            print(f"    Filter table: {e['filter_table_size']} bytes")
            print(f"    Sequences: {e['sequences_count']}")
            print(f"    Orderlists: {e['orderlists_count']}")
        elif result_no_ref['error']:
            print(f"    ERROR: {result_no_ref['error']}")
        else:
            print(f"    Empty extraction (heuristic mode returns empty)")

        if result_with_ref:
            print(f"\n  Extraction WITH SF2 reference:")
            if result_with_ref['extraction']:
                e = result_with_ref['extraction']
                print(f"    Instruments: {e['instruments']}")
                print(f"    Wave table: {e['wave_table_size']} bytes")
                print(f"    Pulse table: {e['pulse_table_size']} bytes")
                print(f"    Filter table: {e['filter_table_size']} bytes")
                print(f"    Sequences: {e['sequences_count']}")
                print(f"    Orderlists: {e['orderlists_count']}")
            elif result_with_ref['error']:
                print(f"    ERROR: {result_with_ref['error']}")

        results.append({
            'file': sid_file.name,
            'no_ref': result_no_ref,
            'with_ref': result_with_ref
        })

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = sum(1 for r in results if r['no_ref']['success'])
    print(f"Header parsing: {successful}/{len(results)} successful")

    with_data = sum(1 for r in results if r['no_ref']['extraction'] and r['no_ref']['extraction']['instruments'] > 0)
    print(f"Extraction (no ref): {with_data}/{len(results)} with data")

    if sf2_reference:
        with_data_ref = sum(1 for r in results if r['with_ref'] and r['with_ref']['extraction'] and r['with_ref']['extraction']['instruments'] > 0)
        print(f"Extraction (with ref): {with_data_ref}/{len(results)} with data")

if __name__ == "__main__":
    main()
