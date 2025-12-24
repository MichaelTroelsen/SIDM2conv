"""Test disassembler on real Laxity SID files.

Tests the 6502 disassembler on actual Laxity NewPlayer v21 SID files,
including Stinsens_Last_Night_of_89.sid.
"""

import sys
from pathlib import Path
from typing import Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from disassembler_6502 import Disassembler6502


def parse_sid_header(sid_data: bytes) -> dict:
    """Parse PSID/RSID file header.

    Args:
        sid_data: Complete SID file data

    Returns:
        Dictionary with header information
    """
    if len(sid_data) < 0x7C:
        raise ValueError("File too small to be a valid SID file")

    magic = sid_data[0:4].decode('ascii', errors='ignore')
    if magic not in ('PSID', 'RSID'):
        raise ValueError(f"Invalid magic: {magic}")

    version = (sid_data[4] << 8) | sid_data[5]
    data_offset = (sid_data[6] << 8) | sid_data[7]
    load_addr = (sid_data[8] << 8) | sid_data[9]
    init_addr = (sid_data[0xA] << 8) | sid_data[0xB]
    play_addr = (sid_data[0xC] << 8) | sid_data[0xD]
    songs = (sid_data[0xE] << 8) | sid_data[0xF]
    start_song = (sid_data[0x10] << 8) | sid_data[0x11]

    # Extract title, author, copyright (null-terminated strings)
    title = sid_data[0x16:0x36].decode('ascii', errors='ignore').rstrip('\x00')
    author = sid_data[0x36:0x56].decode('ascii', errors='ignore').rstrip('\x00')
    copyright = sid_data[0x56:0x76].decode('ascii', errors='ignore').rstrip('\x00')

    # If load_addr is 0, it's embedded in the file at data_offset
    if load_addr == 0 and len(sid_data) > data_offset + 2:
        load_addr = sid_data[data_offset] | (sid_data[data_offset + 1] << 8)
        code_start = data_offset + 2
    else:
        code_start = data_offset

    return {
        'magic': magic,
        'version': version,
        'data_offset': data_offset,
        'load_addr': load_addr,
        'init_addr': init_addr,
        'play_addr': play_addr,
        'songs': songs,
        'start_song': start_song,
        'title': title,
        'author': author,
        'copyright': copyright,
        'code_start': code_start,
    }


def disassemble_sid_file(filepath: Path, max_instructions: int = 100) -> Tuple[dict, str]:
    """Disassemble SID file.

    Args:
        filepath: Path to SID file
        max_instructions: Maximum instructions to disassemble

    Returns:
        Tuple of (header_info, disassembly_listing)
    """
    # Read SID file
    sid_data = filepath.read_bytes()

    # Parse header
    header = parse_sid_header(sid_data)

    # Extract code
    code_start = header['code_start']
    load_addr = header['load_addr']
    code_data = sid_data[code_start:code_start + 2048]  # First 2KB

    # Disassemble
    disasm = Disassembler6502()
    instructions = disasm.disassemble_range(code_data, load_addr, min(len(code_data), max_instructions * 3))

    # Limit to max_instructions
    instructions = instructions[:max_instructions]

    # Format listing
    listing = disasm.format_listing(instructions, show_hex=True)

    return header, listing


