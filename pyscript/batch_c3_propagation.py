"""Real C3 edit-propagation verification for F1 (sequences) + F3 (wave).

For each file with F1 and/or F3 *wired* (per the C3 survey CSV), this
actually PATCHES the SF2 edit area and runs zig64 to confirm the edit
changes playback — separating "wired" (routine present) from
"propagates" (player actually reads the patched bytes).

Method per column:
  1. Convert SID -> SF2, parse "SF2 edit area: ... Seq=$X ... Wave=$Y"
  2. zig64 baseline trace (60 frames, cycle-stripped tuples)
  3. For several candidate rows (row 0 can be a silent no-op — Unboxed
     proved this), patch one byte to a marker, retrace, count tuple
     divergences. Take the MAX across candidate rows.
  4. PASS if max divergences >= THRESHOLD.

Usage:
  py -3 pyscript/batch_c3_propagation.py [c3_csv] [out_csv] [limit]

Defaults: bin/_laxity_c3.csv -> bin/_laxity_c3_prop.csv, all files.
"""
import csv, re, struct, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONV = ROOT / "scripts" / "sid_to_sf2.py"
TRACER = ROOT / "tools" / "sidm2-sid-trace.exe"
LOAD_BASE = 0x0D7E
FRAMES = 60
THRESHOLD = 5

EDIT_RE = re.compile(
    r"SF2 edit area:.*?Seq=\$([0-9A-Fa-f]{4}).*?Wave=\$([0-9A-Fa-f]{4})")


def trace(prg: Path):
    r = subprocess.run([str(TRACER), str(prg), str(FRAMES)],
                        capture_output=True, text=True, cwd=str(ROOT))
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


def max_divergence(sf2_path: Path, base_rows, offsets):
    """Patch each offset (one at a time) to a marker; return max tuple
    divergence vs baseline across all candidate offsets."""
    data = sf2_path.read_bytes()
    best = 0
    for off in offsets:
        if off >= len(data):
            continue
        old = data[off]
        new = (old ^ 0xA5) & 0xFF
        if new == old:
            new = (old ^ 0x5A) & 0xFF
        patched = bytearray(data)
        patched[off] = new
        with tempfile.NamedTemporaryFile(suffix=".sf2", delete=False) as f:
            f.write(patched); pp = Path(f.name)
        try:
            pr = trace(pp)
            n = min(len(base_rows), len(pr))
            d = sum(1 for i in range(n) if base_rows[i] != pr[i])
            d += abs(len(base_rows) - len(pr))
            best = max(best, d)
        finally:
            try: pp.unlink()
            except FileNotFoundError: pass
        if best >= THRESHOLD:
            break  # already a clear PASS, no need to test more rows
    return best


def main(argv):
    c3_csv = Path(argv[0]) if argv else ROOT / "bin" / "_laxity_c3.csv"
    out_csv = Path(argv[1]) if len(argv) > 1 else ROOT / "bin" / "_laxity_c3_prop.csv"
    limit = int(argv[2]) if len(argv) > 2 else 0

    survey = list(csv.reader(open(c3_csv)))[1:]
    todo = [r for r in survey if r[1] == "OK" and (r[2] == "wired" or r[4] == "Y")]
    if limit:
        todo = todo[:limit]

    sid_dir = ROOT / "SID" / "Laxity"
    results = []
    nf1w = nf1p = nf3w = nf3p = 0
    for i, r in enumerate(todo, 1):
        name = r[0]
        f1_wired = r[2] == "wired"
        f3_wired = r[4] == "Y"
        sid = sid_dir / f"{name}.sid"
        sf2 = ROOT / "bin" / f"_p_{name[:38]}.sf2"
        for p in (sf2, sf2.with_suffix(".txt")):
            try: p.unlink()
            except FileNotFoundError: pass
        rc = subprocess.run([sys.executable, str(CONV), str(sid), str(sf2)],
                            capture_output=True, text=True, cwd=str(ROOT))
        log = rc.stderr + rc.stdout
        m = EDIT_RE.search(log)
        if rc.returncode != 0 or not sf2.exists() or not m:
            results.append((name, f1_wired, "?", f3_wired, "?"))
            print(f"[{i}/{len(todo)}] {name}: NO_EDIT_AREA", flush=True)
            continue
        seq_addr = int(m.group(1), 16)
        wave_addr = int(m.group(2), 16)
        base = trace(sf2)

        f1_res = ""
        if f1_wired:
            nf1w += 1
            # Seq rows: first pattern body bytes — try offsets 0..6
            base_off = seq_addr - LOAD_BASE + 2
            offs = [base_off + k for k in (0, 1, 2, 3, 4, 6, 8)]
            d = max_divergence(sf2, base, offs)
            f1_res = "PASS" if d >= THRESHOLD else f"FAIL({d})"
            if d >= THRESHOLD:
                nf1p += 1

        f3_res = ""
        if f3_wired:
            nf3w += 1
            base_off = wave_addr - LOAD_BASE + 2
            # Wave rows are 2B; col 0 at row r = base + r*2. Try rows 0..6.
            offs = [base_off + r * 2 for r in (0, 1, 2, 3, 5, 8, 12)]
            d = max_divergence(sf2, base, offs)
            f3_res = "PASS" if d >= THRESHOLD else f"FAIL({d})"
            if d >= THRESHOLD:
                nf3p += 1

        results.append((name, f1_wired, f1_res, f3_wired, f3_res))
        print(f"[{i}/{len(todo)}] {name}: F1={f1_res or '-'} F3={f3_res or '-'}",
              flush=True)
        try: sf2.unlink()
        except FileNotFoundError: pass

    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "F1_wired", "F1_propagates", "F3_wired", "F3_propagates"])
        w.writerows(results)

    print("\n========== REAL PROPAGATION AGGREGATE ==========")
    print(f"Files tested:           {len(todo)}")
    print(f"F1 wired:               {nf1w}")
    print(f"F1 PROPAGATES (verified):{nf1p}/{nf1w}" if nf1w else "F1 wired: 0")
    print(f"F3 wired:               {nf3w}")
    print(f"F3 PROPAGATES (verified):{nf3p}/{nf3w}" if nf3w else "F3 wired: 0")
    print(f"CSV: {out_csv}")


if __name__ == "__main__":
    main(sys.argv[1:])
