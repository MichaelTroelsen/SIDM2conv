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
import atexit
import glob
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import launch_failure  # noqa: E402
from sidm2.sdi_parser import load_sid, SDIModule  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(ROOT, "SID", "Gallefoss_Glenn")
BUILDER = os.path.join(ROOT, "bin", "build_sdi_native_song.py")

# Kill-safety lives in pyscript/process_group.py so both sweeps can reach it
# without importing each other; see that module for the measurement behind it.
from process_group import bind_children_to_this_process  # noqa: E402

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

    THE COST MODEL, RE-MEASURED 2026-09-05 -- AND THE PUBLISHED r DOES NOT
    REPRODUCE. runs.jsonl:sdi-six-timeouts-at-j16 reports "build time vs trace
    window r=0.942, vs part count alone only r=0.420" over NINE files (the n was
    never printed beside the r). Recomputing both against the spans this
    function returns, using that record's own nine files and its own recorded
    build times:

        build time vs part count      r = 0.420   <- reproduces EXACTLY
        build time vs trace window    r = 0.335   <- published as 0.942

    Part count reproducing to three decimals says the arithmetic and the file
    set are right, so the disagreement is in the WINDOW numbers or the TIMES.
    It is the times. The record asserts "the ratio build/window is 0.45-0.74
    across all nine, mostly ~0.5"; measured, five files fit that model and four
    do not:

        GT_Groove         span 1602s   0.5s/s predicts  801s   recorded 1081s  ok
        L-Forza_long_edit span 1562s                    781s            1156s  ok
        Countdown_to_NIL  span  543s                    272s             305s  ok
        Jazzmjux          span   94s                     47s              50s  ok
        Rocker            span   54s                     27s              26s  ok
        Onkie_Donkie      span  262s                    131s            1104s  NO
        Culture_Mix_1     span  132s                     66s            1152s  NO
        Culture_Mix_2     span  102s                     51s            1144s  NO
        Lame              span   71s                     36s            1078s  NO

    The four failures all sit at 1078-1152s -- a 7% band across spans differing
    3.7x, which is a FIXED cost, not a per-second one. And `Lame` was later
    re-timed at **16.6s** (runs.jsonl:sdi-control-rerun-at-j8), 65x below the
    1077.8s here and close to the 36s the model predicts. So four of those nine
    timings are not per-file build cost, and the r computed from them is not a
    cost model.

    WHAT SURVIVES, and why span-desc is still the right key: where the model is
    checkable it holds (5 of 5), and the record's own claim that the six
    expensive files "are simply long songs" is HALF true -- two of them span
    1562-1602s, and the other four span 71-262s. Scheduling longest-first is
    justified by the five, not by r=0.942. Do not re-cite that number.

    A SECOND CLAIM THAT DOES NOT REPRODUCE: runs.jsonl:sdi-sweep-schedule-
    longest-first reports the six ranking at "positions 11-25 of 441". Measured
    here, they rank 6, 7, 83, 188, 221 and 267 -- so span-desc puts TWO of the
    six in the head of the queue, not all six. The spans are deterministic
    (SID/ is unchanged) so this is a straight correction.
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


# --- Durable run journal ------------------------------------------------------
# WHY THIS EXISTS. On 2026-08-20 a full 441-file sweep was launched detached,
# ran for hours, and DIED with its log frozen at three banner lines, 0 files
# written and no stderr beyond them (runs.jsonl:sdi-part-counts-stale-after-d-
# rebuild). Nothing could say whether it crashed, was killed, or never got past
# scheduling -- because the only record was the LAUNCHER's stdout redirect, and
# a redirect captures nothing a dying process never manages to print.
#
# So the sweep now records its own progress, itself, as it goes. The journal is
# rewritten after every file and closed by an atexit hook that fires on a normal
# return, an exception AND a KeyboardInterrupt, so the file on disk always names
# how the run ended. It sits BESIDE --json rather than in a temp directory: the
# 2026-08-20 run's log, result JSON and start-epoch file all lived in a session
# scratchpad that was garbage-collected nine days later, taking the only
# evidence with them (runs.jsonl:sdi-funk-facet-pre-onset-anchor).
_JOURNAL = {"state": "starting", "started": None, "pid": os.getpid(),
            "done": 0, "total": None, "built": 0, "last_file": None,
            "ended": None, "how": None}
