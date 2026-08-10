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
# The second shipped player build: a different variable allocation AND a
# different code layout, so no positional table can follow it. These are seeded
# per-variable from each one's own consumer instead -- see
# `HardTrackModule.voice_var_addrs`.
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
def test_second_build_is_seeded_by_signature_not_by_layout(name):
    """These files have no `_RAM` layout, so they are seeded per-variable.

    `seeded` used to be a bool. It is now the name of the source, because there
    are three states and collapsing them loses the one that matters: 'signature'
    means five variables were placed from their own consumers while the other 38
    started at zero. Ablation on build 1 prices those 38 at 0.03 points, so a
    file scoring below the seeded population is NOT short of seed data.
    """
    acc, _, live, seeded = validate(sid(name), seconds=20)
    assert live and seeded == 'signature'
    ok, tot = acc['freq']
    assert ok / tot > 0.99, f'{name}: {ok}/{tot}'
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


# --------------------------------------------------------------------------
# The filter engine. It is global rather than per-voice, which is what makes
# most of these worth pinning: everything else in this player is indexed by X.
# --------------------------------------------------------------------------

def _decodable():
    import glob
    for p in sorted(glob.glob(os.path.join(CORP, '*.sid'))):
        try:
            yield p, HardTrackModule.from_sid(p)
        except HardTrackError:
            continue


@needs_corpus
def test_filter_engine_is_located_in_every_decodable_file():
    missing = [os.path.basename(p) for p, m in _decodable()
               if m.filter_table is None]
    assert not missing, f'filter engine not located: {missing}'


@needs_corpus
def test_filter_field_tables_agree_with_the_instrument_stride():
    """Two independent recoveries of f6/f7/f12 must land on the same address.

    The signature reads them off the re-arm's own operands; the stride reads
    them off `instrument_base + k * num_instruments`. They share no inputs, so
    agreement on every file is what rules out a plausible-looking table that
    happens to be the neighbouring field -- the exact error that had fields 3
    and 4 swapped for two commits.
    """
    for p, m in _decodable():
        b, st = m.instrument_base, m.num_instruments
        assert (m.filter_f6_table, m.filter_f7_table, m.filter_f12_table) == \
            (b + 6 * st, b + 7 * st, b + 12 * st), os.path.basename(p)


@needs_corpus
def test_cutoff_low_byte_is_never_written():
    """$D415 has no store anywhere in the corpus, so the cutoff is 8-bit.

    If this ever fails the model is wrong by construction: it accumulates into
    a single byte and compares against siddump's FCut >> 3.
    """
    from sidm2.hardtrack_parser import _word
    for p, m in _decodable():
        hits = [i for i in range(len(m.data) - 2)
                if m.data[i] in (0x8D, 0x99, 0x9D)
                and _word(m.data, i + 1) in (0xD415, 0xD414)]
        assert not hits, f'{os.path.basename(p)}: writes $D415'


@needs_corpus
def test_saved_filter_cursor_is_pair_aligned():
    """The program is [delta][delay] pairs, so a cursor into it must be even."""
    odd = [os.path.basename(p) for p, m in _decodable() if m.filter_cursor % 2]
    assert not odd, f'odd filter cursor: {odd}'


@needs_corpus
def test_volume_is_taken_from_inits_store_not_the_saved_image():
    """`init` sets the volume byte, so the image value is not what plays.

    `Tribute_to_Laxity` shifts that block by one instruction, which is why this
    is recovered by searching for the store rather than by a fixed offset.
    """
    for p, m in _decodable():
        assert m.filter_volume == 0x0F, os.path.basename(p)


@needs_corpus
def test_love_tune_2_cutoff_sweeps_and_wraps():
    """A golden capture: $1a + $40 a frame, wrapping at 8 bits.

    Taken from siddump's FCut column ($02D0 $04D0 $06D0 $00D0 $02D0 >> 3), so a
    regression here means the model stopped agreeing with the real playroutine
    without needing siddump on the path.
    """
    from sidm2.hardtrack_synth import simulate_all
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    assert (m.filter_cutoff, m.filter_delta) == (0x1A, 0x40)
    _, filt = simulate_all(m, 0, 5)
    assert [f.cutoff for f in filt] == [0x5A, 0x9A, 0xDA, 0x1A, 0x5A]


@needs_corpus
def test_cutoff_accumulator_wraps_rather_than_clamping():
    """The negative control for the golden capture above.

    Clamping at 255 instead of wrapping scores 24.75% against siddump rather
    than 100%, so this is the single assumption the cutoff column rests on.
    """
    from sidm2.hardtrack_synth import simulate_all
    _, filt = simulate_all(HardTrackModule.from_sid(sid('Love_tune_2')), 0, 400)
    assert max(f.cutoff for f in filt) <= 0xFF
    assert any(filt[i].cutoff < filt[i - 1].cutoff for i in range(1, len(filt))), \
        'the accumulator never wrapped -- it is being clamped'


