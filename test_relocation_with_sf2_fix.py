#!/usr/bin/env python3
"""Test pointer relocation with SF2-aware extraction"""

from pathlib import Path
from sidm2.sf2_packer import SF2Packer
from sidm2.cpu6502 import CPU6502

sf2_path = Path("output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2")

print("="*80)
print("TESTING POINTER RELOCATION WITH SF2-AWARE FETCH")
print("="*80)

packer = SF2Packer(sf2_path)

print(f"\n1. File Format Detection")
print(f"   SF2 format: {packer.is_sf2_format}")

print(f"\n2. Extracting sections")
packer.fetch_driver_code()
packer.fetch_orderlists()
packer.fetch_sequences()

print(f"   Total sections: {len(packer.data_sections)}")

# Show section breakdown
code_sections = [s for s in packer.data_sections if s.is_code]
data_sections = [s for s in packer.data_sections if not s.is_code]
print(f"   Code sections: {len(code_sections)}")
print(f"   Data sections: {len(data_sections)}")

print(f"\n3. Analyzing first code section (most important)")
if code_sections:
    first_code = code_sections[0]
    print(f"   Address: ${first_code.source_address:04X}")
    print(f"   Size: {len(first_code.data)} bytes")

    # Check opcodes
    from sidm2.cpu6502 import INSTRUCTION_SIZES
    first_bytes = first_code.data[:32]
    valid_opcodes = sum(1 for b in first_bytes if INSTRUCTION_SIZES[b] > 0)
    print(f"   Valid 6502 opcodes: {valid_opcodes}/{len(first_bytes)}")

    # Is this better than before?
    print(f"\n   CRITICAL TEST: Can scan_relocatable_addresses() find pointers?")

    code_start = min(s.source_address for s in code_sections)
    code_end = max(s.source_address + len(s.data) for s in code_sections)

    cpu = CPU6502(bytes(first_code.data))
    relocatable_addrs = cpu.scan_relocatable_addresses(0, len(first_code.data), code_start, code_end)

    print(f"   Range to scan: ${code_start:04X}-${code_end:04X}")
    print(f"   Relocatable addresses found: {len(relocatable_addrs)}")

    if relocatable_addrs:
        print(f"   SUCCESS! Found {len(relocatable_addrs)} pointers to relocate!")
        for i, (offset, addr) in enumerate(relocatable_addrs[:5]):
            print(f"     [{i}] Offset 0x{offset:04X}: ${addr:04X}")
        if len(relocatable_addrs) > 5:
            print(f"     ... and {len(relocatable_addrs) - 5} more")
    else:
        print(f"   PROBLEM: Found ZERO pointers (same as before)")
else:
    print(f"   (no code sections)")

print(f"\n" + "="*80)
print("END TEST")
print("="*80)
