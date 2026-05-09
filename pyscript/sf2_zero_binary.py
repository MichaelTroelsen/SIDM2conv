"""Zero out the c64_data region of an Action_Biker-style SF2 to test if
the deterministic crash is in the binary content vs the SF2 metadata.

Action_Biker layout (per writer log):
    Magic+headers: $0D7E-$0F8A   (525 bytes)
    Handlers     : $0F90 (12B)
    Binary       : $C000-$CBC1   (3010 bytes)
    Edit area    : $CBC2-$D??    (~1638 bytes)
    Aux          : $D???-end     (~430 bytes)

File offset for binary = ($C000 - $0D7E) + 2 = $B284.
"""
import sys, shutil
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
shutil.copy(src, dst)
buf = bytearray(dst.read_bytes())

# Read load addr (LE u16 at file start)
load = buf[0] | (buf[1] << 8)
# Find the binary region by scanning for non-zero past handler block.
# Handler @ HANDLER_BASE is JSR (3B) + RTS (1B) ×3 = 12 bytes max at $0F90.
# After the handlers, until the binary, we expect ZEROS (gap padding).
# So find the first non-zero byte after offset ~($0FA0 - load + 2).
# Skip past trampoline+aux-pointer at $0FFB-$1005 by jumping to a safe high point.
# We're looking for the player binary at $C000 specifically.
TARGET_C64 = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0xC000
bin_start_off = (TARGET_C64 - load) + 2

# Determine binary length: PSID load addr is bin_start_off - 2 + load
bin_addr = bin_start_off - 2 + load
print(f'binary detected at file off ${bin_start_off:04X}, c64 addr ${bin_addr:04X}')

# Zero out 3010 bytes (Action_Biker's known size)
n_zero = int(sys.argv[3]) if len(sys.argv) > 3 else 3010
for i in range(bin_start_off, bin_start_off + n_zero):
    buf[i] = 0
print(f'zeroed {n_zero} bytes from ${bin_start_off:04X}')

dst.write_bytes(buf)
print(f'wrote {dst} ({len(buf)} bytes)')
