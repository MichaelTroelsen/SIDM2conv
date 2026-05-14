"""Verify SF2 embeds the original SID's NP21 binary verbatim at $1000.

This is the architectural guarantee for criterion 2 (playback accuracy):
- v3.1.5 introduced raw-NP21 embedding for all Laxity songs
- zig64 dispatches INIT/PLAY through trampoline -> JMP play_addr
- so SF2 register writes == SID register writes (modulo wrapper cycle drift)

Usage:  py -3 pyscript/verify_np21_embed.py <file.sid> <file.sf2>

Exits 0 if embedded NP21 matches the SID binary, non-zero otherwise.
"""
import struct, sys
from pathlib import Path


def extract_sid_binary(sid_path: Path) -> tuple[int, bytes]:
    """Return (load_address, c64_binary_bytes)."""
    data = sid_path.read_bytes()
    if data[:4] not in (b"PSID", b"RSID"):
        raise ValueError(f"Not a PSID/RSID file: {sid_path}")
    data_offset = struct.unpack(">H", data[6:8])[0]
    load_address = struct.unpack(">H", data[8:10])[0]
    c64_data = data[data_offset:]
    if load_address == 0:
        # Load address is the first 2 bytes (little-endian) of c64_data
        load_address = struct.unpack("<H", c64_data[:2])[0]
        c64_binary = c64_data[2:]
    else:
        c64_binary = c64_data
    return load_address, c64_binary


def extract_sf2_at_load(sf2_path: Path, load_address: int, length: int) -> bytes:
    """Read SF2 file as PRG-like (first 2 bytes = load addr) and extract
    the byte window starting at `load_address` for `length` bytes."""
    data = sf2_path.read_bytes()
    sf2_load = struct.unpack("<H", data[:2])[0]
    body = data[2:]
    # Build a sparse 64K map: body starts at sf2_load
    offset = load_address - sf2_load
    if offset < 0 or offset + length > len(body):
        raise ValueError(
            f"NP21 window [${load_address:04X}..${load_address+length:04X}] "
            f"not contained in SF2 body (sf2_load=${sf2_load:04X}, len=${len(body):X})"
        )
    return body[offset:offset + length]


def main(argv):
    if len(argv) < 2:
        print(__doc__); sys.exit(2)
    sid_path = Path(argv[0])
    sf2_path = Path(argv[1])

    sid_load, sid_bin = extract_sid_binary(sid_path)
    print(f"SID: load=${sid_load:04X}, binary={len(sid_bin)} bytes")

    sf2_window = extract_sf2_at_load(sf2_path, sid_load, len(sid_bin))
    print(f"SF2 window at ${sid_load:04X}: {len(sf2_window)} bytes")

    if sf2_window == sid_bin:
        print(f"PASS: SF2 embeds original SID binary verbatim at ${sid_load:04X}")
        sys.exit(0)

    # Find first diff and count differences
    diffs = []
    for i, (a, b) in enumerate(zip(sid_bin, sf2_window)):
        if a != b:
            diffs.append((i, a, b))
            if len(diffs) > 20:
                break
    print(f"FAIL: {sum(1 for a, b in zip(sid_bin, sf2_window) if a != b)} byte differences")
    print(f"  First 20 diffs (offset = absolute - ${sid_load:04X}):")
    for off, a, b in diffs[:20]:
        print(f"    +${off:04X} (=${sid_load+off:04X}): SID=${a:02X}  SF2=${b:02X}")
    sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
