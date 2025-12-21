#!/usr/bin/env python3
"""
Analyze Laxity Player for Relocation Requirements

Scans the extracted player binary to identify all absolute address references
that will need to be patched when relocating from $1000 to $0E00.

Author: SIDM2 Project
Date: 2025-12-13
"""

import sys
import struct
from pathlib import Path
from dataclasses import dataclass
from typing import List, Set


@dataclass
class AddressReference:
    """Represents an absolute address reference in the code."""
    offset: int          # Byte offset in binary
    address: int         # Actual 6502 address
    target: int          # Target address being referenced
    opcode: int          # 6502 opcode byte
    opcode_name: str     # Human-readable opcode
    needs_relocation: bool  # Whether this needs patching


# 6502 opcodes that use absolute addressing (16-bit addresses)
ABSOLUTE_OPCODES = {
    # Format: opcode: (mnemonic, bytes, description)
    0x0D: ('ORA', 3, 'ORA absolute'),
    0x0E: ('ASL', 3, 'ASL absolute'),
    0x2C: ('BIT', 3, 'BIT absolute'),
    0x2D: ('AND', 3, 'AND absolute'),
    0x2E: ('ROL', 3, 'ROL absolute'),
    0x4C: ('JMP', 3, 'JMP absolute'),
    0x4D: ('EOR', 3, 'EOR absolute'),
    0x4E: ('LSR', 3, 'LSR absolute'),
    0x6D: ('ADC', 3, 'ADC absolute'),
    0x6E: ('ROR', 3, 'ROR absolute'),
    0x8C: ('STY', 3, 'STY absolute'),
    0x8D: ('STA', 3, 'STA absolute'),
    0x8E: ('STX', 3, 'STX absolute'),
    0xAC: ('LDY', 3, 'LDY absolute'),
    0xAD: ('LDA', 3, 'LDA absolute'),
    0xAE: ('LDX', 3, 'LDX absolute'),
    0xCC: ('CPY', 3, 'CPY absolute'),
    0xCD: ('CMP', 3, 'CMP absolute'),
    0xCE: ('DEC', 3, 'DEC absolute'),
    0xEC: ('CPX', 3, 'CPX absolute'),
    0xED: ('SBC', 3, 'SBC absolute'),
    0xEE: ('INC', 3, 'INC absolute'),
}

# Absolute indexed addressing modes
ABSOLUTE_INDEXED_OPCODES = {
    0x19: ('ORA', 3, 'ORA absolute,Y'),
    0x1D: ('ORA', 3, 'ORA absolute,X'),
    0x1E: ('ASL', 3, 'ASL absolute,X'),
    0x39: ('AND', 3, 'AND absolute,Y'),
    0x3D: ('AND', 3, 'AND absolute,X'),
    0x3E: ('ROL', 3, 'ROL absolute,X'),
    0x59: ('EOR', 3, 'EOR absolute,Y'),
    0x5D: ('EOR', 3, 'EOR absolute,X'),
    0x5E: ('LSR', 3, 'LSR absolute,X'),
    0x79: ('ADC', 3, 'ADC absolute,Y'),
    0x7D: ('ADC', 3, 'ADC absolute,X'),
    0x7E: ('ROR', 3, 'ROR absolute,X'),
    0x99: ('STA', 3, 'STA absolute,Y'),
    0x9D: ('STA', 3, 'STA absolute,X'),
    0xB9: ('LDA', 3, 'LDA absolute,Y'),
    0xBD: ('LDA', 3, 'LDA absolute,X'),
    0xBE: ('LDX', 3, 'LDX absolute,Y'),
    0xD9: ('CMP', 3, 'CMP absolute,Y'),
    0xDD: ('CMP', 3, 'CMP absolute,X'),
    0xDE: ('DEC', 3, 'DEC absolute,X'),
    0xF9: ('SBC', 3, 'SBC absolute,Y'),
    0xFD: ('SBC', 3, 'SBC absolute,X'),
    0xFE: ('INC', 3, 'INC absolute,X'),
}

# Combine all absolute addressing modes
ALL_ABSOLUTE_OPCODES = {**ABSOLUTE_OPCODES, **ABSOLUTE_INDEXED_OPCODES}


