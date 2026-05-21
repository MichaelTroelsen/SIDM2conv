"""Batch C2 (audio match vs original SID) + C4 (round-trip audio+metadata)
across a directory of SID files. No GUI — pure zig64 + file parsing, fast.

For each SID:
  1. Convert SID -> SF2 (skip on convert failure)
  2. C2: zig64-trace SID + SF2, compare (frame,register,value) ignoring cycle
  3. C4: SF2 -> SID round-trip; re-trace; compare metadata bytes
  Writes a CSV summary + prints aggregate totals.

Usage:  py -3 pyscript/batch_c2_c4.py <sid_dir> [limit] [out_csv]
"""
import csv, struct, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONV = ROOT / "scripts" / "sid_to_sf2.py"
RTRIP = ROOT / "scripts" / "sf2_to_sid.py"
TRACER = ROOT / "tools" / "sidm2-sid-trace.exe"
FRAMES = 300


def psid(sid: Path):
    d = sid.read_bytes()
    if d[:4] not in (b"PSID", b"RSID"):
        return None
    do = struct.unpack(">H", d[6:8])[0]
    la = struct.unpack(">H", d[8:10])[0]
    ia = struct.unpack(">H", d[10:12])[0]
    pa = struct.unpack(">H", d[12:14])[0]
    c = d[do:]
    if la == 0:
        la = struct.unpack("<H", c[:2])[0]; c = c[2:]
    if ia == 0: ia = la
    if pa == 0: pa = ia + 3
    return la, ia, pa, c


def meta(p: Path):
    d = p.read_bytes()
    return (d[0x16:0x36].split(b"\x00")[0],
            d[0x36:0x56].split(b"\x00")[0],
            d[0x56:0x76].split(b"\x00")[0])


def trace(prg: Path, frames, ia=None, pa=None):
    args = [str(TRACER), str(prg), str(frames)]
    if ia is not None: args.append(f"{ia:04x}")
    if pa is not None: args.append(f"{pa:04x}")
    r = subprocess.run(args, capture_output=True, text=True, cwd=str(ROOT))
    rows, incsv = [], False
    for ln in r.stderr.splitlines():
        if ln.startswith("frame,cycle,register,"):
            incsv = True; continue
        if not incsv or ln.startswith("---") or not ln.strip():
            continue
        p = ln.split(",")
        if len(p) >= 5:
            rows.append((p[0], p[2], p[3], p[4]))
    return rows


def sf2_block2_entries(sf2: Path):
    """Parse Block 2 DriverCommon and return (init_addr, update_addr).
    Falls back to (None, None) → caller uses zig64 default. The SF2 PRG
    layout: file[0:2]=TopAddr LE, magic at TopAddr+2 (file off 2), block
    chain starts at TopAddr+2 (file off 4): [id:1][size:1][body]. Block
    id=2 body = [InitAddress:2][StopAddress:2][UpdateAddress:2]...
    Needed for low-load SF2 layouts where $1000 isn't INIT (binary lives
    elsewhere); without this the SF2-trace falsely fails."""
    try:
        d = sf2.read_bytes()
        o = 4
        while o + 2 <= len(d):
            bid = d[o]
            if bid == 0xFF:
                break
            bsz = d[o + 1]
            body = d[o + 2:o + 2 + bsz]
            if bid == 2 and len(body) >= 6:
                return (body[0] | (body[1] << 8),
                        body[4] | (body[5] << 8))
            o += 2 + bsz
    except Exception:
        pass
    return (None, None)


