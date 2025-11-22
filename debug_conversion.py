#!/usr/bin/env python3
"""Debug the conversion to see what events were created"""

import struct
from laxity_parser import LaxityParser

def main():
    # Load SID file
    with open('SID/Angular.sid', 'rb') as f:
        data = f.read()

    # Parse PSID header
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_address = struct.unpack('>H', data[8:10])[0]

    c64_data = data[data_offset:]
    if load_address == 0:
        load_address = struct.unpack('<H', c64_data[0:2])[0]
        c64_data = c64_data[2:]

    # Parse with Laxity parser
    laxity = LaxityParser(c64_data, load_address)
    laxity_data = laxity.parse()

    # Show what we'd write for each sequence
    print("\n" + "=" * 60)
    print("CONVERSION DEBUG - WHAT GETS WRITTEN TO SF2")
    print("=" * 60)

    for seq_idx, raw_seq in enumerate(laxity_data.sequences[:5]):
        print(f"\nSequence {seq_idx} ({len(raw_seq)} bytes)")
        print(f"  Raw: {' '.join(f'{b:02X}' for b in raw_seq[:40])}")

        # Parse into events
        events = []
        current_instr = 0x80
        current_cmd = 0x00

        i = 0
        while i < len(raw_seq):
            b = raw_seq[i]

            if b == 0x7F:
                events.append((0x80, 0x00, 0x7F, "END"))
                break
            elif 0xA0 <= b <= 0xAF:
                current_instr = b
                events.append((b, None, None, f"INSTR={b-0xA0}"))
            elif 0x80 <= b <= 0x9F:
                current_cmd = b
                events.append((None, b, None, f"DUR={b-0x80}"))
            elif 0xC0 <= b <= 0xCF:
                current_cmd = b
                events.append((None, b, None, f"CMD={b-0xC0}"))
            elif b <= 0x70 or b == 0x7E:
                events.append((current_instr, current_cmd, b, f"NOTE={b:02X}"))
                current_instr = 0x80
                current_cmd = 0x00

            i += 1

        print("  Events:")
        for ev in events[:15]:
            print(f"    {ev}")
        if len(events) > 15:
            print(f"    ... and {len(events) - 15} more")

        # Show what would be written
        output = []
        for ev in events:
            instr, cmd, note, desc = ev
            if instr is not None and instr != 0x80 and note is None:
                # Standalone instrument change - don't write yet
                continue
            if cmd is not None and note is None:
                # Standalone duration/command - don't write yet
                continue
            if note is not None:
                if instr is not None and instr != 0x80:
                    output.append(instr)
                if cmd is not None and cmd != 0x00:
                    output.append(cmd)
                output.append(note)

        print(f"  Would write: {' '.join(f'{b:02X}' for b in output[:30])}")
        if len(output) > 30:
            print(f"               ... and {len(output) - 30} more bytes")


if __name__ == '__main__':
    main()
