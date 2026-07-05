"""Regression tests for the Supremacy (Jeroen Tel / MoN flat variant) parser path in
sidm2/mon_parser.py (ol_mode='supremacy').

Ground truth = py65 trace of the player's freq-lookup ($1644) note stream. Subtune 0 is
a 3-voice canon; all three voices decode byte-exact. (The arp/command voices in subtunes
1-2 are a known WIP — see memory/myth-supremacy-mon-re.md — and are not asserted here.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sidm2.mon_parser import load_sid, MON

SID = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "SID", "Tel_Jeroen", "Supremacy.sid")

# Subtune-0 collapsed note onsets (consecutive same-pitch merged), from the py65
# EVENT-BOUNDARY tracer (bin/mon_event_trace.py, kind='note' = actual $12C1 gate
# triggers) — the earlier freq-lookup-derived list carried one phantom pitch (a
# non-trigger lookup); onset frames are additionally validated EXACT vs siddump
# by bin/mon_validate.py (sub0 V0 137/137 over 60s).
SUB0_ONSETS = [0x39, 0x3B, 0x3C, 0x39, 0x3E, 0x3C, 0x3B, 0x39,
               0x38, 0x34, 0x40, 0x3E, 0x3C, 0x3B, 0x39, 0x40]


def _collapsed(m, voice):
    out = []
    for ev in m.voices[voice]:
        if ev.rest:                       # rests are silences, not pitches
            continue
        if not out or out[-1] != ev.note:
            out.append(ev.note)
    return out


def test_supremacy_detected():
    d, la, h = load_sid(SID)
    m = MON(d, la, 0)
    assert m.ol_mode == "supremacy"
    assert m.tbl_olptr == 0x16DC
    assert (m.tbl_pat_lo, m.tbl_pat_hi) == (0x16F3, 0x171C)
    assert (m.tbl_freq, m.tbl_freq_hi) == (0x1644, 0x168A)
    assert m.note_base == -3            # $16E3[0] = $FD, signed


def test_supremacy_sub0_all_voices_byte_exact():
    d, la, h = load_sid(SID)
    m = MON(d, la, 0)
    for v in range(3):
        got = _collapsed(m, v)
        assert got[:len(SUB0_ONSETS)] == SUB0_ONSETS, f"voice {v}: {got[:16]}"


def test_supremacy_arp_voices_base_note():
    # The arpeggio voices (sub1 v2, sub2 v0/v1) don't decode to identical onset
    # streams (the freq-lookup ground truth sees the wave-program arp expansion), but
    # the parser must still decode the correct BASE note the arp is built on. This
    # guards the $60 note/wave boundary fix (a $6x byte is a wave selector, not a note).
    d, la, h = load_sid(SID)
    for sub, voice, first in [(1, 2, 0x31), (2, 0, 0x15), (2, 1, 0x31)]:
        m = MON(d, la, sub)
        got = _collapsed(m, voice)
        assert got and got[0] == first, f"sub{sub} v{voice}: {[hex(x) for x in got[:6]]}"


def test_supremacy_arp_table():
    """The arp/wave-program table ($1746 index -> $17C0 programs) is located and decodes
    to the ROM's compact LOOPING SEMITONE chord-arps. These are byte-exact from ROM and
    were validated against the py65 trace ($106D per frame): sub2 v1 wprog 4 -> [0,3,8]
    cycles exactly; v0 wprog 27 -> octave; v2 wprog 28 -> no arp. Extracting these (vs the
    trace's per-pitch Hz-offset explosion) is the structural key to the FM/bundle cap.
    See memory/myth-supremacy-mon-re.md."""
    d, la, h = load_sid(SID)
    m = MON(d, la, 2)
    assert (m.tbl_arp_idx, m.tbl_arp_base) == (0x1746, 0x17C0)
    # chord arps (root + intervals), looping
    assert m.arp_program(0) == {"dur": 0x10, "steps": [0, 3, 7], "loop": True}   # minor
    assert m.arp_program(1) == {"dur": 0x10, "steps": [0, 4, 7], "loop": True}   # major
    assert m.arp_program(4) == {"dur": 0x10, "steps": [0, 3, 8], "loop": True}   # v1 (traced)
    assert m.arp_program(27)["steps"] == [12, 0]                                 # v0 octave
    # every step is a signed semitone offset in a sane arp range
    for w in range(16):
        prog = m.arp_program(w)
        assert prog["steps"] and all(-24 <= s <= 36 for s in prog["steps"])


def test_supremacy_note_freq_table():
    # note $39 must resolve via the located split freq table (sane 16-bit value)
    d, la, h = load_sid(SID)
    m = MON(d, la, 0)
    f = m.note_freq(0x39)
    assert 0x0200 <= f <= 0x4000, hex(f)


def test_supremacy_swing_tempo_flag():
    """The speed byte's $80 bit is the SWING-TEMPO flag (RE'd from the $1128-$114D
    tempo gate: the reload toggles $E2 and alternates speed / speed+1 frame periods).
    sub0=$02 / sub1=$04 constant; sub2=$82 swing."""
    d, la, h = load_sid(SID)
    for sub, speed, toggle in [(0, 2, False), (1, 4, False), (2, 2, True)]:
        m = MON(d, la, sub)
        assert (m.speed, m.tempo_toggle) == (speed, toggle), f"sub{sub}"


def test_tick_to_frame_grids():
    d, la, h = load_sid(SID)
    m0 = MON(d, la, 0)                    # constant: 3 frames/tick
    assert [m0.tick_to_frame(t) for t in range(5)] == [0, 3, 6, 9, 12]
    m2 = MON(d, la, 2)                    # swing 2,3: ticks at 0,2,5,7,10,...
    assert [m2.tick_to_frame(t) for t in range(6)] == [0, 2, 5, 7, 10, 12]
    # 20% length difference vs the old constant model — the whats-next.md blocker:
    # 24 ticks = 60 frames (was 72 under speed+1=3)
    assert m2.tick_to_frame(24) == 60


def test_supremacy_rests_and_slides_decoded():
    """The event-tracer-verified pattern semantics: top-level $E0+ = REST (b&$1F
    ticks of silence, e.g. sub1 v2's $F0 = 16 ticks at fr800), and $FD = the
    4-byte SLIDE (speed, note, target — a gated trigger; sub1 v1 fr80 = note
    $33 -> target $35 speed 6). Additive durations: sub0 pattern $03's `A0 A0`
    note lasts 64 ticks. All onset-frame-validated EXACT by bin/mon_validate.py
    (sub2 962/962 @120s, sub0 V0 137/137 @60s, sub1 136/136 @37s/one pass)."""
    d, la, h = load_sid(SID)
    m1 = MON(d, la, 1)
    assert any(ev.rest and ev.dur == 16 for ev in m1.voices[2])
    slides = [ev for ev in m1.voices[1] if ev.slide]
    assert slides and slides[0].slide[0] == 6            # speed 6 (tracer-verified)
    m0 = MON(d, la, 0)
    assert any(ev.dur == 64 for ev in m0.voices[0])      # the additive `A0 A0` hold


def test_supremacy_sub2_onset_frames_match_siddump():
    """End-to-end swing-grid regression: parser onset frames (tick_to_frame + the
    constant +2 engine output delay) must equal the siddump ground truth. Frames
    hardcoded from pyscript/siddump_complete.py -a2 (validated EXACT 97/97 + 37/37
    across 30s by bin/mon_validate.py on 2026-07-05)."""
    d, la, h = load_sid(SID)
    m = MON(d, la, 2)
    # V2's third onset per phrase (72, 152, ...) exists only via the prefix-chain
    # RETRIGGER (a $Cx byte followed by another prefix replays the previous note) —
    # this guards both the swing grid AND the retrigger decode.
    expect = {0: [2, 42, 82, 122, 162, 202, 242, 282],
              1: [2, 62, 82, 142, 162, 222, 242, 322],
              2: [2, 62, 72, 82, 142, 152, 162, 222, 232, 242]}
    for v, want in expect.items():
        ticks, got = 0, []
        for ev in m.voices[v]:
            if ev.retrig:
                got.append(m.tick_to_frame(ticks) + 2)
            ticks += ev.dur
            if len(got) >= len(want):
                break
        assert got[:len(want)] == want, f"v{v}: {got[:len(want)]}"
