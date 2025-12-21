#!/usr/bin/env python3
"""Detailed trace of scan_relocatable_addresses to see why it finds nothing"""

from pathlib import Path
from sidm2.sf2_packer import SF2Packer
from sidm2.cpu6502 import INSTRUCTION_SIZES, RELOCATABLE_OPCODES

sf2_path = Path("output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2")

print("="*80)
print("SCANNING TRACE - FIRST CODE SECTION")
print("="*80)

packer = SF2Packer(sf2_path)
packer.fetch_driver_code()

# Get first code section
code_sections = [s for s in packer.data_sections if s.is_code]
first_code = code_sections[0]

print(f"\nFirst code section:")
print(f"  Source address: ${first_code.source_address:04X}")
print(f"  Size: {len(first_code.data)} bytes")
print(f"  Data (first 64 bytes): {' '.join(f'{b:02x}' for b in first_code.data[:64])}")

# Manual scan
print(f"\nManual instruction scan (like scan_relocatable_addresses):")
code_start = 0x1000  # Real addresses
code_end = 0x404C

pc = 0  # Offset in the code section
instruction_num = 0
found_count = 0

while pc < len(first_code.data) and instruction_num < 20:
    opcode = first_code.data[pc]
    size = INSTRUCTION_SIZES[opcode]

    # Show instruction details
    if size == 0:
        print(f"  [{instruction_num:2d}] Offset 0x{pc:04X}: Opcode 0x{opcode:02X} - Unknown/Illegal (size=0), skipping")
        pc += 1
    else:
        is_3byte = (size == 3)
        is_relocatable = (opcode in RELOCATABLE_OPCODES)
        in_range = False
        has_address = ""

        if is_3byte and pc + 2 < len(first_code.data):
            addr_lo = first_code.data[pc + 1]
            addr_hi = first_code.data[pc + 2]
            address = (addr_hi << 8) | addr_lo
            has_address = f" operand=${address:04X}"
            in_range = (code_start <= address < code_end)

        print(f"  [{instruction_num:2d}] Offset 0x{pc:04X}: Opcode 0x{opcode:02X} - size={size}, relocatable={is_relocatable}, 3-byte={is_3byte}{has_address}", end="")

        if size == 3 and opcode in RELOCATABLE_OPCODES:
            if pc + 2 < len(first_code.data):
                addr_lo = first_code.data[pc + 1]
                addr_hi = first_code.data[pc + 2]
                address = (addr_hi << 8) | addr_lo

                if code_start <= address < code_end:
                    if 0xD000 <= address < 0xE000:
                        print(f" -> Hardware address, NOT relocating")
                    else:
                        print(f" -> RELOCATE!")
                        found_count += 1
                else:
                    print(f" -> Outside relocatable range [{code_start:04X}-{code_end:04X}]")
            else:
                print(f" -> Not enough data")
        else:
            print()

        pc += size

    instruction_num += 1

print(f"\nTotal found: {found_count}")

# Now try the actual scan_relocatable_addresses method
print(f"\n" + "="*80)
print("ACTUAL scan_relocatable_addresses() CALL")
print("="*80)

from sidm2.cpu6502 import CPU6502

cpu = CPU6502(bytes(first_code.data))
relocatable_addrs = cpu.scan_relocatable_addresses(0, len(first_code.data), code_start, code_end)

print(f"Found {len(relocatable_addrs)} relocatable addresses:")
for offset, addr in relocatable_addrs:
    print(f"  Offset {offset}: ${addr:04X}")
