#!/usr/bin/env python3
"""DMC (Demo Music Creator) native corpus sweep -- score every shipped build.

`docs/players/DMC.md` quotes "Balloon: 77 parts merged into ONE 400s SF2,
wf/pulse 100x3 over the FULL 400s (n=19996/voice) -- the best-evidenced number
in the project", and `ACCURACY_MATRIX.md` carries it too. Until now every one of
those figures came from `bin/_dmc_fidelity.py`, which is **untracked**
(`.gitignore` excludes `bin/_*.py`) and scores **one part passed on argv**. So
the project's best-evidenced number was not reproducible from a checkout, and
nothing swept the corpus at all.

That is the same defect `pyscript/soundmonitor_sweep.py` and
`pyscript/sdi_native_sweep.py` were promoted to fix, and this is the third
instance. It derives its corpus from the tracked SID directory rather than
naming one.

IT SCORES THE ARTIFACT, NOT A REBUILD. That is deliberate and it is the lesson
this player just taught: `cffc51e` fixed the `$D418` passband in the builder on
2026-08-10 and 968 of 984 shipped `.sf2` still predated it two days later, while
DMC.md quoted the builder. A sweep that rebuilds before measuring would have
reported the corpus healthy and told you nothing about what shipped. Use
`--build` when you want the other question answered.

WHAT IT DOES NOT COVER, stated because it is easy to misread the totals:
  - **Part 1 only, and only when its span is KNOWN.** DMC's adaptive splitter
    emits parts of 2-20 s -- `Cant_Stop` has 114, `Alf_TV_Theme` 40 -- and the
    part->original-window mapping is printed at build time, not stored in the
    SF2. Scoring
    part 1 against a fixed 20 s window is therefore a guess, and the
    magnitudes were measured rather than assumed. Part-1 spans across this
    corpus run **6.9 s to 399.9 s**, so a fixed window over-runs some files and
    falls short of others, and it is wrong in BOTH directions:

        Alf_TV_Theme      span  6.9s   20s said 73.9/69.4/58.4   true 99.7/99.7/99.7
        Camel_Riders_Inc  span  9.9s   20s said 49.3/20.4/43.2   true 85.1/40.9/81.9
        Cant_Stop         span 17.9s   20s said 34.8/86.0/91.5   true 37.2/95.2/98.1
        Blobby            span 67.9s   20s said v3 97.9          true v3 59.5
        Blue_Monday_88    span 37.9s   20s said v1 87.8          true v1 65.8

    The over-run cases understate (the window runs past part 1 into music it
    never contained). The SHORT cases FLATTER -- `Blobby`'s 20 s stopped before
    the divergence and reported 97.9% where its real 67.9 s part scores 59.5%.
    A guessed window does not merely add noise; it can hide a defect.

    So the window must be ASSERTED. `--build` reads the real bounds off the
    builder's own stdout; `--seconds N` lets a caller assert one for a spot
    check. With neither, NOTHING is scored -- every row says NEEDS BOUNDS. A
    sweep that scores nothing is a nuisance; one that scores the wrong window
    is a published number, and this project has retracted several of those.
  - **freq / waveform / pulse only.** `$D418` is in none of them -- which is
    precisely how the passband defect survived here for two days. Run
    `pyscript/passband_check.py --player dmc` for that dimension; it is a
    separate tool because folding it in here would leave the same blind spot in
    a longer function.

    py -3 pyscript/dmc_native_sweep.py
    py -3 pyscript/dmc_native_sweep.py --files Balloon Rockbuster
    py -3 pyscript/dmc_native_sweep.py --json out.json
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import (  # noqa: E402
    freq_to_semi, fmt_pct, part_span, psid_wrap, score_pct,
    siddump_per_frame, underpowered)
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(ROOT, "SID", "JohannesBjerregaard")
BUILD_DIR = os.path.join(ROOT, "out", "dmc")

# The builder boots a few frames after the original; every scorer in this repo
# fits this rather than assuming it. Range matches `_dmc_fidelity.py`'s, so the
# published numbers reproduce exactly.
OFFSETS = range(-6, 12)


def corpus_files(limit=None, names=None):
    """The sweep corpus, DERIVED from the tracked SID directory.

    Not a curated list -- a named list is what let "the best-evidenced number in
    the project" rest on a single file measured by an untracked script.
    """
    if names:
        return list(names)
    out = sorted(os.path.splitext(os.path.basename(p))[0]
                 for p in glob.glob(os.path.join(CORPUS_DIR, "*.sid")))
    return out[:limit] if limit else out


_PART1 = re.compile(r"part 1/\d+ \(\d+-\d+s, (\d+)-(\d+)f\)")


def part1_span(text):
    """Frames covered by part 1, read off the builder's own stdout.

    Takes the LAST `part 1/N` line, not the first. This builder runs a legato
    A/B before the real build -- two PROBE builds (`_abg`, `_abl`) over a 90 s
    head, to decide which voices are legato -- and each emits its own part
    lines into the same stdout:

        part 1/1 (0-90s, 0-4500f)     <- a probe build, different span
        part 1/2 (0-7s, 0-395f)       <- the part actually emitted

    `search()` took the trial, so `Happy_Jingle`'s 7-second part 1 was scored
    over 90 seconds and read 23.4/16.1/8.1 where it is really 98.3/100.0/98.8.
    Past its end our part LOOPS against the original's continuing music and the
    difference scores as a defect -- the same error this module's own docstring
    documents, surviving in the one place that parses it back.

    Prefer `part_span` (the `.span` sidecar) over this: the sidecar is written
    by the code that emitted the artifact, and a record beats a re-parse of a
    log. Returns None when no line is present -- never zero.
    """
    ms = list(_PART1.finditer(text))
    return int(ms[-1].group(2)) - int(ms[-1].group(1)) if ms else None


def _probe(sf2_path):
    """PSID-wrap a built .sf2 so siddump will play it."""
    sf2 = open(sf2_path, "rb").read()
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(bytearray(sf2), info)
    probe = os.path.join(BUILD_DIR, "_dmc_sweep_probe.sid")
    open(probe, "wb").write(psid_wrap(bytes(sf2[2:]), sla, 0x1000, 0x1003))
    return probe


def score_pair(orig, prb, secs):
    """Per-voice freq/wf/pulse agreement at the best-fitting boot offset.

    Returns ({voice: {metric: pct|None}}, n, offset). Percentages come from
    `score_pct`, so a metric nothing exercised is None -- never 100.0, never
    0.0. The frame count is returned so the caller can mark a thin comparison:
    a DMC part can be a couple of seconds long and would otherwise print the
    same confident 100.0 as `Balloon`'s 20,000 frames.
    """
    n = min(len(orig), len(prb), secs * 50) - 4
    if n <= 0:
        return None, 0, 0

    def fit(d):
        s = 0
        for i in range(0, n, 2):                     # every other frame: the
            j = d + i                                # offset fit does not need
            if not (0 <= j < len(orig)):             # every one, and this is
                continue                             # the hot loop
            for vi in range(3):
                a, b = orig[j][0][vi]["freq"], prb[i][0][vi]["freq"]
                if a and b and freq_to_semi(a) == freq_to_semi(b):
                    s += 1
        return s

    dly = max(OFFSETS, key=fit)
    per = {}
    counted = 0
    for vi in range(3):
        tot = {k: 0 for k in ("freq", "wf", "pul")}
        ok = dict(tot)
        atot = dict(tot)
        aok = dict(tot)
        for i in range(n):
            j = dly + i
            if not (0 <= j < len(orig)):
                continue
            o, p = orig[j][0][vi], prb[i][0][vi]
            # AUDIBLE = either side has the gate bit set. A voice that has not
            # entered yet is gated off on BOTH sides and inaudible, but the two
            # sides' idle registers still differ -- the original holds whatever
            # init left in $D404/$D400, ours holds the rest row's. Scoring those
            # frames answers a question nobody asked, and it dominates: after the
            # leading-rest fix `Billie_Jean` v2 has 962 of its 1,896 frames before
            # the voice enters, so its raw wf reads 49.3% while every one of the
            # 190 frames it actually sounds is exact. Quote BOTH columns with
            # their n (the same discipline FC's raw/audible pair carries) -- raw
            # alone hides a real regression behind a rest, and audible alone is
            # blind to a defect that plays through a release tail.
            aud = bool(((o["wf"] or 0) | (p["wf"] or 0)) & 1)
            for k in tot:
                if o[k] is None and p[k] is None:
                    continue        # neither side ever wrote it: not a test
                tot[k] += 1
                if k == "freq":
                    hit = (o[k] is not None and p[k] is not None
                           and freq_to_semi(o[k]) == freq_to_semi(p[k]))
                else:
                    hit = o[k] == p[k]
                ok[k] += hit
                if aud:
                    atot[k] += 1
                    aok[k] += hit
        per[vi] = {k: score_pct(ok[k], tot[k]) for k in tot}
        per[vi]["audible"] = {k: score_pct(aok[k], atot[k]) for k in tot}
        per[vi]["audible_n"] = atot["freq"]
        counted = max(counted, tot["freq"])
    return per, counted, dly


_REFUSALS = (
    "tables not located",
    "cannot build",
    "no sound table",
    "onsets disagree",
)


def _classify_build_failure(text):
    """Builder refusal (a result) vs unexpected failure (a fault).

    The builder states its reason; anything matching one of the known refusal
    phrases is recorded as `refused` with that reason rather than counted as an
    error. Unknown failures stay errors -- a refusal list that swallows
    everything would hide a real break.
    """
    tail = [l for l in text.splitlines() if l.strip()]
    last = tail[-1][:160] if tail else ""
    for phrase in _REFUSALS:
        if phrase in text:
            return {"refused": last or phrase}
    return {"error": last or "build failed with no output"}


def measure(name, secs, build=False, timeout=1800):
    """One song -> a record. Distinguishes the outcomes that matter: scored,
    never built, or source missing."""
    sid = os.path.join(CORPUS_DIR, f"{name}.sid")
    if not os.path.exists(sid):
        return {"error": "no .sid in corpus dir"}
    span = None
    if build:
        import subprocess
        r = subprocess.run(
            [sys.executable, os.path.join(ROOT, "bin", "build_dmc_native_song.py"),
             sid, "auto"], capture_output=True, text=True, cwd=ROOT, timeout=timeout)
        if r.returncode != 0:
            return _classify_build_failure(r.stdout + r.stderr)
        span = part1_span(r.stdout + r.stderr)
    parts = sorted(glob.glob(os.path.join(BUILD_DIR, f"{name}_part*.sf2")))
    if parts:
        # The artifact's OWN record wins over re-parsing the builder's stdout.
        # `_write_span` is called by the emitter with the window it just built,
        # so it cannot pick up a discarded trial split the way a log scrape can
        # -- which is exactly how `Happy_Jingle` came to be scored over 90s of a
        # 7s part. It also retires the `needs_bounds` class without a rebuild.
        # Frames, to match part1_span.
        secs_span = part_span(parts[0])
        if secs_span:
            span = secs_span * 50
    if not parts:
        # NOT an error and NOT a zero: 32 of the 88 corpus files are NO-TABLES
        # or FALLBACK and were never built. Scoring them 0 would make a build
        # gap look like a fidelity gap.
        return {"not_built": True}
    if span is None and secs is None:
        # Refuse rather than emit a plausible number. Without a `.span` sidecar
        # a part's window is not recoverable from the SF2 -- not for a
        # multi-part song, and not for a single-part one either, whose span is
        # the whole song and whose length varies. Forcing Balloon's 400 s onto
        # `Zoom` scored it 24.4/27.7/23.9 with a confident n=19996; the window
        # was measuring itself. See module docstring. An artifact built before
        # the sidecar existed still lands here, which is correct: absent is not
        # zero, and a rebuild (or --build) is what establishes it.
        return {"needs_bounds": True, "parts": len(parts)}
    win = (span // 50 if span else secs) if span is None or secs is None         else min(secs, max(1, span // 50))
    win = max(1, win)
    prb = _probe(parts[0])
    orig = siddump_per_frame(sid, ["-a0", f"-t{win + 1}"])
    got = siddump_per_frame(prb, [f"-t{win + 1}"])
    per, n, dly = score_pair(orig, got, win)
    if per is None:
        return {"error": f"empty window (orig={len(orig)} probe={len(got)})"}
    return {"voices": {str(v): per[v] for v in per}, "n": n, "offset": dly,
            "parts": len(parts)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", nargs="*", help="explicit song names (no .sid)")
    ap.add_argument("--limit", type=int, help="first N corpus files only")
    ap.add_argument("--seconds", type=int, default=None,
                    help="ASSERT the window in seconds. Without it, and without "
                         "--build, nothing is scored: a part's span is not in "
                         "the SF2 and a guessed window measures itself. The "
                         "published Balloon figure used 400.")
    ap.add_argument("--build", action="store_true",
                    help="rebuild before scoring (answers a DIFFERENT question: "
                         "'is the builder right' rather than 'is what shipped right')")
    ap.add_argument("--json", help="write the full per-file record here")
    ap.add_argument("--jobs", "-j", type=int, default=1, metavar="N",
                    help="build/score N songs concurrently (default 1). Sets "
                         "MON_BUILD_LOCK=1 so the one section touching shared "
                         "driver state is serialised -- that is what makes it "
                         "safe, see PATTERNS F2. Results are collected in "
                         "CORPUS ORDER regardless of completion order, so the "
                         "output is byte-comparable against a -j1 run.")
    a = ap.parse_args(argv)

    corpus = corpus_files(a.limit, a.files)
    print(f"DMC native sweep -- {len(corpus)} file(s) from {CORPUS_DIR}", flush=True)
    win_note = (f"{a.seconds}s window (asserted)" if a.seconds
                else "window from the builder" if a.build
                else "NO WINDOW GIVEN -- nothing will be scored")
    print(f"  scoring PART 1 only, freq/wf/pulse only, {win_note}"
          f"{' (rebuilding first)' if a.build else ' (as shipped)'}", flush=True)
    results = {}
    pre = {}
    if a.jobs > 1:
        # The lock is the WHOLE safety argument, so set it here rather than
        # trusting the caller. Builds serialise on the one section that touches
        # shared driver state (see _build_lock in build_mon_native_song), so the
        # bytes are identical to a serial run by construction. Without it a
        # parallel sweep interleaves driver tables and every number it prints is
        # suspect -- measured, not feared: an unguarded -j4 corrupted 5 of 71
        # artifacts while the part-1-only scores read identical.
        os.environ["MON_BUILD_LOCK"] = "1"
        from concurrent.futures import ThreadPoolExecutor
        print(f"  -j{a.jobs}: MON_BUILD_LOCK=1 (shared driver state serialised)",
              flush=True)
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            futs = {ex.submit(measure, n, a.seconds, a.build): n for n in corpus}
            for f in futs:
                pass
            for fut, n in futs.items():
                try:
                    pre[n] = fut.result()
                except Exception as e:            # one song must not sink the sweep
                    pre[n] = {"error": f"{type(e).__name__}: {e}"}
    for i, name in enumerate(corpus, 1):
        rec = pre[name] if name in pre else measure(name, a.seconds, a.build)
        results[name] = rec
        if rec.get("voices"):
            cells = []
            for v in ("0", "1", "2"):
                m = rec["voices"][v]
                cell = (f"v{int(v)+1} f{fmt_pct(m['freq'], n=rec['n'])}"
                        f"/w{fmt_pct(m['wf'], n=rec['n'])}"
                        f"/p{fmt_pct(m['pul'], n=rec['n'])}")
                # Show the audible column only where it DIFFERS -- a voice that
                # sounds throughout its window has nothing extra to say, and a
                # second number on every row is how the first one stops being read.
                au, an = m.get("audible"), m.get("audible_n") or 0
                if au and an and any(
                        au[k] is not None and m[k] is not None
                        and abs(au[k] - m[k]) >= 0.05 for k in ("freq", "wf", "pul")):
                    cell += (f" [aud f{fmt_pct(au['freq'], n=an)}"
                             f"/w{fmt_pct(au['wf'], n=an)}"
                             f"/p{fmt_pct(au['pul'], n=an)} n={an}]")
                cells.append(cell)
            print(f"  [{i}/{len(corpus)}] {name:28s} dly={rec['offset']:+d} "
                  f"{'  '.join(cells)}  n={rec['n']} parts={rec['parts']}", flush=True)
        elif rec.get("refused"):
            print(f"  [{i}/{len(corpus)}] {name:28s} "
                  f"REFUSED ({rec['refused'][:70]})", flush=True)
        elif rec.get("not_built"):
            print(f"  [{i}/{len(corpus)}] {name:28s} NOT BUILT", flush=True)
        elif rec.get("needs_bounds"):
            print(f"  [{i}/{len(corpus)}] {name:28s} NEEDS BOUNDS "
                  f"({rec['parts']} parts; re-run with --build)", flush=True)
        else:
            print(f"  [{i}/{len(corpus)}] {name:28s} ERROR {rec.get('error')}",
                  flush=True)

    scored = {k: v for k, v in results.items() if v.get("voices")}
    not_built = sum(1 for v in results.values() if v.get("not_built"))
    needs = sum(1 for v in results.values() if v.get("needs_bounds"))
    refused = sum(1 for v in results.values() if v.get("refused"))
    errored = len(results) - len(scored) - not_built - needs - refused
    print(f"\nscored {len(scored)}  refused {refused}  not built {not_built}  "
          f"needs bounds {needs}  errored {errored}  of {len(corpus)}")
    if needs:
        print(f"  ({needs} multi-part song(s) not scored: part 1's span is not "
              f"in the SF2, and a fixed window measures itself. Use --build.)")
    thin = [k for k, v in scored.items() if underpowered(v["n"])]
    if thin:
        print(f"!! {len(thin)} scored over a thin window (marked `!`): "
              f"{', '.join(sorted(thin)[:8])}"
              f"{' ...' if len(thin) > 8 else ''}")
    # A bare failure count is not a finding. Group by cause -- "16 files exceed
    # a 256-row table" and "16 files crashed" are different pieces of work, and
    # only one of them is a bug.
    if refused or errored:
        classes = {}
        for k, v in results.items():
            msg = v.get("refused") or v.get("error")
            if not msg:
                continue
            if "not located" in msg:
                key = "DMC tables not located (variant)"
            elif "WAVE overflow" in msg:
                key = "WAVE overflow (builder cap, >256 rows)"
            elif "timeout" in msg.lower():
                key = "timeout"
            elif "onsets disagree" in msg:
                key = "onsets disagree (multispeed / self-IRQ)"
            else:
                key = msg[:60]
            classes.setdefault(key, []).append(k)
        print("\nfailure classes:")
        for key, files in sorted(classes.items(), key=lambda kv: -len(kv[1])):
            print(f"  {len(files):4d}  {key}")

    # Medians per metric, over every voice of every scored file. Medians, not
    # means, matching how this repo already quotes SDI.
    #
    # BOTH columns, always. A build can be strictly better and score WORSE raw:
    # a voice placed at its true entry frame spends the frames before it on rest
    # rows, where the original is holding whatever init left -- inaudible on both
    # sides and counted by neither ear. Printing only `raw` would have read the
    # leading-rest fix as a corpus-wide regression. Printing only `audible` would
    # hide a defect that plays through a release tail, which is the trap
    # MATTGRAY.md records. Neither number is the answer on its own.
    def _median(vals):
        vals = sorted(vals)
        if not vals:
            return None
        return (vals[len(vals) // 2] if len(vals) % 2 else
                (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2)

    for metric in ("freq", "wf", "pul"):
        vals = [m[metric] for v in scored.values()
                for m in v["voices"].values() if m[metric] is not None]
        if not vals:
            continue
        line = (f"  {metric:>5s}: median {_median(vals):6.1f}  over {len(vals)} "
                f"voices, {sum(1 for x in vals if x >= 99.95)} at 100, "
                f"{sum(1 for x in vals if x < 90)} below 90")
        av = [m["audible"][metric] for v in scored.values()
              for m in v["voices"].values()
              if m.get("audible") and m["audible"].get(metric) is not None]
        if av:
            line += (f"   | audible median {_median(av):6.1f} over {len(av)} "
                     f"voices, {sum(1 for x in av if x < 90)} below 90")
        print(line)
    print("\nNOT a $D418 figure -- run pyscript/passband_check.py --player dmc")
    if a.json:
        json.dump(results, open(a.json, "w", encoding="utf-8"), indent=1)
        print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
