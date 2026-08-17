"""PATTERNS D10 tolerance sweep over the CURRENT DMC artifacts (k = 0, 2, 10).

Mirrors dmc_native_sweep.measure's window/probe/offset logic exactly, so the
k=0 column reproduces the sweep's strict column instead of being a second
implementation of it. Anything else would compare two scorers, not two k.
"""
import glob, io, json, os, sys, time
sys.path.insert(0, os.getcwd())
from concurrent.futures import ProcessPoolExecutor, as_completed
import pyscript.dmc_native_sweep as S
from sidm2.fidelity_common import score_pct, part_span, siddump_per_frame

KS = (0, 2, 10)
METRICS = ("freq", "wf", "pul")


def series(name):
    """(orig, probe, win, dly) using measure()'s own rules, or a reason."""
    sid = os.path.join(S.CORPUS_DIR, name + ".sid")
    if not os.path.exists(sid):
        return None, "no .sid"
    parts = sorted(glob.glob(os.path.join(S.BUILD_DIR, name + "_part*.sf2")))
    if not parts:
        return None, "not built"
    span = part_span(parts[0])
    if span is None:
        return None, "needs bounds"
    win = max(1, span)
    prb = S._probe(parts[0])
    try:
        orig = siddump_per_frame(sid, ["-a0", "-t%d" % (win + 1)])
        got = siddump_per_frame(prb, ["-t%d" % (win + 1)])
    finally:
        try:
            os.remove(prb)
        except OSError:
            pass
    _per, n, dly = S.score_pair(orig, got, win)
    if _per is None:
        return None, "empty window"
    return (orig, got, win, dly, n), None


def tol(orig, prb, win, dly):
    """Same comparison rules as score_pair -- freq by SEMITONE, everything else
    raw. Using raw equality for freq scored Roadblaster v2 58.2 where the sweep
    says 96.9, which is a different scorer, not a different tolerance."""
    n = min(len(orig), len(prb), win * 50) - 4
    out = {}
    for vi in range(3):
        out[vi] = {}
        for m in METRICS:
            Oraw = [f[0][vi][m] for f in orig]
            Praw = [prb[i][0][vi][m] for i in range(min(n, len(prb)))]
            if m == "freq":
                key = lambda x: None if not x else S.freq_to_semi(x)
            else:
                key = lambda x: x
            Okey = [key(x) for x in Oraw]
            Pkey = [key(x) for x in Praw]
            for k in KS:
                tot = ok = 0
                for i in range(len(Praw)):
                    j = dly + i
                    if not (0 <= j < len(Oraw)):
                        continue
                    if Oraw[j] is None and Praw[i] is None:
                        continue      # neither side ever wrote it: not a test
                    tot += 1
                    pk = Pkey[i]
                    if m == "freq" and pk is None:
                        continue      # a freq hit needs BOTH sides present
                    if k == 0:
                        if Okey[j] == pk and not (m == "freq" and Okey[j] is None):
                            ok += 1
                    elif pk in Okey[max(0, j - k):j + k + 1]:
                        ok += 1
                out[vi].setdefault(k, {})[m] = score_pct(ok, tot)
    return out, n


def one(name):
    try:
        s, why = series(name)
        if s is None:
            return name, {"skip": why}
        orig, got, win, dly, _n = s
        t, n = tol(orig, got, win, dly)
        return name, {"tol": {str(v): {str(k): t[v][k] for k in KS} for v in t},
                      "n": n, "offset": dly, "win": win}
    except Exception as e:                       # a crash on one song must not
        return name, {"skip": "error: %r" % (e,)}   # take the sweep with it


if __name__ == "__main__":
    names = sorted(os.path.splitext(os.path.basename(p))[0]
                   for p in glob.glob(os.path.join(S.CORPUS_DIR, "*.sid")))
    jobs = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    out, t0 = {}, time.time()
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(one, nm): nm for nm in names}
        for c, f in enumerate(as_completed(futs), 1):
            nm, rec = f.result()
            out[nm] = rec
            print("  ...%d/%d %s%s" % (c, len(names), nm,
                  "" if "tol" in rec else "  [" + rec["skip"] + "]"), flush=True)
    json.dump(out, io.open(sys.argv[2] if len(sys.argv) > 2 else "tol.json",
                           "w", encoding="utf-8"))
    print("elapsed %ds, scored %d of %d"
          % (time.time() - t0, sum(1 for r in out.values() if "tol" in r), len(names)))
