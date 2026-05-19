"""Verify SF2 register-write sequence matches the original SID exactly.

Method: trace both binaries with zig64 (cycle-accurate emulator), then
compare (frame, register, old_val, new_val) tuples ignoring the cycle
column. The cycle column drifts because the SF2 wrapper at $0E00 and
multipat translator at $0F90+ run extra code per PLAY tick — but the
NP21 player at $1000 is byte-identical (modulo 8 documented patches:
trampoline at $1003-1005 + ch_seq_ptr at $1A1C-1A21) so the SEQUENCE
of register writes must match.

Usage:  py -3 pyscript/verify_audio_match.py <file.sid> <file.sf2> [frames=300]

Exits 0 if every (frame, register, value) tuple matches; non-zero on
divergence with first-diff context.
"""
import struct, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACER = ROOT / "tools" / "sidm2-sid-trace.exe"


def parse_psid(sid_path: Path):
    """Return (load_addr, init_addr, play_addr, c64_binary_bytes)."""
    data = sid_path.read_bytes()
    if data[:4] not in (b"PSID", b"RSID"):
        raise ValueError(f"Not a PSID/RSID file: {sid_path}")
    data_offset = struct.unpack(">H", data[6:8])[0]
    load_addr = struct.unpack(">H", data[8:10])[0]
    init_addr = struct.unpack(">H", data[10:12])[0]
    play_addr = struct.unpack(">H", data[12:14])[0]
    c64_data = data[data_offset:]
    if load_addr == 0:
        load_addr = struct.unpack("<H", c64_data[:2])[0]
        c64_binary = c64_data[2:]
    else:
        c64_binary = c64_data
    if init_addr == 0:
        init_addr = load_addr
    if play_addr == 0:
        # play_addr 0 means INIT installs the play vector itself (CIA IRQ).
        # For Laxity NP21 the convention is INIT+3 = JMP play.
        play_addr = init_addr + 3
    return load_addr, init_addr, play_addr, c64_binary


def trace_prg(prg_path: Path, frames: int, init_addr: int = None, play_addr: int = None) -> str:
    args = [str(TRACER), str(prg_path), str(frames)]
    if init_addr is not None:
        args.append(f"{init_addr:04x}")
    if play_addr is not None:
        args.append(f"{play_addr:04x}")
    rc = subprocess.run(args, capture_output=True, text=True, cwd=str(ROOT))
    return rc.stderr


def csv_rows(trace_text: str) -> list[str]:
    rows = []
    in_csv = False
    for line in trace_text.splitlines():
        if line.startswith("frame,cycle,register,"):
            in_csv = True
            continue  # skip header — we re-emit below
        if not in_csv:
            continue
        if line.startswith("---") or not line.strip():
            continue
        rows.append(line)
    return rows


def strip_cycle(row: str) -> tuple:
    """Drop the cycle column; return (frame, register, old_val, new_val)."""
    parts = row.split(",")
    if len(parts) < 5:
        return tuple(parts)
    return (parts[0], parts[2], parts[3], parts[4])


def main(argv):
    if len(argv) < 2:
        print(__doc__); sys.exit(2)
    sid_path = Path(argv[0])
    sf2_path = Path(argv[1])
    frames = int(argv[2]) if len(argv) > 2 else 300

    # 1. Extract SID -> temporary PRG (load_addr LE + binary)
    load_addr, init_addr, play_addr, c64_bin = parse_psid(sid_path)
    print(f"SID: load=${load_addr:04X} init=${init_addr:04X} play=${play_addr:04X} bin={len(c64_bin)}B")

    with tempfile.NamedTemporaryFile(suffix=".prg", delete=False) as f:
        f.write(struct.pack("<H", load_addr))
        f.write(c64_bin)
        sid_prg = Path(f.name)

    try:
        # 2. Trace original SID as PRG
        sid_trace = trace_prg(sid_prg, frames, init_addr, play_addr)
        sid_rows = csv_rows(sid_trace)
        print(f"SID trace: {len(sid_rows)} register writes over {frames} frames")

        # 3. Trace SF2 via its DECLARED Block 2 init/play (not zig64's
        #    default $1000/$1003). SF2II calls Block 2 DriverCommon
        #    InitAddress/UpdateAddress; low-load layouts (binary < $1000)
        #    put real handlers high, and many players' play != $1003.
        #    Block chain: magic at TopAddr+2 (file off 2), blocks at
        #    TopAddr+2 (file off 4): [id:1][size:1][body]. id=2 body =
        #    [InitAddr:2][StopAddr:2][UpdateAddr:2]...
        s_init = s_play = None
        try:
            sd = sf2_path.read_bytes()
            o = 4  # first block (file offset; PRG load:2 + magic:2)
            while o + 2 <= len(sd):
                bid = sd[o]
                if bid == 0xFF:
                    break
                bsz = sd[o + 1]
                body = sd[o + 2:o + 2 + bsz]
                if bid == 2 and len(body) >= 6:
                    s_init = body[0] | (body[1] << 8)
                    s_play = body[4] | (body[5] << 8)
                    break
                o += 2 + bsz
        except Exception:
            pass
        sf2_trace = trace_prg(sf2_path, frames, s_init, s_play)
        sf2_rows = csv_rows(sf2_trace)
        _via = (f"Block2 init=${s_init:04X} play=${s_play:04X}"
                if s_init is not None else "zig64 default $1000/$1003")
        print(f"SF2 trace: {len(sf2_rows)} register writes over {frames} "
              f"frames (via {_via})")

        # 4. Strip cycle and compare
        sid_strip = [strip_cycle(r) for r in sid_rows]
        sf2_strip = [strip_cycle(r) for r in sf2_rows]

        if sid_strip == sf2_strip:
            print(f"PASS: {len(sid_strip)} (frame, register, value) tuples match exactly")
            sys.exit(0)

        # Find first divergence
        n = min(len(sid_strip), len(sf2_strip))
        first = None
        for i in range(n):
            if sid_strip[i] != sf2_strip[i]:
                first = i
                break
        if first is None:
            first = n

        print(f"FAIL: SID={len(sid_strip)} SF2={len(sf2_strip)} writes; first diff at row {first}")
        for i in range(max(0, first - 2), min(n, first + 3)):
            mark = " <-- DIFF" if i == first else ""
            print(f"  row {i:4d}  SID={sid_strip[i]}  SF2={sf2_strip[i]}{mark}")

        # Count total tuple diffs (capped)
        diff_count = sum(1 for a, b in zip(sid_strip, sf2_strip) if a != b)
        diff_count += abs(len(sid_strip) - len(sf2_strip))
        print(f"Total tuple divergences (cap n=min): {diff_count}")
        sys.exit(1)
    finally:
        try: sid_prg.unlink()
        except FileNotFoundError: pass


if __name__ == "__main__":
    main(sys.argv[1:])
