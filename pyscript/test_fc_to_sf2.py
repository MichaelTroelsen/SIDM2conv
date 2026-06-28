"""Tests for bin/fc_to_sf2.py transpile helpers (FC score -> Driver 11 rows).

Focus: FC instrument 0 is the "hold" sentinel — a note on instrument 0 makes no
sound, it just sustains the currently-ringing note (verified vs original siddump:
the real player neither re-gates nor changes frequency on instr 0). The converter
must emit such a note as a sustain, never as a fresh note-on (which would sound a
phantom note the real FC player never plays).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'bin'))

from sidm2.fc_parser import FCNote
from sidm2.galway_to_driver11 import SF2_GATE_ON, SF2_GATE_OFF
import fc_to_sf2 as F


def _note_ons(rows):
    """Rows that re-gate a NEW note (not a sustain/rest control row)."""
    return [r for r in rows if r.note not in (SF2_GATE_ON, SF2_GATE_OFF)]


def test_instr0_midsong_is_sustain_not_a_new_note():
    # real note (instr 1), then an instr-0 "grace" note, then another real note.
    rows = F.build_track([
        FCNote(note=20, dur=1, instr=1),
        FCNote(note=30, dur=1, instr=0),   # instr 0 -> hold, no new note
        FCNote(note=24, dur=1, instr=1),
    ], base=0)
    ons = _note_ons(rows)
    assert len(ons) == 2                       # only the two real notes gate
    # the instr-0 note contributes sustain rows, never a $1e (=30) note-on
    assert all(r.note != 30 + 0 + 1 for r in ons)


def test_instr0_at_start_is_silent():
    # instr-0 notes before any real instrument: nothing is ringing -> silence,
    # so they must NOT produce a note-on (they become gate rows).
    rows = F.build_track([
        FCNote(note=48, dur=2, instr=0),
        FCNote(note=48, dur=2, instr=0),
        FCNote(note=22, dur=1, instr=3),       # first real note
    ], base=0)
    ons = _note_ons(rows)
    assert len(ons) == 1
    assert ons[0].instrument == 3


def test_real_instrument_change_still_emits_setinstr():
    rows = F.build_track([
        FCNote(note=20, dur=0, instr=1),
        FCNote(note=20, dur=0, instr=2),       # instrument change -> set-instr
    ], base=0)
    ons = _note_ons(rows)
    assert [r.instrument for r in ons] == [1, 2]
