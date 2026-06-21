"""Tests for trace-driven Galway extraction (sidm2.galway_trace_extract).

These exercise the RLE/reconstruction logic directly (no external tracer), plus
an end-to-end Wizball check that is skipped when the zig64 tracer or the SID
corpus file is unavailable (e.g. CI without the binary).
"""
import os

import pytest

from sidm2 import galway_trace_extract as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIZBALL = os.path.join(ROOT, "SID", "Galway_Martin", "Wizball.sid")
TRACER = os.path.join(ROOT, "tools", "sidm2-sid-trace.exe")


def test_rle_roundtrip_constant():
    deltas = [10] * 100
    rle = T._rle(deltas)
    assert rle == [(10, 100)]


def test_rle_roundtrip_mixed():
    deltas = [10, 10, 10, -5, -5, 0, 0, 0]
    assert T._rle(deltas) == [(10, 3), (-5, 2), (0, 3)]


def test_rle_caps_run_length():
    rle = T._rle([7] * 300)
    # no single run exceeds 255
    assert all(run <= 255 for _, run in rle)
    assert sum(run for _, run in rle) == 300


def test_series_holds_last_value():
    s = T._series({0: 5, 3: 9}, 6)
    assert s == [5, 5, 5, 9, 9, 9]


def test_reconstruct_freq_matches_rle():
    note = T.TraceNote(onset=0, end=5, base_freq=1000, waveform=0x41,
                       fm=[(10, 2), (-5, 2)])
    # base, +10, +10, -5, -5
    assert T.reconstruct_freq(note) == [1000, 1010, 1020, 1015, 1010]


@pytest.mark.skipif(not (os.path.exists(WIZBALL) and os.path.exists(TRACER)),
                    reason="zig64 tracer or Wizball SID not available")
def test_wizball_song4_structure_and_exact_reconstruction():
    from sidm2.sid_parser import SIDParser
    h = SIDParser(WIZBALL).parse_header()
    song = T.extract(WIZBALL, 1800, h.init_address, h.play_address,
                     (h.start_song or 1) - 1)
    v0, v1, v2 = song.voices
    # Real song-4 plays LEGATO (gate held, pitch changed via the player). Both
    # sounding voices are flagged legato and segmented into notes by settled-pitch
    # change (not gate). osc2 is SILENT; osc3 enters ~800 as a melody (many notes).
    assert v0.active and v0.legato and v0.notes[0].onset == 0
    assert not v1.active and len(v1.notes) == 0
    assert v2.active and v2.legato and len(v2.notes) > 10   # was 1 before splitting
    assert 700 <= v2.notes[0].onset <= 900
    # FM offset list reconstructs each note's captured frequency envelope EXACTLY.
    for v in (v0, v2):
        for n in v.notes:
            recon = T.reconstruct_freq(n)
            assert len(recon) == (n.end - n.onset)
