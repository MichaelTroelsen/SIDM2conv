"""Verify SF2 editor-area edits propagate to playback via zig64 trace.

Method:
  1. Trace unedited SF2 with zig64 -> baseline register writes
  2. Patch the SF2 file at the specified byte offset
  3. Trace patched SF2 with zig64 -> compare register writes
  4. PASS if at least min_diffs (frame, register, value) tuples differ

Usage:
  py -3 pyscript/verify_edit_propagates.py <file.sf2> <patch_offset> <new_val> <expected_min_diffs>

Example:
  # Patch SF2 wave row 0 col 0 ($21 -> $11) and expect at least 30 register-write divergences:
  py -3 pyscript/verify_edit_propagates.py bin/Stinsen.sf2 0x2CA5 0x11 30
"""
import shutil, struct, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACER = ROOT / "tools" / "sidm2-sid-trace.exe"


def trace(sf2: Path, frames: int = 60) -> list[tuple]:
    rc = subprocess.run(
        [str(TRACER), str(sf2), str(frames)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    rows = []
    in_csv = False
    for line in rc.stderr.splitlines():
        if line.startswith("frame,cycle,register,"):
            in_csv = True
            continue
        if not in_csv or line.startswith("---") or not line.strip():
            continue
        parts = line.split(",")
        if len(parts) >= 5:
            rows.append((parts[0], parts[2], parts[3], parts[4]))  # drop cycle
    return rows


def main(argv):
    if len(argv) < 4:
        print(__doc__); sys.exit(2)
    sf2_orig = Path(argv[0])
    offset = int(argv[1], 0)
    new_val = int(argv[2], 0)
    min_diffs = int(argv[3])

    data = sf2_orig.read_bytes()
    old_val = data[offset]
    if old_val == new_val:
        new_val = (old_val ^ 0xA0) & 0xFF  # pick a different value
        print(f"Note: old_val == new_val; using {new_val:#04x} instead")

    base_rows = trace(sf2_orig)

    patched = bytearray(data)
    patched[offset] = new_val
    with tempfile.NamedTemporaryFile(suffix=".sf2", delete=False) as f:
        f.write(patched)
        patched_path = Path(f.name)
    try:
        patched_rows = trace(patched_path)
        diffs = 0
        n = min(len(base_rows), len(patched_rows))
        for i in range(n):
            if base_rows[i] != patched_rows[i]:
                diffs += 1
        diffs += abs(len(base_rows) - len(patched_rows))

        print(f"Baseline: {len(base_rows)} writes")
        print(f"Patched:  {len(patched_rows)} writes (offset 0x{offset:X} {old_val:#04x}->{new_val:#04x})")
        print(f"Tuple divergences: {diffs} (require >= {min_diffs})")
        if diffs >= min_diffs:
            print("PASS: edit propagates to playback")
            sys.exit(0)
        else:
            print("FAIL: edit does NOT propagate (or insufficient divergence)")
            sys.exit(1)
    finally:
        try: patched_path.unlink()
        except FileNotFoundError: pass


if __name__ == "__main__":
    main(sys.argv[1:])
