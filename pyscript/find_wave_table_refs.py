"""
Find wave table address references in Stinsens SID file assembly code.

Searches for 6502 instructions that reference the wave table addresses:
- Note offsets: $190C
- Waveforms: $18DA
"""

import sys
from pathlib import Path

def find_lda_instructions(data, target_addr):
    """Find LDA instructions that reference target_addr"""
    results = []

    # LDA absolute,Y (opcode 0xB9)
    lo = target_addr & 0xFF
    hi = (target_addr >> 8) & 0xFF
    pattern = bytes([0xB9, lo, hi])

    offset = 0
    while True:
        offset = data.find(pattern, offset)
        if offset == -1:
            break
        results.append(('LDA abs,Y', offset, pattern))
        offset += 1

    # LDA absolute (opcode 0xAD)
    pattern = bytes([0xAD, lo, hi])
    offset = 0
    while True:
        offset = data.find(pattern, offset)
        if offset == -1:
            break
        results.append(('LDA abs', offset, pattern))
        offset += 1

    # STA absolute (opcode 0x8D) - stores to address
    pattern = bytes([0x8D, lo, hi])
    offset = 0
    while True:
        offset = data.find(pattern, offset)
        if offset == -1:
            break
        results.append(('STA abs', offset, pattern))
        offset += 1

    return results

def show_context(data, offset, context=10):
    """Show bytes around offset"""
    start = max(0, offset - context)
    end = min(len(data), offset + context)

    result = []
    for i in range(start, end):
        if i == offset:
            result.append(f">>> {i:04X}: {data[i]:02X} <<<")
        else:
            result.append(f"    {i:04X}: {data[i]:02X}")

    return '\n'.join(result)

def main():
    sid_file = Path('Laxity/Stinsens_Last_Night_of_89.sid')

    if not sid_file.exists():
        print(f"Error: {sid_file} not found")
        return 1

    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"Analyzing {sid_file.name} ({len(data)} bytes)")
    print("=" * 70)

    # Wave table addresses
    NOTE_OFFSET_ADDR = 0x190C
    WAVEFORM_ADDR = 0x18DA

    print(f"\nSearching for references to NOTE OFFSETS table at ${NOTE_OFFSET_ADDR:04X}...")
    print("-" * 70)
    results = find_lda_instructions(data, NOTE_OFFSET_ADDR)

    if results:
        for instr, offset, pattern in results:
            print(f"\n{instr} ${NOTE_OFFSET_ADDR:04X},Y found at file offset {offset:04X}")
            print(f"Instruction bytes: {' '.join(f'{b:02X}' for b in pattern)}")
            print("\nContext:")
            print(show_context(data, offset, context=8))
    else:
        print("No direct references found")

    print(f"\n\nSearching for references to WAVEFORMS table at ${WAVEFORM_ADDR:04X}...")
    print("-" * 70)
    results = find_lda_instructions(data, WAVEFORM_ADDR)

    if results:
        for instr, offset, pattern in results:
            print(f"\n{instr} ${WAVEFORM_ADDR:04X},Y found at file offset {offset:04X}")
            print(f"Instruction bytes: {' '.join(f'{b:02X}' for b in pattern)}")
            print("\nContext:")
            print(show_context(data, offset, context=8))
    else:
        print("No direct references found")

    # Also search for the low/high bytes separately in case they're loaded
    # into zero page for indirect addressing
    print(f"\n\nSearching for address byte patterns...")
    print("-" * 70)

    note_lo = NOTE_OFFSET_ADDR & 0xFF  # 0x0C
    note_hi = (NOTE_OFFSET_ADDR >> 8) & 0xFF  # 0x19

    wave_lo = WAVEFORM_ADDR & 0xFF  # 0xDA
    wave_hi = (WAVEFORM_ADDR >> 8) & 0xFF  # 0x18

    # Search for LDA #$lo / LDA #$hi immediate loads
    for label, addr in [("NOTE_OFFSET", NOTE_OFFSET_ADDR), ("WAVEFORM", WAVEFORM_ADDR)]:
        lo = addr & 0xFF
        hi = (addr >> 8) & 0xFF

        # LDA #$lo (opcode 0xA9)
        pattern_lo = bytes([0xA9, lo])
        # LDA #$hi (opcode 0xA9)
        pattern_hi = bytes([0xA9, hi])

        offset = 0
        found_pairs = []
        while True:
            offset = data.find(pattern_lo, offset)
            if offset == -1:
                break
            # Look for high byte within next 10 bytes
            for j in range(offset + 2, min(offset + 12, len(data) - 1)):
                if data[j:j+2] == pattern_hi:
                    found_pairs.append((offset, j))
                    break
            offset += 1

        if found_pairs:
            print(f"\n{label} (${addr:04X}) address setup found:")
            for lo_off, hi_off in found_pairs:
                print(f"  LDA #${lo:02X} at {lo_off:04X}, LDA #${hi:02X} at {hi_off:04X}")

if __name__ == '__main__':
    sys.exit(main())
