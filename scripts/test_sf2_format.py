#!/usr/bin/env python3
"""
Test SF2 format by comparing our output with working template byte-by-byte.
"""

import sys

def load_file(path):
    with open(path, 'rb') as f:
        return bytearray(f.read())

def get_word(data, offset):
    return data[offset] | (data[offset + 1] << 8)

def analyze_sf2(data, name):
    """Analyze SF2 file structure"""
    print(f"\n{'='*60}")
    print(f"ANALYSIS: {name}")
    print(f"{'='*60}")

    load_addr = get_word(data, 0)
    print(f"Load address: ${load_addr:04X}")

    # Key addresses for Driver 11
    # Orderlist pointers at $2324 (lo) and $2327 (hi)
    ol_ptrs_lo = 0x2324
    ol_ptrs_hi = 0x2327

    # Sequence pointers at $232A (lo) and $23AA (hi)
    seq_ptrs_lo = 0x232A
    seq_ptrs_hi = 0x23AA

    print(f"\n--- ORDERLIST POINTERS ---")
    print(f"Pointer table lo: ${ol_ptrs_lo:04X}, hi: ${ol_ptrs_hi:04X}")

    orderlists = []
    for t in range(3):
        lo_off = ol_ptrs_lo - load_addr + 2
        hi_off = ol_ptrs_hi - load_addr + 2
        addr = data[lo_off + t] | (data[hi_off + t] << 8)
        orderlists.append(addr)

        file_off = addr - load_addr + 2
        ol_data = data[file_off:file_off+20]
        hex_str = ' '.join(f'{b:02X}' for b in ol_data)
        print(f"  Track {t}: ${addr:04X} (offset {file_off})")
        print(f"    Raw: {hex_str}")

        # Parse orderlist
        parsed = []
        i = 0
        trans = 0xA0
        while i < 20:
            b = ol_data[i]
            if b == 0xFF:
                parsed.append(f"LOOP->{ol_data[i+1]:02X}")
                break
            elif b == 0xFE:
                parsed.append("END")
                break
            elif 0x80 <= b <= 0xBF:
                trans = b
                i += 1
            else:
                parsed.append(f"T{trans-0xA0:+d}:S{b}")
                i += 1
        print(f"    Parsed: {', '.join(parsed)}")

    print(f"\n--- SEQUENCE POINTERS ---")
    print(f"Pointer table lo: ${seq_ptrs_lo:04X}, hi: ${seq_ptrs_hi:04X}")

    sequences = []
    for i in range(10):  # First 10 sequences
        lo_off = seq_ptrs_lo - load_addr + 2
        hi_off = seq_ptrs_hi - load_addr + 2
        addr = data[lo_off + i] | (data[hi_off + i] << 8)
        sequences.append(addr)

        file_off = addr - load_addr + 2
        seq_data = data[file_off:file_off+30]
        hex_str = ' '.join(f'{b:02X}' for b in seq_data)
        print(f"  Seq {i}: ${addr:04X} (offset {file_off})")
        print(f"    Raw: {hex_str}")

    return {
        'load_addr': load_addr,
        'orderlists': orderlists,
        'sequences': sequences
    }

def compare_formats():
    """Compare working template with our output"""

    template_path = 'G5/examples/Driver 11 Test - Arpeggio.sf2'
    our_path = 'G5/examples/Driver 11 Test - Filter.sf2'

    # Check if files exist before trying to load
    import os
    if not os.path.exists(template_path):
        print(f"Template file not found: {template_path}")
        print("Skipping SF2 format comparison tests")
        return

    if not os.path.exists(our_path):
        print(f"Test file not found: {our_path}")
        print("Skipping SF2 format comparison tests")
        return

    template = load_file(template_path)
    ours = load_file(our_path)

    template_info = analyze_sf2(template, "WORKING TEMPLATE")
    our_info = analyze_sf2(ours, "OUR OUTPUT")

    print(f"\n{'='*60}")
    print("COMPARISON")
    print(f"{'='*60}")

    # Compare orderlist addresses
    print("\nOrderlist addresses:")
    for t in range(3):
        t_addr = template_info['orderlists'][t]
        o_addr = our_info['orderlists'][t]
        match = "OK" if t_addr == o_addr else "MISMATCH"
        print(f"  Track {t}: Template=${t_addr:04X}, Ours=${o_addr:04X} [{match}]")

    # Compare sequence addresses
    print("\nSequence addresses (first 10):")
    for i in range(10):
        t_addr = template_info['sequences'][i]
        o_addr = our_info['sequences'][i]
        match = "OK" if t_addr == o_addr else "MISMATCH"
        print(f"  Seq {i}: Template=${t_addr:04X}, Ours=${o_addr:04X} [{match}]")

    # Check expected addresses based on 256-byte slots
    print("\n--- EXPECTED ADDRESSES (256-byte slots) ---")

    # Orderlists should start at $242A
    ol_base = 0x242A
    print(f"Orderlists (base ${ol_base:04X}, 256-byte slots):")
    for t in range(3):
        expected = ol_base + (t * 256)
        actual = our_info['orderlists'][t]
        match = "OK" if expected == actual else "MISMATCH"
        print(f"  Track {t}: Expected=${expected:04X}, Actual=${actual:04X} [{match}]")

    # Sequences should start at $272A
    seq_base = 0x272A
    print(f"\nSequences (base ${seq_base:04X}, 256-byte slots):")
    for i in range(10):
        expected = seq_base + (i * 256)
        actual = our_info['sequences'][i]
        match = "OK" if expected == actual else "MISMATCH"
        print(f"  Seq {i}: Expected=${expected:04X}, Actual=${actual:04X} [{match}]")

