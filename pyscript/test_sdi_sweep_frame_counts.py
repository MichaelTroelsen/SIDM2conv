"""The SDI Stage B fidelity print carries its frame count -- and what that n is NOT.

The corpus sweep publishes 786 per-voice percentages. Until now the builder
printed `voice N: X%` with no denominator, so `underpowered()` could not mark a
thin comparison and CLAUDE.md's rule -- never quote a fidelity number without its
n -- could not be satisfied by anything downstream.

Wiring it in is straightforward. The part worth pinning is the LIMIT, because it
is not visible in the output: `measure_parts` skips a frame only when BOTH sides
have freq 0, and siddump holds a voice's last written frequency through rests, so
after a voice's first note its freq is essentially never 0 again. The n that
results is therefore the SONG LENGTH, identical across all three voices
(measured: Kirby 2144/2144/2144, Delta 7770/7770/7770, Eurovision 802/802/802).

So this n answers "was the song long enough to mean anything?" and NOT "did THIS
voice carry enough information?" -- a voice that plays one note and falls silent
scores over the same n as one that plays throughout. That second question is the
one a PER-VOICE percentage actually needs, and it is still unanswered.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sdi_native_sweep as sw  # noqa: E402
from sidm2.fidelity_common import MIN_INFORMATIVE_FRAMES, fmt_pct  # noqa: E402

_NEW = ("Kirby: la=$1000 variant=E\n"
        "  FIDELITY (per-frame freq+wf semitone, all parts vs original):\n"
        "    voice 0:  99.7%  (n=2144)\n"
        "    voice 1: 100.0%  (n=2144)\n"
        "    voice 2:  99.7%  (n=2144)\n"
        "packed into 5 adaptive parts\n")

_THIN = ("Sting: la=$1000 variant=A\n"
         "    voice 0:  99.7!%  (n=46)\n"
         "    voice 1: 100.0!%  (n=46)\n"
         "    voice 2:  98.0!%  (n=46)\n"
         "packed into 1 adaptive part\n")

# What a checkout from before this change emitted.
_OLD = ("Kirby: la=$1000 variant=E\n"
        "    voice 0:  99.7%\n"
        "    voice 1: 100.0%\n"
        "    voice 2:  99.7%\n"
        "packed into 5 adaptive parts\n")


def test_the_sweep_records_the_frame_count():
    rec = sw.parse_build_output(_NEW)
    assert rec["voices"] == [99.7, 100.0, 99.7]
    assert rec["n"] == [2144, 2144, 2144]


def test_a_marked_percentage_still_parses_as_its_number():
    """The `!` must not corrupt the value -- the sweep medians read these."""
    rec = sw.parse_build_output(_THIN)
    assert rec["voices"] == [99.7, 100.0, 98.0]
    assert rec["n"] == [46, 46, 46]


def test_output_without_n_is_recorded_as_unknown_not_as_a_number():
    """A build from an older checkout must not silently acquire a fabricated
    count -- `no n` and `n=0` are different claims."""
    rec = sw.parse_build_output(_OLD)
    assert rec["voices"] == [99.7, 100.0, 99.7]
    assert rec["n"] is None


def test_the_rollup_names_files_whose_n_is_unknown():
    s = sw.summarize({
        "new": {"voices": [99.7, 100.0, 99.7], "variant": "E", "n": [2144] * 3},
        "old": {"voices": [99.0, 99.0, 99.0], "variant": "E", "n": None},
        "thin": {"voices": [100.0, 100.0, 100.0], "variant": "A", "n": [46] * 3},
    })
    assert s["files_without_n"] == 1
    assert s["thin_voices"] == 3


def test_the_marker_fires_only_below_the_threshold():
    assert fmt_pct(99.7, n=MIN_INFORMATIVE_FRAMES - 1).endswith("!")
    assert not fmt_pct(99.7, n=MIN_INFORMATIVE_FRAMES).endswith("!")


def test_the_builder_prints_a_count_for_every_voice():
    """Source-level pin: the print site must pass n, or the whole chain above is
    parsing something that is never emitted."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "bin", "build_sdi_native_song.py"),
        encoding="utf-8").read()
    assert "fmt_pct(per[v], n=ns[v])" in src
    assert re.search(r"underpowered\(n\) for n in ns", src), \
        "the builder must explain the marker when one fires"
