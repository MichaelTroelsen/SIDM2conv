#!/usr/bin/env python3
"""
Re-examine the sequence pointers from the disassembly.

From STINSENS_PLAYER_DISASSEMBLY.md:
$107F  BD 1C 1A      LDA    $1A1C,X        ; Load sequence pointer low byte
$1084  BD 1F 1A      LDA    $1A1F,X        ; Load sequence pointer high byte

This reads from $1A1C-$1A21 (6 bytes) in split format.
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset."""
    return 0x7E + (mem_addr - 0x1000)

def file_to_mem_addr(file_offset):
    """Convert file offset to memory address."""
    return 0x1000 + (file_offset - 0x7E)

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("RE-EXAMINING SEQUENCE POINTERS FROM DISASSEMBLY")
    print("=" * 70)
    print()

    with open(sid_file, 'rb') as f:
        data = f.read()

    # Check the disassembly addresses
    print("From disassembly at $107F and $1084:")
    print("  LDA $1A1C,X  ; Load sequence pointer low byte")
    print("  LDA $1A1F,X  ; Load sequence pointer high byte")
    print()

    # Read the 6 bytes at $1A1C-$1A21
    ptr_addr = 0x1A1C
    ptr_offset = mem_to_file_offset(ptr_addr)

    print(f"Reading 6 bytes from memory ${ptr_addr:04X} (file offset 0x{ptr_offset:04X}):")

    bytes_at_loc = []
    for i in range(6):
        b = data[ptr_offset + i]
        bytes_at_loc.append(b)
        print(f"  ${ptr_addr + i:04X} (0x{ptr_offset + i:04X}): {b:02X}")

    print()
    print("These bytes in split format (3 low, 3 high):")
    print(f"  Low bytes:  {bytes_at_loc[0]:02X} {bytes_at_loc[1]:02X} {bytes_at_loc[2]:02X}")
    print(f"  High bytes: {bytes_at_loc[3]:02X} {bytes_at_loc[4]:02X} {bytes_at_loc[5]:02X}")
    print()

    # Decode pointers
    pointers = []
    for i in range(3):
        lo = bytes_at_loc[i]
        hi = bytes_at_loc[i + 3]
        ptr = lo | (hi << 8)
        pointers.append(ptr)

    print("Decoded pointers (voice 0, 1, 2):")
    for i, ptr in enumerate(pointers):
        file_off = mem_to_file_offset(ptr)
        print(f"  Voice {i}: ${ptr:04X} (file offset 0x{file_off:04X})")
    print()

    # Check what's at these addresses
    print("=" * 70)
    print("EXAMINING DATA AT THESE POINTER LOCATIONS")
    print("=" * 70)
    print()

    for i, ptr in enumerate(pointers):
        file_off = mem_to_file_offset(ptr)
        print(f"Voice {i} - Memory ${ptr:04X} (file 0x{file_off:04X}):")

        # Show first 48 bytes as 3-byte entries
        print("  First 16 entries:")
        for j in range(16):
            offset = file_off + j * 3
            if offset + 2 < len(data):
                inst = data[offset]
                cmd = data[offset + 1]
                note = data[offset + 2]

                note_str = f"{note:02X}"
                if note == 0x7E:
                    note_str = "7E (+++)"
                elif note == 0x7F:
                    note_str = "7F (END)"
                elif note == 0x80:
                    note_str = "80 (---)"
                elif note == 0xFF:
                    note_str = "FF (LOOP)"
                elif note >= 0xA0:
                    note_str = f"{note:02X} (TRAN)"

                print(f"    +{j*3:02d}: [{inst:02X}] [{cmd:02X}] [{note_str}]")
        print()

    # Compare with orderlists
    print("=" * 70)
    print("COMPARE WITH ORDERLIST LOCATIONS")
    print("=" * 70)
    print()

    orderlist_addrs = {
        'Voice 0': 0x1AEE,
        'Voice 1': 0x1B1A,
        'Voice 2': 0x1B31
    }

    for voice, addr in orderlist_addrs.items():
        offset = mem_to_file_offset(addr)
        print(f"{voice} orderlist:")
        print(f"  Memory: ${addr:04X}")
        print(f"  File offset: 0x{offset:04X}")
        print()

    # Check if pointers point to orderlists or before them
    print("Analysis:")
    for i, ptr in enumerate(pointers):
        print(f"  Voice {i} pointer ${ptr:04X}:")
        if ptr < 0x1AEE:  # Before first orderlist
            print(f"    BEFORE orderlists - could be sequence data")
        elif ptr >= 0x1AEE and ptr < 0x1B60:  # In orderlist range
            print(f"    IN ORDERLIST RANGE - likely IS an orderlist!")
        else:
            print(f"    AFTER orderlists")
    print()

if __name__ == '__main__':
    main()
