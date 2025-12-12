#!/usr/bin/env python3
"""
Re-analyze the "orderlists" - they might actually BE the sequence data!

The code at $108C reads: LDA ($FC),Y
Where $FC/$FD points to what we called "orderlists" at $1A70, $1A9B, $1AB3.

This means those locations contain the ACTUAL SEQUENCE DATA, not just
references to sequences!
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset."""
    return 0x7E + (mem_addr - 0x1000)

def file_to_mem_addr(file_offset):
    """Convert file offset to memory address."""
    return 0x1000 + (file_offset - 0x7E)

def extract_sequence_direct(data, start_offset, max_entries=200):
    """
    Extract sequence data directly from location.

    Format appears to be:
    - Transpose markers ($A0+) followed by data
    - Or direct note/instrument/command data
    """
    entries = []
    offset = start_offset
    count = 0

    while offset + 2 < len(data) and count < max_entries:
        byte1 = data[offset]
        byte2 = data[offset + 1]
        byte3 = data[offset + 2]

        # Check for end markers
        if byte1 == 0xFF or byte1 == 0xFE:
            entries.append({
                'type': 'END',
                'bytes': [byte1, byte2, byte3],
                'offset': offset
            })
            break

        # Check for transpose marker (>= $A0)
        if byte1 >= 0xA0:
            entries.append({
                'type': 'TRANSPOSE',
                'transpose': byte1,
                'note': byte2,
                'cmd': byte3,
                'offset': offset
            })
            offset += 3
        else:
            entries.append({
                'type': 'NOTE',
                'note': byte1,
                'inst': byte2,
                'cmd': byte3,
                'offset': offset
            })
            offset += 3

        count += 1

    return entries

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("ANALYZING 'ORDERLISTS' AS SEQUENCE DATA")
    print("=" * 70)
    print()

    with open(sid_file, 'rb') as f:
        data = f.read()

    # The three "orderlist" addresses from pointers
    voice_addrs = {
        'Voice 0': 0x1A70,
        'Voice 1': 0x1A9B,
        'Voice 2': 0x1AB3
    }

    for voice, addr in voice_addrs.items():
        offset = mem_to_file_offset(addr)

        print(f"{voice}")
        print(f"  Memory: ${addr:04X}")
        print(f"  File offset: 0x{offset:04X}")
        print()

        # Extract data
        entries = extract_sequence_direct(data, offset, 50)

        print(f"  Extracted {len(entries)} entries:")
        print()

        for i, entry in enumerate(entries[:20]):  # Show first 20
            if entry['type'] == 'TRANSPOSE':
                trans_val = entry['transpose'] - 0xA0
                print(f"    +{i*3:03d}: TRAN {trans_val:+d} | Note {entry['note']:02X} | Cmd {entry['cmd']:02X}")
            elif entry['type'] == 'NOTE':
                print(f"    +{i*3:03d}: Note {entry['note']:02X} | Inst {entry['inst']:02X} | Cmd {entry['cmd']:02X}")
            elif entry['type'] == 'END':
                print(f"    +{i*3:03d}: END | {entry['bytes'][1]:02X} | {entry['bytes'][2]:02X}")
                break

        if len(entries) > 20:
            print(f"    ... and {len(entries) - 20} more entries")

        print()
        print("=" * 70)
        print()

    print()
    print("CONCLUSION:")
    print("=" * 70)
    print()
    print("If these look like sequence data (notes, instruments, commands),")
    print("then the 'orderlists' ARE the sequences!")
    print()
    print("The confusion may be:")
    print("  - Laxity format doesn't have separate sequence/orderlist levels")
    print("  - What we called 'orderlists' are actually the pattern tracks")
    print("  - There may not be a separate sequence pointer table")
    print()

if __name__ == '__main__':
    main()
