#!/usr/bin/env python3
"""Extract Laxity NewPlayer v21 code from reference SID file."""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def extract_player_from_sid(sid_file: str, output_file: str = None) -> bytes:
    """Extract Laxity player code from SID file."""
    with open(sid_file, 'rb') as f:
        header = f.read(126)
        music_data = f.read()  # Read while file is still open!

    if header[0:4] not in [b'PSID', b'RSID']:
        raise ValueError("Not a valid SID file")

    load_addr = struct.unpack('>H', header[8:10])[0]
    init_addr = struct.unpack('>H', header[10:12])[0]
    play_addr = struct.unpack('>H', header[12:14])[0]

    print(f"SID Header Info:")
    print(f"  Load Address: ${load_addr:04X}")
    print(f"  Init Address: ${init_addr:04X}")
    print(f"  Play Address: ${play_addr:04X}")

    if load_addr == 0x0000:
        player_start = 0x1000
    else:
        player_start = init_addr - load_addr

    player_end = player_start + 0x0A00

    if player_end > len(music_data):
        player_end = len(music_data)

    player_code = music_data[player_start:player_end]

    print(f"\nExtraction:")
    print(f"  Player Start Offset: ${player_start:04X}")
    print(f"  Player End Offset:   ${player_end:04X}")
    print(f"  Player Size:         {len(player_code):,} bytes (${len(player_code):04X})")

    if output_file:
        with open(output_file, 'wb') as f:
            f.write(player_code)
        print(f"  Output File:         {output_file}")

    return player_code


def analyze_player_code(player_code: bytes) -> dict:
    """Analyze extracted player code for relocation information."""
    analysis = {
        'absolute_addresses': [],
        'zero_page_usage': set(),
        'entry_points': [],
        'size': len(player_code),
        'estimated_tables': {}
    }

    for offset in range(len(player_code) - 1):
        lo = player_code[offset]
        hi = player_code[offset + 1]
        addr = (hi << 8) | lo

        if 0x1000 <= addr <= 0x1AFF:
            analysis['absolute_addresses'].append({
                'offset': offset,
                'address': addr,
            })

    common_table_addrs = {
        0x1A1E: 'Filter table',
        0x1A3B: 'Pulse table',
        0x1A6B: 'Instruments table',
        0x1ACB: 'Wave table',
    }

    analysis['estimated_tables'] = {
        addr: desc for addr, desc in common_table_addrs.items()
        if any(ref['address'] == addr for ref in analysis['absolute_addresses'])
    }

    zero_page_refs = set()
    for offset in range(len(player_code) - 1):
        opcode = player_code[offset]
        operand = player_code[offset + 1] if offset + 1 < len(player_code) else 0

        if opcode in [0xA5, 0xA6, 0xA4, 0x85, 0x86, 0x84, 0xE5, 0xE4, 0xE6, 0xC5, 0xC4, 0xC6]:
            if operand < 0xFF:
                zero_page_refs.add(operand)

    analysis['zero_page_usage'] = sorted(zero_page_refs)

    entry_points = []
    for offset in range(len(player_code)):
        if player_code[offset] == 0x60:  # RTS
            entry_points.append(offset)

    analysis['entry_points'] = entry_points[:10]

    return analysis


def main():
    """Main entry point"""
    reference_sid = Path('./Laxity/Stinsens_Last_Night_of_89.sid')

    if not reference_sid.exists():
        print(f"Error: Reference file not found: {reference_sid}")
        laxity_dir = Path('./Laxity')
        if laxity_dir.exists():
            for sid_file in sorted(laxity_dir.glob('*.sid'))[:5]:
                print(f"  - {sid_file.name}")
        return

    print(f"Extracting player from: {reference_sid}")
    print()

    output_path = Path('./drivers/laxity/laxity_player_reference.bin')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        player_code = extract_player_from_sid(str(reference_sid), str(output_path))

        print()
        print("Analyzing player code...")
        analysis = analyze_player_code(player_code)

        print(f"\nAnalysis Results:")
        print(f"  Player Size: {analysis['size']:,} bytes")
        print(f"  Absolute Address References: {len(analysis['absolute_addresses'])}")
        print(f"  Zero Page Usage: {len(analysis['zero_page_usage'])} locations")
        if analysis['zero_page_usage']:
            print(f"    Addresses: {' '.join(f'${z:02X}' for z in analysis['zero_page_usage'])}")
        print(f"  Entry Points (RTS): {len(analysis['entry_points'])}")
        if analysis['estimated_tables']:
            print(f"  Estimated Tables Found:")
            for addr, desc in sorted(analysis['estimated_tables'].items()):
                print(f"    ${addr:04X}: {desc}")

        report_path = Path('./drivers/laxity/extraction_analysis.txt')
        with open(report_path, 'w') as f:
            f.write("LAXITY PLAYER EXTRACTION ANALYSIS\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Reference SID: {reference_sid}\n")
            f.write(f"Player Size: {analysis['size']:,} bytes (${analysis['size']:04X})\n\n")
            f.write(f"ABSOLUTE ADDRESSES: {len(analysis['absolute_addresses'])}\n")
            f.write(f"ZERO PAGE USAGE: {len(analysis['zero_page_usage'])} locations\n")
            f.write(f"ESTIMATED TABLES: {len(analysis['estimated_tables'])}\n")

        print(f"\nAnalysis saved to: {report_path}")
        print(f"\n=== Phase 1 Complete ===")
        print(f"Player extracted to: {output_path}")
        print(f"Analysis report: {report_path}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
