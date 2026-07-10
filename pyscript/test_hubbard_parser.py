"""Rob Hubbard v1 parser — detection + decode regression tests.

Ground truth: the C=Hacking #5 Monty on the Run commented disassembly
(docs/analysis/hubbard/chacking5_monty_disassembly.txt) + a siddump onset
sweep verified 2026-07-06: 100% of real gate-on frames matched at tick*fpt
(phase 0) on all three voices over 120s of Monty_on_the_Run.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sidm2.hubbard_parser import (HubbardModule, decode_pattern, decode_song,
                                  load_sid)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONTY = os.path.join(ROOT, "SID", "Hubbard_Rob", "Monty_on_the_Run.sid")
COMMANDO = os.path.join(ROOT, "SID", "Hubbard_Rob", "Commando.sid")

pytestmark = pytest.mark.skipif(not os.path.exists(MONTY),
                                reason="Hubbard corpus not present")


def _mod(path):
    d, la, _ = load_sid(path)
    return HubbardModule(d, la)


def test_monty_layout():
    m = _mod(MONTY)
    # verified against the C=Hacking source layout ($8000 module)
    assert m.lay.songs == 0x856C
    assert m.lay.patptl == 0x857E
    assert m.lay.freq == 0x8400
    assert m.lay.instr == 0x93B4
    assert m.resetspd == 1 and m.frames_per_tick == 2


def test_monty_freq_table_semitones():
    m = _mod(MONTY)
    # 12-semitone rollover: freq(n+12) ~= 2*freq(n) (playbook step-4 sanity)
    for n in (0, 12, 24, 36):
        a, b = m.note_freq(n), m.note_freq(n + 12)
        assert abs(b - 2 * a) <= 2, (n, a, b)


def test_monty_instrument_sanity():
    m = _mod(MONTY)
    ins = m.instrument(0)
    assert 0 < ins["ctrl"] < 0x90          # a real SID control byte
    assert set(ins) == {"pwlo", "pwhi", "ctrl", "ad", "sr",
                        "vibdepth", "pulsespeed", "fx"}


def test_monty_tracks_balanced():
    m = _mod(MONTY)
    voices, totals = decode_song(m, 0)
    assert totals == [8768, 8768, 8768]      # one-pass song length in ticks
    for v in range(3):
        pats, loops = m.track_patterns(0, v)
        assert loops                          # Monty main tune loops ($ff)
        assert len(pats) > 10


def test_monty_first_onsets():
    """First predicted onset frames, verified against siddump 2026-07-06."""
    m = _mod(MONTY)
    voices, _ = decode_song(m, 0)
    fpt = m.frames_per_tick
    v1 = [(tk * fpt, n.pitch) for tk, n in voices[1]
          if not n.append and n.pitch >= 0]
    assert [f for f, _ in v1[:8]] == [0, 512, 560, 568, 624, 632, 688, 696]


def test_note_flags_decode():
    m = _mod(MONTY)
    voices, _ = decode_song(m, 0)
    evs = [n for _, n in voices[0]]
    assert any(n.append for n in evs)         # ties exist
    assert any(n.porta for n in evs) or any(n.instr >= 0 for n in evs)
    assert all(1 <= n.ticks <= 32 for n in evs)


def test_commando_detects():
    if not os.path.exists(COMMANDO):
        pytest.skip("no Commando.sid")
    m = _mod(COMMANDO)
    voices, totals = decode_song(m, 0)
    assert totals == [3936, 3936, 3936]
    assert m.frames_per_tick == 3


def test_track_transpose_generations():
    """The later swallow revisions use bit7 track bytes as TRANSPOSE commands
    (ROM-verified: Shockway $ED99 one-byte `$80|semis`, Auf_Wiedersehen $E49D
    two-byte `$80 nn`). Decoding them as pattern numbers 128+ made one voice
    'decode' 10x too long (Shockway 3210s -> a 638-part build of repeats).
    With the fix, per-voice one-pass lengths come out near-equal (synced
    tracks) and V1 files stay tmode=0."""
    import os
    from sidm2.hubbard_parser import HubbardModule, decode_song, load_sid

    def one_pass(name):
        d, la, h = load_sid(os.path.join("SID", "Hubbard_Rob", name + ".sid"))
        m = HubbardModule(d, la)
        vr, _ = decode_song(m, 0, expand_loops=False)
        return m.lay.trk_transpose, [max((tk + n.ticks for tk, n in vr[v]),
                                         default=0) for v in range(3)]
    tm, op = one_pass("Shockway_Rider")
    assert tm == 1 and max(op) < 2 * min(op)          # was 261 vs 3210s-worth
    tm, op = one_pass("Saboteur_II")
    assert tm == 1 and len(set(op)) == 1              # perfectly synced
    tm, op = one_pass("Auf_Wiedersehen_Monty")
    assert tm == 2 and max(op) < 1.5 * min(op)
    tm, op = one_pass("Monty_on_the_Run")
    assert tm == 0 and len(set(op)) == 1              # V1 untouched
