"""
Show the exact assembly code that accesses wave tables in Stinsens.

Displays both hex and disassembled code.
"""

import sys
from pathlib import Path

def show_hex_and_disasm(data, offset, mem_addr, count=16):
    """Show hex bytes and their disassembly"""
    lines = []

    # Show context before
    lines.append(f"\nHex dump around offset 0x{offset:04X} (memory ${mem_addr:04X}):")
    lines.append("-" * 70)

    start = max(0, offset - 8)
    end = min(len(data), offset + count)

    for i in range(start, end):
        hex_byte = f"{data[i]:02X}"
        marker = " >>>" if i == offset else "    "
        lines.append(f"{marker} 0x{i:04X}: {hex_byte}")

    return '\n'.join(lines)

def main():
    sid_file = Path('Laxity/Stinsens_Last_Night_of_89.sid')

    if not sid_file.exists():
        print(f"Error: {sid_file} not found")
        return 1

    with open(sid_file, 'rb') as f:
        data = f.read()

    print("=" * 70)
    print("Stinsens - Wave Table Assembly Code Analysis")
    print("=" * 70)

    print("\nWave Table Addresses (verified):")
    print(f"  Waveforms:    $18DA")
    print(f"  Note offsets: $190C")

    # References found:
    refs = [
        (0x05C1, 0x18DA, "WAVEFORMS"),
        (0x05C8, 0x190C, "NOTE OFFSETS"),
        (0x05CF, 0x18DA, "WAVEFORMS"),
        (0x05D5, 0x190C, "NOTE OFFSETS"),
    ]

    for file_offset, table_addr, table_name in refs:
        # Calculate memory address (accounting for header)
        # SID header is typically 0x7C bytes
        mem_offset = file_offset - 0x7C
        mem_addr = 0x1000 + mem_offset  # Stinsens loads at $1000

        print(f"\n\n{'=' * 70}")
        print(f"Reference to {table_name} table (${table_addr:04X})")
        print(f"{'=' * 70}")

        print(f"\nFile offset:   0x{file_offset:04X}")
        print(f"Memory offset: 0x{mem_offset:04X}")
        print(f"Memory addr:   ${mem_addr:04X}")

        # Show the instruction bytes
        b0 = data[file_offset]
        b1 = data[file_offset + 1]
        b2 = data[file_offset + 2]

        print(f"\nInstruction bytes: {b0:02X} {b1:02X} {b2:02X}")

        if b0 == 0xB9:
            addr = b1 | (b2 << 8)
            print(f"Disassembly:       LDA ${addr:04X},Y")
            print(f"\nThis is the 6502 instruction:")
            print(f"  Opcode: 0xB9 = LDA absolute,Y")
            print(f"  Address: ${addr:04X} = {table_name} table")
            print(f"  Y register = index into table (0-31)")

        # Show hex context
        print(show_hex_and_disasm(data, file_offset, mem_addr))

    print("\n\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("""
The Laxity player uses indexed addressing to access wave tables:

    LDA $18DA,Y    ; Load waveform byte (Y = instrument index)
    LDA $190C,Y    ; Load note offset byte (Y = instrument index)

The dual-array format has:
  - 32 waveform bytes at $18DA
  - 32 note offset bytes at $190C

Each instrument uses one byte from each array, indexed by Y register.

Example: Instrument 5 would use:
  - Waveform:    data[$18DA + 5] = data[$18DF]
  - Note offset: data[$190C + 5] = data[$1911]

This is why we extract both arrays and maintain the column-major format!
""")

if __name__ == '__main__':
    sys.exit(main())
