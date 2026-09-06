"""Snapshot and verify the native-build corpora around an A/B.

    py -3 corpus_hash.py                       # print the current state
    py -3 corpus_hash.py --save before.json    # snapshot
    py -3 corpus_hash.py --check before.json   # compare, exit 1 on any change

Covers the six artifact directories AND the four shared driver files that every
`bin/build_*_native_song.py` rewrites -- those are reported separately, because
they change on any build (including one with emission stubbed) and are gitignored
build products, whereas a changed ARTIFACT directory means the corpus moved.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

ARTIFACT_DIRS = [
    "out/sdi", "out/mon", "out/dmc", "out/mattgray_native",
    "out/hardtrack_native", "out/fc", "out/soundmonitor", "out/romuzak",
]
SHARED_FILES = [
    "drivers_src/mon/layout.inc",
    "drivers_src/mon/freqtable.inc",
    "drivers_src/romuzak/layout.inc",
    "out/romuzak_driver.prg",
]


def dir_digest(rel: str):
    """(file count, digest of every name+size) -- cheap and change-sensitive."""
    d = ROOT / rel
    if not d.is_dir():
        return None
    total, acc = 0, hashlib.sha256()
    for base, _, files in os.walk(d):
        for f in sorted(files):
            total += 1
            acc.update(f.encode("utf-8", "replace"))
            acc.update(str((Path(base) / f).stat().st_size).encode())
    return [total, acc.hexdigest()[:16]]


def file_digest(rel: str):
    p = ROOT / rel
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def snapshot():
    return {
        "artifacts": {r: dir_digest(r) for r in ARTIFACT_DIRS},
        "shared": {r: file_digest(r) for r in SHARED_FILES},
    }


def show(snap):
    for rel, v in snap["artifacts"].items():
        print("  %-24s %s" % (rel, "absent" if v is None
                              else "%6d files  %s" % (v[0], v[1])))
    print("  -- shared driver state (rewritten by ANY build) --")
    for rel, v in snap["shared"].items():
        print("  %-34s %s" % (rel, v or "absent"))


def check(snap, prev):
    moved_art, moved_shared = [], []
    for rel, v in snap["artifacts"].items():
        if prev["artifacts"].get(rel) != v:
            moved_art.append((rel, prev["artifacts"].get(rel), v))
    for rel, v in snap["shared"].items():
        if prev["shared"].get(rel) != v:
            moved_shared.append(rel)

    for rel, was, now in moved_art:
        print("CHANGED  %-24s %s -> %s" % (rel, was, now))
    if moved_shared:
        print("shared driver state rewritten (expected after any build): %s"
              % ", ".join(moved_shared))
    if not moved_art:
        print("ARTIFACTS UNCHANGED across all %d directories -- corpus restored"
              % len(snap["artifacts"]))
        return 0
    print("\n%d artifact director%s moved. The corpus was NOT restored."
          % (len(moved_art), "y" if len(moved_art) == 1 else "ies"))
    return 1


def main(argv) -> int:
    snap = snapshot()
    if "--save" in argv:
        out = Path(argv[argv.index("--save") + 1])
        out.write_text(json.dumps(snap, indent=1), encoding="utf-8")
        print("saved %s" % out)
        show(snap)
        return 0
    if "--check" in argv:
        ref = Path(argv[argv.index("--check") + 1])
        if not ref.is_file():
            print("no snapshot at %s -- cannot verify a restore without one" % ref)
            return 2
        return check(snap, json.loads(ref.read_text(encoding="utf-8")))
    show(snap)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
