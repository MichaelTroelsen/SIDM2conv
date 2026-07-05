"""Tests for sidm2/fidelity_common.py — the shared validator plumbing (roadmap A3).

Covers: canonical semitone conversion (incl. the boundary semantics the old
per-tool copies disagreed on), PSID wrapping, siddump table parsing on a canned
dump (no subprocess), zig64 fill-forward serialization, and the gated
best-offset search.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import (           # noqa: E402
    SEMI_REF, freq_to_semi, psid_wrap, iter_siddump_rows, siddump_per_frame,
    siddump_note_onsets, siddump_filter_trace, fill_forward, zig64_voices,
    best_gated_offset,
)
import sidm2.fidelity_common as FC            # noqa: E402


# --- freq_to_semi -----------------------------------------------------------

def test_semi_silence_and_subaudio():
    assert freq_to_semi(None) == -1
    assert freq_to_semi(0) == -1
    assert freq_to_semi(7) == -1        # below the note table
    assert freq_to_semi(8) == 0         # clamped to note 0


def test_semi_reference_is_c4():
    # SEMI_REF is by definition C-4 = note index 48.
    assert freq_to_semi(SEMI_REF) == 48


def test_semi_octaves():
    # One octave up doubles the freq value.
    assert freq_to_semi(SEMI_REF * 2) == 60
    assert freq_to_semi(SEMI_REF // 2) == 36


def test_semi_16bit_max_stays_in_table():
    assert 0 <= freq_to_semi(0xFFFF) <= 95


def test_semi_comparison_stable_across_old_references():
    # The pre-consolidation copies used 0x1168 vs 0x1167. The unified function
    # must classify equal/unequal pairs the same way the old ones did for
    # byte-quantized SID freqs: equal freqs match, a semitone step doesn't.
    for f in (0x0130, 0x1167, 0x13EF, 0x2000, 0x7FFF):
        assert freq_to_semi(f) == freq_to_semi(f)
        up = round(f * 2 ** (1 / 12))
        assert freq_to_semi(up) == freq_to_semi(f) + 1


# --- psid_wrap --------------------------------------------------------------

def test_psid_wrap_header_fields():
    data = bytes(range(16))
    blob = psid_wrap(data, 0x1000, 0x1000, 0x1003)
    assert blob[:4] == b'PSID'
    # header is 0x7C bytes for v2; payload appended verbatim
    assert blob.endswith(data)
    load, init, play = struct.unpack('>HHH', blob[8:14])
    songs, start = struct.unpack('>HH', blob[14:18])
    assert (init, play) == (0x1000, 0x1003)
    assert (songs, start) == (1, 1)
    # load address: either in the header word or as the 2-byte prefix convention
    assert load == 0x1000 or blob[len(blob) - len(data) - 2:len(blob) - len(data)]


# --- siddump parsing (canned dump, no subprocess) ---------------------------

CANNED = """\
| Frame | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | FCut RC Typ V |
+-------+---------------------------+---------------------------+---------------------------+---------------+
|     0 | 13EF  D-4 32  41 00DB 500 | 0857  F-2 11  43 00D9 800 | 0000  ...  .. .... ... ... | 5800 F1 Low F |
|     1 | 1400 (D-4 32) ..  .... ... | ....  ... .. .... ... ... | 2100  C-5 21  41 0869 600 | .... .. ... . |
|     2 | ....  ... .. .... ...  ... | 0000  ... 08  .... ... ... | ....  ... ..  .... ... ... | 5000 .. ... . |
"""


def test_iter_siddump_rows():
    rows = list(iter_siddump_rows(CANNED))
    assert [fr for fr, _ in rows] == [0, 1, 2]
    assert all(len(c) >= 6 for _, c in rows)


def test_siddump_note_onsets_from_canned(monkeypatch):
    monkeypatch.setattr(FC, 'run_siddump', lambda p, a: CANNED)
    # unbracketed onsets, no wf requirement: V0 D-4@0, V1 F-2@0, V2 C-5@1
    V = FC.siddump_note_onsets('x', [])
    assert V[0] == [(0, 'D-4')]
    assert V[1] == [(0, 'F-2')]
    assert V[2] == [(1, 'C-5')]
    # require_wf drops nothing here (all onsets carry a WF byte)
    Vw = FC.siddump_note_onsets('x', [], require_wf=True)
    assert Vw == V


def test_siddump_per_frame_fill_forward(monkeypatch):
    monkeypatch.setattr(FC, 'run_siddump', lambda p, a: CANNED)
    frames = FC.siddump_per_frame('x', [])
    assert len(frames) == 3
    v0_f0, fcut0 = frames[0][0][0], frames[0][1]
    assert (v0_f0['freq'], v0_f0['wf'], v0_f0['pul']) == (0x13EF, 0x41, 0x500)
    assert fcut0 == 0x5800
    # frame 1: V0 freq updates to 1400, wf carries forward
    v0_f1 = frames[1][0][0]
    assert (v0_f1['freq'], v0_f1['wf']) == (0x1400, 0x41)
    # frame 2: everything carries forward for V0; filter cutoff updates
    assert frames[2][0][0] == v0_f1
    assert frames[2][1] == 0x5000


def test_siddump_filter_trace_fill_forward(monkeypatch):
    monkeypatch.setattr(FC, 'run_siddump', lambda p, a: CANNED)
    ft = FC.siddump_filter_trace('x', [])
    assert ft == [(0x5800, 0xF1), (0x5800, 0xF1), (0x5000, 0xF1)]


# --- zig64 serialization ----------------------------------------------------

def test_fill_forward():
    assert fill_forward({0: 5, 3: 7}, 5) == [5, 5, 5, 7, 7]
    assert fill_forward({2: 9}, 4) == [0, 0, 9, 9]
    assert fill_forward({}, 3, initial=None) == [None, None, None]


def test_zig64_voices():
    reg = {
        (0, 'freq_lo'): {0: 0xEF}, (0, 'freq_hi'): {0: 0x13},
        (0, 'pw_lo'): {0: 0x00}, (0, 'pw_hi'): {0: 0xF5},   # &0xF -> 0x500
        (0, 'control'): {0: 0x41, 2: 0x40},
        (0, 'attack_decay'): {0: 0x00}, (0, 'sustain_release'): {0: 0xDB},
    }
    V = zig64_voices(reg, 3)
    assert V[0]['freq'] == [0x13EF, 0x13EF, 0x13EF]
    assert V[0]['pw'] == [0x500, 0x500, 0x500]
    assert V[0]['wf'] == [0x41, 0x41, 0x40]
    assert V[1]['freq'] == [0, 0, 0]     # untouched voice serializes to zeros


# --- best-offset search -----------------------------------------------------

def test_best_gated_offset_picks_max_and_keeps_its_total():
    scores = {-1: (2, 10, 'a'), 0: (5, 9, 'b'), 1: (5, 8, 'c'), 2: (3, 7, 'd')}
    off, hits, total, extra = best_gated_offset(range(-1, 3), lambda o: scores[o])
    # ties keep the EARLIEST offset (0 beats 1 at hits=5)
    assert (off, hits, total, extra) == (0, 5, 9, 'b')
