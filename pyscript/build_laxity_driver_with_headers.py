#!/usr/bin/env python3
"""
Build complete Laxity driver PRG with SF2 headers.

Creates: drivers/laxity/sf2driver_laxity_00.prg
Structure: [LoadAddr:2][Magic:2][Headers:N][Player:1979][Padding]
"""

import struct
from pathlib import Path
from sidm2.sf2_header_generator import SF2HeaderGenerator

def build_laxity_driver():
    """Build complete driver PRG file with SF2 headers."""

    # Load relocated player code
    player_file = Path("drivers/laxity/laxity_player_relocated.bin")
    if not player_file.exists():
        print(f"ERROR: Player binary not found: {player_file}")
        return False

    with open(player_file, "rb") as f:
        player_code = f.read()

    print(f"Loaded player code: {len(player_code)} bytes")

    # Generate SF2 headers
    gen = SF2HeaderGenerator(driver_size=8192)
    headers = gen.generate_complete_headers()

    print(f"Generated SF2 headers: {len(headers)} bytes")

    # Build PRG file structure
    # [LoadAddress:2][Data]
    # LoadAddress for this driver: $0D7E
    load_address = 0x0D7E

    prg_data = bytearray()

    # PRG load address (little-endian)
    prg_data.extend(struct.pack("<H", load_address))

    # SF2 headers
    prg_data.extend(headers)

    # Player code at $0E00 (starts at offset 194 + 2 = 196)
    prg_data.extend(player_code)

    # Pad to approximately 8192 bytes for driver space
    target_size = 8192
    if len(prg_data) < target_size:
        padding = target_size - len(prg_data)
        prg_data.extend(bytes(padding))

    # Write driver file
    driver_file = Path("drivers/laxity/sf2driver_laxity_00.prg")
    driver_file.parent.mkdir(parents=True, exist_ok=True)

    with open(driver_file, "wb") as f:
        f.write(prg_data)

    print(f"\nDriver built successfully!")
    print(f"  File: {driver_file}")
    print(f"  Size: {len(prg_data)} bytes")
    print(f"  Load Address: ${load_address:04X}")
    print(f"  Structure:")
    print(f"    Load address: 2 bytes")
    print(f"    SF2 headers: {len(headers)} bytes")
    print(f"    Player code: {len(player_code)} bytes")
    print(f"    Padding: {target_size - len(prg_data) + (target_size - len(prg_data))} bytes")

    # Verify structure
    print(f"\nVerification:")
    with open(driver_file, "rb") as f:
        verify_data = f.read()

    # Check load address
    load_addr_read = struct.unpack("<H", verify_data[0:2])[0]
    print(f"  Load address: ${load_addr_read:04X} (expected ${load_address:04X})")
    assert load_addr_read == load_address, "Load address mismatch!"

    # Check magic number
    magic = struct.unpack("<H", verify_data[2:4])[0]
    print(f"  Magic number: 0x{magic:04X} (expected 0x1337)")
    assert magic == 0x1337, "Magic number mismatch!"

    # Check player code location
    expected_player_start = 2 + len(headers)
    actual_player_start = verify_data[expected_player_start:expected_player_start+2]
    print(f"  Player code at offset: {expected_player_start} (0x{expected_player_start:04X})")

    print(f"\n[OK] Driver file verified!")
    return True

if __name__ == "__main__":
    success = build_laxity_driver()
    exit(0 if success else 1)
