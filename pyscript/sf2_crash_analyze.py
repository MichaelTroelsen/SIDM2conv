"""Decode SF2II crash minidumps from %LOCALAPPDATA%\\CrashDumps and resolve
the access-violation address to a SIDFactoryII.exe RVA + disassembly.

Windows automatically captures user-mode minidumps for unhandled exceptions
in apps that haven't disabled WER. The dumps live in:
    %LOCALAPPDATA%\\CrashDumps\\SIDFactoryII.exe.<pid>.dmp

This tool:
  1. Locates the most recent SF2II crash dump.
  2. Pulls the EXCEPTION_ACCESS_VIOLATION info: code address, accessed
     address, read/write flag.
  3. Maps the code address back to RVA in SIDFactoryII.exe.
  4. Disassembles 64 bytes before and 32 after, marking the crash insn.

Findings on the v3.3.0+full-blocks SF2 crash (commits 821168c..e0cea67):
  - All dumps crash at SIDFactoryII.exe RVA 0x7EF42:
        mov rdx, qword ptr [rax + rcx*8]
  - rax was loaded ~5 insns earlier from a struct field; it's NULL.
  - rcx = 9 (= byte at [r14 + 0x2e] * 3, where the byte value was 3).
  - Read addr = 0 + 9*8 = 0x48 — i.e., classic NULL+offset segfault.
  - The struct holding the array pointer is one ParseAuxilaryData
    populates; when that phase silently throws, the array is NULL and
    the editor-view setup phase deref-crashes here.

Usage:
    python pyscript/sf2_crash_analyze.py [dump_path]
    (no arg → newest SF2II dump in %LOCALAPPDATA%\\CrashDumps)
"""
import os
import sys
import glob
from pathlib import Path

try:
    from minidump.minidumpfile import MinidumpFile
except ImportError:
    sys.exit("install: py -3 -m pip install minidump pefile capstone")
try:
    import pefile
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
except ImportError:
    sys.exit("install: py -3 -m pip install pefile capstone")


def find_newest_dump():
    pattern = os.path.expandvars(r'%LOCALAPPDATA%\CrashDumps\SIDFactoryII.exe.*.dmp')
    matches = glob.glob(pattern)
    if not matches:
        sys.exit(f'No SF2II dumps at {pattern}')
    return max(matches, key=os.path.getmtime)


def find_exe(rel='bin/SIDFactoryII.exe'):
    here = Path(__file__).parent.parent
    p = here / rel
    if p.exists():
        return str(p)
    sys.exit(f'SIDFactoryII.exe not found at {p}')


def disasm_around(exe_path: str, target_rva: int, before: int = 64, after: int = 64):
    pe = pefile.PE(exe_path, fast_load=True)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    crash_va = image_base + target_rva
    for sec in pe.sections:
        if sec.VirtualAddress <= target_rva < sec.VirtualAddress + sec.Misc_VirtualSize:
            file_off = sec.PointerToRawData + (target_rva - sec.VirtualAddress)
            with open(exe_path, 'rb') as f:
                f.seek(file_off - before)
                blob = f.read(before + after)
            md = Cs(CS_ARCH_X86, CS_MODE_64)
            for ins in md.disasm(blob, crash_va - before):
                marker = '  >>>' if ins.address <= crash_va < ins.address + ins.size else '     '
                rva_str = f'0x{ins.address - image_base:08X}'
                print(f'{marker} {rva_str}  {ins.bytes.hex():<20s}  {ins.mnemonic} {ins.op_str}')
                if ins.address > crash_va + after:
                    break
            return
    print(f'  RVA 0x{target_rva:X} not in any code section')


def main(args):
    dump_path = args[0] if args else find_newest_dump()
    print(f'Analyzing: {dump_path}')
    print(f'Modified : {os.path.getmtime(dump_path)}')
    print(f'Size     : {os.path.getsize(dump_path)} bytes')

    md = MinidumpFile.parse(dump_path)
    if not md.exception or not md.exception.exception_records:
        print('  no exception record')
        return

    er_outer = md.exception.exception_records[0]
    er = er_outer.ExceptionRecord
    code = er.ExceptionCode
    addr = er.ExceptionAddress
    info = list(er.ExceptionInformation[:er.NumberParameters])

    print(f'\n=== Exception ===')
    print(f'  ThreadId  = 0x{er_outer.ThreadId:X}')
    print(f'  Code      = {code}')
    print(f'  PC (Va)   = 0x{addr:016X}')
    if er.NumberParameters >= 2:
        access = info[0]
        accessed = info[1]
        kind = {0: 'READ', 1: 'WRITE', 8: 'DEP'}.get(access, f'?{access}')
        print(f'  Type      = {kind} of address 0x{accessed:X}')

    mod = next((m for m in md.modules.modules
                if m.baseaddress <= addr < m.endaddress), None)
    if mod is None:
        print(f'  No module at PC')
        return

    rva = addr - mod.baseaddress
    print(f'  Module    = {os.path.basename(mod.name)}  (rva 0x{rva:X})')

    if os.path.basename(mod.name).lower() == 'sidfactoryii.exe':
        print(f'\n=== Disassembly around crash ===')
        disasm_around(find_exe(), rva)
    else:
        print(f'  (crash in {mod.name} — outside our binary)')


if __name__ == '__main__':
    main(sys.argv[1:])
