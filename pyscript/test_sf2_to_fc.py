"""Tests for the SF2->FC reader (sidm2.sf2_to_fc) and the full FC<->SF2 round-trip.

Pipeline: FC tune -> fc_to_sf2 (Driver 11 SF2) -> sf2_to_fcsong -> (write_fc).
Audible notes must survive the round-trip exactly (the only loss is FC note 0,
which fc_to_sf2 clamps to the SF2 note floor — a silent/lowest placeholder).
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'bin'))

from sidm2.fc_parser import parse_fc
from sidm2.sf2_to_fc import sf2_to_fcsong
from sidm2.fc_writer import write_fc
from sidm2.galway_driver11_emitter import emit_driver11_sf2
import fc_to_sf2 as F          # bin/fc_to_sf2.py

TRIANGLE = os.path.join(ROOT, 'SID', 'Fun_Fun', 'Triangle_Intro.sid')
TUNES = [os.path.join(ROOT, 'out', 'fc_native', n + '.prg')
         for n in ('GAME_OVER', 'HEART', 'VOICES_IN_SPC_')]


def _load_sid(p):
    from sidm2.sid_parser import SIDParser
    h = SIDParser(p).parse_header()
    d = open(p, 'rb').read()[h.data_offset:]
    la = h.load_address
    if la == 0:
        la = d[0] | (d[1] << 8)
        d = d[2:]
    return d, la


def _load_prg(p):
    raw = open(p, 'rb').read()
    return raw[2:], raw[0] | (raw[1] << 8)


def _audible(song):
    return [[(n.note, n.instr) for n in v if not n.is_rest] for v in song.voices]


def _assert_audible_match(orig, other):
    """Per voice, sounding notes must match — except FC notes 0/1, which fc_to_sf2
    clamps to the SF2 note floor (a lossy, inaudible low/silent placeholder)."""
    o, b = _audible(orig), _audible(other)
    for v in range(3):
        assert len(o[v]) == len(b[v]), f"voice {v} note count"
        for (on, oi), (bn, bi) in zip(o[v], b[v]):
            if on <= 1:                # clamp edge -> skip
                continue
            assert (on, oi) == (bn, bi)


def _check_roundtrip(d, la):
    orig = parse_fc(d, la)
    sf2 = emit_driver11_sf2(F.fc_to_song(orig))
    back = sf2_to_fcsong(sf2, orig)
    _assert_audible_match(orig, back)
    # close the loop: a native FC module that re-parses to the same audible notes
    final = write_fc(back)
    re = parse_fc(final[2:], final[0] | (final[1] << 8))
    _assert_audible_match(orig, re)


@pytest.mark.skipif(not os.path.exists(TRIANGLE), reason="corpus SID missing")
def test_roundtrip_triangle():
    d, la = _load_sid(TRIANGLE)
    _check_roundtrip(d, la)


@pytest.mark.parametrize('path', TUNES)
def test_roundtrip_native(path):
    if not os.path.exists(path):
        pytest.skip("native tune missing")
    d, la = _load_prg(path)
    _check_roundtrip(d, la)