def test_sequence_format():
    """Test that sequence format matches SF2 requirements"""
    print(f"\n{'='*60}")
    print("SEQUENCE FORMAT TEST")
    print(f"{'='*60}")

    template_path = r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2'

    template = load_file(template_path)
    load_addr = get_word(template, 0)

    # Get sequence 0 from template
    seq_ptrs_lo = 0x232A
    seq_ptrs_hi = 0x23AA

    lo_off = seq_ptrs_lo - load_addr + 2
    hi_off = seq_ptrs_hi - load_addr + 2

    seq_addr = template[lo_off] | (template[hi_off] << 8)
    seq_off = seq_addr - load_addr + 2

    print(f"\nTemplate Sequence 0 at ${seq_addr:04X}:")
    seq_data = template[seq_off:seq_off+40]

    # Parse sequence format
    print("Parsing sequence format:")
    i = 0
    while i < 40:
        b = seq_data[i]
        if b == 0x7F:
            print(f"  [{i:02d}] 0x{b:02X} - END MARKER")
            break
        elif 0xC0 <= b <= 0xCF:
            print(f"  [{i:02d}] 0x{b:02X} - COMMAND {b-0xC0}")
        elif 0xA0 <= b <= 0xBF:
            print(f"  [{i:02d}] 0x{b:02X} - INSTRUMENT {b-0xA0}")
        elif 0x80 <= b <= 0x9F:
            print(f"  [{i:02d}] 0x{b:02X} - DURATION {b-0x80}")
        elif 0x00 <= b <= 0x6F:
            note_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
            octave = b // 12
            note = b % 12
            print(f"  [{i:02d}] 0x{b:02X} - NOTE {note_names[note]}{octave}")
        elif b == 0x7E:
            print(f"  [{i:02d}] 0x{b:02X} - TIE/REST")
        else:
            print(f"  [{i:02d}] 0x{b:02X} - UNKNOWN")
        i += 1

def validate_sf2_aux_pointer(filepath):
    """
    Validate that SF2 file doesn't have aux pointer pointing to valid aux data.
    SID Factory II crashes when loading files with valid aux data pointers.

    Returns: (is_valid, message)
    """
    import struct

    with open(filepath, 'rb') as f:
        data = f.read()

    if len(data) < 0x300:
        return (False, f"File too small: {len(data)} bytes")

    load_addr = struct.unpack('<H', data[:2])[0]
    file_size = len(data)
    max_addr = load_addr + file_size - 2

    # Aux pointer is at memory address $0FFB
    aux_ptr_offset = 0x0FFB - load_addr + 2

    if aux_ptr_offset >= len(data) - 2:
        return (False, f"Aux pointer offset 0x{aux_ptr_offset:04X} outside file")

    aux_ptr = struct.unpack('<H', data[aux_ptr_offset:aux_ptr_offset+2])[0]

    # Check if pointer points within file
    if aux_ptr > max_addr:
        return (True, f"Aux pointer ${aux_ptr:04X} is beyond file (OK - ignored by SF2)")

    # Calculate file offset of aux data
    aux_file_offset = aux_ptr - load_addr + 2

    if aux_file_offset >= len(data):
        return (True, f"Aux offset 0x{aux_file_offset:04X} beyond file (OK - ignored by SF2)")

    # Check if it points to valid aux data (Type 4 or 5)
    first_byte = data[aux_file_offset]

    if first_byte == 4 or first_byte == 5:
        # Verify it's actually valid aux data by checking version and size
        if aux_file_offset + 5 <= len(data):
            version = struct.unpack('<H', data[aux_file_offset+1:aux_file_offset+3])[0]
            size = struct.unpack('<H', data[aux_file_offset+3:aux_file_offset+5])[0]

            if 0 < version <= 10 and 0 < size < 0x2000:
                return (False, f"CRASH RISK: Aux pointer ${aux_ptr:04X} points to valid aux data (Type={first_byte}, Version={version}, Size={size})")

    return (True, f"Aux pointer ${aux_ptr:04X} points to non-aux data (byte 0x{first_byte:02X}) - SF2 will ignore it")


def test_all_sf2_files():
    """Test all SF2 files in the SF2 directory for aux pointer issues"""
    import os

    print(f"\n{'='*60}")
    print("SF2 AUX POINTER VALIDATION")
    print(f"{'='*60}")

    sf2_dir = 'SF2'
    if not os.path.exists(sf2_dir):
        print(f"Directory not found: {sf2_dir}")
        return False

    all_valid = True
    files_checked = 0

    for filename in sorted(os.listdir(sf2_dir)):
        if filename.endswith('.sf2'):
            filepath = os.path.join(sf2_dir, filename)
            is_valid, message = validate_sf2_aux_pointer(filepath)

            status = "PASS" if is_valid else "FAIL"
            print(f"\n{filename}: [{status}]")
            print(f"  {message}")

            if not is_valid:
                all_valid = False
            files_checked += 1

    print(f"\n{'='*60}")
    print(f"Total files checked: {files_checked}")
    print(f"Result: {'ALL PASSED' if all_valid else 'SOME FAILED'}")
    print(f"{'='*60}")

    return all_valid


if __name__ == '__main__':
    # Run aux pointer validation first
    aux_valid = test_all_sf2_files()

    # Only run other tests if aux validation passes
    if aux_valid:
        compare_formats()
        test_sequence_format()
    else:
        print("\nSkipping other tests due to aux pointer validation failures")
        sys.exit(1)
