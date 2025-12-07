#!/usr/bin/env python3
"""Debug Broware packing issue."""

import logging
import sys
from pathlib import Path
from sidm2.sf2_packer import SF2Packer, create_psid_header

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

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

    # Look for JMP/JSR to $0000 or other suspicious addresses
    print(f'\nScanning for problematic JMP/JSR instructions...')
    count = 0
    for i in range(len(packed_data) - 2):
        opcode = packed_data[i]
        if opcode in [0x20, 0x4C, 0x6C]:  # JSR, JMP absolute, JMP indirect
            target = packed_data[i+1] | (packed_data[i+2] << 8)
            if target == 0x0000 or target < 0x0100:
                inst_name = {0x20: 'JSR', 0x4C: 'JMP', 0x6C: 'JMP (ind)'}[opcode]
                print(f'  At ${i:04X} (mem ${i+0x1000:04X}): {inst_name} ${target:04X}')
                count += 1

    if count == 0:
        print('  No problematic instructions found')
    else:
        print(f'  Total: {count} suspicious instructions')

    # Create PSID header
    header = create_psid_header('Broware', 'Test', '2025', 0, init_addr, play_addr)
    with open(output_path, 'wb') as f:
        f.write(header)
        # Add PRG load address
        f.write(bytes([0x00, 0x10]))  # $1000 little-endian
        f.write(packed_data)

    print(f'\nWrote to {output_path}')
    return output_path

if __name__ == '__main__':
    sf2_path = Path('output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2')
    output_path = Path('test_broware_debug.sid')
    result = debug_pack(sf2_path, output_path)

    # Test with SIDwinder
    print('\n' + '='*60)
    print('Testing with SIDwinder...')
    print('='*60)
    import subprocess
    result = subprocess.run(['tools/SIDwinder.exe', '-disassemble', str(output_path), 'test_broware_debug.asm'],
                          capture_output=True, text=True)
    print(result.stderr if result.stderr else result.stdout)
