"""Tests for pyscript/dmc_tolerance_sweep.py (PATTERNS D10 tolerance scoring).

The invariant that matters is `test_k0_reproduces_score_pair`: at k=0 this
scorer must agree with `dmc_native_sweep.score_pair`, because a tolerance sweep
that disagrees with the strict column at zero tolerance is a DIFFERENT SCORER,
not a different tolerance -- and its k=2/k=10 columns then measure the
disagreement between two scorers rather than a phase defect.

That is not hypothetical. The first version of this module compared `freq` by
raw equality; `score_pair` compares it by SEMITONE. It scored Roadblaster v2 at
58.2 where the sweep says 96.9, which would have manufactured a "different
content" bucket full of pitch-correct voices. `test_freq_compared_by_semitone`
pins that specific bug.

Everything here runs on synthetic frames: no build, no siddump, no artifacts.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyscript.dmc_native_sweep as S  # noqa: E402
import pyscript.dmc_tolerance_sweep as T  # noqa: E402


def frames(per_voice, n):
    """siddump_per_frame's shape: [({voice: {metric: value}}, fcut), ...].

    `per_voice(vi, i)` returns the dict for voice vi at frame i.
    """
    return [({vi: per_voice(vi, i) for vi in range(3)}, 0) for i in range(n)]


def steady(freq=4000, wf=65, pul=2048):
    return lambda vi, i: {"freq": freq + vi, "wf": wf, "pul": pul}


def melody(shift=0):
    """A series that actually varies, so a comparison over it is informative."""
    def f(vi, i):
        j = i + shift
        return {"freq": 3000 + ((j * 37) % 500), "wf": 65 if (j // 8) % 2 else 17,
                "pul": 1024 + ((j * 11) % 300)}
    return f


N = 300
SECS = 6


def test_identical_series_scores_100_at_every_k():
    a = frames(melody(), N)
    out, n = T.tol(a, a, SECS, 0)
    assert n > 0
    for vi in range(3):
        for k in T.KS:
            for m in T.METRICS:
                assert out[vi][k][m] == 100.0, (vi, k, m)


def test_freq_compared_by_semitone_not_raw():
    """The regression test for the bug this module shipped with.

    Two raw frequencies that map to the same semitone must count as a MATCH,
    exactly as score_pair counts them.
    """
    base = 3000
    same = next((f for f in range(base + 1, base + 400)
                 if S.freq_to_semi(f) == S.freq_to_semi(base)), None)
    assert same is not None, "no semitone-equal pair found; adjust base"
    assert same != base

    a = frames(steady(freq=base), N)
    b = frames(steady(freq=same), N)
    out, _ = T.tol(a, b, SECS, 0)
    # voice 0's freq is base+0 vs same+0 -- different raw, same semitone.
    assert out[0][0]["freq"] == 100.0, "freq must be compared by semitone"


def test_bounded_skew_recovers_at_k2_and_is_flat_to_k10():
    """D10's 'bounded per-note skew' signature: recovers at +-2, no further gain."""
    a = frames(melody(), N)
    b = frames(melody(shift=2), N)
    out, _ = T.tol(a, b, SECS, 0)
    strict = out[0][0]["wf"]
    at2 = out[0][2]["wf"]
    at10 = out[0][10]["wf"]
    assert strict < at2, (strict, at2)
    assert at2 >= 99.0
    assert at10 == pytest.approx(at2, abs=1.0), (at2, at10)


def test_different_content_does_not_recover():
    """The 'content' bucket: tolerance cannot rescue genuinely different music."""
    a = frames(lambda vi, i: {"freq": 3000 + (i * 37) % 500, "wf": 65, "pul": 1024}, N)
    b = frames(lambda vi, i: {"freq": 9000 - (i * 91) % 700, "wf": 65, "pul": 1024}, N)
    out, _ = T.tol(a, b, SECS, 0)
    assert out[0][0]["freq"] < 50.0
    assert out[0][10]["freq"] < 80.0, "content should not reach a recovery plateau"


def test_metric_neither_side_wrote_is_not_scored():
    """score_pct must return None, never 0.0 or 100.0, when nothing was compared."""
    def none_pul(vi, i):
        d = melody()(vi, i)
        d["pul"] = None
        return d
    a = frames(none_pul, N)
    out, _ = T.tol(a, a, SECS, 0)
    assert out[0][0]["pul"] is None, "a metric neither side wrote is not a test"
    assert out[0][0]["freq"] == 100.0, "the other metrics still score"


@pytest.mark.parametrize("shift", [0, 3])
def test_k0_reproduces_score_pair(shift):
    """THE invariant: at k=0 this scorer equals dmc_native_sweep's strict column.

    Run at score_pair's own fitted offset, so the two see the same alignment and
    any difference is a scoring difference rather than a windowing one.
    """
    a = frames(melody(), N)
    b = frames(melody(shift=shift), N)
    per, n, dly = S.score_pair(a, b, SECS)
    assert per is not None and n > 0
    out, _ = T.tol(a, b, SECS, dly)
    for vi in range(3):
        for m in T.METRICS:
            mine, theirs = out[vi][0][m], per[vi][m]
            if mine is None or theirs is None:
                assert mine is theirs, (vi, m, mine, theirs)
            else:
                assert mine == pytest.approx(theirs, abs=0.05), (vi, m, mine, theirs)


def test_freq_zero_is_not_treated_as_missing():
    """A genuine freq=0 write must score as a SILENCE match, not get dropped.

    key() used to route freq through `None if not x else ...`, which sends the
    falsy 0 down the same branch as an actual None. `freq_to_semi(0)` already
    returns -1 (silence) -- there is no need to special-case 0 at all, and
    doing so made two real zero-frequency writes look like "neither side
    wrote it", which score_pair (an `is not None` check) does not do.
    """
    def zero_freq(vi, i):
        d = melody()(vi, i)
        d["freq"] = 0
        return d
    a = frames(zero_freq, N)
    per, n, dly = S.score_pair(a, a, SECS)
    assert per is not None and n > 0
    out, _ = T.tol(a, a, SECS, dly)
    assert per[0]["freq"] == 100.0, "sanity: score_pair credits a 0/0 freq match"
    assert out[0][0]["freq"] == pytest.approx(per[0]["freq"], abs=0.05)


def test_ks_and_metrics_are_the_documented_ones():
    assert T.KS == (0, 2, 10), "D10 specifies k = 0, 2, 10"
    assert set(T.METRICS) == {"freq", "wf", "pul"}
