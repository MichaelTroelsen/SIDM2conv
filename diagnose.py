#!/usr/bin/env python3
"""
Diagnostic tool to compare our output with a working SF2 file.
"""

import sys

def analyze_working_template():
    """Analyze the working template to understand exact format."""
    template_path = r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2'

    with open(template_path, 'rb') as f:
        data = f.read()

    load_addr = data[0] | (data[1] << 8)

    print("=" * 60)
    print("WORKING TEMPLATE ANALYSIS")
    print("=" * 60)

    # Orderlist pointers
    ol_ptrs_lo = 0x2324
    ol_ptrs_hi = 0x2327

    ol_lo_off = ol_ptrs_lo - load_addr + 2
    ol_hi_off = ol_ptrs_hi - load_addr + 2

    print("\nOrderlist Pointers:")
    for t in range(3):
        addr = data[ol_lo_off + t] | (data[ol_hi_off + t] << 8)
        file_off = addr - load_addr + 2
        print(f"  Track {t}: ${addr:04X}")

        # Show orderlist data
        ol_data = data[file_off:file_off+30]
        hex_str = ' '.join(f'{b:02X}' for b in ol_data)
        print(f"    {hex_str}")

    # Sequence pointers
    seq_ptrs_lo = 0x232A
    seq_ptrs_hi = 0x23AA

    seq_lo_off = seq_ptrs_lo - load_addr + 2
    seq_hi_off = seq_ptrs_hi - load_addr + 2

    print("\nFirst 3 Sequences:")
    for i in range(3):
        addr = data[seq_lo_off + i] | (data[seq_hi_off + i] << 8)
        file_off = addr - load_addr + 2
        print(f"  Seq {i}: ${addr:04X}")

        seq_data = data[file_off:file_off+40]
        hex_str = ' '.join(f'{b:02X}' for b in seq_data)
        print(f"    {hex_str}")

def analyze_our_output(filepath):
    """Analyze our converted SF2 file."""
    with open(filepath, 'rb') as f:
        data = f.read()

    load_addr = data[0] | (data[1] << 8)

    print("\n" + "=" * 60)
    print(f"OUR OUTPUT ANALYSIS: {filepath}")
    print("=" * 60)

    # Orderlist pointers
    ol_ptrs_lo = 0x2324
    ol_ptrs_hi = 0x2327

    ol_lo_off = ol_ptrs_lo - load_addr + 2
    ol_hi_off = ol_ptrs_hi - load_addr + 2

    print("\nOrderlist Pointers:")
    for t in range(3):
        addr = data[ol_lo_off + t] | (data[ol_hi_off + t] << 8)
        file_off = addr - load_addr + 2
        print(f"  Track {t}: ${addr:04X}")

        # Show orderlist data
        ol_data = data[file_off:file_off+30]
        hex_str = ' '.join(f'{b:02X}' for b in ol_data)
        print(f"    {hex_str}")

    # Sequence pointers
    seq_ptrs_lo = 0x232A
    seq_ptrs_hi = 0x23AA

    seq_lo_off = seq_ptrs_lo - load_addr + 2
    seq_hi_off = seq_ptrs_hi - load_addr + 2

    print("\nFirst 3 Sequences:")
    for i in range(3):
        addr = data[seq_lo_off + i] | (data[seq_hi_off + i] << 8)
        file_off = addr - load_addr + 2
        print(f"  Seq {i}: ${addr:04X}")

        seq_data = data[file_off:file_off+40]
        hex_str = ' '.join(f'{b:02X}' for b in seq_data)
        print(f"    {hex_str}")

def show_extracted_data():
    """Show what we extracted from the SID file."""
    print("\n" + "=" * 60)
    print("EXTRACTED DATA FROM SID")
    print("=" * 60)

    from sid_to_sf2 import SIDParser, LaxityPlayerAnalyzer

    sid_path = 'SID/Angular.sid'
    parser = SIDParser(sid_path)
    header = parser.parse_header()
    c64_data, load_address = parser.get_c64_data(header)

    analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
    data = analyzer.extract_music_data()

    print(f"\nExtracted {len(data.sequences)} sequences")
    print(f"Extracted {len(data.orderlists)} orderlists")

    print("\nFirst 3 Orderlists:")
    for t, ol in enumerate(data.orderlists[:3]):
        print(f"  Track {t}: {len(ol)} entries")
        for i, (trans, seq_idx) in enumerate(ol[:5]):
            print(f"    [{i}] trans={trans}, seq={seq_idx}")
        if len(ol) > 5:
            print(f"    ... and {len(ol)-5} more")

    print("\nFirst 5 Sequences:")
    for i, seq in enumerate(data.sequences[:5]):
        print(f"  Seq {i}: {len(seq)} events")
        for j, event in enumerate(seq[:3]):
            print(f"    [{j}] instr=0x{event.instrument:02X}, cmd=0x{event.command:02X}, note=0x{event.note:02X}")
        if len(seq) > 3:
            print(f"    ... and {len(seq)-3} more events")

if __name__ == '__main__':
    analyze_working_template()
    analyze_our_output('SF2/Angular.sf2')
    show_extracted_data()