def main(argv):
    sid_dir = Path(argv[0]) if argv else ROOT / "SID" / "Laxity"
    limit = int(argv[1]) if len(argv) > 1 else 0
    out_csv = Path(argv[2]) if len(argv) > 2 else ROOT / "bin" / "_laxity_c2_c4.csv"

    sids = sorted(sid_dir.glob("*.sid"))
    if limit:
        sids = sids[:limit]

    results = []
    n_conv_fail = n_c2_pass = n_c4_audio = n_c4_meta = 0
    for i, sid in enumerate(sids, 1):
        name = sid.stem
        sf2 = ROOT / "bin" / f"_lx_{name[:40]}.sf2"
        for p in (sf2, sf2.with_suffix(".txt")):
            try: p.unlink()
            except FileNotFoundError: pass
        rc = subprocess.run([sys.executable, str(CONV), str(sid), str(sf2), "-q"],
                             capture_output=True, text=True, cwd=str(ROOT))
        if rc.returncode != 0 or not sf2.exists():
            results.append((name, "CONV_FAIL", "", "", ""))
            n_conv_fail += 1
            print(f"[{i}/{len(sids)}] {name}: CONV_FAIL", flush=True)
            continue

        info = psid(sid)
        c2 = "?"
        if info:
            la, ia, pa, c64 = info
            with tempfile.NamedTemporaryFile(suffix=".prg", delete=False) as f:
                f.write(struct.pack("<H", la)); f.write(c64)
                sidprg = Path(f.name)
            try:
                sid_rows = trace(sidprg, FRAMES, ia, pa)
                # Trace SF2 via its declared Block 2 init/play (low-load
                # files have $1000 in the gap, not the trampoline).
                si, sp = sf2_block2_entries(sf2)
                sf2_rows = trace(sf2, FRAMES, si, sp)
                c2 = "PASS" if sid_rows == sf2_rows else f"DIFF({len(sid_rows)}v{len(sf2_rows)})"
            finally:
                try: sidprg.unlink()
                except FileNotFoundError: pass
        if c2 == "PASS": n_c2_pass += 1

        # C4 round-trip
        rt = ROOT / "bin" / f"_lx_{name[:40]}_rt.sid"
        try: rt.unlink()
        except FileNotFoundError: pass
        rc2 = subprocess.run([sys.executable, str(RTRIP), str(sf2), str(rt), "-q"],
                             capture_output=True, text=True, cwd=str(ROOT))
        c4a = c4m = "?"
        if rc2.returncode == 0 and rt.exists():
            # The round-trip SID is a PSID file (load=$0D7E, init/play in
            # the SF2 wrapper). zig64 needs a PRG + explicit init/play —
            # extract the embedded binary like the original-SID path.
            rt_info = psid(rt)
            if rt_info:
                rla, ria, rpa, rc64 = rt_info
                with tempfile.NamedTemporaryFile(suffix=".prg", delete=False) as f:
                    f.write(struct.pack("<H", rla)); f.write(rc64)
                    rtprg = Path(f.name)
                try:
                    rt_rows = trace(rtprg, FRAMES, ria, rpa)
                finally:
                    try: rtprg.unlink()
                    except FileNotFoundError: pass
            else:
                rt_rows = trace(rt, FRAMES)
            si, sp = sf2_block2_entries(sf2)
            sf2_rows2 = trace(sf2, FRAMES, si, sp)
            c4a = "PASS" if rt_rows == sf2_rows2 else f"DIFF({len(rt_rows)}v{len(sf2_rows2)})"
            try:
                c4m = "PASS" if meta(sid) == meta(rt) else "DIFFER"
            except Exception:
                c4m = "ERR"
        if c4a == "PASS": n_c4_audio += 1
        if c4m == "PASS": n_c4_meta += 1
        results.append((name, "OK", c2, c4a, c4m))
        print(f"[{i}/{len(sids)}] {name}: C2={c2} C4audio={c4a} C4meta={c4m}", flush=True)

    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "convert", "C2_audio", "C4_audio", "C4_meta"])
        w.writerows(results)

    n = len(sids)
    print("\n========== AGGREGATE ==========")
    print(f"Total files:        {n}")
    print(f"Convert failures:   {n_conv_fail}")
    print(f"C2 audio PASS:      {n_c2_pass}/{n}  ({100*n_c2_pass/n:.0f}%)")
    print(f"C4 audio PASS:      {n_c4_audio}/{n}  ({100*n_c4_audio/n:.0f}%)")
    print(f"C4 metadata PASS:   {n_c4_meta}/{n}  ({100*n_c4_meta/n:.0f}%)")
    print(f"CSV: {out_csv}")


if __name__ == "__main__":
    main(sys.argv[1:])
