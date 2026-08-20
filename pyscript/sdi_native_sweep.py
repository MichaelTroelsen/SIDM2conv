#!/usr/bin/env python3
"""SDI (SID Duzz' It) Stage B corpus sweep -- build natively and score every file.

`docs/players/SDI.md` quotes a set of Stage B per-voice figures ("2_Young
100/100/100", "Kirby ~99.7", "Bahbar v1/v2 ~92.7/90.4", "all 6 V files build"),
and `docs/SF2.md` repeats the verdict. Until now those came from
`bin/_sdi_stageb_sweep.py`, which is **untracked** (`.gitignore` excludes
`bin/_*.py`) and swept a **hand-picked 15-file SAMPLE across 3 of the 6
variants** -- so the published numbers were not reproducible from a fresh clone,
and the "all six variants" claim was never covered by the thing measuring it.
That is the same defect `pyscript/soundmonitor_sweep.py` was promoted to fix
(R21), for the same reason.

This version is self-contained and derives its corpus instead of naming one:
it invokes `bin/build_sdi_native_song.py` per file and parses the per-voice
fidelity straight out of that same subprocess's stdout, so one command
reproduces the sweep from nothing but a checkout (`SID/Gallefoss_Glenn/` is
tracked). It is also the **shipping path** SDI.md lists as open -- the builder
was standalone, one file at a time.

    py -3 pyscript/sdi_native_sweep.py                 # whole corpus (441 files)
    py -3 pyscript/sdi_native_sweep.py --files Kirby Bahbar
    py -3 pyscript/sdi_native_sweep.py --limit 40 --json out.json

A REFUSAL IS A RESULT, NOT A GAP. The builder refuses a file it cannot drive
(`measure_onsets` vs siddump onset agreement < 85% -- multispeed / self-IRQ),
and that refusal is recorded per file with its reason rather than dropped. A
sweep that silently skipped them would report the surviving files' scores as if
they were the corpus, which is exactly how a hand-picked sample flatters itself.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import launch_failure  # noqa: E402
from sidm2.sdi_parser import load_sid, SDIModule  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(ROOT, "SID", "Gallefoss_Glenn")
BUILDER = os.path.join(ROOT, "bin", "build_sdi_native_song.py")

# The launch-failure classifier lives in the shared harness -- this sweep is
# where the failure was FOUND, not where it belongs. See
# `fidelity_common.launch_failure` for what it is and why it is not `errored`.

_HEAD = re.compile(r"^\S+: la=\$([0-9A-F]{4}) variant=(\S+)", re.M)
# The `!` and `(n=...)` are OPTIONAL: a build produced by a checkout from
# before the underpowered guard was wired in still parses, and its record
# simply carries `n: None` rather than a fabricated count.
_VOICE = re.compile(r"^\s+voice (\d): \s*([\d.]+)!?%(?:\s+\(n=(\d+)\))?", re.M)
_PARTS = re.compile(r"packed into (\d+) adaptive part")
_ONSETS = re.compile(r"emulated onsets vs trace: (\d+)/(\d+)")
_REFUSED = re.compile(r"REFUSING to build: ([^\n]+)")
_VWRAP = re.compile(r"V wrapper: module init=")


def corpus_files(limit=None, names=None):
    """The sweep corpus, DERIVED from the tracked SID directory.

    Not a curated list: the scratch script's 15-name SAMPLE is precisely what
    let "all six variants" go unmeasured.
    """
    if names:
        return list(names)
    out = sorted(os.path.splitext(os.path.basename(p))[0]
                 for p in glob.glob(os.path.join(CORPUS_DIR, "*.sid")))
    return out[:limit] if limit else out


def decoded_span(name):
    """The trace window `bin/build_sdi_native_song.py` will use for `name`,
    computed the SAME way the builder does it (its line ~402: max onset frame
    across all 3 voices + 100) but WITHOUT the expensive part -- the siddump /
    py65 trace itself. `decode_voice()` is a pure in-memory table walk over
    the loaded binary, so scanning the whole 441-file corpus this way costs
    well under a minute, not the 2.5 hours the traces do.

    Returns None when the file can't be decoded at all (no SDI signature, or
    the load throws) -- `build_one()` will REFUSE or ERROR on those anyway, so
    they carry no cost signal for scheduling and sort last, not first.

    This is the cost model measured in runs.jsonl (sdi-six-timeouts-at-j16):
    build time vs trace window r=0.942, vs part count alone only r=0.420 --
    GT_Groove (402 parts) and Culture_Mix_1 (4 parts) both cost ~1150s because
    both trace 26-40 minutes of music, while part count alone would have
    ranked them at opposite ends of the corpus.
    """
    sid = os.path.join(CORPUS_DIR, f"{name}.sid")
    try:
        d, la, _h = load_sid(sid)
        m = SDIModule(d, la)
        return max((e.frame for v in range(3) for e in m.decode_voice(v)),
                    default=0) + 100
    except Exception:
        return None


def schedule_longest_first(names):
    """Reorder `names` by decoded span descending. A -jN pool consumes
    ThreadPoolExecutor futures in SUBMISSION order as workers free up, so
    submitting the corpus's 26-40 minute outliers (GT_Groove,
    L-Forza_long_edit, the two Culture_Mix songs, Lame, Onkie_Donkie) first
    starts them immediately across the pool instead of letting them queue
    behind a long tail of 25-300s files and land in the LAST wave, where they
    serialise back-to-back with nothing else left to overlap them against --
    exactly what produced the -j16 timeouts in sdi-six-timeouts-at-j16.
    Files whose span could not be decoded (None) sort last; they have no cost
    signal and `build_one()` disposes of them quickly (refuse/error) either
    way, so scheduling them early buys nothing."""
    spans = {n: decoded_span(n) for n in names}
    ordered = sorted(names, key=lambda n: (spans[n] is None, -(spans[n] or 0)))
    return ordered, spans


def parse_build_output(text):
    """One build's stdout -> a record. Distinguishes the outcomes that matter:
    built (voices present), refused (a stated reason), or failed (neither)."""
    rec = {"variant": None, "voices": None, "parts": None,
           "onset_agree": None, "refused": None, "v_wrapper": bool(_VWRAP.search(text))}
    h = _HEAD.search(text)
    if h:
        rec["variant"] = h.group(2)
    o = _ONSETS.search(text)
    if o:
        rec["onset_agree"] = (int(o.group(1)), int(o.group(2)))
    r = _REFUSED.search(text)
    if r:
        rec["refused"] = r.group(1).strip()
    p = _PARTS.search(text)
    if p:
        rec["parts"] = int(p.group(1))
    v = _VOICE.findall(text)
    if len(v) == 3:
        rec["voices"] = [float(x) for _i, x, _n in v]
        ns = [int(n) if n else None for _i, _x, n in v]
        rec["n"] = ns if any(n is not None for n in ns) else None
    return rec


def build_one(name, timeout=1800):
    sid = os.path.join(CORPUS_DIR, f"{name}.sid")
    if not os.path.exists(sid):
        return {"error": "missing .sid", "voices": None, "refused": None}
    try:
        r = subprocess.run([sys.executable, BUILDER, sid, "auto"],
                           capture_output=True, text=True, cwd=ROOT,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s", "voices": None, "refused": None}
    rec = parse_build_output(r.stdout + r.stderr)
    rec["rc"] = r.returncode
    if rec["voices"] is None and rec["refused"] is None:
        tail = [l for l in (r.stdout + r.stderr).strip().splitlines() if l.strip()]
        rec["error"] = tail[-1][:160] if tail else f"no output (rc={r.returncode})"
        # The child never got far enough to have an opinion about this file.
        infra = launch_failure(r.returncode, r.stdout + r.stderr)
        if infra:
            rec["infra"] = infra
    return rec


def summarize(results):
    """Per-variant rollup. Voice medians, not means: one catastrophic voice in a
    variant with three files would otherwise move the headline more than it
    should, and this repo quotes medians for SDI Stage A already."""
    built = {k: v for k, v in results.items() if v.get("voices")}
    refused = {k: v for k, v in results.items() if v.get("refused")}
    # `infra` is NOT an outcome for the file -- it is the sweep failing to ask.
    # Keeping it out of `errored` is the whole point: pooled into that column it
    # reads as 167 unsupported files instead of 167 unmeasured ones.
    infra = {k: v for k, v in results.items() if v.get("infra")}
    errored = {k: v for k, v in results.items()
               if not v.get("voices") and not v.get("refused") and not v.get("infra")}
    by_var = {}
    for name, rec in built.items():
        by_var.setdefault(rec["variant"] or "?", []).extend(rec["voices"])
    thin = sum(1 for r in built.values() for n in (r.get("n") or [])
               if n is not None and n < 250)
    no_n = sum(1 for r in built.values() if not r.get("n"))
    rollup = {}
    for var, vals in sorted(by_var.items()):
        vals = sorted(vals)
        n = len(vals)
        med = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        rollup[var] = {"voices": n, "median": round(med, 1),
                       "at_100": sum(1 for x in vals if x >= 99.95),
                       "below_90": sum(1 for x in vals if x < 90)}
    return {"built": len(built), "refused": len(refused), "errored": len(errored),
            "unmeasured": len(infra), "thin_voices": thin, "files_without_n": no_n,
            "by_variant": rollup,
            "refusal_reasons": sorted({v["refused"] for v in refused.values()}),
            "errors": {k: v.get("error") for k, v in errored.items()},
            "unmeasured_files": sorted(infra)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", nargs="*", help="explicit song names (no .sid)")
    ap.add_argument("--limit", type=int, help="first N corpus files only")
    ap.add_argument("--timeout", type=int, default=1800, help="per-file seconds")
    ap.add_argument("--json", help="write the full per-file record here")
    ap.add_argument("--jobs", "-j", type=int, default=1, metavar="N",
                    help="build/score N songs concurrently (default 1). Sets "
                         "MON_BUILD_LOCK=1 so the one section touching shared "
                         "driver state is serialised -- that is what makes it "
                         "safe, see PATTERNS F12. Results print in CORPUS "
                         "order regardless of completion order, so a -jN run "
                         "stays comparable to -j1. NOTE --infra-abort changes "
                         "meaning under -j>1: see its help.")
    ap.add_argument("--schedule", choices=("span-desc", "corpus-order"),
                    default="span-desc",
                    help="build order (default span-desc): schedule the "
                         "longest DECODED TRACE WINDOW first so a -jN pool "
                         "starts the corpus's 26-40 minute outliers "
                         "immediately instead of letting them serialise "
                         "behind a tail of short files -- see "
                         "decoded_span()/schedule_longest_first() and "
                         "runs.jsonl sdi-six-timeouts-at-j16. "
                         "'corpus-order' restores the old alphabetical-by-"
                         "filename order for comparison.")
    ap.add_argument("--infra-abort", type=int, default=3, metavar="N",
                    help="stop after N consecutive process-LAUNCH failures "
                         "(0 disables); once the host stops spawning children "
                         "every later file is recorded as a failure it never had. "
                         "Under -j>1 this counts TOTAL launch failures rather "
                         "than consecutive ones -- 'consecutive' has no meaning "
                         "when N files are in flight at once, and the signal it "
                         "stands for (the host has stopped spawning children) is "
                         "if anything more likely at -j16 than at -j1.")
    a = ap.parse_args(argv)

    corpus = corpus_files(a.limit, a.files)
    print(f"SDI Stage B sweep -- {len(corpus)} file(s) from {CORPUS_DIR}", flush=True)
    spans = {}
    if a.schedule == "span-desc":
        corpus, spans = schedule_longest_first(corpus)
        undecoded = sum(1 for v in spans.values() if v is None)
        top = ", ".join(f"{n}={spans[n]}" for n in corpus[:5] if spans.get(n) is not None)
        print(f"  --schedule span-desc: ordered by decoded trace window "
              f"descending (top 5: {top}); {undecoded} file(s) undecoded, "
              f"sorted last", flush=True)
    results = {}
    consec_infra = 0

    pre = {}
    if a.jobs > 1:
        # The lock is the WHOLE safety argument, so set it here rather than
        # trusting the caller: builds serialise on the one section touching
        # shared driver state, so the artifacts are identical to a serial run
        # (PATTERNS F12). Everything expensive -- tracing, parsing, packing --
        # stays concurrent.
        os.environ["MON_BUILD_LOCK"] = "1"
        from concurrent.futures import ThreadPoolExecutor, as_completed
        print(f"  -j{a.jobs}: MON_BUILD_LOCK=1 (shared driver state serialised)",
              flush=True)
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            futs = {ex.submit(build_one, n, a.timeout): n for n in corpus}
            done = 0
            infra_seen = 0
            for fut in as_completed(futs):
                done += 1
                nm = futs[fut]
                try:
                    pre[nm] = fut.result()
                except Exception as e:          # one song must not sink the sweep
                    pre[nm] = {"error": f"{type(e).__name__}: {e}"}
                bad = " LAUNCH FAILURE" if pre[nm].get("infra") else ""
                print(f"  ...{done}/{len(futs)} done ({nm}){bad}", flush=True)
                # TOTAL, not consecutive -- see --infra-abort's help. Cancel what
                # has not started: continuing past host exhaustion records files
                # as failures they never had, which is the whole point of the
                # guard and matters MORE at -j16 than at -j1.
                if pre[nm].get("infra"):
                    infra_seen += 1
                    if a.infra_abort and infra_seen >= a.infra_abort:
                        n_cancelled = sum(1 for f in futs if f.cancel())
                        print(f"ABORTING: {infra_seen} process-launch failures. "
                              f"The host has stopped spawning children. "
                              f"{n_cancelled} queued file(s) cancelled; anything "
                              f"still running will finish.", flush=True)
                        break
        for nm in corpus:
            if nm not in pre:
                pre[nm] = {"infra": "cancelled after launch failures"}

    for i, name in enumerate(corpus, 1):
        rec = pre[name] if name in pre else build_one(name, a.timeout)
        results[name] = rec
        if rec.get("infra"):
            consec_infra += 1
            print(f"  [{i}/{len(corpus)}] {name:34s} {'?':5s} "
                  f"LAUNCH FAILURE ({rec['infra']}) -- not a result", flush=True)
            # Only the SERIAL path aborts here. Under -j>1 the abort has
            # already happened inside the executor and the remaining files are
            # pre-recorded as cancelled; re-firing it would print a second
            # ABORT and truncate `results`, hiding files that were measured.
            if a.jobs == 1 and a.infra_abort and consec_infra >= a.infra_abort:
                rest = corpus[i - consec_infra:]
                print(f"ABORTING: {consec_infra} consecutive process-launch "
                      f"failures. The host has stopped spawning children, so "
                      f"every remaining file would be recorded as a failure it "
                      f"never had.", flush=True)
                print(f"{len(rest)} file(s) UNMEASURED. Resume in a FRESH "
                      f"process (chunk it -- the exhaustion is cumulative):",
                      flush=True)
                print(f"  py -3 pyscript/sdi_native_sweep.py --files "
                      f"{' '.join(rest[:6])}{' ...' if len(rest) > 6 else ''}",
                      flush=True)
                break
            continue
        consec_infra = 0
        if rec.get("voices"):
            v = "/".join(f"{x:.1f}" for x in rec["voices"])
            tag = " [V-wrapper]" if rec.get("v_wrapper") else ""
            print(f"  [{i}/{len(corpus)}] {name:34s} {rec['variant'] or '?':5s} "
                  f"{v:20s} parts={rec['parts']}{tag}", flush=True)
        elif rec.get("refused"):
            print(f"  [{i}/{len(corpus)}] {name:34s} {rec['variant'] or '?':5s} "
                  f"REFUSED ({rec['refused'][:60]})", flush=True)
        else:
            print(f"  [{i}/{len(corpus)}] {name:34s} {rec.get('variant') or '?':5s} "
                  f"ERROR {rec.get('error')}", flush=True)

    s = summarize(results)
    print(f"\nbuilt {s['built']}  refused {s['refused']}  errored {s['errored']}"
          f"  of {len(corpus)}")
    unmeasured = len(corpus) - len(results) + s["unmeasured"]
    if unmeasured:
        print(f"!! {unmeasured} file(s) UNMEASURED (process-launch failure) -- "
              f"the figures below cover {len(results) - s['unmeasured']} files, "
              f"NOT {len(corpus)}. This is not a corpus result.")
    print(f"{'variant':>8s} {'voices':>7s} {'median':>7s} {'=100':>6s} {'<90':>5s}")
    for var, r in s["by_variant"].items():
        print(f"{var:>8s} {r['voices']:7d} {r['median']:7.1f} "
              f"{r['at_100']:6d} {r['below_90']:5d}")
    if s["files_without_n"]:
        print(f"note: {s['files_without_n']} built file(s) reported no frame "
              f"count -- their percentages cannot be checked for being thin")
    if s["thin_voices"]:
        print(f"note: {s['thin_voices']} voice(s) scored over <250 compared "
              f"frames (5 s PAL); those are not fidelity claims")
    if a.json:
        json.dump({"results": results, "summary": s, "schedule": a.schedule,
                   "order": corpus, "spans": spans},
                  open(a.json, "w", encoding="utf-8"), indent=1)
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
