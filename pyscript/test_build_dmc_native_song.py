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


# --- The legato A/B probes are PER SONG, never one shared prefix -------------
# Under `dmc_native_sweep.py --jobs 4` every song's probes wrote `_abg` / `_abl`
# in out/dmc at once: one process's prune deleted another's staging file
# (Thunder_Force FileNotFoundError) and a song could score another song's probe
# (Dreaming_2 shipped 2 parts where a serial build gives 23).

def _dmc_builder_ast():
    import ast
    src = open(os.path.join(ROOT, "bin", "build_dmc_native_song.py"),
               encoding="utf-8").read()
    return ast.parse(src)


def test_probe_names_are_distinct_per_song():
    sys.path.insert(0, os.path.join(ROOT, "bin"))
    sys.path.insert(0, ROOT)
    import build_dmc_native_song as B
    names = {B.probe_name(k, b) for k in ("g", "l") for b in ("Dreaming_2", "Thunder_Force")}
    assert len(names) == 4
    assert all(n.startswith("_ab") for n in names)


def test_no_probe_build_uses_a_constant_prefix():
    import ast
    bad = []
    for node in ast.walk(_dmc_builder_ast()):
        if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "build_song"
                and len(node.args) > 1 and isinstance(node.args[1], ast.Constant)):
            bad.append((node.lineno, node.args[1].value))
    assert bad == [], f"build_song called with a constant prefix: {bad}"


def test_probe_parts_are_pruned_after_the_ab():
    # Probes are measured, not shipped -- they must not stay in out/dmc.
    import ast
    pruned = [n for n in ast.walk(_dmc_builder_ast())
              if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "prune_stale_parts"
              and len(n.args) == 2 and isinstance(n.args[1], ast.Constant) and n.args[1].value == 0]
    assert pruned, "no prune_stale_parts(<probe prefix>, 0) after the legato A/B"
