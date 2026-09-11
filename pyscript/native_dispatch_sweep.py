#!/usr/bin/env python3
"""Reproduce docs/ROADMAP.md A4's dispatch figures from a clean checkout.

WHY THIS EXISTS, and it is not tidiness. A4 carried two measured claims --
"exactly-one-and-correct: 0 of 48" and a 734-file collision count -- and NOTHING
IN THE TREE REGENERATED EITHER. `sidm2/native_dispatch.py` exposes `rank()` and
`dispatch()` and stops there: no `__main__`, no CLI, no sweep. So for three weeks
the only way to challenge those numbers was to disbelieve them, and when they
were finally re-measured (2026-09-11) the headline had moved to 2 of 48 without
anyone noticing.

That is the THIRD time this repo has lost an audit the same way.
`pyscript/hardtrack_duration_law_sweep.py` and `pyscript/sdi_native_sweep.py`
were each promoted from a throwaway probe for exactly this reason, and this file
deliberately copies their shape rather than inventing a third one.

THE SAMPLE IS PRINTED, WHICH IS THE WHOLE POINT OF THE REWRITE. The 2026-08-17
run described its files only as "6 spread across each corpus"; the 2026-09-11
re-measure took the first 6 alphabetically. Neither recorded WHICH files, so the
two could not be compared and three per-probe movements (mattgray 0->1,
blackbird 1->0, sdi 3->1) could not be told apart from sampling noise. This sweep
prints every filename it used and the rule that chose them, so a later run can
reproduce the same draw or deliberately change it.

    py -3 pyscript/native_dispatch_sweep.py
    py -3 pyscript/native_dispatch_sweep.py --per-corpus 12 --json out.json
    py -3 pyscript/native_dispatch_sweep.py --schedule random --seed 7
    py -3 pyscript/native_dispatch_sweep.py --families dmc mon

WHAT "CORRECT" MEANS HERE, stated because the word is doing real work: a file
drawn from family F's corpus is `exactly-one-and-correct` only when the probe set
accepts F AND NOTHING ELSE. A file that F accepts alongside dmc and mon is not a
win -- it is the collision that makes `first_match` unsafe, which is A4's actual
finding.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import sidm2.native_dispatch as N  # noqa: E402

#: family -> the corpus directory whose files that family OWNS.
#:
#: Only families with a probe in `native_dispatch.PROBE_ORDER` belong here: a
#: family with no probe can never be "correct" for its own files, so including
#: one silently drives the headline toward zero. That mistake was made once --
#: galway and deenen have no probe, and adding them turned a real 2-of-48 into a
#: confident 0-of-60.
CORPORA = {
    "blackbird": "SID/LFT",
    "sdi": "SID/Gallefoss_Glenn",
    "hardtrack": "SID/Shogoon",
    "mattgray": "SID/Gray_Matt",
    "hubbard": "SID/Hubbard_Rob",
    "soundmonitor": "SID/Fun_Fun",
    "dmc": "SID/JohannesBjerregaard",
    "mon": "SID/Tel_Jeroen",
}


def probed_families():
    """The families `native_dispatch` actually has a probe for."""
    return {name for name, _fn in N.PROBE_ORDER}


def sample(per_corpus, schedule, seed, families=None):
    """(family, path) pairs, with the choosing rule applied explicitly."""
    want = set(families) if families else set(CORPORA)
    out = []
    rng = random.Random(seed)
    for fam in sorted(CORPORA):
        if fam not in want:
            continue
        files = sorted(glob.glob(os.path.join(ROOT, CORPORA[fam], "*.sid")))
        if schedule == "random":
            files = files[:]
            rng.shuffle(files)
        out.extend((fam, f) for f in files[:per_corpus])
    return out


def measure_one(fam, path):
    """One row: what the probe set said about a file whose family we know."""
    try:
        r = N.rank(path)
    except Exception as e:                                   # pragma: no cover
        return dict(family=fam, file=os.path.basename(path),
                    error="%s: %s" % (type(e).__name__, e),
                    accepted=[], signature=[], best=None, confident=False)
    # THESE KEY NAMES ARE THE CONTRACT and are pinned by the test file. An
    # earlier probe invented a "candidates" list of dicts, read nothing, and
    # reported a confident 0 -- the tell was that no probe accepted anything,
    # which is impossible when dmc and mon accept nearly every file.
    return dict(family=fam, file=os.path.basename(path),
                accepted=list(r["dispatch"]["accepted"]),
                signature=list(r.get("signature") or []),
                best=r.get("best"),
                confident=bool(r.get("confident")))


def summarise(rows):
    n = len(rows)
    accepts = {}
    for r in rows:
        for a in r["accepted"]:
            accepts[a] = accepts.get(a, 0) + 1
    conf = [r for r in rows if r["confident"]]
    return dict(
        files=n,
        exactly_one_and_correct=sum(1 for r in rows if r["accepted"] == [r["family"]]),
        best_is_own_family=sum(1 for r in rows if r["best"] == r["family"]),
        confident=len(conf),
        confident_and_correct=sum(1 for r in conf if r["best"] == r["family"]),
        errors=sum(1 for r in rows if r.get("error")),
        accepts=accepts,
    )


def vacuous(rows, summary):
    """The guard this sweep exists to carry, not an afterthought.

    If NO probe accepted ANY file, the harness is broken -- not the dispatcher.
    `dmc` and `mon` accept nearly everything by construction, so a total of zero
    accepts can only mean `rank()` raised on every file or its return shape
    changed under us. Reporting `0 of N` there would be a measurement of this
    script's own bug, dressed as a finding about the repo.
    """
    if not rows:
        return "no files sampled -- check CORPORA paths against the tree"
    if not summary["accepts"]:
        return ("NO probe accepted ANY of %d files. dmc and mon accept nearly "
                "every file by construction, so this is a harness failure, not "
                "a result -- rank() is raising or its return shape moved. "
                "%d row(s) recorded an error." % (len(rows), summary["errors"]))
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-corpus", type=int, default=6, metavar="N",
                    help="files per corpus (default 6, which is A4's own shape)")
    ap.add_argument("--schedule", choices=("first", "random"), default="first",
                    help="'first' takes the first N alphabetically (default, "
                         "reproducible without a seed); 'random' shuffles")
    ap.add_argument("--seed", type=int, default=0,
                    help="seed for --schedule random, so a draw is repeatable")
    ap.add_argument("--families", nargs="*",
                    help="restrict to these families (default: all probed)")
    ap.add_argument("--json", help="write the full per-file rows here")
    a = ap.parse_args(argv)

    unprobed = set(CORPORA) - probed_families()
    if unprobed:
        print("WARNING: CORPORA names %s, which PROBE_ORDER has no probe for -- "
              "those files can never be correct for their own family and will "
              "drag the headline toward zero." % sorted(unprobed), file=sys.stderr)

    rows_in = sample(a.per_corpus, a.schedule, a.seed, a.families)

    # THE SAMPLE, PRINTED. This is the half the two prior runs omitted, and
    # omitting it is why their numbers could not be compared.
    print("sample rule: %s %d per corpus%s"
          % (a.schedule, a.per_corpus,
             (", seed %d" % a.seed) if a.schedule == "random" else ""))
    print("files (%d):" % len(rows_in))
    for fam, p in rows_in:
        print("  %-14s %s" % (fam, os.path.relpath(p, ROOT).replace("\\", "/")))
    print()

    rows = [measure_one(fam, p) for fam, p in rows_in]
    s = summarise(rows)

    bad = vacuous(rows, s)
    if bad:
        print("REFUSING TO REPORT: %s" % bad, file=sys.stderr)
        return 2

    print("%-34s %s" % ("files probed", s["files"]))
    print("%-34s %d of %d" % ("exactly-one-and-correct",
                              s["exactly_one_and_correct"], s["files"]))
    print("%-34s %d of %d" % ("best == own family",
                              s["best_is_own_family"], s["files"]))
    print("%-34s %d of %d confident" % ("confident AND correct",
                                        s["confident_and_correct"], s["confident"]))
    if s["errors"]:
        print("%-34s %d" % ("rows that ERRORED", s["errors"]))
    print()
    print("probe ACCEPT rate over %d files:" % s["files"])
    for k, v in sorted(s["accepts"].items(), key=lambda kv: -kv[1]):
        print("   %-14s %3d  (%.0f%%)" % (k, v, 100.0 * v / s["files"]))
    for name in sorted(probed_families() - set(s["accepts"])):
        print("   %-14s %3d  (0%%)" % (name, 0))

    if a.json:
        json.dump(dict(sample_rule=dict(schedule=a.schedule,
                                        per_corpus=a.per_corpus, seed=a.seed),
                       files=[os.path.relpath(p, ROOT).replace("\\", "/")
                              for _f, p in rows_in],
                       rows=rows, summary=s),
                  open(a.json, "w", encoding="utf-8"), indent=1)
        print("\nwrote", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
