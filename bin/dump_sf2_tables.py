"""Dump the Instruments + Wave (+ Pulse/Filter) table contents of an .sf2 by
reading the flat load image at each table's declared address. Lets us compare a
known-good Driver 11 reference against our Galway output to see what SF2II
expects in the instrument/wave columns."""
import sys
sys.path.insert(0, ".")
from sidm2.models import SF2DriverInfo
from sidm2 import sf2_parser

path = sys.argv[1]
nrows = int(sys.argv[2]) if len(sys.argv) > 2 else 12
data = open(path, "rb").read()
load = data[0] | (data[1] << 8)
img = bytearray(0x10000)
for i, b in enumerate(data[2:]):
    img[(load + i) & 0xFFFF] = b

di = SF2DriverInfo()
sf2_parser.parse_sf2_blocks(bytearray(data), di)
ta = di.table_addresses
print(f"{path}\n load=${load:04X}")

def col(addr, c, r, rows):
    return img[addr + c * rows + r]

for name in ("Instruments", "Wave", "Pulse", "Filter"):
    if name not in ta:
        continue
    t = ta[name]
    a, cols, rows = t["addr"], t["columns"], t["rows"]
    print(f"\n{name}: addr=${a:04X} cols={cols} rows={rows} (column-major)")
    print("  row | " + " ".join(f"c{c}" for c in range(cols)))
    for r in range(min(nrows, rows)):
        vals = " ".join(f"{col(a, c, r, rows):02X}" for c in range(cols))
        print(f"  {r:3d} | {vals}")
