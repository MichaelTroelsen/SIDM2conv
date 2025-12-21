#!/usr/bin/env python3
"""
Generate SF2 Header Blocks for Laxity Driver

Creates the metadata blocks that allow the SF2 editor to work with
the custom Laxity NewPlayer v21 driver.

Author: SIDM2 Project
Date: 2025-12-13
"""

import struct
from pathlib import Path
from typing import List, Tuple


class SF2HeaderBuilder:
    """Builds SF2 driver header blocks."""

    def __init__(self):
        self.blocks = []

    def add_block(self, block_id: int, data: bytes):
        """Add a header block with ID and data."""
        # Block format: [ID byte] [data bytes] [end marker if needed]
        self.blocks.append((block_id, data))

    def build(self) -> bytes:
        """Build complete header block sequence."""
        header = bytearray()

        for block_id, data in self.blocks:
            header.append(block_id)
            header.extend(data)

        # Add end marker
        header.append(0xFF)

        return bytes(header)


def create_laxity_descriptor_block() -> Tuple[int, bytes]:
    """
    Create Block 1: Descriptor (driver info)

    Contains driver name, version, and basic metadata.
    """
    data = bytearray()

    # Driver name (null-terminated string)
    driver_name = b"Laxity NewPlayer v21\x00"
    data.extend(driver_name)

    # Version string (null-terminated)
    version = b"1.0.0\x00"
    data.extend(version)

    # Additional metadata (format varies by driver)
    # For now, minimal metadata
    data.extend(b"\x00\x00")  # Padding

    return (1, bytes(data))


def create_laxity_common_block(
    load_addr: int = 0x0D7E,
    init_addr: int = 0x0E00,
    play_addr: int = 0x0EA1,
    stop_addr: int = 0x0D84
) -> Tuple[int, bytes]:
    """
    Create Block 2: Driver Common (entry points and addresses)

    Args:
        load_addr: Where driver is loaded ($0D7E for SF2 wrapper)
        init_addr: Init routine address (relocated Laxity init)
        play_addr: Play routine address (relocated Laxity play)
        stop_addr: Stop routine address (wrapper cleanup)

    Returns:
        (block_id, block_data)
    """
    data = bytearray()

    # Pack addresses as little-endian 16-bit words
    data.extend(struct.pack('<H', load_addr))   # Load address
    data.extend(struct.pack('<H', init_addr))   # Init address
    data.extend(struct.pack('<H', play_addr))   # Play address
    data.extend(struct.pack('<H', stop_addr))   # Stop address

    return (2, bytes(data))


def create_laxity_tables_block(
    instruments_addr: int = 0x186B,  # Relocated from $1A6B
    wave_addr: int = 0x18CB,         # Relocated from $1ACB
    pulse_addr: int = 0x183B,        # Relocated from $1A3B
    filter_addr: int = 0x181E        # Relocated from $1A1E
) -> Tuple[int, bytes]:
    """
    Create Block 3: Driver Tables (table definitions for SF2 editor)

    Defines the Laxity table layouts so the SF2 editor can display/edit them.

    Laxity Table Formats:
    - Instruments: 8 bytes × 32 entries, column-major (6 used columns)
    - Wave: 2 bytes × 128 entries, row-major
    - Pulse: 4 bytes × 64 entries, row-major
    - Filter: 4 bytes × 32 entries, row-major

    Args:
        instruments_addr: Relocated instrument table address
        wave_addr: Relocated wave table address
        pulse_addr: Relocated pulse table address
        filter_addr: Relocated filter table address

    Returns:
        (block_id, block_data)
    """
    data = bytearray()

    # Table descriptor format (varies by SF2 version)
    # This is a simplified format based on NP20 driver analysis

    # Instruments table descriptor
    data.extend(struct.pack('<H', instruments_addr))  # Address
    data.append(32)   # Row count (32 instruments)
    data.append(6)    # Column count (AD, SR, Flags, Filter, Pulse, Wave)
    data.append(1)    # Layout: 1 = column-major
    data.append(0)    # Flags

    # Wave table descriptor
    data.extend(struct.pack('<H', wave_addr))  # Address
    data.append(128)  # Row count
    data.append(2)    # Column count (waveform, note offset)
    data.append(0)    # Layout: 0 = row-major
    data.append(0)    # Flags

    # Pulse table descriptor
    data.extend(struct.pack('<H', pulse_addr))  # Address
    data.append(64)   # Row count
    data.append(4)    # Column count (PWM parameters)
    data.append(0)    # Layout: 0 = row-major
    data.append(0)    # Flags

    # Filter table descriptor
    data.extend(struct.pack('<H', filter_addr))  # Address
    data.append(32)   # Row count
    data.append(4)    # Column count (filter parameters)
    data.append(0)    # Layout: 0 = row-major
    data.append(0)    # Flags

    return (3, bytes(data))


