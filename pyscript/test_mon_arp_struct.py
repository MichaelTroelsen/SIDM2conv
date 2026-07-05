"""Tests for the structural-arp FM wiring (whats-next step 2, MON_ARP_STRUCT).

Covers: the phase-aligned looping SEMITONE program emitted from MON.arp_program
(the ROM's compact chord-arp table), the Hz-run cap that keeps byte2 out of the
new $7f/$80+ entry space, and a pure-Python round-trip through a model of the
driver's fm_step dispatch (semitone + loop entries).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin"))

import build_mon_native_song as BM                      # noqa: E402


def test_arp_fm_program_phase_alignment():
    # minor chord, dur $10 -> fps 2. Frame 0 is the driver's pr_note base hold,
    # so step0 gets fps-1 frames, then the rotation step1..stepN,step0 at full
    # fps, looping over the rotation.
    prog = BM.arp_fm_program({'dur': 0x10, 'steps': [0, 3, 7], 'loop': True})
    assert prog == [(0, 0, 0x81),                       # step0 remainder (1 frame)
                    (3, 0, 0x82), (7, 0, 0x82), (0, 0, 0x82),
                    (1, 0, 0x7F)]                       # loop to the rotation start


def test_arp_fm_program_negative_and_end():
    prog = BM.arp_fm_program({'dur': 0x10, 'steps': [12, 0], 'loop': False})
    assert prog[0] == (12, 0, 0x81)
    assert prog[-1] == (0, 0, 0)                        # $fe END -> freeze
    neg = BM.arp_fm_program({'dur': 0x10, 'steps': [0, -12], 'loop': True})
    assert neg[1] == (0xF4, 0, 0x82)                    # signed semitone byte


def test_fm_program_run_cap():
    # a >126-frame flat vibrato hold must split so byte2 never reaches $7f
    frames = [({0: {'freq': 0x1000 + (k % 2), 'wf': 0x41, 'pul': 0x800},
                1: {'freq': None, 'wf': None, 'pul': None},
                2: {'freq': None, 'wf': None, 'pul': None}}, 0)
              for k in range(200)]
    prog = BM.fm_program_for(frames, 0, 0, 200, 0x1000)
    assert all(1 <= e[2] <= 126 or e == (0, 0, 0) for e in prog)


def _run_fm_model(prog, freqtable, basenote, vfreq, nframes):
    """Faithful model of the driver's fm_step dispatch (Hz run / freeze /
    semitone / loop) producing the per-frame freq output."""
    out, acc, off, cnt, ip = [], 0, 0, 1, 0          # pr_note: 1-frame base hold
    for _ in range(nframes):
        if cnt == 0:
            guard = 16
            while True:
                b0, b1, b2 = prog[ip]
                if b2 == 0:
                    off, cnt = 0, -1                  # freeze
                    break
                if b2 >= 0x80:                        # semitone hold
                    s = b0 - 256 if b0 >= 0x80 else b0
                    acc = (freqtable[(basenote + s) & 0x7F] - vfreq) & 0xFFFF
                    off, cnt = 0, b2 & 0x7F
                    ip += 1
                    break
                if b2 == 0x7F:                        # loop
                    ip = b0
                    guard -= 1
                    if guard == 0:
                        off, cnt = 0, -1
                        break
                    continue
                off, cnt = (b0 | (b1 << 8)), b2       # Hz run
                ip += 1
                break
        acc = (acc + off) & 0xFFFF
        if cnt > 0:
            cnt -= 1
        out.append((vfreq + acc) & 0xFFFF)
    return out


def test_vibrato_program_detection_and_unroll():
    # captured Hz vibrato: 9-frame delay, centered legs (+$32 x2 first, then
    # alternating 5-frame legs) — the exact instr-31 shape at note $39, whose
    # semitone step is 427: depth $32 == (427*30)>>8 -> scale 30.
    step = 427
    prog = [(0, 0, 9), (0x32, 0, 2), (0xCE, 0xFF, 5), (0x32, 0, 5),
            (0xCE, 0xFF, 5), (0x32, 0, 5), (0, 0, 0)]
    vib = BM._vibrato_program(prog, step)
    assert vib is not None
    assert vib[0] == (0, 0, 9)                          # delay
    assert vib[1] == (30, 0x40, 2)                      # half first leg, positive
    assert vib[-1] == (2, 0, 0x7F)                      # loop over the steady legs
    # the scaled program must unroll identically to the Hz capture
    assert BM._fm_unroll(vib, 30, step) == BM._fm_unroll(prog, 30)
    # and serve ANOTHER pitch exactly (pitch-proportional): step 214 -> depth 25
    prog2 = [(0, 0, 9), (25, 0, 2), (0x100 - 25, 0xFF, 5), (25, 0, 5),
             (0x100 - 25, 0xFF, 5), (0, 0, 0)]
    assert BM._fm_unroll(vib, 24, 214) == BM._fm_unroll(prog2, 24)


def test_vibrato_program_rejects_non_vibrato():
    assert BM._vibrato_program([(0x10, 0, 3), (0x20, 0, 3), (0, 0, 0)], 427) is None
    assert BM._vibrato_program([(0, 0, 9), (0, 0, 0)], 427) is None
    # depth not an exact step fraction -> reject (byte-exactness guard):
    # 52 -> scale round(52*256/427)=31, but (427*31)>>8 == 51 != 52
    assert BM._vibrato_program([(0x34, 0, 2), (0xCC, 0xFF, 5), (0x34, 0, 5),
                                (0, 0, 0)], 427) is None


def test_pulse_unroll_models_driver():
    prog = [(0x88, 0x00, 1), (0x0F, 0xF0, 3), (0x7F, 0, 0)]   # set $800, add -$10 x3
    assert BM._pulse_unroll(prog, 6) == [0x800, 0x7F0, 0x7E0, 0x7D0, 0x7D0, 0x7D0]


def test_arp_round_trip_matches_rom_phase():
    # freqtable where note n has freq 1000+n so semitone math is legible
    ft = [1000 + n for n in range(128)]
    note = 40
    prog = BM.arp_fm_program({'dur': 0x10, 'steps': [0, 3, 8], 'loop': True})
    got = _run_fm_model(prog, ft, note, ft[note], 14)
    # ROM: step k occupies frames [2k, 2k+2): base,base, +3,+3, +8,+8, cycle
    want = [1040, 1040, 1043, 1043, 1048, 1048,
            1040, 1040, 1043, 1043, 1048, 1048, 1040, 1040]
    assert got == want
