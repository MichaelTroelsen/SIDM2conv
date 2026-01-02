#!/usr/bin/env python3
"""Find all instances of tempo pattern in SID file"""

# Read SID file
with open('Laxity/Stinsens_Last_Night_of_89.sid', 'rb') as f:
    sid_full = f.read()

# Search for tempo pattern
pattern = bytes([0x03, 0x04, 0x7F])

print('Searching for ALL instances of tempo pattern (03 04 7F):')
print('=' * 60)

instances = []
offset = 0
while True:
    offset = sid_full.find(pattern, offset)
    if offset == -1:
        break

    mem_addr = offset - 0x7C + 0x1000
    instances.append((offset, mem_addr))

    # Show context (10 bytes before and after)
    start = max(0, offset - 5)
    end = min(len(sid_full), offset + 8)
    context = sid_full[start:end]

    print(f'\nInstance {len(instances)}:')
    print(f'  File offset: 0x{offset:04X}')
    print(f'  Memory addr: 0x{mem_addr:04X}')
    print(f'  Context: {" ".join(f"{b:02X}" for b in context)}')
    print(f'           {" " * (15 if start == offset - 5 else 0)}^^^ ^^^ ^^^')

    offset += 1

print(f'\n{len(instances)} instance(s) found')

if len(instances) == 1:
    offset, mem_addr = instances[0]
    print(f'\nSingle instance confirms tempo location: 0x{mem_addr:04X}')
    print(f'\nConclusion:')
    print(f'  - Laxity tempo table is only 3 bytes (not 256 like SF2)')
    print(f'  - Values: 0x03, 0x04, 0x7F')
    print(f'  - Address: 0x{mem_addr:04X}')
    print(f'  - SF2 pads this to 256 bytes with zeros for compatibility')
