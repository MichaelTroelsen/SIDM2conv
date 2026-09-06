"""A REST ENDS A NOTE -- the legato boundary scan in bin/build_dmc_native_song.py.

WHY THIS EXISTS. The scan emitted a boundary only on a pitch CHANGE, and `prev`
survived intervening rests. Dreaming_2's voice 2 opens with three separate
pitch-54 notes at frames 69, 197 and 357, each 16 ticks, separated by 96-160
frames of rest. Only the first produced a boundary; the other two were swallowed
into one 380-frame note, and `_wave_prog_for` then -- correctly -- sampled the
original's gate-off $50 across that span, yielding a program that can never gate.
Part01's voice 3 rendered SILENT: 0 gate frames where the original has 75.

The guard is the SCAN's own rule, tested on the real module rather than a
re-implementation, because a re-implementation is what would drift.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SID = os.path.join(ROOT, "SID", "JohannesBjerregaard", "Dreaming_2.sid")

sys.path.insert(0, ROOT)

pytestmark = pytest.mark.skipif(
    not os.path.exists(SID), reason="SID/JohannesBjerregaard/Dreaming_2.sid not present")


def _scan(voices, v, ofpt, phase, reset_on_rest):
    """The boundary scan, both ways -- the FIXED form is what the builder runs."""
    ons, prev = [], None
    for tk, n in voices[v]:
        if n.pitch < 0:
            if reset_on_rest:
                prev = None
            continue
        fr = tk * ofpt + phase
        if fr >= 0 and n.pitch != prev:
            ons.append(fr)
            prev = n.pitch
    return ons


@pytest.fixture(scope="module")
def decoded():
    from sidm2.dmc_parser import load_sid, DMCModule, decode_song
    d, la, _h = load_sid(SID)
    m = DMCModule(d, la)
    return m, decode_song(m, tick_budget=4000)


def test_the_source_still_resets_prev_on_a_rest(decoded):
    """The rule, asserted against the BUILDER SOURCE -- if someone deletes the
    reset, this fires even though the scan below is a local copy."""
    src = open(os.path.join(ROOT, "bin", "build_dmc_native_song.py"),
               encoding="utf-8").read()
    body = src.split("if v in legato_set:", 1)[1].split("else:", 1)[0]
    assert "prev = None" in body, (
        "the legato boundary scan no longer resets `prev` on a rest -- a "
        "re-articulation after silence will be swallowed into the previous "
        "note and can render as a silent voice (Dreaming_2 part01)")


def test_a_rest_ends_the_note_so_a_re_attack_is_a_new_boundary(decoded):
    """POSITIVE CONTROL FIRST: the two scans must actually DIFFER on this
    material, or the assertion below would pass against a broken scan too."""
    m, voices = decoded
    ofpt, phase = m.lay.tempo_reload + 1, 5
    old = _scan(voices, 2, ofpt, phase, reset_on_rest=False)
    new = _scan(voices, 2, ofpt, phase, reset_on_rest=True)
    assert len(new) > len(old), "the two scans agree -- this file no longer exercises the defect"

    # part01 is frames 0..450 (its .span sidecar records 0..9 s).
    old_in_part01 = [f for f in old if f < 450]
    new_in_part01 = [f for f in new if f < 450]
    assert old_in_part01 == [69], old_in_part01
    assert new_in_part01 == [69, 197, 357], new_in_part01


def test_a_held_note_is_still_not_a_new_boundary(decoded):
    """The other half of the rule, and the reason the fix is a rest-reset rather
    than 'a boundary on every note start': consecutive same-pitch events with NO
    rest between them are one held note and must stay one."""
    m, voices = decoded
    ofpt, phase = m.lay.tempo_reload + 1, 5
    for v in range(3):
        held = 0
        prev_pitch, prev_was_note = None, False
        for _tk, n in voices[v]:
            if n.pitch < 0:
                prev_was_note = False
                continue
            if prev_was_note and n.pitch == prev_pitch:
                held += 1
            prev_pitch, prev_was_note = n.pitch, True
        if held:
            # every such event is suppressed by BOTH scans
            assert len(_scan(voices, v, ofpt, phase, True)) \
                <= sum(1 for _tk, n in voices[v] if n.pitch >= 0) - held
            return
    pytest.skip("no consecutive same-pitch note pairs in this file")
