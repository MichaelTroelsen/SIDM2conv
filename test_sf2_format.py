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

    template_path = r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2'
    our_path = 'SF2/Angular.sf2'

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

if __name__ == '__main__':
    compare_formats()
    test_sequence_format()
