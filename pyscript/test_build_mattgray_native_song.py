"""Guard for the Matt Gray builder/parser subtune-default mismatch.

sidm2.mattgray_parser.parse_sid defaults to subtune=1; the builder used to
default its own CLI-derived SUB to 0. That silent disagreement made an
UNQUALIFIED run refuse for a reason that reads exactly like a genuine decode
failure -- "REFUSED: address $0000 outside image $1000-$1a1a" on
Pogo_Stick_Olympics, the same shape as Driller's real refusal -- when passing
subtune=1 decodes and builds cleanly. The census in
docs/players/MATTGRAY.md-adjacent measurement: parse_sid at its own default
(1) decodes 13/55 files under SID/Gray_Matt; forced to 0 it decodes only 2/57
recursive (Last_Ninja_2 and Tusker, whose track-table entry 0 happens to be
non-null too).

These tests are cheap (no siddump/tracing) and pin the fix at the level that
actually matters: the two defaults must not silently disagree again.
"""

import inspect
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if os.path.join(ROOT, "bin") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "bin"))

import build_mattgray_native_song as BM  # noqa: E402
from sidm2.mattgray_parser import MattGrayError, parse_sid  # noqa: E402

# Files that decode under parse_sid's OWN default (subtune=1) but that the
# builder used to refuse unqualified because it forced subtune=0 -- see the
# "REFUSED: address $0000 outside image ..." shape in the task write-up.
DEFAULT_ONLY_FILES = [
    os.path.join(ROOT, "SID", "Gray_Matt", "Pogo_Stick_Olympics.sid"),
    os.path.join(ROOT, "SID", "Gray_Matt", "Warriors.sid"),
]


def test_builder_default_subtune_matches_parser_default():
    """The two defaults must agree -- this is the bug itself, pinned directly.

    SABOTAGE CHECK: restore `SUB = _argv(3, 0, int)` in
    bin/build_mattgray_native_song.py (the pre-fix line) and this must FAIL,
    because sidm2.mattgray_parser.parse_sid's own default is 1, not 0.
    """
    parser_default = inspect.signature(parse_sid).parameters["subtune"].default
    assert BM.SUB == parser_default, (
        f"builder's unqualified default SUB={BM.SUB!r} disagrees with "
        f"parse_sid's own default subtune={parser_default!r} -- an "
        f"unqualified run will refuse on files that decode fine at the "
        f"parser's real default"
    )


def test_unqualified_default_does_not_refuse_files_that_decode_at_parser_default():
    """The behavioural half of the same guard: actually calling parse_sid with
    the builder's module-level SUB (exactly what an unqualified `main()` run
    does) must not raise MattGrayError on files known to decode at subtune=1.

    Before the fix this raised MattGrayError("address $0000 outside image
    $1000-$1a1a") for Pogo_Stick_Olympics and the analogous $2000-$2a15 error
    for Warriors -- the identical shape as a genuine decode refusal.
    """
    for path in DEFAULT_ONLY_FILES:
        assert os.path.exists(path), path
        try:
            song = parse_sid(path, subtune=BM.SUB)
        except MattGrayError as e:
            raise AssertionError(
                f"{os.path.basename(path)} refused at the builder's own "
                f"unqualified default SUB={BM.SUB}: {e}"
            )
        assert song is not None
