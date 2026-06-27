"""Tests for the Future Composer module writer (sidm2.fc_writer).

Round-trip: a native FC tune parsed -> written -> re-parsed must reproduce the
exact per-voice note/dur/instrument/tie streams, proving the writer emits a valid
$1800 player+data module (the format the C64 editor's SAVE writes).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fc_parser import parse_fc
from sidm2.fc_writer import write_fc, encode_voice_blocks, MAX_BLOCK

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TUNES = [os.path.join(ROOT, 'out', 'fc_native', n + '.prg')
         for n in ('GAME_OVER', 'HEART', 'ITS_A_SIN', 'VOICES_IN_SPC_')]
TRIANGLE = os.path.join(ROOT, 'SID', 'Fun_Fun', 'Triangle_Intro.sid')


def _voices(song):
    return [[(n.note, n.dur, n.instr, n.tie) for n in v] for v in song.voices]


def _load_prg(p):
    raw = open(p, 'rb').read()
    return raw[2:], raw[0] | (raw[1] << 8)


def _load_sid(p):
    from sidm2.sid_parser import SIDParser
    h = SIDParser(p).parse_header()
    d = open(p, 'rb').read()[h.data_offset:]
    la = h.load_address
    if la == 0:
        la = d[0] | (d[1] << 8)
        d = d[2:]
    return d, la


@pytest.mark.skipif(not os.path.exists(TRIANGLE), reason="corpus SID missing")
def test_roundtrip_triangle_sid():
    d, la = _load_sid(TRIANGLE)
    s = parse_fc(d, la)
    out = write_fc(s)
    assert out[0] | (out[1] << 8) == 0x1800        # PRG loads at $1800
    s2 = parse_fc(out[2:], 0x1800)
    assert _voices(s2) == _voices(s)


@pytest.mark.parametrize('path', TUNES)
def test_roundtrip_native_tunes(path):
    if not os.path.exists(path):
        pytest.skip("native tune missing")
    d, la = _load_prg(path)
    s = parse_fc(d, la)
    out = write_fc(s)
    s2 = parse_fc(out[2:], out[0] | (out[1] << 8))
    assert _voices(s2) == _voices(s)


@pytest.mark.skipif(not os.path.exists(TRIANGLE), reason="corpus SID missing")
def test_blocks_within_8bit_index():
    """Every emitted block must be < 256 bytes (the player's in-block index is
    8-bit) so it can't wrap mid-block."""
    d, la = _load_sid(TRIANGLE)
    s = parse_fc(d, la)
    for v in s.voices:
        for blk in encode_voice_blocks(v):
            assert len(blk) <= MAX_BLOCK + 1       # +1 for the $ff terminator