def create_music_data_block() -> Tuple[int, bytes]:
    """
    Create Block 5: Music Data (pointers to sequences/orderlists)

    Format (18 bytes total):
    - track_count (1)
    - orderlist_ptrs_lo (2)
    - orderlist_ptrs_hi (2)
    - sequence_count (1)
    - sequence_ptrs_lo (2)
    - sequence_ptrs_hi (2)
    - orderlist_size (2)
    - orderlist_start (2)
    - sequence_size (2)
    - sequence_start (2)
    """
    data = bytearray()

    # Laxity format defaults
    track_count = 3  # 3 voices
    orderlist_start = 0x1900  # Orderlists start after relocated player
    orderlist_size = 3 * 256  # 3 tracks × 256 bytes max
    sequence_start = orderlist_start + orderlist_size  # Sequences after orderlists
    sequence_size = 1024  # Placeholder
    sequence_count = 32  # Placeholder

    orderlist_ptrs_lo = orderlist_start
    orderlist_ptrs_hi = orderlist_start + 256  # High bytes 256 bytes later
    sequence_ptrs_lo = sequence_start
    sequence_ptrs_hi = sequence_start + 256

    data.append(track_count)
    data.extend(struct.pack('<H', orderlist_ptrs_lo))
    data.extend(struct.pack('<H', orderlist_ptrs_hi))
    data.append(sequence_count)
    data.extend(struct.pack('<H', sequence_ptrs_lo))
    data.extend(struct.pack('<H', sequence_ptrs_hi))
    data.extend(struct.pack('<H', orderlist_size))
    data.extend(struct.pack('<H', orderlist_start))
    data.extend(struct.pack('<H', sequence_size))
    data.extend(struct.pack('<H', sequence_start))

    return (5, bytes(data))


def generate_laxity_driver_header(
    output_path: Path,
    relocation_offset: int = -0x0200  # $1000 → $0E00
) -> bytes:
    """
    Generate complete SF2 header for Laxity driver.

    Args:
        output_path: Where to write header binary
        relocation_offset: Offset applied during relocation

    Returns:
        Header bytes
    """
    builder = SF2HeaderBuilder()

    # Calculate relocated addresses
    # Original Laxity addresses:
    # - Init: $1000
    # - Play: $10A1
    # - Tables: $1A1E (filter), $1A3B (pulse), $1A6B (instruments), $1ACB (wave)

    # After relocation ($1000 → $0E00, offset -$0200):
    init_addr = 0x1000 + relocation_offset       # $0E00
    play_addr = 0x10A1 + relocation_offset       # $0EA1
    filter_addr = 0x1A1E + relocation_offset     # $181E
    pulse_addr = 0x1A3B + relocation_offset      # $183B
    instruments_addr = 0x1A6B + relocation_offset  # $186B
    wave_addr = 0x1ACB + relocation_offset       # $18CB

    print(f"Generating SF2 header with relocation offset: {relocation_offset:+05X}")
    print(f"\nEntry Points:")
    print(f"  Init:  0x{init_addr:04X}")
    print(f"  Play:  0x{play_addr:04X}")
    print(f"\nTable Addresses:")
    print(f"  Instruments: 0x{instruments_addr:04X}")
    print(f"  Wave:        0x{wave_addr:04X}")
    print(f"  Pulse:       0x{pulse_addr:04X}")
    print(f"  Filter:      0x{filter_addr:04X}")

    # Add header blocks
    builder.add_block(*create_laxity_descriptor_block())
    builder.add_block(*create_laxity_common_block(
        init_addr=init_addr,
        play_addr=play_addr
    ))
    builder.add_block(*create_laxity_tables_block(
        instruments_addr=instruments_addr,
        wave_addr=wave_addr,
        pulse_addr=pulse_addr,
        filter_addr=filter_addr
    ))
    builder.add_block(*create_music_data_block())

    # Build complete header
    header = builder.build()

    # Write to file
    with open(output_path, 'wb') as f:
        f.write(header)

    print(f"\nHeader written to: {output_path}")
    print(f"Size: {len(header)} bytes")

    # Show hex dump of first 64 bytes
    print(f"\nFirst 64 bytes:")
    for i in range(0, min(64, len(header)), 16):
        hex_str = ' '.join(f'{b:02x}' for b in header[i:i+16])
        print(f"  {i:04X}: {hex_str}")

    return header


def main():
    """Main header generation workflow."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generate_sf2_header.py <output_file> [relocation_offset]")
        print("\nExample:")
        print("  python generate_sf2_header.py drivers/laxity/header.bin")
        print("  python generate_sf2_header.py drivers/laxity/header.bin -0x0200")
        return

    output_path = Path(sys.argv[1])
    relocation_offset = -0x0200  # Default: $1000 → $0E00

    if len(sys.argv) >= 3:
        offset_str = sys.argv[2]
        relocation_offset = int(offset_str, 16) if offset_str.startswith(('0x', '-0x')) else int(offset_str)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate header
    print("="*70)
    print("SF2 HEADER GENERATOR FOR LAXITY DRIVER")
    print("="*70)

    header = generate_laxity_driver_header(output_path, relocation_offset)

    print("\n" + "="*70)
    print("HEADER GENERATION COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. Build relocation engine (Phase 3)")
    print("2. Relocate player code to $0E00")
    print("3. Combine header + relocated player + wrapper")
    print("4. Test driver in SF2 editor")


if __name__ == '__main__':
    main()
