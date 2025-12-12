#!/usr/bin/env python3
"""
Analyze how sequences are laid out in an actual SF2 file.

Based on SF2_FORMAT_SPEC.md:
- Sequence Pointers section starts at $0903
- Contains BOTH order lists and sequences
- Sequences use "contiguous stacking" (like Tetris)
- Format: 3 bytes per entry [Instrument] [Command] [Note]
- 0x80 = "no change" marker for persistence encoding
"""

def analyze_sf2_sequences(sf2_file):
    """Analyze sequence layout in an SF2 file."""
    print(f"Reading: {sf2_file}\n")

    with open(sf2_file, 'rb') as f:
        data = f.read()

    # SF2 files start with load address
    load_addr = data[0] | (data[1] << 8)
    print(f"Load address: ${load_addr:04X}")
    print(f"File size: {len(data)} bytes\n")

    # Sequence pointers section starts at $0903 (memory) = file offset depends on load address
    seq_section_mem = 0x0903
    seq_section_file = seq_section_mem - load_addr + 2  # +2 for load address bytes

    print(f"Sequence Pointers section:")
    print(f"  Memory address: ${seq_section_mem:04X}")
    print(f"  File offset: 0x{seq_section_file:04X}\n")

    # Show first 256 bytes of this section
    print(f"First 256 bytes of Sequence Pointers section:\n")

    for i in range(0, min(256, len(data) - seq_section_file), 16):
        offset = seq_section_file + i
        if offset >= len(data):
            break

        hex_vals = ' '.join(f'{data[offset+j]:02X}' for j in range(min(16, len(data)-offset)))
        print(f"  +0x{i:04X} (${seq_section_mem+i:04X}): {hex_vals}")

    # Look for patterns that might indicate structure:
    # - 0x80 markers (persistence encoding)
    # - 0x7F markers (end of sequence)
    # - Repeating values

    print(f"\n\n=== Analyzing Structure ===\n")

    # Count 0x80 markers (no-change markers)
    count_80 = 0
    count_7F = 0
    count_7E = 0

    for i in range(seq_section_file, min(seq_section_file + 512, len(data))):
        if data[i] == 0x80:
            count_80 += 1
        elif data[i] == 0x7F:
            count_7F += 1
        elif data[i] == 0x7E:
            count_7E += 1

    print(f"In first 512 bytes of section:")
    print(f"  0x80 markers (---): {count_80}")
    print(f"  0x7F markers (END): {count_7F}")
    print(f"  0x7E markers (+++): {count_7E}\n")

    # Try to parse as 3-byte entries
    print(f"Parsing as 3-byte entries (first 30 entries):\n")

    for i in range(30):
        offset = seq_section_file + (i * 3)
        if offset + 2 >= len(data):
            break

        inst = data[offset]
        cmd = data[offset+1]
        note = data[offset+2]

        # Format special values
        inst_str = f"{inst:02X}"
        if inst == 0x80:
            inst_str = "-- (80)"
        elif inst >= 0xA0 and inst <= 0xBF:
            inst_str = f"I{inst-0xA0:02d}"

        cmd_str = f"{cmd:02X}"
        if cmd == 0x80:
            cmd_str = "-- (80)"
        elif cmd >= 0xC0:
            cmd_str = f"C{cmd-0xC0:02d}"

        note_str = f"{note:02X}"
        if note == 0x7E:
            note_str = "+++ (7E)"
        elif note == 0x7F:
            note_str = "END (7F)"
        elif note == 0x80:
            note_str = "--- (80)"

        print(f"  Entry {i:02d} (+0x{i*3:04X}): [{inst_str:8s}] [{cmd_str:8s}] [{note_str}]")

def main():
    # Analyze the template file
    template_file = 'output/Stinsens_Last_Night_of_89_WITH_ORDERLISTS_EXPANDED.sf2'

    print("=" * 70)
    print("TEMPLATE SF2 FILE ANALYSIS")
    print("=" * 70 + "\n")

    analyze_sf2_sequences(template_file)

    # Also analyze the reference file if it exists
    ref_file = 'learnings/Laxity - Stinsen - Last Night Of 89.sf2'

    try:
        print("\n\n" + "=" * 70)
        print("REFERENCE SF2 FILE ANALYSIS")
        print("=" * 70 + "\n")

        analyze_sf2_sequences(ref_file)
    except FileNotFoundError:
        print(f"\nReference file not found: {ref_file}")

if __name__ == '__main__':
    main()
