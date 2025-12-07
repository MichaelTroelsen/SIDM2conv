#!/usr/bin/env python3
"""Debug script to test SF2 packer and find $0000 jump issue."""

import logging
import sys
from pathlib import Path
from sidm2.sf2_packer import SF2Packer, create_psid_header

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

def debug_pack(sf2_path, output_path):
    """Pack SF2 and show debug info."""
    print('='*60)
    print(f'Packing {sf2_path.name}')
    print('='*60)

    packer = SF2Packer(sf2_path)
    packed_data, init_addr, play_addr = packer.pack()

    print(f'\nPacked data size: {len(packed_data)} bytes')
    print(f'Init address: ${init_addr:04X}')
    print(f'Play address: ${play_addr:04X}')

    # Check first 20 bytes
    print(f'\nFirst 20 bytes of packed data:')
    for i in range(min(20, len(packed_data))):
        if i % 8 == 0:
            print(f'  [{i:02X}]', end='  ')
        print(f'{packed_data[i]:02X}', end=' ')
        if i % 8 == 7:
            print()
    print()

    # Look for $0000 references in JMP/JSR instructions
    print(f'\nScanning for JMP/JSR to $0000...')
    count = 0
    for i in range(len(packed_data) - 2):
        opcode = packed_data[i]
        if opcode in [0x20, 0x4C]:  # JSR or JMP absolute
            target = packed_data[i+1] | (packed_data[i+2] << 8)
            if target == 0x0000:
                inst = 'JSR' if opcode == 0x20 else 'JMP'
                print(f'  Found at offset ${i:04X}: {inst} $0000')
                count += 1

    if count == 0:
        print('  No JMP/JSR to $0000 found in packed data')
    else:
        print(f'  Total: {count} instructions')

    # Create PSID header
    header = create_psid_header('Test', 'Test', '2025', 0x1000, init_addr, play_addr)
    with open(output_path, 'wb') as f:
        f.write(header)
        f.write(packed_data)

    print(f'\nWrote to {output_path}')

if __name__ == '__main__':
    sf2_path = Path('output/SIDSF2player_Complete_Pipeline/Aint_Somebody/New/Aint_Somebody.sf2')
    output_path = Path('test_aint_pack_debug.sid')
    debug_pack(sf2_path, output_path)
