"""Stage-6 regression skeleton — guards audio fidelity for Stinsen + Unboxed.

For each golden SID file we:
  1. Re-convert SID -> SF2 with current code
  2. Run zig64 cycle-accurate tracer on the resulting SF2 for N=300 frames
  3. Diff the SID-write CSV against the baseline saved in tests/golden/

Any divergence in SID register writes (frame, cycle, register, value) means
playback has changed — fail the test loud and immediately.

This is the safety net required by the v3.3.0+ ultraplan: every Stage 1+
change (pattern splitting, prefix correctness, Block 9 work) MUST keep this
test green or the change reverts.

Re-baselining (only when an intentional change is the cause):
  py -3 tests/test_corpus_regression.py --rebaseline
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACER = ROOT / "tools" / "sidm2-sid-trace.exe"
CONVERTER = ROOT / "scripts" / "sid_to_sf2.py"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

CORPUS = [
    ("Stinsens_Last_Night_of_89", "laxity", 1909),  # acceptance frame count
    ("Unboxed_Ending_8580",       "laxity", 2733),
]
TRACE_FRAMES = 300  # capture window for diff (covers song intros)


def convert(sid: Path, sf2: Path, driver: str) -> None:
    rc = subprocess.run(
        [sys.executable, str(CONVERTER), str(sid), str(sf2), "--driver", driver],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if rc.returncode != 0:
        raise RuntimeError(f"Conversion failed for {sid.name}: {rc.stderr}")


def trace(sf2: Path, frames: int) -> str:
    """Return zig64 stderr (the CSV trace)."""
    rc = subprocess.run(
        [str(TRACER), str(sf2), str(frames)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return rc.stderr


def csv_writes(trace_text: str) -> list[str]:
    """Return only the SID-write rows (drop the header banner + comment lines)."""
    rows = []
    in_csv = False
    for line in trace_text.splitlines():
        if line.startswith("frame,cycle,register,"):
            in_csv = True
            rows.append(line)
            continue
        if not in_csv:
            continue
        if line.startswith("---"):  # frame separator comment
            continue
        if line.strip():
            rows.append(line)
    return rows


def diff_traces(actual_text: str, baseline_text: str, name: str) -> tuple[bool, str]:
    actual = csv_writes(actual_text)
    baseline = csv_writes(baseline_text)
    if actual == baseline:
        return True, f"{name}: PASS ({len(actual)} write rows match baseline)"
    # Find first divergence
    n = min(len(actual), len(baseline))
    first_diff = None
    for i in range(n):
        if actual[i] != baseline[i]:
            first_diff = i
            break
    if first_diff is None:
        first_diff = n
    msg = (
        f"{name}: FAIL — actual={len(actual)} rows, baseline={len(baseline)} rows.\n"
        f"  First divergence at row {first_diff}:\n"
        f"    expected: {baseline[first_diff] if first_diff < len(baseline) else '<EOF>'}\n"
        f"    actual:   {actual[first_diff] if first_diff < len(actual) else '<EOF>'}"
    )
    return False, msg


def run_one(name: str, driver: str, frame_target: int, rebaseline: bool) -> bool:
    sid = ROOT / "SID" / f"{name}.sid"
    sf2 = ROOT / "SF2" / f"{name}.sf2"
    golden = GOLDEN_DIR / f"{name}.trace.csv"

    if not sid.exists():
        print(f"{name}: SKIP (no SID file at {sid})")
        return True

    convert(sid, sf2, driver)
    trace_text = trace(sf2, TRACE_FRAMES)

    if rebaseline:
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(trace_text)
        print(f"{name}: REBASELINED -> {golden}")
        return True

    if not golden.exists():
        print(f"{name}: ERROR — no baseline at {golden}; run with --rebaseline first")
        return False

    baseline_text = golden.read_text()
    ok, msg = diff_traces(trace_text, baseline_text, name)
    print(msg)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebaseline", action="store_true",
                    help="Capture current trace as the new baseline (DANGEROUS)")
    args = ap.parse_args()

    if not TRACER.exists():
        print(f"ERROR: zig64 tracer not found at {TRACER}")
        return 2

    all_ok = True
    for name, driver, frame_target in CORPUS:
        ok = run_one(name, driver, frame_target, args.rebaseline)
        all_ok &= ok

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
