"""Tests for the Future Composer parser (sidm2.fc_parser).

Validates the $1800 FC player variant decode against the Triangle_Intro rip,
including the melody voice matching the cycle-accurate siddump ground truth.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.sid_parser import SIDParser
from sidm2.fc_parser import parse_fc, detect_player

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIANGLE = os.path.join(ROOT, 'SID', 'Fun_Fun', 'Triangle_Intro.sid')


def _load(path):
    h = SIDParser(path).parse_header()
    d = open(path, 'rb').read()[h.data_offset:]
    la = h.load_address
    if la == 0 and len(d) >= 2:
        la = d[0] | (d[1] << 8)
        d = d[2:]
    return d, la


@pytest.mark.skipif(not os.path.exists(TRIANGLE), reason="corpus SID missing")
def test_detect_and_load():
    d, la = _load(TRIANGLE)
    assert la == 0x1800
    assert detect_player(d, la) is True


@pytest.mark.skipif(not os.path.exists(TRIANGLE), reason="corpus SID missing")
def test_parse_structure():
    d, la = _load(TRIANGLE)
    s = parse_fc(d, la)
    assert s.speed == 1                       # master speed $211d
    assert len(s.instruments) == 17
    # instrument 1 = $2190: pulse $30, waveform $41, AD $0f, SR $ec
    i1 = s.instruments[1]
    assert (i1.pulse, i1.waveform, i1.ad, i1.sr) == (0x30, 0x41, 0x0F, 0xEC)
    # three sounding voices
    assert all(len(v) > 0 for v in s.voices)


@pytest.mark.skipif(not os.path.exists(TRIANGLE), reason="corpus SID missing")
def test_v2_melody_matches_ground_truth():
    """V2's first note indices must match the siddump-traced osc3 melody.

    Ground truth (siddump osc3 note-ons): B-1 B-1 B-1 B-3 D-2 E-2 E-2 E-2 ...
    With idx24 == B-1, the freq-table indices are 24/48/27/29/25/26/31/22.
    """
    d, la = _load(TRIANGLE)
    s = parse_fc(d, la)
    v2 = [r.note for r in s.voices[2] if not r.is_rest]
    expected = [24, 24, 24, 48, 27, 29, 29, 29, 48, 25, 26, 26, 26, 48]
    assert v2[:len(expected)] == expected


@pytest.mark.skipif(not os.path.exists(TRIANGLE), reason="corpus SID missing")
def test_arp_instruments_decode():
    """Arp instruments (mctrl & $04) expose chord offsets in byte [5]."""
    d, la = _load(TRIANGLE)
    s = parse_fc(d, la)
    arps = {i.index: (i.vibrato >> 4, i.vibrato & 0x0F)
            for i in s.instruments if (i.mctrl & 0x04) and i.vibrato}
    assert arps[13] == (4, 7)        # major chord {0,+4,+7}
    assert arps[16] == (3, 7)        # minor chord {0,+3,+7}


@pytest.mark.skipif(not os.path.exists(TRIANGLE), reason="corpus SID missing")
def test_drum_sequence_matches_trace():
    """instr2 is drumtype 0; its freq burst must match the real osc3 trace
    ($2000,$0E00,$0C00,$3000,...) and lead with a noise waveform ($81)."""
    d, la = _load(TRIANGLE)
    s = parse_fc(d, la)
    assert s.instruments[2].mctrl & 0x10        # instr2 is a drum
    seq = s.drum_sequence(s.instruments[2].vibrato)
    wfs = [w for w, f in seq]
    freqs = [f for w, f in seq]
    assert wfs[0] == 0x81                        # noise burst on the attack
    assert freqs[:4] == [0x2000, 0x0E00, 0x0C00, 0x3000]


@pytest.mark.skipif(not os.path.exists(TRIANGLE), reason="corpus SID missing")
def test_v2_durations_match_trace_timing():
    """dur+1 rows reproduce the trace's 12/6/6-frame note spacing (speed=1)."""
    d, la = _load(TRIANGLE)
    s = parse_fc(d, la)
    v2 = [r.dur for r in s.voices[2] if not r.is_rest]
    # first note dur 5 -> (5+1)*2 = 12 frames; next two dur 2 -> 6 frames each
    assert v2[:3] == [5, 2, 2]