_JOURNAL_PATH = [None]


def journal_path_for(json_path):
    """<json>.journal, or None when --json was not given.

    Deliberately derived from --json rather than being its own flag: a sweep
    worth recording is a sweep worth keeping the result of, and one more flag
    to forget is one more silent death.
    """
    return (json_path + ".journal") if json_path else None


def write_journal():
    """Rewrite the journal. Never raises -- a failure here must not kill a sweep."""
    path = _JOURNAL_PATH[0]
    if not path:
        return
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(_JOURNAL, fh, indent=1)
        os.replace(tmp, path)
    except Exception:                                    # noqa: BLE001
        pass


def _close_journal():
    if _JOURNAL["state"] == "running":
        # Reached only when the process is going down without main() having
        # set a terminal state: an uncaught exception, a signal, or os._exit
        # from a library. THIS is the line the 2026-08-20 death did not leave.
        _JOURNAL["state"] = "died"
        _JOURNAL["how"] = "process exited while the sweep was still running"
    _JOURNAL["ended"] = time.time()
    write_journal()


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
    _JOURNAL_PATH[0] = journal_path_for(a.json)
    # Reset every counter, not just the new ones: _JOURNAL is module state,
    # so a second main() in the same process would otherwise report the
    # FIRST run's built count beside the second run's total. Found by the
    # positive-control test, which is the only place two sweeps share an
    # interpreter today -- but a future --resume would hit it for real.
    _JOURNAL.update(state="running", started=time.time(), total=len(corpus),
                    done=0, built=0, last_file=None, ended=None, how=None)
    atexit.register(_close_journal)
    write_journal()
    print(f"SDI Stage B sweep -- {len(corpus)} file(s) from {CORPUS_DIR}", flush=True)
    if _JOURNAL_PATH[0]:
        print(f"  journal: {_JOURNAL_PATH[0]} (rewritten after every file)",
              flush=True)
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
        # Say which guarantee is in force, because "killed" meaning "still building"
        # is exactly the failure this line exists to make visible.
        print("  kill-safety: %s" % ("builders die with this process (job object)"
                                     if bind_children_to_this_process() else
                                     "NOT ESTABLISHED -- a hard kill will leave "
                                     "builders running; kill the TREE (taskkill /T)"),
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
        _JOURNAL.update(done=i, last_file=name)
        if rec.get("voices"):
            _JOURNAL["built"] += 1
        write_journal()
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
    # A SWEEP THAT BUILT NOTHING IS NOT A COMPLETED SWEEP, and must not be
    # readable as one. The 2026-08-20 run died having written 0 files; had it
    # reached this point it would have emitted a perfectly well-formed result
    # JSON whose only tell was a zero buried in the summary. `complete` is
    # therefore written into the file itself AND returned as a non-zero exit
    # status, so a shell chain and a later reader each see the failure without
    # having to interpret a count.
    complete = bool(s["built"])
    if not complete:
        print("!! 0 files BUILT. This is NOT a corpus result -- a sweep that "
              "built nothing has measured nothing, whatever the refused and "
              "errored columns say. Exiting non-zero.", flush=True)
    _JOURNAL.update(state="finished" if complete else "no-files-built",
                    how="built %d of %d" % (s["built"], len(corpus)))
    # Write it HERE, not only from the atexit hook. Otherwise the journal on
    # disk still reads "running" for as long as the interpreter takes to shut
    # down, and anything reading it in that window -- a watchdog, a second
    # sweep, a human checking on a detached job -- sees a finished run as a
    # live one. Caught by this change's own positive-control test.
    write_journal()
    if a.json:
        json.dump({"complete": complete,
                   "results": results, "summary": s, "schedule": a.schedule,
                   "order": corpus, "spans": spans},
                  open(a.json, "w", encoding="utf-8"), indent=1)
        print(f"\nwrote {a.json}" + ("" if complete else "  (complete=false)"))
    return 0 if complete else 1


if __name__ == "__main__":
    sys.exit(main())
