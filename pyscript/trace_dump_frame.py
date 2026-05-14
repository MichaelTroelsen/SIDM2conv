"""Dump all register writes for a specific frame range from a SID or SF2.

Usage:  py -3 pyscript/trace_dump_frame.py <file.sid|file.sf2> <frame_start> <frame_end>
"""
import struct, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACER = ROOT / "tools" / "sidm2-sid-trace.exe"


def parse_psid(sid_path: Path):
    data = sid_path.read_bytes()
    if data[:4] not in (b"PSID", b"RSID"):
        return None
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
        play_addr = init_addr + 3
    return load_addr, init_addr, play_addr, c64_binary


def main(argv):
    f = Path(argv[0])
    fs = int(argv[1])
    fe = int(argv[2])
    frames = max(fe + 5, 30)

    sid_info = parse_psid(f) if f.suffix.lower() == ".sid" else None
    if sid_info:
        load, init_a, play_a, c64 = sid_info
        with tempfile.NamedTemporaryFile(suffix=".prg", delete=False) as t:
            t.write(struct.pack("<H", load))
            t.write(c64)
            prg = Path(t.name)
        args = [str(TRACER), str(prg), str(frames), f"{init_a:04x}", f"{play_a:04x}"]
    else:
        args = [str(TRACER), str(f), str(frames)]

    rc = subprocess.run(args, capture_output=True, text=True, cwd=str(ROOT))
    in_csv = False
    for line in rc.stderr.splitlines():
        if line.startswith("frame,cycle,register,"):
            in_csv = True
            print(line)
            continue
        if not in_csv:
            continue
        if line.startswith("---") or not line.strip():
            continue
        try:
            frame = int(line.split(",")[0])
        except (ValueError, IndexError):
            continue
        if fs <= frame <= fe:
            print(line)
    if sid_info:
        try: prg.unlink()
        except FileNotFoundError: pass


if __name__ == "__main__":
    main(sys.argv[1:])
