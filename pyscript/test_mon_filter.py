"""Regression tests for the MoN native-driver FILTER reconstruction in
bin/build_mon_native_song.py (routed-voice detection, drive detection, per-note cutoff
ENVELOPE capture, and its composite (instrument, shape) keying).

Background: the MoN filter is one global cutoff envelope restarted on the routed voice's
note-ons. These tests pin the three building blocks + a round-trip of the captured
program through a faithful model of the driver's filt_prog_step, guarding two regressions
found while raising Myth sub0's filter fidelity:
  * a fast per-frame sweep (Hawkeye: +-8 hi/frame == FILT_FAST) must NOT be mistaken for a
    restart on every frame (drive detection stays note-on-aligned);
  * co-existing envelope shapes (Myth sub0: up-ramp from 64 vs down-ramp from 128) must
    produce DISTINCT programs, never conflated into one.
See memory/hawkeye-mon-filter-engine-re.md + myth-supremacy-mon-re.md.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

import build_mon_native_song as BM


def _ftr(cutoffs, ctrl=0xF2):
    """Build an ftr list [(cutoff11, ctrl)] from a list of 8-bit $D416 hi values."""
    return [((c << 3) & 0x7FF, ctrl) for c in cutoffs]


def _run_program(prog, nframes):
    """Faithful model of the driver's filt_prog_step: SET base, ADD delta/frame for a
    count, 0x7f = freeze. Returns the $D416 hi-byte cutoff produced per frame."""
    chi = 0
    idx = 0
    cnt = 0
    add = 0
    out = []
    for _ in range(nframes):
        if cnt == 0 and idx < len(prog):
            b0, b1, b2 = prog[idx]
            if b0 == 0x7F:                       # freeze: hold current cutoff forever
                add = 0
                cnt = 1 << 30
            elif b0 & 0x80:                      # SET: cutoff hi = (b0&f):(b1) high nibble
                chi = ((b0 & 0x0F) << 4) | (b1 >> 4)
                add = 0
                cnt = 1
                idx += 1
            else:                                # ADD: 12-bit delta<<4 -> hi-byte delta
                twelve = ((b0 & 0x0F) << 8) | b1
                if twelve & 0x800:
                    twelve -= 0x1000
                add = twelve >> 4                # per-frame hi-byte delta
                cnt = b2
                idx += 1
        chi = (chi + add) & 0xFF
        out.append(chi)
        if cnt:
            cnt -= 1
    return out


# --- routed_voice ---------------------------------------------------------------------

def test_routed_voice_single_bit():
    assert BM.routed_voice(_ftr([100] * 8, ctrl=0x01)) == 0
    assert BM.routed_voice(_ftr([100] * 8, ctrl=0x02)) == 1
    assert BM.routed_voice(_ftr([100] * 8, ctrl=0x04)) == 2
    # high nibble (resonance) is ignored; only the low routing nibble matters
    assert BM.routed_voice(_ftr([100] * 8, ctrl=0xF2)) == 1


def test_routed_voice_none_when_ambiguous():
    assert BM.routed_voice(_ftr([100] * 8, ctrl=0x00)) is None   # nothing routed
    assert BM.routed_voice(_ftr([100] * 8, ctrl=0x03)) is None   # two voices routed


# --- detect_filter_drives -------------------------------------------------------------

def test_drives_restricted_to_routed_voice():
    # a single downward reset at frame 5; note-ons on voice 0 (frame 4) and voice 1
    # (frame 5). Routed to voice 1 -> only the voice-1 note-on is credited.
    cut = [64 + 2 * k for k in range(5)] + [64 + 2 * k for k in range(10)]
    ftr = _ftr(cut, ctrl=0x02)
    onsets = [{4}, {5}, set()]
    drv_any = BM.detect_filter_drives(ftr, onsets, routed=None)
    drv_v1 = BM.detect_filter_drives(ftr, onsets, routed=1)
    assert set(drv_v1.values()) == {1}                 # only the routed voice
    assert 4 not in drv_v1                              # the unrouted voice-0 note dropped
    assert drv_any                                     # unrestricted still finds a drive


def test_fast_sweep_not_over_detected_as_restarts():
    # a continuous +-8 hi/frame sweep (== FILT_FAST) with NO note-ons must yield NO drives:
    # the per-frame delta alone must not be mistaken for a restart (the Hawkeye regression).
    cut = []
    v, d = 100, 8
    for _ in range(40):
        cut.append(v)
        v += d
        if v >= 220 or v <= 40:
            d = -d
    ftr = _ftr(cut, ctrl=0x02)
    drives = BM.detect_filter_drives(ftr, [set(), set(), set()], routed=1)
    assert drives == {}


# --- filter_program_for (envelope capture + round-trip) -------------------------------

def test_program_roundtrip_upramp():
    # base 64, +2/frame for 30 frames -> then sustain; the captured program must replay
    # to the same cutoff sequence.
    cut = [64 + 2 * k for k in range(30)] + [124] * 10
    ftr = _ftr(cut)
    flag, prog = BM.filter_program_for(ftr, 0, len(cut))
    assert flag == 0x40 and prog
    replay = _run_program(prog, len(cut))
    assert replay == cut


def test_program_roundtrip_downramp():
    cut = [128 - 4 * k for k in range(20)] + [48] * 8
    ftr = _ftr(cut)
    flag, prog = BM.filter_program_for(ftr, 0, len(cut))
    replay = _run_program(prog, len(cut))
    assert replay == cut


def test_up_and_down_ramps_are_distinct_programs():
    up = BM.filter_program_for(_ftr([64 + 2 * k for k in range(20)]), 0, 20)[1]
    down = BM.filter_program_for(_ftr([128 - 4 * k for k in range(20)]), 0, 20)[1]
    assert up != down
