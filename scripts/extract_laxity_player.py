#!/usr/bin/env python3
"""
Extract Laxity NewPlayer v21 Binary

Extracts the Laxity player code and tables from a reference SID file
for use in building a custom SF2 driver.

Author: SIDM2 Project
Date: 2025-12-13
"""

import sys
import struct
from pathlib import Path


def parse_sid_header(sid_path):
    """Parse SID file header to get load address and data offset."""
    with open(sid_path, 'rb') as f:
        data = f.read()

    # Check magic
    magic = data[0:4].decode('ascii', errors='ignore')
    if magic not in ['PSID', 'RSID']:
        raise ValueError(f"Not a valid SID file: {magic}")

    # Parse header
    version = struct.unpack('>H', data[4:6])[0]
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_addr = struct.unpack('>H', data[8:10])[0]
    init_addr = struct.unpack('>H', data[10:12])[0]
    play_addr = struct.unpack('>H', data[12:14])[0]

    print(f"SID File: {sid_path.name}")
    print(f"  Magic: {magic}")
    print(f"  Version: {version}")
    print(f"  Data Offset: 0x{data_offset:04X}")
    print(f"  Load Address: 0x{load_addr:04X}")
    print(f"  Init Address: 0x{init_addr:04X}")
    print(f"  Play Address: 0x{play_addr:04X}")

    return data, data_offset, load_addr, init_addr, play_addr


def extract_player(sid_path, output_path, start_addr=0x1000, end_addr=0x1CFF):
    """
    Extract Laxity player binary from SID file.

    Standard Laxity NewPlayer v21 layout:
    - $1000-$10A0: Init routine
    - $10A1-$1A1D: Play routine and helper functions
    - $1A1E-$1A3A: Filter table (29 bytes)
    - $1A3B-$1A6A: Pulse table (48 bytes)
    - $1A6B-$1ACA: Instruments table (96 bytes)
    - $1ACB+: Wave table (variable length)

    Args:
        sid_path: Path to reference SID file
        output_path: Path for output binary
        start_addr: Start address of player code (default 0x1000)
        end_addr: End address of player + tables (default 0x1CFF, ~3.25KB)
    """
    data, data_offset, load_addr, init_addr, play_addr = parse_sid_header(sid_path)

    # Verify this is a standard Laxity file
    if init_addr != 0x1000:
        print(f"\nWARNING: Init address is 0x{init_addr:04X}, not standard 0x1000")
        print(f"This may not be a standard Laxity NewPlayer v21 file!")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Extraction cancelled.")
            return None

    # Calculate extraction range
    sid_data = data[data_offset:]

    # If load_addr is 0, data starts at the address embedded in first 2 bytes
    if load_addr == 0:
        load_addr = struct.unpack('<H', sid_data[0:2])[0]
        sid_data = sid_data[2:]  # Skip the embedded load address
        print(f"  Actual Load Address: 0x{load_addr:04X} (from embedded)")

    # Calculate byte offsets
    start_offset = start_addr - load_addr
    end_offset = end_addr - load_addr + 1

    if start_offset < 0 or end_offset > len(sid_data):
        print(f"\nERROR: Extraction range out of bounds!")
        print(f"  Requested: 0x{start_addr:04X} - 0x{end_addr:04X}")
        print(f"  Available: 0x{load_addr:04X} - 0x{load_addr + len(sid_data):04X}")
        return None

    # Extract player binary
    player_binary = sid_data[start_offset:end_offset]

    print(f"\nExtraction Summary:")
    print(f"  Address Range: 0x{start_addr:04X} - 0x{end_addr:04X}")
    print(f"  Size: {len(player_binary)} bytes ({len(player_binary) / 1024:.2f} KB)")
    print(f"  Output: {output_path}")

    # Write to file
    with open(output_path, 'wb') as f:
        f.write(player_binary)

    print(f"\n✓ Laxity player extracted successfully!")

    return player_binary


def analyze_player_structure(player_binary, base_addr=0x1000):
    """Quick analysis of extracted player binary."""
    print(f"\n{'='*70}")
    print("PLAYER STRUCTURE ANALYSIS")
    print(f"{'='*70}")

    # Check for known Laxity patterns
    print(f"\nSearching for Laxity player signatures...")

    # LDA #$00, STA pattern (common in init)
    init_pattern = bytes([0xA9, 0x00, 0x8D])
    if init_pattern in player_binary[:0x50]:
        offset = player_binary[:0x50].index(init_pattern)
        print(f"  ✓ Found init pattern at offset 0x{offset:04X} (addr 0x{base_addr + offset:04X})")

    # Look for SID register writes (STA $D4xx)
    sid_writes = 0
    for i in range(len(player_binary) - 2):
        if player_binary[i] == 0x8D:  # STA absolute
            addr = struct.unpack('<H', player_binary[i+1:i+3])[0]
            if 0xD400 <= addr <= 0xD41C:  # SID register range
                sid_writes += 1

    print(f"  ✓ Found {sid_writes} SID register writes (STA $D4xx)")

    # Estimate code vs data sections
    print(f"\nEstimated layout (assuming base address 0x{base_addr:04X}):")
    print(f"  Code section: 0x{base_addr:04X} - ~0x{base_addr + 0xA00:04X}")
    print(f"  Table section: ~0x{base_addr + 0xA1E:04X} - 0x{base_addr + len(player_binary):04X}")

    # Show first 32 bytes (hex dump)
    print(f"\nFirst 32 bytes (init routine start):")
    for i in range(0, min(32, len(player_binary)), 16):
        hex_str = ' '.join(f'{b:02x}' for b in player_binary[i:i+16])
        addr_str = f"  {base_addr + i:04X}:"
        print(f"{addr_str} {hex_str}")

    print(f"\n{'='*70}")


def main():
    """Main extraction workflow."""
    if len(sys.argv) < 2:
        print("Usage: python extract_laxity_player.py <sid_file> [output_file] [end_addr]")
        print("\nExample:")
        print("  python extract_laxity_player.py SIDSF2player/Stinsens.sid")
        print("  python extract_laxity_player.py SIDSF2player/Stinsens.sid drivers/laxity/player.bin 0x1DFF")
        return

    sid_path = Path(sys.argv[1])
    if not sid_path.exists():
        print(f"ERROR: File not found: {sid_path}")
        return

    # Default output path
    output_path = Path("drivers/laxity/laxity_player_reference.bin")
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])

    # Default end address (covers player + tables, ~3.25KB)
    end_addr = 0x1CFF
    if len(sys.argv) >= 4:
        end_addr = int(sys.argv[3], 16) if sys.argv[3].startswith('0x') else int(sys.argv[3])

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Extract player
    player_binary = extract_player(sid_path, output_path, end_addr=end_addr)

    if player_binary:
        # Analyze structure
        analyze_player_structure(player_binary)

        print(f"\n{'='*70}")
        print("NEXT STEPS:")
        print(f"{'='*70}")
        print("1. Disassemble with SIDwinder:")
        print(f"   tools/SIDwinder.exe disassemble {sid_path}")
        print("\n2. Analyze relocation requirements:")
        print(f"   python scripts/analyze_laxity_relocation.py {output_path}")
        print("\n3. Build relocation engine (Phase 3)")
        print(f"{'='*70}")


if __name__ == '__main__':
    main()