@needs_corpus
@pytest.mark.parametrize('name', ['Love_tune_2', 'Hopscotch', 'Ritual_II_tune_1',
                                  'Walk_to_Soul', 'Tribute_to_Laxity'])
def test_filter_registers_are_byte_exact_against_the_real_playroutine(name):
    acc, _, _, _ = validate(sid(name), seconds=6)
    for key in ('cutoff', 'res_route', 'mode_vol'):
        ok, tot = acc[key]
        if not tot:            # exercised() withheld it: no information here
            continue
        assert ok == tot, f'{name} {key}: {ok}/{tot}'


@needs_corpus
def test_f12_zero_clears_the_voices_routing_bit():
    """`f12 == 0` is an active switch-out, not a no-op.

    Reading it as "skip the re-arm" scores $D417 at 48.28% instead of 100%.
    """
    from sidm2.hardtrack_synth import _F, _arm_filter

    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    f = _F(m)
    f.shadow = 0xF7                      # resonance $F0 + all three voices in

    class V:
        instr = prev_instr = 0

    _arm_filter(V(), 1, 0, f, lambda k, n: 0, lambda n: 0)
    assert f.shadow == 0xF5, 'voice 1 was not switched out of the filter'
    assert f.r_d417 == 0xF5


@needs_corpus
def test_field5_bit4_is_not_exercised_by_this_corpus():
    """Guards a NEGATIVE result, so nobody records the gate as verified.

    Field 5 bit 4 gates the filter re-arm on a repeated note. Ignoring it
    entirely changes no measured number on this corpus, and this is why: only
    21 instruments set it and just one of those has a filter to re-arm. The
    reading comes from its only consumer in the disassembly, and the corpus can
    neither confirm nor refute it. If this count ever moves, the gate becomes
    testable and the claim can be upgraded.
    """
    set_bit4 = with_filter = 0
    for _p, m in _decodable():
        if m.flag_table is None:
            continue
        for i in range(m.num_instruments):
            if m.byte(m.flag_table + i) & 0x10:
                set_bit4 += 1
                with_filter += bool(m.byte(m.filter_f12_table + i))
    assert (set_bit4, with_filter) == (21, 1)


@needs_corpus
def test_simulate_registers_still_returns_only_the_voices():
    """The filter arrived through a new entry point, not by changing this one."""
    from sidm2.hardtrack_synth import simulate_all
    m = HardTrackModule.from_sid(sid('Zakplus'))
    voices = simulate_registers(m, 0, 50)
    assert voices == simulate_all(m, 0, 50)[0]
    assert all(len(row) == 3 for row in voices)


# --------------------------------------------------------------------------
# Per-variable seeding by signature: how the second player build stops running
# from zeroes without anyone hand-mapping its variable allocation.
# --------------------------------------------------------------------------

@needs_corpus
def test_voice_var_addrs_resolves_on_every_decodable_file():
    """Including the second build and Tribute_to_Laxity's third shape.

    `ram_layout_base` covers 18 of 33; this covers 33 of 33, because it asks
    each variable's own consumer instead of assuming an allocation.
    """
    missing = [os.path.basename(p) for p, m in _decodable() if not m.voice_var_addrs()]
    assert not missing, f'voice_var_addrs did not resolve: {missing}'


@needs_corpus
def test_signature_addrs_agree_with_the_layout_where_both_exist():
    """The cross-check that makes the signatures trustworthy on files with no layout.

    On the 18 build-1 files both recoveries are available and share no inputs --
    one walks a positional table from the abs-flag anchor, the other reads
    operands out of two unrelated instruction blocks. Agreement on every one is
    what licenses using the signatures alone on the other 15.
    """
    from sidm2.hardtrack_synth import _RAM_INDEX, _ram_addr, ram_layout_base
    checked = 0
    for p, m in _decodable():
        base = ram_layout_base(m)
        if base is None:
            continue
        checked += 1
        for name, addr in m.voice_var_addrs().items():
            if name in _RAM_INDEX:
                assert addr == _ram_addr(base, _RAM_INDEX[name]), \
                    f'{os.path.basename(p)}: {name}'
    assert checked == 18


@needs_corpus
def test_seed_source_splits_the_corpus_the_way_the_report_claims():
    from sidm2.hardtrack_synth import seed_source
    from collections import Counter
    c = Counter(seed_source(m)[1] for _p, m in _decodable())
    assert dict(c) == {'layout+sig': 18, 'signature': 15}


@needs_corpus
def test_seeding_the_second_build_actually_changes_its_output():
    """Negative control: a seed that changed nothing would score the same.

    Without it, "the second build is now seeded" could be true of the code and
    false of the result -- the exact shape of a vacuous pass.
    """
    import sidm2.hardtrack_synth as HS
    m = HardTrackModule.from_sid(sid('What_Can_I_Say_Crap'))
    seeded = HS.simulate_registers(m, 0, 300)
    orig = HS.seed_source
    try:
        HS.seed_source = lambda mod: (None, 'none')
        bare = HS.simulate_registers(m, 0, 300)
    finally:
        HS.seed_source = orig
    assert seeded != bare, 'seeding the second build changed nothing'
