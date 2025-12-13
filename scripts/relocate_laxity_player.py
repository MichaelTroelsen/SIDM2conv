#!/usr/bin/env python3
"""
Relocate Laxity Player Binary

Relocates the Laxity NewPlayer v21 from $1000 to $0E00 by patching
all absolute address references.

Author: SIDM2 Project
Date: 2025-12-13
"""

import sys
import struct
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Set


@dataclass
class RelocationPatch:
    """Represents a single address patch to be applied."""
    offset: int          # Byte offset in binary
    old_address: int     # Original target address
    new_address: int     # Relocated target address
    opcode: int          # 6502 opcode
    opcode_name: str     # Human-readable name


# 6502 opcodes that use absolute addressing (same as analyze script)
ABSOLUTE_OPCODES = {
    0x0D: ('ORA', 3), 0x0E: ('ASL', 3), 0x2C: ('BIT', 3), 0x2D: ('AND', 3),
    0x2E: ('ROL', 3), 0x4C: ('JMP', 3), 0x4D: ('EOR', 3), 0x4E: ('LSR', 3),
    0x6D: ('ADC', 3), 0x6E: ('ROR', 3), 0x8C: ('STY', 3), 0x8D: ('STA', 3),
    0x8E: ('STX', 3), 0xAC: ('LDY', 3), 0xAD: ('LDA', 3), 0xAE: ('LDX', 3),
    0xCC: ('CPY', 3), 0xCD: ('CMP', 3), 0xCE: ('DEC', 3), 0xEC: ('CPX', 3),
    0xED: ('SBC', 3), 0xEE: ('INC', 3),
}

ABSOLUTE_INDEXED_OPCODES = {
    0x19: ('ORA', 3), 0x1D: ('ORA', 3), 0x1E: ('ASL', 3), 0x39: ('AND', 3),
    0x3D: ('AND', 3), 0x3E: ('ROL', 3), 0x59: ('EOR', 3), 0x5D: ('EOR', 3),
    0x5E: ('LSR', 3), 0x79: ('ADC', 3), 0x7D: ('ADC', 3), 0x7E: ('ROR', 3),
    0x99: ('STA', 3), 0x9D: ('STA', 3), 0xB9: ('LDA', 3), 0xBD: ('LDA', 3),
    0xBE: ('LDX', 3), 0xD9: ('CMP', 3), 0xDD: ('CMP', 3), 0xDE: ('DEC', 3),
    0xF9: ('SBC', 3), 0xFD: ('SBC', 3), 0xFE: ('INC', 3),
}

ALL_ABSOLUTE_OPCODES = {**ABSOLUTE_OPCODES, **ABSOLUTE_INDEXED_OPCODES}


