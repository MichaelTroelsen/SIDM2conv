#!/usr/bin/env python3
"""Scan built .sf2 modules for the silent sequence-truncation signature.

`galway_driver11_emitter` caps sequences at the 128-entry pointer table and,
until 2026-07-30, dropped the excess SILENTLY -- in the segmenting branch its
`break` left the voice loop, so later voices were emitted as a single empty
sequence and went completely silent; in the caller-supplied branch the slice
dropped sequences and the orderlist filter then removed every entry pointing at
them. Either way the file parses, loads and plays -- it is just missing music.
That emitter is shared by ~13 Stage A builders, so this scans what has already
been shipped.

WHAT IS AND IS NOT PROOF. Truncation can only occur once the table is FULL, so:

  * used < 128            -> provably clean, no drop was possible
  * used == 128           -> CANDIDATE; the table is exactly full, which is the
                             precondition for a drop (and also what an honestly
                             128-sequence song looks like)
  * used == 128 AND a voice references only empty sequences
                          -> STRONG: the emergency-empty-sequence signature of
                             the segmenting branch's voice-loop break

A candidate is not a defect on its own. Rebuild it and read the emitter's
warning to decide -- that is the only oracle that knows what was requested.

    py -3 pyscript/sf2_truncation_scan.py [dir ...]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sidm2.models import SF2DriverInfo          # noqa: E402
from sidm2 import sf2_parser                    # noqa: E402

SEQ_SLOTS = 128


def scan_file(path):
    """(used, empty_voices, n_voices) or None if the file is not parseable."""
    try:
        blob = bytearray(open(path, "rb").read())
        di = SF2DriverInfo()
        la = sf2_parser.parse_sf2_blocks(blob, di)
        if la is None:
            return None
    except Exception:
        return None

    def at(addr):
        return addr - la + 2

    used = sum(1 for i in range(di.sequence_count)
               if blob[at(di.sequence_ptrs_lo + i)]
               or blob[at(di.sequence_ptrs_hi + i)])

    # A voice is "empty" when every sequence its orderlist reaches is a bare
    # terminator -- the emergency sequence the emitter appends for a voice that
    # got nothing. $A0-$BF in an orderlist is a transpose byte, $FF ends it.
    empty_voices = 0
    for v in range(min(3, di.track_count)):
        ol = blob[at(di.orderlist_start + v * di.orderlist_size):][:di.orderlist_size]
        refs = []
        for b in ol:
            if b == 0xFF:
                break
            if 0xA0 <= b <= 0xBF:       # transpose, not a sequence index
                continue
            refs.append(b & 0x7F)
        if not refs:
            empty_voices += 1
            continue
        all_empty = True
        for idx in refs:
            if idx >= di.sequence_count:
                continue
            addr = (blob[at(di.sequence_ptrs_lo + idx)]
                    | (blob[at(di.sequence_ptrs_hi + idx)] << 8))
            body = blob[at(addr):at(addr) + 0x100]
            if body and body[0] != 0x7F:
                all_empty = False
                break
        if all_empty:
            empty_voices += 1
    return used, empty_voices, min(3, di.track_count)


def main(argv):
    dirs = argv or [os.path.join(ROOT, "out"), os.path.join(ROOT, "SF2")]
    files = []
    for d in dirs:
        for root, _dirs, names in os.walk(d):
            files.extend(os.path.join(root, n) for n in names
                         if n.lower().endswith(".sf2"))
    files.sort()

    scanned = clean = 0
    candidates, strong = [], []
    for f in files:
        r = scan_file(f)
        if r is None:
            continue
        scanned += 1
        used, empty_voices, n_voices = r
        if used < SEQ_SLOTS:
            clean += 1
            continue
        rel = os.path.relpath(f, ROOT)
        (strong if empty_voices else candidates).append((rel, used, empty_voices))

    print(f"scanned {scanned} .sf2 file(s) under {', '.join(dirs)}")
    print(f"  provably clean (used < {SEQ_SLOTS}):        {clean}")
    print(f"  candidates     (used == {SEQ_SLOTS}):       {len(candidates)}")
    print(f"  STRONG (full table AND an empty voice):  {len(strong)}")
    for rel, used, ev in strong:
        print(f"    !! {rel}  used={used} empty_voices={ev}")
    for rel, used, ev in candidates[:40]:
        print(f"     ? {rel}  used={used}")
    if len(candidates) > 40:
        print(f"     ... and {len(candidates) - 40} more candidates")
    return 1 if strong else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
