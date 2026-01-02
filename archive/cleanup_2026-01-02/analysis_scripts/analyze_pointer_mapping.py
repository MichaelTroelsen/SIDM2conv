"""Analyze pointer mapping between found pointers and injection addresses.

This script maps the 32 found pointers from regenerate_laxity_patches.py
to the injection addresses used in sf2_writer.py to determine if pointer
patches are needed.
"""

# Found pointers from regenerate_laxity_patches.py
found_pointers = [
    (0x0089, 0x3B, 0x1A, 0x3B, 0x1A),  # $0E05 -> $1A3B
    (0x009D, 0x00, 0x1E, 0x00, 0x1E),  # $0E19 -> $1E00
    (0x009E, 0x1E, 0x1A, 0x1E, 0x1A),  # $0E1A -> $1A1E
    (0x00B6, 0x00, 0x19, 0x00, 0x19),  # $0E32 -> $1900
    (0x00BE, 0x00, 0x19, 0x00, 0x19),  # $0E3A -> $1900
    (0x02A0, 0x83, 0x1C, 0x83, 0x1C),  # $101C -> $1C83
    (0x02B2, 0x80, 0x1D, 0x80, 0x1D),  # $102E -> $1D80
    (0x02BE, 0xA4, 0x1D, 0xA4, 0x1D),  # $103A -> $1DA4
    (0x02C0, 0x91, 0x1B, 0x91, 0x1B),  # $103C -> $1B91
    (0x02C3, 0x83, 0x1A, 0x83, 0x1A),  # $103F -> $1A83
    (0x02C8, 0xA1, 0x1D, 0xA1, 0x1D),  # $1044 -> $1DA1
    (0x02D2, 0x81, 0x1B, 0x81, 0x1B),  # $104E -> $1B81
    (0x02DD, 0xA1, 0x1F, 0xA1, 0x1F),  # $1059 -> $1FA1
    (0x02DF, 0xA4, 0x1B, 0xA4, 0x1B),  # $105B -> $1BA4
    (0x02E1, 0x91, 0x1A, 0x91, 0x1A),  # $105D -> $1A91
    (0x02F1, 0x81, 0x1A, 0x81, 0x1A),  # $106D -> $1A81
    (0x04C9, 0x80, 0x1D, 0x80, 0x1D),  # $1245 -> $1D80
    (0x04E9, 0x81, 0x1B, 0x81, 0x1B),  # $1265 -> $1B81
    (0x04F4, 0xA1, 0x1F, 0xA1, 0x1F),  # $1270 -> $1FA1
    (0x04F6, 0xA4, 0x1B, 0xA4, 0x1B),  # $1272 -> $1BA4
    (0x04F8, 0x91, 0x1A, 0x91, 0x1A),  # $1274 -> $1A91
    (0x0508, 0x81, 0x1A, 0x81, 0x1A),  # $1284 -> $1A81
    (0x069B, 0x90, 0x1F, 0x90, 0x1F),  # $1417 -> $1F90
    (0x069D, 0x90, 0x1D, 0x90, 0x1D),  # $1419 -> $1D90
    (0x069F, 0x9F, 0x1A, 0x9F, 0x1A),  # $141B -> $1A9F
    (0x06BB, 0x21, 0x1D, 0x21, 0x1D),  # $1437 -> $1D21
    (0x075E, 0x00, 0x1D, 0x00, 0x1D),  # $14DA -> $1D00
    (0x0793, 0xA1, 0x1A, 0xA1, 0x1A),  # $150F -> $1AA1
    (0x079F, 0x80, 0x1A, 0x80, 0x1A),  # $151B -> $1A80
    (0x07A3, 0x83, 0x1A, 0x83, 0x1A),  # $151F -> $1A83
    (0x07AF, 0xA4, 0x1F, 0xA4, 0x1F),  # $152B -> $1FA4
    (0x07F1, 0x91, 0x1A, 0x91, 0x1A),  # $156D -> $1A91
]

# Injection addresses from sf2_writer.py
INJECTION_ADDRESSES = {
    'orderlist_track0': 0x1900,
    'orderlist_track1': 0x1A00,
    'orderlist_track2': 0x1B00,
    'sequences': 0x1C00,  # After 3×256 byte orderlists
    'instrument_table': 0x1A81,
    'wave_table_waveforms': 0x1942,
    'wave_table_note_offsets': 0x1974,
    'pulse_table': 0x1E00,
    'filter_table': 0x1F00,
}

