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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(ROOT, "SID", "Gallefoss_Glenn")
BUILDER = os.path.join(ROOT, "bin", "build_sdi_native_song.py")

# A SWEEP THAT CANNOT LAUNCH A PROCESS IS NOT A SWEEP THAT MEASURED A FILE.
# The first full-corpus run of this script returned these codes for every file
# from #275 of 441 onward -- ~5 h in, the long-lived parent could no longer spawn
# a child -- and the summary counted all 167 as "errored", i.e. reported an
# infrastructure collapse in the same column as `not an SDI play+3 rip`. Three of
# them built cleanly on a fresh invocation, so the run had fabricated 167 results
# and its own per-variant medians silently became an A-O sample. These codes are
# therefore quarantined from the result classes and abort the run by default.
LAUNCH_FAILURE_RCS = {
    3221225794: "STATUS_DLL_INIT_FAILED (0xC0000142)",
    3221225495: "STATUS_NO_MEMORY (0xC0000017)",
    3221225781: "STATUS_DLL_NOT_FOUND (0xC0000135)",
}

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
        if not tail and r.returncode in LAUNCH_FAILURE_RCS:
            rec["infra"] = LAUNCH_FAILURE_RCS[r.returncode]
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
    ap.add_argument("--infra-abort", type=int, default=3, metavar="N",
                    help="stop after N consecutive process-LAUNCH failures "
                         "(0 disables); once the host stops spawning children "
                         "every later file is recorded as a failure it never had")
    a = ap.parse_args(argv)

    corpus = corpus_files(a.limit, a.files)
    print(f"SDI Stage B sweep -- {len(corpus)} file(s) from {CORPUS_DIR}", flush=True)
    results = {}
    consec_infra = 0
    for i, name in enumerate(corpus, 1):
        rec = build_one(name, a.timeout)
        results[name] = rec
        if rec.get("infra"):
            consec_infra += 1
            print(f"  [{i}/{len(corpus)}] {name:34s} {'?':5s} "
                  f"LAUNCH FAILURE ({rec['infra']}) -- not a result", flush=True)
            if a.infra_abort and consec_infra >= a.infra_abort:
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
        json.dump({"results": results, "summary": s},
                  open(a.json, "w", encoding="utf-8"), indent=1)
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
