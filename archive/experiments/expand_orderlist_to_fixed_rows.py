#!/usr/bin/env python3
"""
Expand compact orderlist format to fixed-row XXYY format.

Compact format: A0 0E 0F AC 02 03...
  - Transpose markers (A0, AC) are implicit
  - Only changes in transpose are marked

Expanded format: A0 0E A0 0F AC 02 AC 03...
  - Every entry is explicit XXYY (2 bytes)
  - Transpose is repeated for each sequence

This ensures consistent row numbering in the SID Factory II editor display.
"""

def expand_orderlist_to_fixed_rows():
    """Expand compact orderlists to explicit XXYY format."""

    # Load compact orderlists
    orderlists_compact = []
    for voice_idx in range(3):
        orderlist_path = f'output/orderlist_voice{voice_idx}_driver11.bin'
        with open(orderlist_path, 'rb') as f:
            # Add A0 marker for Voice 1 if missing
            data = bytearray(f.read())
            if voice_idx == 1 and data[0] != 0xA0:
                data = bytearray([0xA0]) + data
            orderlists_compact.append(data)

    print("=== EXPANDING ORDERLISTS TO FIXED-ROW FORMAT ===\n")

    orderlists_expanded = []

    for voice_idx, compact_data in enumerate(orderlists_compact):
        print(f"Voice {voice_idx}:")
        print(f"  Compact size: {len(compact_data)} bytes")

        # Expand to XXYY format
        expanded = bytearray()
        current_transpose = 0xA0  # Default

        i = 0
        entry_count = 0
        while i < len(compact_data):
            byte = compact_data[i]

            # Check for end markers
            if byte == 0xFF:
                # Loop marker - add as-is
                expanded.append(byte)
                if i + 1 < len(compact_data):
                    expanded.append(compact_data[i + 1])
                break
            elif byte == 0xFE:
                # End marker
                expanded.append(byte)
                break

            # Check if transpose marker
            if 0x80 <= byte <= 0xBF:
                current_transpose = byte
                i += 1
            else:
                # Sequence number - add as XXYY entry
                expanded.append(current_transpose)
                expanded.append(byte)
                entry_count += 1
                i += 1

        print(f"  Expanded size: {len(expanded)} bytes")
        print(f"  Entries: {entry_count}")

        # Show first 32 bytes
        hex_preview = ' '.join(f'{expanded[j]:02X}' for j in range(min(32, len(expanded))))
        print(f"  Preview: {hex_preview}")
        print()

        orderlists_expanded.append(bytes(expanded))

    # Now inject into SF2 file
    print("=== INJECTING EXPANDED ORDERLISTS INTO SF2 ===\n")

    with open('output/Stinsens_Last_Night_of_89_ALL_7_TABLES.sf2', 'rb') as f:
        sf2_data = bytearray(f.read())

    load_addr = int.from_bytes(sf2_data[0:2], 'little')
    orderlist_addrs = [0x242A, 0x252A, 0x262A]

    for voice_idx, expanded_data in enumerate(orderlists_expanded):
        mem_addr = orderlist_addrs[voice_idx]
        file_offset = mem_addr - load_addr + 2

        print(f"Voice {voice_idx} at \${mem_addr:04X}:")

        # Inject expanded orderlist
        sf2_data[file_offset:file_offset+len(expanded_data)] = expanded_data

        # Show what was written
        after = sf2_data[file_offset:file_offset+min(64, len(expanded_data))]
        hex_str = ' '.join(f'{b:02X}' for b in after[:32])
        print(f"  Written: {hex_str}")
        print()

    # Save updated SF2 file
    output_path = 'output/Stinsens_Last_Night_of_89_WITH_ORDERLISTS_EXPANDED.sf2'
    with open(output_path, 'wb') as f:
        f.write(sf2_data)

    print(f"Saved to: {output_path}")
    print(f"File size: {len(sf2_data)} bytes")


if __name__ == '__main__':
    expand_orderlist_to_fixed_rows()
