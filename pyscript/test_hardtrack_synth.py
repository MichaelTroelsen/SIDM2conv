"""Tests for the HardTrack Composer per-frame synth engine.

The corpus (SID/Shogoon) is tracked, so the end-to-end tests here really run:
they drive the model and the real 6502 playroutine over the same frames and
require the SID registers to agree byte for byte. That is the only test that
protects the claim -- a unit test on the stepper in isolation would have passed
happily while `pulse_table` pointed outside the module and `pulse_program()`
returned a full-length series of zeroes.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from hardtrack_synth_validate import register_tracks, validate  # noqa: E402
from sidm2.hardtrack_parser import HardTrackError, HardTrackModule  # noqa: E402
from sidm2.hardtrack_synth import (  # noqa: E402
    _RAM, _ram_addr, ram_layout_base, simulate_registers,
)

CORP = os.path.join(os.path.dirname(_HERE), 'SID', 'Shogoon')
needs_corpus = pytest.mark.skipif(not os.path.isdir(CORP),
                                  reason='Shogoon corpus absent')

# Files whose per-voice RAM layout the three signature anchors agree on.
SEEDED = ['Zakplus', 'Hopscotch', 'Love_tune_3', 'Ritual_II_tune_2',
          'Walk_to_Soul']
# The second shipped player build: a different variable allocation, so the model
# runs from zeroes and carries a startup transient until the first note-on.
UNSEEDED = ['What_Can_I_Say_Crap', 'Illmatic_end']


def sid(name):
    return os.path.join(CORP, name + '.sid')


@needs_corpus
def test_pulse_table_lands_inside_the_module():
    """Regression: the operand is at signature+7, the OPCODE sits at +6.

    Reading +6 put this table outside every module in the corpus, so
    `pulse_program()` decoded nothing but zeroes -- which looks exactly like a
    valid program that happens to hold the pulse width still.
    """
    seen = 0
    for name in sorted(os.listdir(CORP)):
        try:
            m = HardTrackModule.from_sid(os.path.join(CORP, name))
        except HardTrackError:
            continue
        if m.pulse_table is None:
            continue
        seen += 1
        assert m.load <= m.pulse_table < m.load + len(m.data), name
    assert seen > 20


@needs_corpus
def test_pulse_programs_carry_real_sweep_steps():
    """At least one instrument must sweep. All-zero is the bug's signature."""
    m = HardTrackModule.from_sid(sid('Zakplus'))
    steps = [s for n in range(m.num_instruments)
             for s in m.pulse_program(m.instrument(n).pulse_cursor)]
    assert any(mag for mag, _ in steps), 'no pulse sweep decoded at all'


@needs_corpus
@pytest.mark.parametrize('name', SEEDED)
def test_ram_layout_anchors_agree(name):
    assert ram_layout_base(HardTrackModule.from_sid(sid(name))) is not None


@needs_corpus
def test_ram_layout_lands_on_the_known_addresses():
    """Zakplus is unrelocated, so the block's addresses are readable constants."""
    base = ram_layout_base(HardTrackModule.from_sid(sid('Zakplus')))
    for want, var in ((0x168B, 'ad'), (0x1697, 'pulse_lo'), (0x16B9, 'abs_freq'),
                      (0x16C2, 'pulse_cur'), (0x16CE, 'prev_mode'),
                      (0x16D4, 'wave_freeze'), (0x16F2, 'wave_cur'),
                      (0x1701, 'instr'), (0x170A, 'active')):
        assert _ram_addr(base, _RAM.index(var)) == want, var


@needs_corpus
def test_power_on_ram_is_not_zero():
    """The block is inside the loaded image, so init does NOT leave it blank.

    Assuming zero is what put the first note of every voice one vibrato tick
    out of phase; this pins the fact the seeding relies on.
    """
    m = HardTrackModule.from_sid(sid('Zakplus'))
    base = ram_layout_base(m)
    mode = _ram_addr(base, _RAM.index('mode'))
    assert any(m.byte(mode + v) for v in range(3))


@needs_corpus
def test_note_on_writes_only_the_gate_then_the_frequency_next_frame():
    """The three-frame pipeline: $D404 = $09 first, registers the frame after."""
    rows = simulate_registers(HardTrackModule.from_sid(sid('Zakplus')), 0, 12)
    gate = [f for f, r in enumerate(rows) if r[0].waveform == 0x09]
    assert gate, 'no note-on gate frame found'
    f = gate[0]
    assert rows[f][0].freq == rows[f - 1][0].freq      # not written yet
    assert rows[f + 1][0].freq != rows[f][0].freq      # written by $1553


@needs_corpus
@pytest.mark.parametrize('name', SEEDED)
def test_registers_are_byte_exact_against_the_real_playroutine(name):
    acc, _, live, seeded = validate(sid(name), seconds=10)
    assert live, 'the compared series carry no information'
    assert seeded
    for reg in ('freq', 'wf', 'pulse'):
        ok, tot = acc[reg]
        assert tot > 1000, (name, reg, tot)
        assert ok == tot, f'{name} {reg}: {tot - ok} frames differ'


@needs_corpus
def test_program_driven_instruments_are_scoreable_now():
    """The whole point: field-5 bit 7 notes used to score 2.6% by construction.

    They score that because onset scoring predicts the sequencer pitch, which
    for these instruments is never written anywhere. Predicting the register the
    wave program actually writes puts them at parity with everything else.
    """
    acc, _, _, _ = validate(sid('Ritual_II_tune_2'), seconds=10)
    ok, tot = acc['freq_drv']
    assert tot > 100, 'this file is supposed to exercise the flag'
    assert ok == tot


@needs_corpus
@pytest.mark.parametrize('name', UNSEEDED)
def test_unseeded_build_is_still_right_once_it_has_started(name):
    acc, _, live, seeded = validate(sid(name), seconds=20)
    assert live and not seeded
    ok, tot = acc['freq']
    assert ok / tot > 0.9, f'{name}: {ok}/{tot}'
    assert acc['wf'][0] == acc['wf'][1], 'the waveform program must be exact'


@needs_corpus
def test_the_compared_series_actually_vary():
    """Guards the 100%s: two constant series also agree on every frame."""
    m = HardTrackModule.from_sid(sid('Zakplus'))
    rows = simulate_registers(m, 0, 500)
    for vi in range(3):
        assert len({r[vi].freq for r in rows}) > 5
        assert len({r[vi].waveform for r in rows}) > 2


@needs_corpus
def test_model_is_deterministic():
    m = HardTrackModule.from_sid(sid('Hopscotch'))
    a = [(v.freq, v.waveform, v.pulse) for r in simulate_registers(m, 0, 300) for v in r]
    b = [(v.freq, v.waveform, v.pulse) for r in simulate_registers(m, 0, 300) for v in r]
    assert a == b


@needs_corpus
def test_refuses_when_the_program_tables_are_missing():
    m = HardTrackModule.from_sid(sid('Zakplus'))
    m.pulse_table = None
    with pytest.raises(HardTrackError):
        simulate_registers(m, 0, 10)


@needs_corpus
def test_siddump_frame_alignment_is_zero_not_fitted():
    """Offset 0 must be a sharp peak, or the alignment was tuned into the score."""
    at = {o: validate(sid('Zakplus'), seconds=10, offset=o)[0]['freq'] for o in (-1, 0, 1)}
    best = at[0][0] / at[0][1]
    assert best == 1.0
    for o in (-1, 1):
        assert at[o][0] / at[o][1] < 0.8, o
