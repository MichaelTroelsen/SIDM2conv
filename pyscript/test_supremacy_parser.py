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
# freq-lookup ground truth — identical across the 3 canon voices for the first bars.
SUB0_ONSETS = [0x39, 0x3B, 0x3C, 0x3E, 0x39, 0x3E, 0x3C, 0x3B,
               0x39, 0x38, 0x34, 0x40, 0x3E, 0x3C, 0x3B, 0x39]


def _collapsed(m, voice):
    out = []
    for ev in m.voices[voice]:
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
