"""The ROMUZAK builder's wave bound is checked BEFORE the write it guards.

This is the pin for a TIDINESS change, and the distinction matters enough to
state at the top: the previous order — write the rows, advance the cursor, then
test it — could not ship a truncated table. The spill landed in an in-memory
bytearray, `wave_cursor` after the increment equals `start + len(wp)` exactly,
and the raise preceded the `drivers_src/romuzak/layout.inc` write, so a refused
build emitted nothing. Moving the check changes what the code SAYS, not what it
does. Anyone reading this file for a bug fix will not find one.

Two of these are source-order assertions, which is unusual and deliberate: the
old and new orders are behaviourally indistinguishable — that is the whole
finding — so ordering is the only thing a test can hold.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "bin", "build_romuzak_native_song.py")

needs_src = pytest.mark.skipif(not os.path.exists(SRC),
                               reason="bin/build_romuzak_native_song.py absent")


def _lines():
    with open(SRC, encoding="utf-8") as fh:
        return fh.read().splitlines()


@needs_src
def test_the_wave_bound_is_checked_BEFORE_the_row_write():
    """THE CHANGE THIS FILE EXISTS FOR.

    `if start + len(wp) > 256` must appear above `edit[wo + 0 * 256 + ...]`.
    If someone re-orders them the code goes back to testing a cursor it has
    already used, which is the shape that reads as a bug even though it is not.
    """
    lines = _lines()
    chk = [i for i, l in enumerate(lines) if "start + len(wp) > 256" in l]
    wrt = [i for i, l in enumerate(lines) if "edit[wo + 0 * 256 + start + r]" in l]
    assert len(chk) == 1, chk
    assert len(wrt) == 1, wrt
    assert chk[0] < wrt[0], (
        "the WAVE bound is tested at line %d, AFTER the row write at %d"
        % (chk[0] + 1, wrt[0] + 1))


@needs_src
def test_the_raise_reports_the_same_number_as_before():
    """The message must not drift while the order changes.

    The old check raised the post-increment `wave_cursor`; the new one raises
    `start + len(wp)`. Those are the same value by construction (start IS
    wave_cursor at that point), so the operator-visible number is unchanged and
    any log or doc quoting it stays true. A rewrite that reported, say, `start`
    would silently halve every number in the message.
    """
    lines = _lines()
    raises = [l for l in lines if "WAVE overflow" in l]
    assert len(raises) == 1, raises
    assert "start + len(wp)" in raises[0], raises[0]


@needs_src
def test_the_raise_still_precedes_the_layout_inc_write():
    """Mirrors the pin in test_build_mon_native_song.py, kept HERE too.

    That pin lives in the MoN test file because the finding was made there;
    this builder is the one it is about, and a reader of this file should not
    have to know that. If the raise ever moves below the layout.inc write, a
    refused build starts leaving a half-written include behind.
    """
    lines = _lines()
    raise_ln = [i for i, l in enumerate(lines) if "WAVE overflow" in l]
    layout_ln = [i for i, l in enumerate(lines)
                 if re.search(r"layout\.inc", l) and "open(" in l]
    assert len(raise_ln) == 1, raise_ln
    if not layout_ln:                       # the write moved or is built up
        pytest.skip("no single layout.inc open() line to order against")
    assert raise_ln[0] < layout_ln[0], (
        "the WAVE overflow raise no longer precedes the layout.inc write")


@needs_src
def test_the_FILTER_bound_STILL_has_the_old_order_and_that_is_known():
    """RECORDED, NOT FIXED — so nobody reads the wave change as covering both.

    `filt_cursor` is tested after its rows are written, exactly as the wave
    cursor used to be, thirty lines further up the same function. It is the same
    non-bug for the same reasons and it was left alone because the task that
    moved the wave check named only that one. If someone tidies it too, delete
    this test rather than inverting it — an assertion that a wart persists is
    only worth keeping while the wart does.
    """
    lines = _lines()
    chk = [i for i, l in enumerate(lines) if "filt_cursor > 256" in l]
    wrt = [i for i, l in enumerate(lines) if "edit[fo + 0 * 256 + start + r]" in l]
    assert len(chk) == 1 and len(wrt) == 1, (chk, wrt)
    assert wrt[0] < chk[0], (
        "the FILTER bound now precedes its write too -- good; delete this test")
