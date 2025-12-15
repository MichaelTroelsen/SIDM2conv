#!/usr/bin/env python3
"""Investigate where entry stubs should come from"""

from pathlib import Path
from sidm2.sf2_packer import SF2Packer
import struct

sf2_path = Path("output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2")

print("="*80)
print("ENTRY STUB INVESTIGATION")
print("="*80)

# Load SF2
with open(sf2_path, 'rb') as f:
    sf2_data = f.read()

load_addr = struct.unpack('<H', sf2_data[0:2])[0]
print(f"\nSF2 Load address: ${load_addr:04X}")

# What's at the start of the SF2 data (after load address)?
first_bytes = sf2_data[2:20]
print(f"First bytes in SF2 (offset +2): {' '.join(f'{b:02x}' for b in first_bytes)}")

# Now check the packer's memory after loading
packer = SF2Packer(sf2_path)
print(f"\nMemory after loading into packer:")
print(f"  At load address ${load_addr:04X}: {' '.join(f'{packer.memory[load_addr+i]:02x}' for i in range(16))}")
print(f"  At $1000: {' '.join(f'{packer.memory[0x1000+i]:02x}' for i in range(16))}")

# The Broware SF2 is a Laxity driver export, so it's loaded at 0x0D7E
# The original driver code is at 0x1000 in the SF2 memory layout
print(f"\nKey insight:")
print(f"  SF2 file contains Laxity driver starting at ${load_addr:04X}")
print(f"  Driver code is located AT ${load_addr:04X} in the SF2 file, NOT at $1000")
print(f"  When we pack, we need to move this to $1000")
print(f"  The entry stubs should be CREATED at $1000, not extracted from the data")

# Check if the packer ever creates entry stubs
print(f"\n" + "="*80)
print(f"Where do entry stubs come from in the pack() method?")
print(f"="*80)

# Look at the pack() method - does it create stubs?
# Let me trace what should happen during packing

print(f"\nExpected packing flow:")
print(f"  1. Load SF2 file (currently at ${load_addr:04X})")
print(f"  2. Extract driver code, tables, data")
print(f"  3. Compute destination addresses for all sections")
print(f"  4. Apply relocation to pointer references")
print(f"  5. CREATE entry stubs at offsets 0 and 3 pointing to init/play routines")
print(f"  6. Write all relocated data to output")
print(f"  7. Patch entry stub JMP targets")

print(f"\nCritical question:")
print(f"  WHERE in the code are entry stubs CREATED?")
print(f"  Are they created at all, or are they extracted from the driver?")
