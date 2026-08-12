"""The third guard: "were there ENOUGH frames?"

`score_pct` stops an empty comparison reporting 100%; `exercised` stops a
comparison full of frames but empty of information reporting it either. Neither
asks whether there were *enough* frames to mean anything -- so a voice compared
over 46 frames printed a 100.0 identical to one compared over 6,000, and a
corpus table averaged a 1-second stinger against a 2-minute song.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import (  # noqa: E402
    MIN_INFORMATIVE_FRAMES, fmt_pct, underpowered,
)


def test_underpowered_only_below_the_threshold():
    assert underpowered(46)
    assert underpowered(MIN_INFORMATIVE_FRAMES - 1)
    assert not underpowered(MIN_INFORMATIVE_FRAMES)
    assert not underpowered(6000)


def test_underpowered_ignores_none():
    """None is `score_pct`'s "no evidence" case and is already handled there;
    it must not additionally read as underpowered."""
    assert not underpowered(None)


def test_existing_fmt_pct_callers_are_byte_identical():
    """~40 call sites and several output-parsing scripts depend on this format.
    Without `n` the rendering must not change at all."""
    assert fmt_pct(99.7) == " 99.7"
    assert fmt_pct(100.0) == "100.0"
    assert fmt_pct(None) == "  n/a"
    assert fmt_pct(1.0, width=7, prec=3) == "  1.000"


def test_fmt_pct_marks_a_thin_comparison():
    assert fmt_pct(100.0, n=46) == "100.0!"
    assert fmt_pct(100.0, n=6000) == "100.0"


def test_a_thin_comparison_that_measured_nothing_stays_n_a():
    """`!` must never turn an absent measurement into a present-looking one --
    None outranks it."""
    assert fmt_pct(None, n=46) == "  n/a"


def test_the_builder_reports_the_marker():
    """The guard is worthless if it is computed and not shown."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(root, "bin", "build_mattgray_native_song.py"),
               encoding="utf-8").read()
    assert "underpowered" in src
    assert "MIN_INFORMATIVE_FRAMES" in src