def test_laxity_files():
    """Test disassembler on Laxity SID files."""
    print("=" * 80)
    print("LAXITY SID FILE DISASSEMBLY TEST")
    print("=" * 80)

    # Find Laxity directory
    laxity_dir = Path(__file__).parent.parent / "Laxity"

    if not laxity_dir.exists():
        print(f"ERROR: Laxity directory not found: {laxity_dir}")
        return 1

    # Test files (prioritize Stinsens)
    test_files = [
        "Stinsens_Last_Night_of_89.sid",
        "Broware.sid",
        "1983_Sauna_Tango.sid",
        "Fun_Funk.sid",
    ]

    for filename in test_files:
        filepath = laxity_dir / filename

        if not filepath.exists():
            print(f"\nWARNING: File not found: {filename}")
            continue

        print(f"\n{'=' * 80}")
        print(f"FILE: {filename}")
        print(f"{'=' * 80}")

        try:
            # Disassemble
            header, listing = disassemble_sid_file(filepath, max_instructions=50)

            # Print header info
            print(f"\nHEADER INFO:")
            print(f"  Title:      {header['title']}")
            print(f"  Author:     {header['author']}")
            print(f"  Copyright:  {header['copyright']}")
            print(f"  Format:     {header['magic']} v{header['version']}")
            print(f"  Load Addr:  ${header['load_addr']:04X}")
            print(f"  Init Addr:  ${header['init_addr']:04X}")
            print(f"  Play Addr:  ${header['play_addr']:04X}")
            print(f"  Songs:      {header['songs']} (start: {header['start_song']})")

            # Print disassembly
            print(f"\nDISASSEMBLY (first 50 instructions):")
            print(listing)

        except Exception as e:
            print(f"ERROR: Failed to disassemble {filename}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print(f"{'=' * 80}")

    return 0


def test_stinsens_detailed():
    """Detailed analysis of Stinsens_Last_Night_of_89.sid."""
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS: Stinsens_Last_Night_of_89.sid")
    print("=" * 80)

    laxity_dir = Path(__file__).parent.parent / "Laxity"
    filepath = laxity_dir / "Stinsens_Last_Night_of_89.sid"

    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}")
        return 1

    # Read and parse
    sid_data = filepath.read_bytes()
    header = parse_sid_header(sid_data)

    print(f"\nFILE INFORMATION:")
    print(f"  Path: {filepath}")
    print(f"  Size: {len(sid_data)} bytes")
    print(f"  Title: {header['title']}")
    print(f"  Author: {header['author']}")

    print(f"\nMEMORY LAYOUT:")
    print(f"  Load Address:  ${header['load_addr']:04X}")
    print(f"  Init Address:  ${header['init_addr']:04X}")
    print(f"  Play Address:  ${header['play_addr']:04X}")
    print(f"  Code Start:    Offset ${header['code_start']:04X} in file")

    # Disassemble INIT routine
    code_start = header['code_start']
    load_addr = header['load_addr']
    init_addr = header['init_addr']
    play_addr = header['play_addr']

    print(f"\nDISASSEMBLY AT LOAD ADDRESS (${load_addr:04X}):")
    print("-" * 80)

    code_data = sid_data[code_start:]
    disasm = Disassembler6502()

    # Disassemble from load address (100 instructions)
    instructions = disasm.disassemble_range(code_data, load_addr, min(len(code_data), 300))
    instructions = instructions[:100]
    listing = disasm.format_listing(instructions, show_hex=True)
    print(listing)

    # Find INIT and PLAY addresses in disassembly
    print(f"\nLOOKING FOR INIT ADDRESS (${init_addr:04X}):")
    init_instructions = [i for i in instructions if i.address == init_addr]
    if init_instructions:
        idx = instructions.index(init_instructions[0])
        print(f"Found at instruction #{idx}")
        print("Context:")
        for i in range(max(0, idx-2), min(len(instructions), idx+10)):
            instr = instructions[i]
            marker = " <-- INIT" if instr.address == init_addr else ""
            print(f"  {instr}{marker}")
    else:
        print(f"  INIT address ${init_addr:04X} not found in first 100 instructions")

    print(f"\nLOOKING FOR PLAY ADDRESS (${play_addr:04X}):")
    play_instructions = [i for i in instructions if i.address == play_addr]
    if play_instructions:
        idx = instructions.index(play_instructions[0])
        print(f"Found at instruction #{idx}")
        print("Context:")
        for i in range(max(0, idx-2), min(len(instructions), idx+10)):
            instr = instructions[i]
            marker = " <-- PLAY" if instr.address == play_addr else ""
            print(f"  {instr}{marker}")
    else:
        print(f"  PLAY address ${play_addr:04X} not found in first 100 instructions")

    # Look for Laxity patterns
    print(f"\nLOOKING FOR LAXITY PATTERNS:")

    # Pattern 1: SEI, LDA #$00, STA $D412
    print("  Pattern 1: SEI, LDA #$00, STA $D412 (cutoff frequency clear)")
    for i in range(len(instructions) - 2):
        if (instructions[i].mnemonic == "SEI" and
            instructions[i+1].mnemonic == "LDA" and instructions[i+1].operand_str == "#$00" and
            instructions[i+2].mnemonic == "STA" and "$D412" in instructions[i+2].operand_str):
            print(f"    Found at ${instructions[i].address:04X}")
            for j in range(i, min(i+5, len(instructions))):
                print(f"      {instructions[j]}")

    # Pattern 2: LDX #$00, LDA $xxxx,X (loading table)
    print("  Pattern 2: LDX #$00, LDA $xxxx,X (table loading)")
    for i in range(len(instructions) - 1):
        if (instructions[i].mnemonic == "LDX" and instructions[i].operand_str == "#$00" and
            instructions[i+1].mnemonic == "LDA" and ",X" in instructions[i+1].operand_str):
            print(f"    Found at ${instructions[i].address:04X}")
            for j in range(i, min(i+5, len(instructions))):
                print(f"      {instructions[j]}")
            break  # Only show first match

    return 0


if __name__ == "__main__":
    # Run basic test on multiple files
    result = test_laxity_files()

    # Detailed analysis of Stinsens
    test_stinsens_detailed()

    sys.exit(result)
