#!/usr/bin/env python3
"""
Convert Order list from SF2-packed compact format to Driver 11 compact format.

SF2-packed format: TT [SS SS SS...]
Driver 11 format: Same compact format with pointers at $2324-$2329

Key differences:
- SF2-packed stores all 3 orderlists consecutively in one block
- Driver 11 stores each orderlist separately and uses pointers to locate them
"""

def convert_sf2_packed_to_driver11_orderlists():
    """Convert Order lists from SF2-packed to Driver 11 format."""

    with open('SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid', 'rb') as f:
        packed_data = f.read()

    # Order list starts at 0x0A9B in SF2-packed file
    # Voice 0 (Track 0) data at: 0x0AEE
    # Voice 1 (Track 1) data at: 0x0B1A
    # Voice 2 (Track 2) data at: 0x0B31
    voice_offsets = [0x0AEE, 0x0B1A, 0x0B31]

    print("=== CONVERTING SF2-PACKED TO DRIVER 11 ORDERLISTS ===\n")

    orderlists = []

    for voice_idx, start_offset in enumerate(voice_offsets):
        print(f"Voice {voice_idx}:")

        # Extract compact orderlist data for this voice
        orderlist_bytes = bytearray()
        pos = start_offset

        while pos < len(packed_data):
            byte = packed_data[pos]

            # Check for end markers
            if byte == 0xFF:
                # End of orderlist - add FF and loop target
                orderlist_bytes.append(byte)
                if pos + 1 < len(packed_data):
                    orderlist_bytes.append(packed_data[pos + 1])
                break
            elif byte == 0xFE:
                # End marker
                orderlist_bytes.append(byte)
                break

            # Add byte to orderlist
            orderlist_bytes.append(byte)
            pos += 1

            # Safety limit
            if len(orderlist_bytes) > 512:
                print(f"  WARNING: Orderlist exceeded 512 bytes, truncating")
                orderlist_bytes.append(0xFE)  # Add end marker
                break

        print(f"  Extracted {len(orderlist_bytes)} bytes")

        # Show first 32 bytes
        hex_preview = ' '.join(f'{orderlist_bytes[i]:02X}' for i in range(min(32, len(orderlist_bytes))))
        print(f"  Preview: {hex_preview}")

        # Parse and show structure
        parsed = []
        i = 0
        current_trans = 0xA0
        while i < len(orderlist_bytes):
            b = orderlist_bytes[i]
            if b == 0xFF:
                if i + 1 < len(orderlist_bytes):
                    parsed.append(f"LOOP->{orderlist_bytes[i+1]:02X}")
                break
            elif b == 0xFE:
                parsed.append("END")
                break
            elif 0x80 <= b <= 0xBF:
                # Transpose marker
                current_trans = b
                parsed.append(f"T={b:02X}")
                i += 1
            else:
                # Sequence number
                trans_offset = current_trans - 0xA0
                parsed.append(f"T{trans_offset:+d}:S{b:02X}")
                i += 1

            # Limit parsed output
            if len(parsed) >= 20:
                parsed.append("...")
                break

        print(f"  Parsed: {', '.join(parsed)}")
        print()

        orderlists.append(bytes(orderlist_bytes))

    # Save orderlists to separate files
    for voice_idx, orderlist_data in enumerate(orderlists):
        output_path = f'output/orderlist_voice{voice_idx}_driver11.bin'
        with open(output_path, 'wb') as f:
            f.write(orderlist_data)
        print(f"Saved Voice {voice_idx} orderlist ({len(orderlist_data)} bytes) to: {output_path}")

    print(f"\nTotal orderlists: {len(orderlists)}")
    print(f"Total bytes: {sum(len(ol) for ol in orderlists)}")

    return orderlists


if __name__ == '__main__':
    orderlists = convert_sf2_packed_to_driver11_orderlists()
