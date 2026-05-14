"""Batch C3 wave edit-propagation test across multiple SF2 files.

For each file: convert, parse the "Wave=$XXXX" address from the converter
log, find file offset to wave row 0 col 0, patch byte to $A0, trace
zig64 baseline vs patched, count divergences.

Usage:  py -3 pyscript/batch_c3_wave.py file1.sid file2.sid ...
"""
import subprocess, sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONV = ROOT / "scripts" / "sid_to_sf2.py"

# Match the "SF2 edit area: ... Wave=$XXXX" line — this is the EDITABLE
# wave table address in the SF2 edit area (NOT the Block 3 header pointer
# to the binary's NP21 wave table — those have the same Wave= prefix).
EDIT_AREA_WAVE_RE = re.compile(r"SF2 edit area:.*?Wave=\$([0-9A-Fa-f]{4})")
LOAD_BASE = 0x0D7E


def convert_and_get_wave_addr(sid: Path, sf2: Path) -> int | None:
    rc = subprocess.run(
        [sys.executable, str(CONV), str(sid), str(sf2)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    m = EDIT_AREA_WAVE_RE.search(rc.stderr) or EDIT_AREA_WAVE_RE.search(rc.stdout)
    if m:
        return int(m.group(1), 16)
    return None


def main(argv):
    print(f"{'file':<32s} {'wave_addr':>10s} {'file_off':>10s} {'divergences':>12s} {'verdict':>10s}")
    for sid_path_str in argv:
        sid = ROOT / sid_path_str
        if not sid.exists():
            print(f"{sid.name:<32s} MISSING")
            continue
        sf2 = ROOT / "bin" / f"{sid.stem}.sf2"
        wave_addr = convert_and_get_wave_addr(sid, sf2)
        if wave_addr is None:
            print(f"{sid.stem:<32s} {'no Wave addr in log':>50s}")
            continue
        file_off = wave_addr - LOAD_BASE + 2
        # Run verify_edit_propagates with min_diffs=5
        rc = subprocess.run(
            [sys.executable, str(ROOT / "pyscript" / "verify_edit_propagates.py"),
             str(sf2), hex(file_off), "0xA0", "5"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        divs = "?"
        for line in rc.stdout.splitlines():
            if "Tuple divergences:" in line:
                m = re.search(r"Tuple divergences: (\d+)", line)
                if m:
                    divs = m.group(1)
        verdict = "PASS" if "PASS" in rc.stdout.split("\n")[-2] else "FAIL"
        print(f"{sid.stem:<32s} ${wave_addr:>9X} 0x{file_off:>8X} {divs:>12s} {verdict:>10s}")


if __name__ == "__main__":
    main(sys.argv[1:])