def analyze_binary(binary_data: bytes, base_addr: int = 0x1000) -> List[AddressReference]:
    """
    Scan binary for absolute address references.

    Args:
        binary_data: The player binary bytes
        base_addr: Base address where player is loaded (default $1000)

    Returns:
        List of AddressReference objects
    """
    references = []
    i = 0

    while i < len(binary_data) - 2:
        opcode = binary_data[i]

        if opcode in ALL_ABSOLUTE_OPCODES:
            # Read 16-bit target address (little-endian)
            target = struct.unpack('<H', binary_data[i+1:i+3])[0]
            opcode_info = ALL_ABSOLUTE_OPCODES[opcode]

            # Determine if this reference needs relocation
            # References in range $1000-$1FFF need relocation (player code/data)
            # References to SID registers ($D400-$D41C) do NOT need relocation
            # References to zero page ($00-$FF) do NOT need relocation
            needs_reloc = 0x1000 <= target <= 0x1FFF

            ref = AddressReference(
                offset=i,
                address=base_addr + i,
                target=target,
                opcode=opcode,
                opcode_name=opcode_info[2],
                needs_relocation=needs_reloc
            )
            references.append(ref)

            # Skip opcode + operand bytes
            i += opcode_info[1]
        else:
            i += 1

    return references


def analyze_zero_page_usage(binary_data: bytes) -> Set[int]:
    """
    Identify zero-page addresses used by the player.

    Returns:
        Set of zero-page addresses used
    """
    zp_addresses = set()

    # Zero-page addressing opcodes (2-byte instructions)
    ZP_OPCODES = {
        0x05, 0x06, 0x24, 0x25, 0x26, 0x45, 0x46, 0x65, 0x66,
        0x84, 0x85, 0x86, 0xA4, 0xA5, 0xA6, 0xC4, 0xC5, 0xC6,
        0xE4, 0xE5, 0xE6,
        # Zero-page indexed
        0x15, 0x16, 0x35, 0x36, 0x55, 0x56, 0x75, 0x76,
        0x94, 0x95, 0x96, 0xB4, 0xB5, 0xB6, 0xD5, 0xD6,
        0xF5, 0xF6,
    }

    i = 0
    while i < len(binary_data) - 1:
        if binary_data[i] in ZP_OPCODES:
            zp_addr = binary_data[i + 1]
            zp_addresses.add(zp_addr)
            i += 2
        else:
            i += 1

    return zp_addresses


def print_relocation_map(references: List[AddressReference], base_addr: int = 0x1000):
    """Print detailed relocation map."""
    print(f"\n{'='*80}")
    print("RELOCATION ANALYSIS REPORT")
    print(f"{'='*80}")

    # Filter references that need relocation
    reloc_refs = [r for r in references if r.needs_relocation]
    other_refs = [r for r in references if not r.needs_relocation]

    print(f"\nTotal absolute addressing instructions: {len(references)}")
    print(f"  Need relocation (player code/data): {len(reloc_refs)}")
    print(f"  Don't need relocation (SID/ZP/ROM): {len(other_refs)}")

    # Group by target address range
    sid_refs = [r for r in other_refs if 0xD400 <= r.target <= 0xD41C]
    zp_refs = [r for r in other_refs if r.target <= 0xFF]
    other_external = [r for r in other_refs if r not in sid_refs and r not in zp_refs]

    print(f"\nBreakdown:")
    print(f"  SID register references ($D400-$D41C): {len(sid_refs)}")
    print(f"  Zero-page references ($00-$FF): {len(zp_refs)}")
    print(f"  Other external references: {len(other_external)}")

    # Show first 20 references that need relocation
    print(f"\n{'='*80}")
    print(f"REFERENCES REQUIRING RELOCATION (first 20 of {len(reloc_refs)})")
    print(f"{'='*80}")
    print(f"{'Offset':<8} {'Address':<10} {'Opcode':<25} {'Target':<10} {'New Target'}")
    print(f"{'-'*80}")

    for ref in reloc_refs[:20]:
        new_target = ref.target - 0x0200  # Relocation offset: $1000 -> $0E00
        print(f"${ref.offset:04X}    "
              f"${ref.address:04X}     "
              f"{ref.opcode_name:<25} "
              f"${ref.target:04X}     "
              f"${new_target:04X}")

    if len(reloc_refs) > 20:
        print(f"... and {len(reloc_refs) - 20} more")

    # Show SID references (these should NOT be relocated)
    print(f"\n{'='*80}")
    print(f"SID REGISTER REFERENCES (do NOT relocate) - first 10 of {len(sid_refs)}")
    print(f"{'='*80}")

    for ref in sid_refs[:10]:
        print(f"${ref.offset:04X}    "
              f"${ref.address:04X}     "
              f"{ref.opcode_name:<25} "
              f"${ref.target:04X}")

    if len(sid_refs) > 10:
        print(f"... and {len(sid_refs) - 10} more")

    print(f"\n{'='*80}")


