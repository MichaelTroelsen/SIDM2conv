#!/usr/bin/env python3
"""
Trace Orderlist Memory Access

Scans Laxity player code to identify which instructions access orderlist memory.
Uses static analysis to find all absolute address references in orderlist ranges.

Author: SIDM2 Project
Date: 2025-12-13
"""

import struct
import sys
from pathlib import Path
from collections import defaultdict


class OrderlistScanner:
    """Scans player code for orderlist address references"""

    def __init__(self, sid_path: str):
        self.sid_path = sid_path
        self.player_data = None
        self.load_addr = 0
        self.init_addr = 0
        self.play_addr = 0
        self.orderlist_ranges = []
        self.findings = []  # List of (pc, opcode, operand_addr, mode)

    def load_sid(self):
        """Load SID file and extract player data"""
        with open(self.sid_path, 'rb') as f:
            sid_data = f.read()

        # Parse PSID header
        if sid_data[0:4] != b'PSID':
            raise ValueError("Not a PSID file")

        load_addr = struct.unpack('>H', sid_data[8:10])[0]
        self.init_addr = struct.unpack('>H', sid_data[10:12])[0]
        self.play_addr = struct.unpack('>H', sid_data[12:14])[0]

        # Get C64 data
        c64_data = sid_data[124:]
        if load_addr == 0:
            # Old-style PSID - load address in data
            load_addr = struct.unpack('<H', c64_data[0:2])[0]
            c64_data = c64_data[2:]

        self.load_addr = load_addr
        self.player_data = c64_data

        print(f"SID Info:")
        print(f"  Load: ${load_addr:04X}")
        print(f"  Init: ${self.init_addr:04X}")
        print(f"  Play: ${self.play_addr:04X}")
        print(f"  Size: {len(c64_data)} bytes")
        print()

        return load_addr

    def set_orderlist_range(self, start_addr: int, end_addr: int):
        """Set memory range to watch for orderlist accesses"""
        self.orderlist_ranges.append((start_addr, end_addr))
        print(f"Watching orderlist range: ${start_addr:04X}-${end_addr:04X}")

    def is_in_orderlist_range(self, addr: int) -> bool:
        """Check if address is in any orderlist range"""
        for start, end in self.orderlist_ranges:
            if start <= addr <= end:
                return True
        return False

    def scan_player_code(self):
        """Scan player code for instructions accessing orderlist ranges"""
        print(f"\nScanning player code for orderlist references...")

        # Scan from load address to end of data
        pc = self.load_addr
        data_end = self.load_addr + len(self.player_data)

        scanned = 0
        while pc < data_end:
            offset = pc - self.load_addr
            if offset >= len(self.player_data):
                break

            opcode = self.player_data[offset]

            # Check if this opcode uses absolute addressing
            operand_addr = None
            mode = None
            instr_size = 1

            # Absolute addressing modes (reads 2-byte address)
            if opcode in [0xAD, 0xAE, 0xAC]:  # LDA/LDX/LDY abs
                if offset + 2 < len(self.player_data):
                    lo = self.player_data[offset + 1]
                    hi = self.player_data[offset + 2]
                    operand_addr = lo | (hi << 8)
                    mode = "Absolute"
                    instr_size = 3

            elif opcode in [0xBD, 0xBE, 0xBC]:  # LDA/LDX/LDY abs,X/abs,Y
                if offset + 2 < len(self.player_data):
                    lo = self.player_data[offset + 1]
                    hi = self.player_data[offset + 2]
                    operand_addr = lo | (hi << 8)
                    if opcode == 0xBD:
                        mode = "Absolute,X (LDA)"
                    elif opcode == 0xBE:
                        mode = "Absolute,Y (LDX)"
                    else:
                        mode = "Absolute,X (LDX)"
                    instr_size = 3

            elif opcode in [0xB9, 0xB1]:  # LDA abs,Y / LDA (ind),Y
                if offset + 2 < len(self.player_data):
                    lo = self.player_data[offset + 1]
                    hi = self.player_data[offset + 2]
                    if opcode == 0xB9:
                        operand_addr = lo | (hi << 8)
                        mode = "Absolute,Y (LDA)"
                        instr_size = 3
                    else:
                        # Indirect,Y - reads from zero page
                        mode = f"(Indirect),Y - ZP ${lo:02X}"
                        instr_size = 2

            elif opcode in [0x8D, 0x8E, 0x8C]:  # STA/STX/STY abs
                if offset + 2 < len(self.player_data):
                    lo = self.player_data[offset + 1]
                    hi = self.player_data[offset + 2]
                    operand_addr = lo | (hi << 8)
                    mode = "Absolute (Store)"
                    instr_size = 3

            elif opcode in [0x9D, 0x99]:  # STA abs,X / STA abs,Y
                if offset + 2 < len(self.player_data):
                    lo = self.player_data[offset + 1]
                    hi = self.player_data[offset + 2]
                    operand_addr = lo | (hi << 8)
                    mode = "Absolute,X/Y (Store)"
                    instr_size = 3

            elif opcode in [0xCD, 0xDD, 0xD9]:  # CMP abs / CMP abs,X / CMP abs,Y
                if offset + 2 < len(self.player_data):
                    lo = self.player_data[offset + 1]
                    hi = self.player_data[offset + 2]
                    operand_addr = lo | (hi << 8)
                    mode = "Compare"
                    instr_size = 3

            # Check if operand is in orderlist range
            if operand_addr and self.is_in_orderlist_range(operand_addr):
                instr_bytes = [self.player_data[offset + i] for i in range(min(instr_size, len(self.player_data) - offset))]
                self.findings.append({
                    'pc': pc,
                    'opcode': opcode,
                    'addr': operand_addr,
                    'mode': mode,
                    'bytes': instr_bytes
                })

            # Move to next instruction (estimate)
            pc += instr_size
            scanned += 1

            # Prevent infinite loops
            if scanned > 10000:
                break

        print(f"Scanned {scanned} instructions")

    def analyze_results(self):
        """Analyze findings and generate report"""
        print("\n" + "="*80)
        print("ORDERLIST ACCESS ANALYSIS")
        print("="*80)

        if not self.findings:
            print("\nNo orderlist accesses detected!")
            print("This might mean:")
            print("  1. Orderlist range is wrong")
            print("  2. Player uses indirect addressing (zero-page pointers)")
            print("  3. Player uses different data structure")
            return

        print(f"\nFound {len(self.findings)} instructions accessing orderlists:")
        print()

        for finding in self.findings:
            pc = finding['pc']
            opcode = finding['opcode']
            addr = finding['addr']
            mode = finding['mode']
            instr_bytes = finding['bytes']

            print(f"PC=${pc:04X}:")
            print(f"  Instruction: {' '.join(f'{b:02X}' for b in instr_bytes)}")
            print(f"  Opcode: ${opcode:02X}")
            print(f"  Mode: {mode}")
            print(f"  Accesses: ${addr:04X}")
            print()

    def generate_patch_instructions(self):
        """Generate instructions for patching the relocated player"""
        print("\n" + "="*80)
        print("PATCH INSTRUCTIONS")
        print("="*80)
        print()

        if not self.findings:
            print("No patches needed (no orderlist accesses found)")
            return

        print("For relocated player (load=$0D7E, player at $0E00):")
        print("Original player at $1000, relocated by -$0200")
        print()

        # Group by PC to avoid duplicates
        unique_pcs = {}
        for finding in self.findings:
            pc = finding['pc']
            if pc not in unique_pcs:
                unique_pcs[pc] = finding

        for pc, finding in sorted(unique_pcs.items()):
            # Calculate relocated PC
            relocated_pc = pc - 0x0200

            # Calculate file offset in driver
            driver_load = 0x0D7E
            file_offset = relocated_pc - driver_load + 2

            opcode = finding['opcode']
            addr = finding['addr']
            instr_bytes = finding['bytes']

            print(f"Original PC=${pc:04X} -> Relocated PC=${relocated_pc:04X}")
            print(f"  File offset in driver: ${file_offset:04X}")
            print(f"  Current instruction: {' '.join(f'{b:02X}' for b in instr_bytes)}")

            # Determine what to patch
            if len(instr_bytes) >= 3:
                # Absolute or indexed - patch the address
                current_addr = addr

                # Calculate new address
                # Original orderlists at $1898-$1A98
                # After -$0200 relocation: $1698-$1898
                # We want to point to $1700-$1900 (where we'll inject new data)

                if 0x1698 <= current_addr <= 0x1A98:
                    # Calculate offset from relocated base
                    offset = current_addr - 0x1698
                    new_addr = 0x1700 + offset

                    new_lo = new_addr & 0xFF
                    new_hi = (new_addr >> 8) & 0xFF

                    print(f"  PATCH: Change address ${current_addr:04X} -> ${new_addr:04X}")
                    print(f"  Patch bytes at offset ${file_offset+1:04X}: {instr_bytes[1]:02X} {instr_bytes[2]:02X} -> {new_lo:02X} {new_hi:02X}")

            print()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python trace_orderlist_access.py <sid_file>")
        print()
        print("Example:")
        print("  python trace_orderlist_access.py test_laxity_pipeline/Stinsens_Last_Night_of_89.sid")
        return 1

    sid_path = sys.argv[1]

    print("="*80)
    print("ORDERLIST ACCESS SCANNER")
    print("="*80)
    print()

    scanner = OrderlistScanner(sid_path)

    # Load SID
    load_addr = scanner.load_sid()

    # Set orderlist watch ranges
    # For Stinsens: orderlists at $1898-$1A98 (3 tracks × 256 bytes)
    scanner.set_orderlist_range(0x1898, 0x1898 + 256)  # Track 1
    scanner.set_orderlist_range(0x1998, 0x1998 + 256)  # Track 2
    scanner.set_orderlist_range(0x1A98, 0x1A98 + 256)  # Track 3

    # Scan player code
    scanner.scan_player_code()

    # Analyze results
    scanner.analyze_results()

    # Generate patch instructions
    scanner.generate_patch_instructions()

    print("\n" + "="*80)
    print("NEXT STEPS:")
    print("="*80)
    print()
    print("1. Review the patch instructions above")
    print("2. Apply patches to sidm2/sf2_writer.py in _inject_laxity_music_data()")
    print("3. Patch the driver binary at the specified file offsets")
    print("4. Test with converted SID file")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
