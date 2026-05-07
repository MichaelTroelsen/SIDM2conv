"""Reverse-engineer Laxity's pattern split heuristic for Stage 1.

Goal: figure out what rule Laxity used to split his voice's playback stream
into the ~40 distinct orderlist entries / ~128 patterns we see in the
original Stinsen SF2. Once we know the rule, Stage 1's NP21 splitter can
replicate it.

Comparison setup:
  Original SF2  : Original_SF2/Laxity/Laxity - Stinsen - Last Night Of 89.sf2
  Our extracted : NP21 voice 0 byte stream from SID/Stinsens_Last_Night_of_89.sid
                  ch_seq_ptr at $1A1C/$1A1F (Laxity NP21 layout)

The original SF2 EMBEDS the same NP21 binary at $1000+, so its orderlists
are Laxity's hand-edited version while the NP21 player code is unchanged.
That means:
  1. Both files have the same NP21 voice byte stream (it's a literal
     embedding of the SID file's player binary).
  2. The original SF2's editor view is Laxity's PRE-COMPILE source — what
     he typed into SF2II's editor before "Build" turned it into NP21 bytes.
  3. The orderlist+patterns in the original SF2 are the SOURCE; the NP21
     stream is the COMPILED OUTPUT.

So the reverse-engineering is: given the SOURCE (orderlist + patterns) and
the OUTPUT (NP21 stream), find the compile rule. Or: given just the OUTPUT,
find a split rule that PRODUCES a similar source.

Outputs (printed):
  - First 6 patterns of the original SF2 (their SF2-packed bytes)
  - First 30 bytes of voice-0 NP21 stream we extract
  - Sequence-byte comparison aligned by playback time
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def parse_sf2_block5(sf2_bytes: bytes) -> dict:
    prg = struct.unpack("<H", sf2_bytes[0:2])[0]
    i = 4
    while i < len(sf2_bytes):
        bid = sf2_bytes[i]
        if bid == 0xFF:
            break
        blen = sf2_bytes[i + 1]
        if bid == 0x05:
            body = sf2_bytes[i + 2 : i + 2 + blen]
            return {
                "prg_load": prg,
                "track_count": body[0],
                "ol_lo_addr": body[1] | (body[2] << 8),
                "ol_hi_addr": body[3] | (body[4] << 8),
                "seq_count": body[5],
                "seq_lo_addr": body[6] | (body[7] << 8),
                "seq_hi_addr": body[8] | (body[9] << 8),
                "ol_size": body[10] | (body[11] << 8),
                "ol_track1_addr": body[12] | (body[13] << 8),
                "seq_size": body[14] | (body[15] << 8),
                "seq00_addr": body[16] | (body[17] << 8),
            }
        i += 2 + blen
    raise ValueError("no Block 5 found")


def at(buf: bytes, prg: int, c64_addr: int, n: int) -> bytes:
    return buf[c64_addr - prg + 2 : c64_addr - prg + 2 + n]


def decode_ol(buf: bytes, prg: int, ol_addr: int, max_len: int = 256) -> list:
    """Return list of (kind, value) tuples until 0xFF terminator."""
    out = []
    raw = at(buf, prg, ol_addr, max_len)
    for b in raw:
        if b == 0xFF:
            out.append(("end", b))
            break
        elif b >= 0xA0 and b <= 0xBF:
            out.append(("transpose", b - 0xA0))  # 0..0x1F transpose, signed?
        else:
            out.append(("pattern", b))
    return out


def trim_seq(seq_bytes: bytes) -> bytes:
    """Trim to first 0x7F end marker."""
    end = seq_bytes.find(b"\x7f")
    return seq_bytes[: end if end >= 0 else len(seq_bytes)]


def main() -> None:
    ref_path = ROOT / "Original_SF2" / "Laxity" / "Laxity - Stinsen - Last Night Of 89.sf2"
    sid_path = ROOT / "SID" / "Stinsens_Last_Night_of_89.sid"

    ref = ref_path.read_bytes()
    sid = sid_path.read_bytes()

    # Parse PSID -> raw c64 binary
    psid_hdr = struct.unpack(">H", sid[6:8])[0]
    c64 = sid[psid_hdr + 2 :]
    sid_la = 0x1000  # NP21 always loads at $1000

    # 1) Original SF2 layout
    blk5 = parse_sf2_block5(ref)
    print("=== Original Stinsen SF2 (Laxity-authored) ===")
    print(f"  Block 5: tracks={blk5['track_count']}, seq_count={blk5['seq_count']},"
          f" seq_size={blk5['seq_size']}")
    print(f"  ol_track1_addr=${blk5['ol_track1_addr']:04X}, seq00_addr=${blk5['seq00_addr']:04X}")

    # 2) Voice 0 orderlist (decoded)
    v0_ol_lo = at(ref, blk5["prg_load"], blk5["ol_lo_addr"], 1)[0]
    v0_ol_hi = at(ref, blk5["prg_load"], blk5["ol_hi_addr"], 1)[0]
    v0_ol_addr = (v0_ol_hi << 8) | v0_ol_lo
    print(f"\n  Voice 0 OL @ ${v0_ol_addr:04X}:")
    ol = decode_ol(ref, blk5["prg_load"], v0_ol_addr)
    pat_indices = [b for k, b in ol if k == "pattern"]
    print(f"    decoded ({len(ol)} entries, {len(pat_indices)} pattern refs):")
    line = []
    for kind, val in ol:
        if kind == "transpose":
            line.append(f"[T+{val}]")
        elif kind == "pattern":
            line.append(f"{val:02X}")
        else:
            line.append("END")
    print(f"    {' '.join(line)}")

    # 3) Distinct patterns referenced
    distinct = []
    for p in pat_indices:
        if p not in distinct:
            distinct.append(p)
    print(f"\n  Distinct patterns played by voice 0: {len(distinct)} -> {[f'{p:02X}' for p in distinct]}")

    # 4) Dump first few pattern bodies (trimmed to end-of-seq)
    print(f"\n  First 6 distinct patterns (trimmed):")
    for p in distinct[:6]:
        seq_lo = at(ref, blk5["prg_load"], blk5["seq_lo_addr"] + p, 1)[0]
        seq_hi = at(ref, blk5["prg_load"], blk5["seq_hi_addr"] + p, 1)[0]
        seq_addr = (seq_hi << 8) | seq_lo
        body = trim_seq(at(ref, blk5["prg_load"], seq_addr, blk5["seq_size"]))
        print(f"    pat {p:02X} @ ${seq_addr:04X} ({len(body)}B): {body.hex(' ')}")

    # 5) Our raw NP21 voice 0 stream (from ch_seq_ptr)
    CH_SEQ_LO = 0x0A1C
    CH_SEQ_HI = 0x0A1F
    v0_lo = c64[CH_SEQ_LO]
    v0_hi = c64[CH_SEQ_HI]
    v0_addr = (v0_hi << 8) | v0_lo
    print(f"\n=== Our NP21 voice 0 raw stream ===")
    print(f"  ch_seq_ptr -> ${v0_addr:04X}")
    raw = bytearray()
    j = 0
    addr = v0_addr - sid_la
    while addr + j < len(c64):
        b = c64[addr + j]
        if b == 0xFF:
            print(f"  loop marker 0xFF at offset {j}, target=${c64[addr+j+1]:02X}")
            break
        if b == 0x7F:
            print(f"  end marker 0x7F at offset {j}")
            break
        raw.append(b)
        j += 1
    print(f"  body length: {len(raw)}B")
    print(f"  first 64 bytes: {bytes(raw[:64]).hex(' ')}")
    print(f"  last 32 bytes:  {bytes(raw[-32:]).hex(' ')}")

    # 6) Sanity check: do any 4-byte windows of our NP21 stream match
    #    bytes from the original SF2's patterns? If yes, we've found
    #    direct alignment and can split there.
    print(f"\n=== Cross-search: NP21 4-byte windows seen in original SF2 patterns ===")
    pat_bodies = []
    for p in distinct:
        seq_lo = at(ref, blk5["prg_load"], blk5["seq_lo_addr"] + p, 1)[0]
        seq_hi = at(ref, blk5["prg_load"], blk5["seq_hi_addr"] + p, 1)[0]
        seq_addr = (seq_hi << 8) | seq_lo
        body = trim_seq(at(ref, blk5["prg_load"], seq_addr, blk5["seq_size"]))
        pat_bodies.append((p, bytes(body)))

    matches = 0
    sample_matches = []
    for off in range(0, max(0, len(raw) - 4)):
        win = bytes(raw[off : off + 4])
        for p, body in pat_bodies:
            if win in body:
                matches += 1
                if len(sample_matches) < 8:
                    sample_matches.append((off, p, win))
                break
    print(f"  4-byte windows in NP21 stream that appear in any SF2 pattern: {matches}/{max(0,len(raw)-4)}")
    print(f"  sample matches (NP21 offset, SF2 pattern, bytes):")
    for off, p, win in sample_matches:
        print(f"    NP21+{off:3d} -> pat {p:02X} : {win.hex(' ')}")


if __name__ == "__main__":
    main()
