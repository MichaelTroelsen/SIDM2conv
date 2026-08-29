"""The headless probe's COVERAGE BOUNDARY, pinned so it cannot be assumed away.

`docs/plans/ABPAGE_PORT_PLAN.md` step 5 requires three observations in a real
browser: (a) audio plays and switches, (b) the envelope canvas drew, (c) blind
mode randomizes and tallies. The `claude-in-chrome` MCP that would make them is
not connected on this machine, and `pyscript/abpage_browser_probe.py` was
accepted as the substitute.

It is a PARTIAL substitute and these tests exist to keep that visible. Measured
against the real served page (Angular, port 8730), the probe reports per-voice
highlighted rows, transforms and the status line -- the pattern-scroll path --
and NOTHING about audio, canvas or blind mode. The risk this guards against is
not that the probe is wrong; it is that a future reader sees "browser probe,
passing" and marks step 5 done.

These are static checks on the probe's own injected script. That is deliberate:
they must run in CI with no Chrome, no server and no staged WAVs, or they would
be skipped exactly where they are needed.
"""
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

PROBE_PY = os.path.join(_HERE, "abpage_browser_probe.py")


def _probe_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_abpp", PROBE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_probe_simulates_audio_and_therefore_cannot_observe_it():
    """(a) is NOT covered, and the stub is the proof.

    The injected script redefines currentTime/duration/paused and replaces
    play(). A page whose audio never starts is indistinguishable from one that
    works, because nothing here ever decodes.
    """
    src = _probe_module().PROBE
    assert 'defineProperty(m, "currentTime"' in src
    assert 'm.play = function () {}' in src
    assert 'get: function () { return t; }' in src


def test_the_probe_never_reads_a_canvas():
    """(b) is NOT covered -- the observation the plan says needs http, not file://."""
    src = _probe_module().PROBE
    assert "canvas" not in src.lower()
    assert "getContext" not in src
    assert "getImageData" not in src


def test_the_probe_never_touches_blind_mode():
    """(c) is NOT covered: no blind control is driven and no trial is repeated."""
    src = _probe_module().PROBE
    low = src.lower()
    assert "blind" not in low
    assert "random" not in low


def test_what_the_probe_DOES_sample_is_the_scroll_path():
    """The positive half: the boundary is a boundary, not a blanket failure.

    If this stops matching, the probe has been rewritten and the three
    not-covered tests above need re-checking rather than trusting.
    """
    src = _probe_module().PROBE
    for token in ('"trkin"', "trkin", "trkstat", "transform", "cur"):
        assert token.strip('"') in src, token
    assert "requestAnimationFrame" in src          # rAF ticks are reported
    assert "PROBE_RESULT" in src                   # results come back via the DOM


def test_the_uncovered_observations_are_named_in_the_module_docstring():
    """The gap must stay written down where the next reader will look.

    A coverage boundary that lives only in a run log is one `/whattask` away
    from being forgotten; this keeps it in the file itself.
    """
    doc = _probe_module().__doc__ or ""
    assert "NOT COVERED" in doc
    assert doc.count("NOT COVERED") >= 3, doc.count("NOT COVERED")
    assert "ABPAGE_PORT_PLAN" in doc
    assert re.search(r"step 5 needs a human or the MCP", doc), doc[-400:]
