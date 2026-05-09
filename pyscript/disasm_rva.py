"""Disassemble a region of SIDFactoryII.exe given a relative virtual address.

Usage:  py -3 pyscript/disasm_rva.py 0x63fab [0x7a1b1 0x66cb9 ...]
"""
import sys
from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

EXE = Path('bin') / 'SIDFactoryII.exe'

def disasm_at(rva, lines_before=5, lines_after=15):
    pe = pefile.PE(str(EXE))
    img_base = pe.OPTIONAL_HEADER.ImageBase
    # Find the section containing this RVA
    section = None
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + s.Misc_VirtualSize:
            section = s; break
    if section is None:
        print(f'  RVA 0x{rva:x}: not in any section'); return

    # Read enough bytes around it
    raw_off = section.PointerToRawData + (rva - section.VirtualAddress)
    with open(EXE, 'rb') as f:
        f.seek(max(0, raw_off - 64))
        data = f.read(256)
    base = max(0, raw_off - 64)
    rva_at_base = section.VirtualAddress + (base - section.PointerToRawData)

    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.skipdata = True
    print(f'\n=== SIDFactoryII.exe + 0x{rva:x} (image_base 0x{img_base:x}) ===')
    found_lines = []
    for ins in md.disasm(data, rva_at_base):
        marker = ' >>>' if ins.address == rva else '    '
        line = f'{marker} 0x{ins.address:08x}  {ins.bytes.hex():<24} {ins.mnemonic} {ins.op_str}'
        found_lines.append((ins.address, line))
    # Print 5 before and 15 after the target
    target_idx = next((i for i, (a, _) in enumerate(found_lines) if a == rva), None)
    if target_idx is None:
        print('(target RVA not aligned to instruction boundary; showing nearest)')
        for _, l in found_lines[:30]: print(l)
    else:
        lo = max(0, target_idx - lines_before)
        hi = min(len(found_lines), target_idx + lines_after + 1)
        for _, l in found_lines[lo:hi]: print(l)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    for a in sys.argv[1:]:
        disasm_at(int(a, 16))
