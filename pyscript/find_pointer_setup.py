"""
Find pointer setup code for Laxity tables.

Searches for LDA #$lo / LDA #$hi patterns that load table addresses.
"""

import sys
from pathlib import Path

def find_address_setup(data, target_addr, context=20):
    """Find code that sets up pointers to target_addr"""
    lo = target_addr & 0xFF
    hi = (target_addr >> 8) & 0xFF

    results = []

    # Pattern 1: LDA #$lo followed by LDA #$hi within 20 bytes
    lda_imm = 0xA9
    offset = 0

    while offset < len(data) - 1:
        # Find LDA #$lo
        if data[offset] == lda_imm and data[offset + 1] == lo:
            # Look ahead for LDA #$hi
            for i in range(offset + 2, min(offset + context, len(data) - 1)):
                if data[i] == lda_imm and data[i + 1] == hi:
                    results.append({
                        'type': 'LDA #imm pair',
                        'lo_offset': offset,
                        'hi_offset': i,
                        'distance': i - offset
                    })
                    break
        offset += 1

    # Pattern 2: LDX #$lo / LDY #$hi
    ldx_imm = 0xA2
    ldy_imm = 0xA0

    offset = 0
    while offset < len(data) - 1:
        if data[offset] == ldx_imm and data[offset + 1] == lo:
            for i in range(offset + 2, min(offset + context, len(data) - 1)):
                if data[i] == ldy_imm and data[i + 1] == hi:
                    results.append({
                        'type': 'LDX/LDY pair',
                        'lo_offset': offset,
                        'hi_offset': i,
                        'distance': i - offset
                    })
                    break
        offset += 1

    return results

def show_context(data, offset, lines=5):
    """Show hex context around offset"""
    start = max(0, offset - lines)
    end = min(len(data), offset + lines + 3)

    result = []
    for i in range(start, end):
        marker = ">>>" if i == offset else "   "
        result.append(f"{marker} 0x{i:04X}: {data[i]:02X}")

    return '\n'.join(result)

def main():
    sid_file = Path('Laxity/Stinsens_Last_Night_of_89.sid')

    if not sid_file.exists():
        print(f"Error: {sid_file} not found")
        return 1

    with open(sid_file, 'rb') as f:
        data = f.read()

    print("=" * 70)
    print("Stinsens - Table Pointer Setup Analysis")
    print("=" * 70)

    tables = {
        'Pulse': 0x1837,
        'Filter': 0x1A1E,
        'Instrument': 0x1A6B,
        'Sequence pointers': 0x199F,
    }

    for table_name, table_addr in tables.items():
        print(f"\n{'=' * 70}")
        print(f"{table_name} table (${table_addr:04X})")
        print('=' * 70)

        lo = table_addr & 0xFF
        hi = (table_addr >> 8) & 0xFF
        print(f"Address bytes: lo=${lo:02X}, hi=${hi:02X}")

        results = find_address_setup(data, table_addr)

        if results:
            print(f"\nFound {len(results)} pointer setup pattern(s):")
            for r in results:
                mem_lo = r['lo_offset'] - 0x7C + 0x1000
                mem_hi = r['hi_offset'] - 0x7C + 0x1000

                print(f"\n  {r['type']}:")
                print(f"    Load lo byte at: file 0x{r['lo_offset']:04X}, mem ${mem_lo:04X}")
                print(f"    Load hi byte at: file 0x{r['hi_offset']:04X}, mem ${mem_hi:04X}")
                print(f"    Distance: {r['distance']} bytes apart")

                print(f"\n  Context (lo byte):")
                print(show_context(data, r['lo_offset']))

                print(f"\n  Context (hi byte):")
                print(show_context(data, r['hi_offset']))
        else:
            print("\nNo pointer setup patterns found")
            print("This table may be:")
            print("  - Accessed via hardcoded offsets")
            print("  - Referenced in the player init code")
            print("  - Stored as data rather than accessed by code")

    return 0

if __name__ == '__main__':
    sys.exit(main())
