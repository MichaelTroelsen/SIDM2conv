"""
Find all Laxity table references in Stinsens SID file.

Searches for wave, pulse, filter, instrument, and other table references.
"""

import sys
from pathlib import Path

def find_lda_sta_references(data, target_addr, search_opcodes=None):
    """Find LDA/STA instructions that reference target_addr"""
    if search_opcodes is None:
        search_opcodes = {
            0xB9: 'LDA abs,Y',
            0xAD: 'LDA abs',
            0xBD: 'LDA abs,X',
            0x8D: 'STA abs',
            0x9D: 'STA abs,X',
            0x99: 'STA abs,Y',
        }

    results = []
    lo = target_addr & 0xFF
    hi = (target_addr >> 8) & 0xFF

    for opcode, mnemonic in search_opcodes.items():
        pattern = bytes([opcode, lo, hi])
        offset = 0
        while True:
            offset = data.find(pattern, offset)
            if offset == -1:
                break
            results.append((mnemonic, offset, pattern, opcode))
            offset += 1

    return results

def find_immediate_loads(data, value):
    """Find LDA #$value instructions"""
    results = []
    pattern = bytes([0xA9, value])  # LDA #$value
    offset = 0
    while True:
        offset = data.find(pattern, offset)
        if offset == -1:
            break
        results.append(('LDA #imm', offset, pattern))
        offset += 1
    return results

def main():
    sid_file = Path('Laxity/Stinsens_Last_Night_of_89.sid')

    if not sid_file.exists():
        print(f"Error: {sid_file} not found")
        return 1

    with open(sid_file, 'rb') as f:
        data = f.read()

    print("=" * 70)
    print("Stinsens - Complete Table Reference Analysis")
    print("=" * 70)

    # Known table addresses from verification
    tables = {
        'Wave (waveforms)': 0x18DA,
        'Wave (note offsets)': 0x190C,
        'Pulse': 0x1837,
        'Filter': 0x1A1E,
        'Instrument': 0x1A6B,
        'Sequence pointers': 0x199F,
        'Orderlist voice 1': None,  # Dynamic
        'Orderlist voice 2': None,  # Dynamic
        'Orderlist voice 3': None,  # Dynamic
    }

    all_references = {}

    for table_name, table_addr in tables.items():
        if table_addr is None:
            continue

        print(f"\n{'=' * 70}")
        print(f"Searching for: {table_name} (${table_addr:04X})")
        print('=' * 70)

        results = find_lda_sta_references(data, table_addr)

        if results:
            print(f"Found {len(results)} reference(s):")
            all_references[table_name] = results

            for mnemonic, offset, pattern, opcode in results:
                mem_offset = offset - 0x7C
                mem_addr = 0x1000 + mem_offset
                bytes_str = ' '.join(f'{b:02X}' for b in pattern)

                print(f"  {mnemonic:12s} ${table_addr:04X}  at file offset 0x{offset:04X} (mem ${mem_addr:04X})  [{bytes_str}]")
        else:
            print("  No direct references found")

    # Summary
    print("\n\n" + "=" * 70)
    print("SUMMARY - All Table References Found")
    print("=" * 70)

    for table_name, results in all_references.items():
        print(f"\n{table_name}:")
        for mnemonic, offset, pattern, opcode in results:
            mem_offset = offset - 0x7C
            mem_addr = 0x1000 + mem_offset
            print(f"  ${mem_addr:04X}: {mnemonic}")

    return 0

if __name__ == '__main__':
    sys.exit(main())