class LaxityRelocator:
    """Handles relocation of Laxity player binary."""

    def __init__(
        self,
        binary_data: bytes,
        old_base: int = 0x1000,
        new_base: int = 0x0E00,
        zp_remap: Dict[int, int] = None
    ):
        """
        Initialize relocator.

        Args:
            binary_data: Original player binary
            old_base: Original load address (default $1000)
            new_base: Target load address (default $0E00)
            zp_remap: Optional zero-page address remapping dict
        """
        self.binary = bytearray(binary_data)
        self.old_base = old_base
        self.new_base = new_base
        self.offset = new_base - old_base
        self.zp_remap = zp_remap or {}
        self.patches = []
        self.stats = {
            'total_refs': 0,
            'patched': 0,
            'sid_refs': 0,
            'zp_refs': 0,
            'other_refs': 0,
            'zp_remapped': 0
        }

    def scan_references(self) -> List[RelocationPatch]:
        """
        Scan binary for absolute address references.

        Returns:
            List of patches to apply
        """
        patches = []
        i = 0

        while i < len(self.binary) - 2:
            opcode = self.binary[i]

            if opcode in ALL_ABSOLUTE_OPCODES:
                # Read 16-bit target address (little-endian)
                target = struct.unpack('<H', self.binary[i+1:i+3])[0]
                opcode_info = ALL_ABSOLUTE_OPCODES[opcode]

                self.stats['total_refs'] += 1

                # Determine if this reference needs relocation
                # Player code/data range: $1000-$1FFF
                if 0x1000 <= target <= 0x1FFF:
                    # This is a player reference - needs relocation
                    new_target = target + self.offset
                    patch = RelocationPatch(
                        offset=i + 1,  # Offset of address bytes (skip opcode)
                        old_address=target,
                        new_address=new_target,
                        opcode=opcode,
                        opcode_name=f"{opcode_info[0]} ${target:04X}"
                    )
                    patches.append(patch)
                    self.stats['patched'] += 1
                elif 0xD400 <= target <= 0xD41C:
                    # SID register - do not relocate
                    self.stats['sid_refs'] += 1
                elif target <= 0xFF:
                    # Zero-page reference - check for remap
                    self.stats['zp_refs'] += 1
                else:
                    # Other reference (ROM, etc.) - do not relocate
                    self.stats['other_refs'] += 1

                i += opcode_info[1]
            else:
                i += 1

        return patches

    def apply_patches(self, patches: List[RelocationPatch]):
        """Apply relocation patches to binary."""
        for patch in patches:
            # Pack new address as little-endian 16-bit
            new_addr_bytes = struct.pack('<H', patch.new_address)
            self.binary[patch.offset] = new_addr_bytes[0]
            self.binary[patch.offset + 1] = new_addr_bytes[1]

    def remap_zero_page(self):
        """
        Remap conflicting zero-page addresses.

        Laxity uses: $F2, $F3, $F7, $F9, $FC, $FD, $FE
        These conflict with SF2 standard range ($F0-$FF)
        Remap to safe range: $E0-$EF
        """
        if not self.zp_remap:
            # Default remapping: conflicts to $E0+ range
            conflicts = [0xF2, 0xF3, 0xF7, 0xF9, 0xFC, 0xFD, 0xFE]
            safe_start = 0xE8
            self.zp_remap = {conflict: safe_start + i for i, conflict in enumerate(conflicts)}

        print(f"\nZero-Page Remapping:")
        for old, new in self.zp_remap.items():
            print(f"  ${old:02X} -> ${new:02X}")

        # Scan for zero-page opcodes and remap
        ZP_OPCODES = {
            0x05: 2, 0x06: 2, 0x24: 2, 0x25: 2, 0x26: 2, 0x45: 2, 0x46: 2,
            0x65: 2, 0x66: 2, 0x84: 2, 0x85: 2, 0x86: 2, 0xA4: 2, 0xA5: 2,
            0xA6: 2, 0xC4: 2, 0xC5: 2, 0xC6: 2, 0xE4: 2, 0xE5: 2, 0xE6: 2,
            # Zero-page indexed
            0x15: 2, 0x16: 2, 0x35: 2, 0x36: 2, 0x55: 2, 0x56: 2, 0x75: 2,
            0x76: 2, 0x94: 2, 0x95: 2, 0x96: 2, 0xB4: 2, 0xB5: 2, 0xB6: 2,
            0xD5: 2, 0xD6: 2, 0xF5: 2, 0xF6: 2,
        }

        i = 0
        while i < len(self.binary) - 1:
            if self.binary[i] in ZP_OPCODES:
                zp_addr = self.binary[i + 1]
                if zp_addr in self.zp_remap:
                    old_zp = zp_addr
                    new_zp = self.zp_remap[zp_addr]
                    self.binary[i + 1] = new_zp
                    self.stats['zp_remapped'] += 1
                i += 2
            else:
                i += 1

    def relocate(self) -> bytes:
        """
        Perform complete relocation.

        Returns:
            Relocated binary
        """
        print(f"\n{'='*70}")
        print("RELOCATION PROCESS")
        print(f"{'='*70}")
        print(f"Original base:  ${self.old_base:04X}")
        print(f"New base:       ${self.new_base:04X}")
        print(f"Offset:         {self.offset:+05X} ({self.offset:+d} bytes)")

        # Step 1: Scan for references
        print(f"\nStep 1: Scanning for address references...")
        patches = self.scan_references()
        self.patches = patches

        print(f"  Found {self.stats['total_refs']} absolute addressing instructions")
        print(f"    - Player references to patch: {self.stats['patched']}")
        print(f"    - SID register refs (skip):   {self.stats['sid_refs']}")
        print(f"    - Zero-page refs (remap):     {self.stats['zp_refs']}")
        print(f"    - Other refs (skip):          {self.stats['other_refs']}")

        # Step 2: Apply address patches
        print(f"\nStep 2: Applying {len(patches)} address patches...")
        self.apply_patches(patches)
        print(f"  Patched {len(patches)} references")

        # Step 3: Remap zero-page
        if self.zp_remap or True:  # Always check for conflicts
            print(f"\nStep 3: Remapping zero-page conflicts...")
            self.remap_zero_page()
            print(f"  Remapped {self.stats['zp_remapped']} zero-page references")
        else:
            print(f"\nStep 3: No zero-page remapping needed")

        print(f"\n{'='*70}")
        print("RELOCATION COMPLETE")
        print(f"{'='*70}")

        return bytes(self.binary)

    def print_verification(self, relocated_binary: bytes):
        """Print verification information."""
        print(f"\nVerification:")
        print(f"  Original size: {len(self.binary)} bytes")
        print(f"  Relocated size: {len(relocated_binary)} bytes")

        if len(self.binary) == len(relocated_binary):
            print(f"  Size check: PASS")
        else:
            print(f"  Size check: FAIL (size changed!)")

        # Show first 32 bytes comparison
        print(f"\nFirst 32 bytes (original vs relocated):")
        for i in range(0, min(32, len(self.binary)), 16):
            orig_hex = ' '.join(f'{b:02x}' for b in self.binary[i:i+16])
            reloc_hex = ' '.join(f'{b:02x}' for b in relocated_binary[i:i+16])
            same = "SAME" if orig_hex == reloc_hex else "DIFF"
            print(f"  {i:04X}: {orig_hex} | {same}")

        # Sample some patches
        print(f"\nSample patches applied (first 10):")
        for i, patch in enumerate(self.patches[:10]):
            print(f"  Offset ${patch.offset:04X}: "
                  f"${patch.old_address:04X} -> ${patch.new_address:04X} "
                  f"({patch.opcode_name})")

        if len(self.patches) > 10:
            print(f"  ... and {len(self.patches) - 10} more")