def main():
    """Main analysis workflow."""
    if len(sys.argv) < 2:
        print("Usage: python analyze_laxity_relocation.py <player_binary> [base_addr]")
        print("\nExample:")
        print("  python analyze_laxity_relocation.py drivers/laxity/laxity_player_reference.bin")
        print("  python analyze_laxity_relocation.py drivers/laxity/laxity_player_reference.bin 0x1000")
        return

    bin_path = Path(sys.argv[1])
    if not bin_path.exists():
        print(f"ERROR: File not found: {bin_path}")
        return

    base_addr = 0x1000
    if len(sys.argv) >= 3:
        base_addr = int(sys.argv[2], 16) if sys.argv[2].startswith('0x') else int(sys.argv[2])

    # Load binary
    with open(bin_path, 'rb') as f:
        binary_data = f.read()

    print(f"Analyzing: {bin_path}")
    print(f"Size: {len(binary_data)} bytes ({len(binary_data) / 1024:.2f} KB)")
    print(f"Base Address: 0x{base_addr:04X}")
    print(f"Address Range: 0x{base_addr:04X} - 0x{base_addr + len(binary_data) - 1:04X}")

    # Analyze absolute references
    references = analyze_binary(binary_data, base_addr)

    # Print relocation map
    print_relocation_map(references, base_addr)

    # Analyze zero-page usage
    zp_addresses = analyze_zero_page_usage(binary_data)

    print(f"\n{'='*80}")
    print("ZERO-PAGE USAGE ANALYSIS")
    print(f"{'='*80}")
    print(f"Zero-page addresses used: {len(zp_addresses)}")

    if zp_addresses:
        # Group into ranges for readability
        sorted_zp = sorted(zp_addresses)
        print(f"\nUsed ZP addresses: ", end='')

        ranges = []
        start = sorted_zp[0]
        end = sorted_zp[0]

        for addr in sorted_zp[1:]:
            if addr == end + 1:
                end = addr
            else:
                if start == end:
                    ranges.append(f"${start:02X}")
                else:
                    ranges.append(f"${start:02X}-${end:02X}")
                start = end = addr

        if start == end:
            ranges.append(f"${start:02X}")
        else:
            ranges.append(f"${start:02X}-${end:02X}")

        print(', '.join(ranges))

        # Check for conflicts with SF2 driver standard ZP usage
        # SF2 typically uses $F0-$FF
        sf2_zp_range = set(range(0xF0, 0x100))
        conflicts = zp_addresses & sf2_zp_range

        if conflicts:
            print(f"\nWARNING: {len(conflicts)} potential conflicts with SF2 ZP range ($F0-$FF):")
            print(f"  Conflicts: {', '.join(f'${a:02X}' for a in sorted(conflicts))}")
            print(f"  These may need to be remapped during relocation!")
        else:
            print(f"\nOK: No conflicts with SF2 ZP range ($F0-$FF)")

    # Summary and next steps
    reloc_count = sum(1 for r in references if r.needs_relocation)

    print(f"\n{'='*80}")
    print("RELOCATION SUMMARY")
    print(f"{'='*80}")
    print(f"Player size: {len(binary_data)} bytes")
    print(f"Current address: 0x{base_addr:04X}")
    print(f"Target address: 0x0E00")
    print(f"Relocation offset: -0x0200 (-512 bytes)")
    print(f"\nReferences to patch: {reloc_count}")
    print(f"ZP addresses used: {len(zp_addresses)}")
    print(f"ZP conflicts: {len(conflicts) if zp_addresses else 0}")

    print(f"\n{'='*80}")
    print("NEXT STEPS")
    print(f"{'='*80}")
    print("1. Build relocation engine (Phase 3)")
    print(f"   - Patch {reloc_count} address references")
    print(f"   - Apply offset of -$0200 to all player references")
    print("   - Preserve SID register and ZP references")

    if zp_addresses:
        if conflicts:
            print("   - Remap conflicting ZP addresses")
        else:
            print("   - No ZP conflicts to resolve")

    print("\n2. Test relocated player binary")
    print("   - Verify code still executes correctly at $0E00")
    print("   - Test with reference SID files")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
