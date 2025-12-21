#!/usr/bin/env python3
"""
Analyze raw sequence bytes to understand the format
"""

from pathlib import Path

# Read the file
laxity_file = Path("learnings") / "Laxity - Stinsen - Last Night Of 89.sf2"

with open(laxity_file, 'rb') as f:
    data = f.read()

# Sequence data starts at offset 0x1662
seq_start = 0x1662
seq_end = seq_start + 100

print("RAW BYTES AT SEQUENCE OFFSET 0x1662:")
print("=" * 100)
print(f"{'Offset':>8s} {'Byte':>6s} {'Hex':>6s} {'Dec':>6s} {'ASCII':>8s} {'Interpretation':>30s}")
print("-" * 100)

for i in range(seq_start, min(seq_end, len(data))):
    byte = data[i]
    offset = i - seq_start
    ascii_char = chr(byte) if 32 <= byte < 127 else '.'

    # Interpret the byte
    if byte == 0x7F:
        interpretation = "END MARKER"
    elif byte >= 0xC0:
        interpretation = f"COMMAND (0x{byte:02X})"
    elif byte >= 0xA0:
        interpretation = f"INSTRUMENT (0x{byte:02X})"
    elif byte >= 0x80:
        interpretation = f"DURATION (0x{byte:02X})"
    else:
        interpretation = f"NOTE (0x{byte:02X})"

    print(f"{offset:>8d} {i:>6d} 0x{byte:02X} {byte:>6d} {ascii_char:>8s} {interpretation:>30s}")

print("\n" + "=" * 100)
print("SEQUENCE STRUCTURE ANALYSIS:")
print("=" * 100)

# Manually parse the first 20 bytes
print("\nManual parsing (each event should be: [INSTR?] [CMD?] [NOTE?] or similar)")
i = 0
while i < min(20, len(data) - seq_start):
    byte = data[seq_start + i]
    print(f"\nByte {i}: 0x{byte:02X} ({byte:>3d}) - ", end="")

    if byte == 0x7F:
        print("END MARKER - stop")
        break
    elif byte >= 0xC0:
        print(f"COMMAND byte")
    elif byte >= 0xA0:
        print(f"INSTRUMENT byte")
    elif byte >= 0x80:
        print(f"DURATION byte")
    else:
        print(f"NOTE value ({byte})")

    i += 1

print("\n" + "=" * 100)
print("KEY OBSERVATION:")
print("Looking at the first few bytes: 24 25 26 E1 E1 E1 E1...")
print("- 0x24, 0x25, 0x26 are all < 0x80, so they should be NOTES")
print("- 0xE1 is > 0xC0, so it's a COMMAND")
print("- But 0xE1 appearing repeatedly is suspicious - is this a data terminator or format marker?")
print("\nThis suggests the Laxity SF2 format may be DIFFERENT from generic SF2!")