def main():
    """Main relocation workflow."""
    if len(sys.argv) < 2:
        print("Usage: python relocate_laxity_player.py <input_binary> [output_binary] [new_base]")
        print("\nExample:")
        print("  python relocate_laxity_player.py drivers/laxity/laxity_player_reference.bin")
        print("  python relocate_laxity_player.py input.bin output.bin 0x0E00")
        return

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        return

    # Default output path
    output_path = input_path.parent / "laxity_player_relocated.bin"
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])

    # Default new base address
    new_base = 0x0E00
    if len(sys.argv) >= 4:
        new_base = int(sys.argv[3], 16) if sys.argv[3].startswith('0x') else int(sys.argv[3])

    # Load binary
    with open(input_path, 'rb') as f:
        binary_data = f.read()

    print(f"="*70)
    print("LAXITY PLAYER RELOCATOR")
    print(f"="*70)
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print(f"Size:   {len(binary_data)} bytes ({len(binary_data) / 1024:.2f} KB)")

    # Create relocator
    relocator = LaxityRelocator(
        binary_data,
        old_base=0x1000,
        new_base=new_base
    )

    # Perform relocation
    relocated_binary = relocator.relocate()

    # Verify
    relocator.print_verification(relocated_binary)

    # Write output
    with open(output_path, 'wb') as f:
        f.write(relocated_binary)

    print(f"\n{'='*70}")
    print("SUCCESS")
    print(f"{'='*70}")
    print(f"Relocated player written to: {output_path}")
    print(f"Size: {len(relocated_binary)} bytes")

    print(f"\n{'='*70}")
    print("NEXT STEPS")
    print(f"{'='*70}")
    print("1. Verify with disassembler:")
    print(f"   tools/SIDwinder.exe -disassemble <test_sid_with_relocated_player>")
    print("\n2. Create SF2 wrapper (Phase 4)")
    print("   - Write 6502 assembly wrapper at $0D7E")
    print("   - JSR to relocated init ($0E00) and play ($0EA1)")
    print("\n3. Combine components:")
    print("   - SF2 header (69 bytes)")
    print("   - Wrapper code (~130 bytes)")
    print("   - Relocated player (3328 bytes)")
    print("   - Music data tables")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
