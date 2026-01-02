"""Regenerate pointer patches for Laxity driver.

This script scans the current Laxity driver binary (sf2driver_laxity_00.prg)
and generates a new pointer patch table for sidm2/sf2_writer.py.

The patches redirect default table pointers to injected music data locations.
"""

import struct
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.cpu6502 import CPU6502


def analyze_laxity_driver(driver_path: str):
    """Analyze Laxity driver and generate pointer patches.

    Args:
        driver_path: Path to sf2driver_laxity_00.prg

    Returns:
        List of (file_offset, old_lo, old_hi, new_lo, new_hi, description) tuples
    """
    print(f"Analyzing Laxity driver: {driver_path}")
    print("=" * 70)

    # Read driver binary
    with open(driver_path, 'rb') as f:
        driver_data = f.read()

    print(f"Driver size: {len(driver_data)} bytes (0x{len(driver_data):04X})")

    # Get load address from PRG header
    load_addr = struct.unpack('<H', driver_data[0:2])[0]
    print(f"Load address: ${load_addr:04X}")
    print()

    # Initialize CPU6502 disassembler
    cpu = CPU6502(driver_data)

    # Define memory regions
    #   $0D7E-$0DFF: SF2 Wrapper (130 bytes)
    #   $0E00-$16FF: Relocated Laxity Player (2,304 bytes)
    #   $1700-$18FF: SF2 Header Blocks (512 bytes)
    #   $1900+:      Music Data (orderlists, sequences, wave, pulse, filter, instruments)

    # Music data injection locations (from sf2_writer.py)
    ORDERLIST_ADDR = 0x1900  # 3 orderlists × 256 bytes = 768 bytes
    SEQ_START = 0x1C00       # After orderlists
    WAVE_ADDR = 0x1ACB       # Wave table
    PULSE_ADDR = 0x1B3B      # Pulse table
    FILTER_ADDR = 0x1B9B     # Filter table
    INST_ADDR = 0x1A6B       # Instrument table

    # Scan for all pointers to music data region ($1900-$1FFF)
    # This includes both code instructions and data table pointers
    music_data_start = 0x1900
    music_data_end = 0x2000

    print("Scanning driver code for music data pointers...")
    print(f"Target region: ${music_data_start:04X}-${music_data_end:04X}")
    print()

    # Scan code section ($0E00-$16FF) for absolute addressing instructions
    code_start_offset = 0x0E00 - load_addr + 2
    code_end_offset = 0x1700 - load_addr + 2

    code_pointers = cpu.scan_relocatable_addresses(
        code_start_offset,
        code_end_offset,
        music_data_start,
        music_data_end
    )

    print(f"Found {len(code_pointers)} code pointers to music data region:")

    patches = []
    for offset, addr in code_pointers:
        # Calculate PC address and file offset
        pc_addr = offset + load_addr - 2
        file_offset = offset

        # Get current bytes
        old_lo = driver_data[file_offset]
        old_hi = driver_data[file_offset + 1]

        # For now, keep same address (we'll update targets after analyzing usage)
        new_lo = old_lo
        new_hi = old_hi

        print(f"  ${pc_addr:04X} (offset ${file_offset:04X}): ${addr:04X} = {old_hi:02X} {old_lo:02X}")

        patches.append((file_offset, old_lo, old_hi, new_lo, new_hi, f"${pc_addr:04X} -> ${addr:04X}"))

    print()

    # Scan data tables section for embedded pointers
    data_start_offset = 0x0E00 - load_addr + 2  # Start of player code
    data_end_offset = 0x1700 - load_addr + 2    # Before SF2 headers

    print("Scanning driver data tables for music data pointers...")

    data_pointers = cpu.scan_data_pointers(
        data_start_offset,
        data_end_offset,
        music_data_start,
        music_data_end,
        alignment=1
    )

    print(f"Found {len(data_pointers)} data table pointers to music data region:")

    for offset, addr in data_pointers:
        # Skip if already found in code scan
        if (offset, addr) in code_pointers:
            continue

        # Calculate PC address
        pc_addr = offset + load_addr - 2
        file_offset = offset

        # Get current bytes
        old_lo = driver_data[file_offset]
        old_hi = driver_data[file_offset + 1]

        # For now, keep same address
        new_lo = old_lo
        new_hi = old_hi

        print(f"  ${pc_addr:04X} (offset ${file_offset:04X}): ${addr:04X} = {old_hi:02X} {old_lo:02X}")

        patches.append((file_offset, old_lo, old_hi, new_lo, new_hi, f"${pc_addr:04X} -> ${addr:04X}"))

    print()
    print("=" * 70)
    print(f"TOTAL POINTERS FOUND: {len(patches)}")
    print()

    return patches, load_addr


def generate_patch_code(patches, load_addr):
    """Generate Python code for pointer_patches list.

    Args:
        patches: List of (file_offset, old_lo, old_hi, new_lo, new_hi, desc) tuples
        load_addr: Driver load address
    """
    print("Generated pointer_patches code for sf2_writer.py:")
    print("=" * 70)
    print()
    print("# REGENERATED POINTER PATCHES (v2.9.1)")
    print(f"# Driver: sf2driver_laxity_00.prg (load address ${load_addr:04X})")
    print(f"# Generated: {len(patches)} patches")
    print("#")
    print("# Format: (file_offset, old_lo, old_hi, new_lo, new_hi)")
    print("# where file_offset = PC_address - load_addr + 2")
    print("#")
    print("pointer_patches = [")

    for file_offset, old_lo, old_hi, new_lo, new_hi, desc in patches:
        print(f"    (0x{file_offset:04X}, 0x{old_lo:02X}, 0x{old_hi:02X}, 0x{new_lo:02X}, 0x{new_hi:02X}),  # {desc}")

    print("]")
    print()
    print("=" * 70)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Regenerate Laxity driver pointer patches')
    parser.add_argument('driver', nargs='?',
                       default='drivers/laxity/sf2driver_laxity_00.prg',
                       help='Path to Laxity driver PRG file')
    parser.add_argument('-o', '--output', help='Output file for patches (default: stdout)')

    args = parser.parse_args()

    # Analyze driver
    patches, load_addr = analyze_laxity_driver(args.driver)

    # Generate patch code
    if args.output:
        import sys
        old_stdout = sys.stdout
        sys.stdout = open(args.output, 'w')
        generate_patch_code(patches, load_addr)
        sys.stdout.close()
        sys.stdout = old_stdout
        print(f"Patches written to: {args.output}")
    else:
        generate_patch_code(patches, load_addr)


if __name__ == '__main__':
    main()
