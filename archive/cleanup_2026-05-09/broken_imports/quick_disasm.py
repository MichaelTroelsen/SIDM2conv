"""Quick disassembly of a SID file."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from disassembler_6502 import Disassembler6502
from sidm2.errors import InvalidInputError


def parse_sid_header(sid_data: bytes) -> dict:
    """Parse PSID/RSID file header."""
    if len(sid_data) < 0x7C:
        raise InvalidInputError(
            input_type='SID file',
            value='<input data>',
            expected='At least 124 bytes for SID header',
            got=f'Only {len(sid_data)} bytes available',
            suggestions=[
                'Verify file is a complete SID file (not truncated)',
                'Check if file was fully downloaded',
                f'Data size: {len(sid_data)} bytes',
                'SID files should be at least 124 bytes + music data',
                'Try re-downloading or re-exporting the file'
            ],
            docs_link='guides/TROUBLESHOOTING.md#invalid-sid-files'
        )

    magic = sid_data[0:4].decode('ascii', errors='ignore')
    if magic not in ('PSID', 'RSID'):
        raise InvalidInputError(
            input_type='SID file',
            value='<input data>',
            expected='PSID or RSID magic bytes at file start',
            got=f'Magic bytes: {repr(magic)}',
            suggestions=[
                'Verify file is a valid SID file (not corrupted)',
                'Check file extension is .sid',
                'Try opening file in a SID player (e.g., VICE) to verify',
                'Inspect file header with a hex viewer',
                'Re-download file if obtained from internet'
            ],
            docs_link='guides/TROUBLESHOOTING.md#invalid-sid-files'
        )

    version = (sid_data[4] << 8) | sid_data[5]
    data_offset = (sid_data[6] << 8) | sid_data[7]
    load_addr = (sid_data[8] << 8) | sid_data[9]
    init_addr = (sid_data[0xA] << 8) | sid_data[0xB]
    play_addr = (sid_data[0xC] << 8) | sid_data[0xD]

    title = sid_data[0x16:0x36].decode('ascii', errors='ignore').rstrip('\x00')
    author = sid_data[0x36:0x56].decode('ascii', errors='ignore').rstrip('\x00')

    if load_addr == 0 and len(sid_data) > data_offset + 2:
        load_addr = sid_data[data_offset] | (sid_data[data_offset + 1] << 8)
        code_start = data_offset + 2
    else:
        code_start = data_offset

    return {
        'magic': magic,
        'version': version,
        'load_addr': load_addr,
        'init_addr': init_addr,
        'play_addr': play_addr,
        'title': title,
        'author': author,
        'code_start': code_start,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_disasm.py <sid_file>")
        return 1

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return 1

    # Read and parse
    sid_data = filepath.read_bytes()
    header = parse_sid_header(sid_data)

    print("=" * 80)
    print(f"FILE: {filepath.name}")
    print("=" * 80)
    print(f"Title:      {header['title']}")
    print(f"Author:     {header['author']}")
    print(f"Format:     {header['magic']} v{header['version']}")
    print(f"Load Addr:  ${header['load_addr']:04X}")
    print(f"Init Addr:  ${header['init_addr']:04X}")
    print(f"Play Addr:  ${header['play_addr']:04X}")

    # Disassemble first 100 instructions
    code_start = header['code_start']
    load_addr = header['load_addr']
    code_data = sid_data[code_start:code_start + 2048]

    disasm = Disassembler6502()
    instructions = disasm.disassemble_range(code_data, load_addr, min(len(code_data), 300))
    instructions = instructions[:100]

    print(f"\nDISASSEMBLY (first 100 instructions):")
    print("-" * 80)
    listing = disasm.format_listing(instructions, show_hex=True)
    print(listing)

    return 0


if __name__ == "__main__":
    sys.exit(main())
