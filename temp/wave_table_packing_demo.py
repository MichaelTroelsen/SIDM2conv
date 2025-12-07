#!/usr/bin/env python3
"""
Wave Table Packing/Unpacking Demonstration

Shows how SID Factory II packs Wave table data:
- Editor display: Array of (waveform, note) pairs
- Packed format: Column-major storage (all notes, then all waveforms)

Based on SF2 source analysis and format specification.
"""

def unpack_wave_table(packed_data: bytes) -> list:
    """
    Unpack Wave table from column-major format to editor display format.

    Args:
        packed_data: 64 bytes in column-major format
                    [note0, note1, ..., note31, wave0, wave1, ..., wave31]

    Returns:
        List of (waveform, note) tuples as displayed in editor
    """
    if len(packed_data) < 64:
        raise ValueError(f"Wave table must be 64 bytes, got {len(packed_data)}")

    # Split into columns
    notes = packed_data[0:32]      # First column: all note offsets
    waveforms = packed_data[32:64]  # Second column: all waveforms

    # Combine into rows (waveform, note) pairs
    entries = []
    for i in range(32):
        waveform = waveforms[i]
        note = notes[i]
        entries.append((waveform, note))

    return entries


def pack_wave_table(entries: list) -> bytes:
    """
    Pack Wave table from editor format to column-major format.

    Args:
        entries: List of (waveform, note) tuples from editor

    Returns:
        64 bytes in column-major format
    """
    if len(entries) > 32:
        raise ValueError(f"Wave table max 32 entries, got {len(entries)}")

    # Pad to 32 entries if needed
    while len(entries) < 32:
        entries.append((0x00, 0x00))

    # Separate into columns
    notes = []
    waveforms = []

    for waveform, note in entries:
        notes.append(note)
        waveforms.append(waveform)

    # Pack column-major: all notes first, then all waveforms
    packed = bytes(notes) + bytes(waveforms)

    return packed


def demo_from_images():
    """Demonstrate with data from user's images."""

    print("=" * 80)
    print("WAVE TABLE PACKING DEMONSTRATION")
    print("=" * 80)

    # Example data from Image #2 (hex dump)
    packed_hex = """
    07 c4 ac c0 bc 0c c0 00 0f c0 00 76 74 14 b4 12
    00 18 00 00 1b 00 1d c5 00 20 00 22 c0 00 25 00
    27 00 29 c7 ae a5 c0 2e 00 30 38 00 81 00 00 0f
    7f 88 7f 88 0f 0f 00 7f 88 00 0f 00 7f 86 00 0f
    """

    # Convert hex string to bytes
    packed_bytes = bytes.fromhex(packed_hex.replace('\n', '').replace(' ', ''))

    print("\n1. PACKED FORMAT (Column-Major Storage)")
    print("-" * 80)
    print("First 32 bytes (Note offsets):")
    for i in range(0, 32, 16):
        hex_str = ' '.join(f'{b:02X}' for b in packed_bytes[i:i+16])
        print(f"  {i:02X}: {hex_str}")

    print("\nNext 32 bytes (Waveforms):")
    for i in range(32, 64, 16):
        hex_str = ' '.join(f'{b:02X}' for b in packed_bytes[i:i+16])
        print(f"  {i:02X}: {hex_str}")

    # Unpack to editor format
    entries = unpack_wave_table(packed_bytes)

    print("\n2. EDITOR FORMAT (As Displayed in SF2 Editor)")
    print("-" * 80)
    print("Entry | Waveform | Note Offset | Description")
    print("------|----------|-------------|--------------------------------")

    for i, (waveform, note) in enumerate(entries[:16]):  # Show first 16
        wave_desc = get_waveform_desc(waveform)
        note_desc = get_note_desc(note)
        print(f"  {i:02X}  |    {waveform:02X}    |     {note:02X}      | {wave_desc:12} {note_desc}")

    print("  ... (16 more entries)")

    # Demonstrate round-trip
    print("\n3. ROUND-TRIP TEST")
    print("-" * 80)
    repacked = pack_wave_table(entries)

    if repacked == packed_bytes:
        print("[SUCCESS] Repacked data matches original")
    else:
        print("[FAILED] Repacked data differs")
        print(f"  Original:  {packed_bytes.hex()[:40]}...")
        print(f"  Repacked:  {repacked.hex()[:40]}...")

    # Show example from Image #1
    print("\n4. EXAMPLE FROM IMAGE #1 (Editor Display)")
    print("-" * 80)

    # Example entries from Image #1
    editor_entries = [
        (0x21, 0x80),  # 00: 21 80
        (0x21, 0x80),  # 01: 21 80
        (0x41, 0x00),  # 02: 41 00
        (0x7F, 0x02),  # 03: 7f 02 (loop marker)
        (0x51, 0xC0),  # 04: 51 c0
        (0x41, 0xA1),  # 05: 41 a1
        (0x41, 0x9A),  # 06: 41 9a
        (0x41, 0x00),  # 07: 41 00
        (0x7F, 0x07),  # 08: 7f 07 (loop marker)
        (0x81, 0xC4),  # 09: 81 c4
        (0x41, 0xAC),  # 0a: 41 ac
        (0x80, 0xC0),  # 0b: 80 c0
        (0x80, 0xBC),  # 0c: 80 bc
        (0x7F, 0x0C),  # 0d: 7f 0c (loop marker)
        (0x81, 0xC0),  # 0e: 81 c0
        (0x01, 0x00),  # 0f: 01 00
    ]

    print("Editor format (waveform, note) pairs:")
    for i, (waveform, note) in enumerate(editor_entries):
        print(f"  {i:02X}: {waveform:02X} {note:02X}")

    # Pack to column-major
    packed_example = pack_wave_table(editor_entries)

    print("\nPacked to column-major format:")
    print("Notes (first 16 bytes):")
    print(f"  {packed_example[0:16].hex(' ').upper()}")
    print("Waveforms (bytes 32-47):")
    print(f"  {packed_example[32:48].hex(' ').upper()}")


def get_waveform_desc(waveform: int) -> str:
    """Get waveform description."""
    wave_type = waveform & 0x0F
    gate = waveform & 0x10

    types = {
        0x01: "Triangle",
        0x02: "Sawtooth",
        0x04: "Pulse",
        0x08: "Noise",
        0x00: "None",
    }

    desc = types.get(wave_type, f"${wave_type:02X}")
    if gate:
        desc += "+Gate"

    if waveform == 0x7F:
        return "LOOP MARKER"
    if waveform == 0x7E:
        return "GATE ON"
    if waveform == 0x80:
        return "GATE OFF"

    return desc


def get_note_desc(note: int) -> str:
    """Get note offset description."""
    if note == 0x00:
        return "(no offset)"
    elif note == 0x7F:
        return "(loop ref)"
    elif note >= 0x80:
        return f"(special ${note:02X})"
    else:
        return f"(offset +{note})"


if __name__ == '__main__':
    demo_from_images()