def analyze_pointer(offset, old_lo, old_hi, new_lo, new_hi):
    """Analyze a single pointer."""
    # Calculate addresses
    load_addr = 0x0D7E
    pc_addr = offset + load_addr - 2
    old_addr = old_lo | (old_hi << 8)
    new_addr = new_lo | (new_hi << 8)

    # Determine what this pointer likely references
    category = "Unknown"
    injection_target = None
    needs_patch = False

    if old_addr == INJECTION_ADDRESSES['orderlist_track0']:
        category = "Orderlist Track 0"
        injection_target = INJECTION_ADDRESSES['orderlist_track0']
    elif old_addr == INJECTION_ADDRESSES['orderlist_track1']:
        category = "Orderlist Track 1"
        injection_target = INJECTION_ADDRESSES['orderlist_track1']
    elif old_addr == INJECTION_ADDRESSES['orderlist_track2']:
        category = "Orderlist Track 2"
        injection_target = INJECTION_ADDRESSES['orderlist_track2']
    elif old_addr == INJECTION_ADDRESSES['instrument_table']:
        category = "Instrument Table (EXACT)"
        injection_target = INJECTION_ADDRESSES['instrument_table']
    elif old_addr == INJECTION_ADDRESSES['pulse_table']:
        category = "Pulse Table (EXACT)"
        injection_target = INJECTION_ADDRESSES['pulse_table']
    elif 0x1A80 <= old_addr < 0x1AB0:
        category = "Instrument Table Area"
        injection_target = INJECTION_ADDRESSES['instrument_table']
        needs_patch = (old_addr != INJECTION_ADDRESSES['instrument_table'])
    elif 0x1900 <= old_addr < 0x1B00:
        category = "Orderlist Area"
        # Determine which track
        if old_addr < 0x1A00:
            injection_target = INJECTION_ADDRESSES['orderlist_track0']
        elif old_addr < 0x1B00:
            injection_target = INJECTION_ADDRESSES['orderlist_track1']
    elif 0x1B00 <= old_addr < 0x1E00:
        category = "Sequence Area"
        injection_target = INJECTION_ADDRESSES['sequences']
    elif 0x1E00 <= old_addr < 0x1F00:
        category = "Pulse Table Area"
        injection_target = INJECTION_ADDRESSES['pulse_table']
        needs_patch = (old_addr != INJECTION_ADDRESSES['pulse_table'])
    elif 0x1F00 <= old_addr < 0x2000:
        category = "Filter Table Area"
        injection_target = INJECTION_ADDRESSES['filter_table']
    elif 0x1A00 <= old_addr < 0x1A80:
        # This might be wave table area
        category = "Possible Wave Table"
        # Check if close to wave table addresses
        if abs(old_addr - INJECTION_ADDRESSES['wave_table_waveforms']) < 0x50:
            injection_target = INJECTION_ADDRESSES['wave_table_waveforms']
            needs_patch = (old_addr != INJECTION_ADDRESSES['wave_table_waveforms'])
        elif abs(old_addr - INJECTION_ADDRESSES['wave_table_note_offsets']) < 0x50:
            injection_target = INJECTION_ADDRESSES['wave_table_note_offsets']
            needs_patch = (old_addr != INJECTION_ADDRESSES['wave_table_note_offsets'])

    return {
        'offset': offset,
        'pc_addr': pc_addr,
        'old_addr': old_addr,
        'new_addr': new_addr,
        'category': category,
        'injection_target': injection_target,
        'needs_patch': needs_patch,
        'matches': old_addr == injection_target if injection_target else None
    }

def main():
    print("=" * 80)
    print("POINTER MAPPING ANALYSIS")
    print("=" * 80)
    print()

    print("Injection Addresses:")
    for name, addr in sorted(INJECTION_ADDRESSES.items()):
        print(f"  {name:30s}: ${addr:04X}")
    print()

    print("=" * 80)
    print("POINTER ANALYSIS")
    print("=" * 80)
    print()

    categories = {}
    needs_patching = []

    for offset, old_lo, old_hi, new_lo, new_hi in found_pointers:
        result = analyze_pointer(offset, old_lo, old_hi, new_lo, new_hi)

        # Group by category
        cat = result['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(result)

        # Track pointers that need patching
        if result['needs_patch']:
            needs_patching.append(result)

    # Print by category
    for category in sorted(categories.keys()):
        pointers = categories[category]
        print(f"{category} ({len(pointers)} pointers):")
        print("-" * 80)

        for p in pointers:
            match_str = ""
            if p['injection_target']:
                if p['matches']:
                    match_str = " [OK] MATCHES"
                elif p['needs_patch']:
                    match_str = f" [PATCH] NEEDS PATCH -> ${p['injection_target']:04X}"
                else:
                    match_str = f" (target: ${p['injection_target']:04X})"

            print(f"  ${p['pc_addr']:04X} (offset ${p['offset']:04X}): "
                  f"${p['old_addr']:04X}{match_str}")
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total pointers found: {len(found_pointers)}")
    print(f"Pointers that need patching: {len(needs_patching)}")
    print()

    if needs_patching:
        print("Pointers requiring patches:")
        for p in needs_patching:
            print(f"  ${p['pc_addr']:04X}: ${p['old_addr']:04X} -> ${p['injection_target']:04X}")
            print(f"    (offset ${p['offset']:04X}, category: {p['category']})")
        print()

        print("Recommended action: Update pointer_patches in sf2_writer.py")
    else:
        print("All pointers appear to match injection addresses!")
        print("The 'all zeros' problem might have a different cause.")
        print()
        print("Possible causes:")
        print("  1. Data injection not working properly")
        print("  2. Table format mismatch")
        print("  3. Missing initialization")

if __name__ == '__main__':
    main()
