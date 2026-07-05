"""Tests for the structural WAVE split (whats-next step 3, MON_ARP_STRUCT).

The MoN release is a duration-relative terminal GATE-OFF; the structural build
moves it out of the per-note wave program into sequence gate-off rows (note $00
-> VGMASK=$fe) so one canonical attack+steady program serves every duration.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin"))

import build_mon_native_song as BM                      # noqa: E402


def _frames(wfs, v=0):
    blank = {'freq': None, 'wf': None, 'pul': None}
    return [({0: dict(blank, wf=w) if v == 0 else dict(blank),
              1: dict(blank, wf=w) if v == 1 else dict(blank),
              2: dict(blank, wf=w) if v == 2 else dict(blank)}, 0) for w in wfs]


class _ConstGrid:
    """Minimal MON-like grid: 3 frames/tick, no swing, no delay."""
    def tick_to_frame(self, t):
        return t * 3

    def frame_to_tick(self, f):
        return max(0, (f + 2) // 3)


def test_gate_split_finds_tick_aligned_release(monkeypatch):
    monkeypatch.setattr(BM, "ARP_STRUCT", True)
    m = _ConstGrid()
    # 8-tick note (24 frames): attack $11, steady $41 until frame 12, then $40
    wfs = [0x11] + [0x41] * 11 + [0x40] * 12
    gt, cap, off_k, end = BM._gate_split(m, _frames(wfs), 0, 0, 24, 0, 8)
    assert (gt, off_k, end) == (4, 12, 24)              # gate-off at tick 4 exactly
    assert BM._settle_trim(cap[:off_k]) == (0x11, 0x41)


def test_gate_split_tolerates_one_frame_skew_and_bleed(monkeypatch):
    monkeypatch.setattr(BM, "ARP_STRUCT", True)
    m = _ConstGrid()
    # gate-off at frame 11 (1 before the tick-12 boundary: the wf-leads-freq skew),
    # plus 2 trailing frames of next-note attack bleed ($41)
    wfs = [0x11] + [0x41] * 10 + [0x40] * 11 + [0x41] * 2
    gt, cap, off_k, end = BM._gate_split(m, _frames(wfs), 0, 0, 24, 0, 8)
    assert (gt, off_k, end) == (4, 11, 22)


def test_gate_split_rejects_unaligned_and_flag_off(monkeypatch):
    monkeypatch.setattr(BM, "ARP_STRUCT", True)
    m = _ConstGrid()
    # gate-off at frame 10: 2 frames before the tick boundary -> no split
    wfs = [0x11] + [0x41] * 9 + [0x40] * 14
    gt, cap, off_k, end = BM._gate_split(m, _frames(wfs), 0, 0, 24, 0, 8)
    assert (gt, off_k) == (8, None)
    monkeypatch.setattr(BM, "ARP_STRUCT", False)
    gt, cap, off_k, end = BM._gate_split(m, _frames([0x41] * 24), 0, 0, 24, 0, 8)
    assert (gt, cap, off_k) == (8, None, None)          # flag off -> untouched path


def test_wave_masked_ok_canonical_reproduces_short_echo():
    # canonical (long note): attack $11 + steady $41. A short echo note gates off
    # after 1 frame: original shows $11, then $40 x9. The canonical program under
    # the gate mask reproduces it exactly ($41 & $fe == $40).
    canon = (0x11, 0x41)
    wfs = [0x11] + [0x40] * 9
    assert BM._wave_masked_ok(canon, wfs, 1, 1, 10)
    # but not if the tail has a different shape
    assert not BM._wave_masked_ok(canon, [0x11] + [0x20] * 9, 1, 1, 10)
