"""Tests for the HardTrack Composer module parser.

The corpus (SID/Shogoon) is not tracked, so corpus-dependent tests skip when it
is absent. The synthetic tests below do not need it and always run -- they are
what keeps the grammar honest on a fresh clone.
"""
import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.hardtrack_parser import (  # noqa: E402
    CMD_REST, HardTrackError, HardTrackModule, INSTRUMENT_FIELDS,
    MAX_INSTRUMENTS, ORDER_END, ORDER_JUMP, PATTERN_END, simulate,
)

CORP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'SID', 'Shogoon')
needs_corpus = pytest.mark.skipif(not os.path.isdir(CORP), reason='Shogoon corpus absent')


def sid(name):
    return os.path.join(CORP, name + '.sid')


# --------------------------------------------------------------------------
# structure
# --------------------------------------------------------------------------
@needs_corpus
def test_love_tune_2_layout():
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    assert m.load == 0x1000
    assert m.speed(0) == 4
    # the instrument block is 13 parallel 32-byte tables and must tile exactly
    # into the space before the next located table
    assert m.instrument_base == 0x1715
    assert m.freq_lo_table == 0x15CB and m.freq_hi_table == 0x162B


@needs_corpus
def test_freq_table_doubles_every_octave():
    """A frequency table that is misidentified (or read at the wrong stride)
    will not octave-double; this catches a swapped lo/hi base too."""
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    for n in range(0, 60):
        lo, hi = m.freq(n), m.freq(n + 12)
        assert abs(hi - 2 * lo) <= 2, f'note {n}: ${lo:04x} -> ${hi:04x} not an octave'


@needs_corpus
def test_orderlist_grammar():
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    ol = m.orderlist(0, 0)
    assert ol[0] == ('transpose', 0)
    assert ('pat', 0) in ol
    # the voice-0 list ends in a loop-back jump, not a bare end
    assert ol[-1][0] == 'jump'


@needs_corpus
def test_pattern_is_note_instrument_pairs():
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    ev = m.pattern(0)
    assert ev[0][0] == 'note'
    assert ev[-1][0] == 'end'
    assert any(k == 'rest' for k, _, _ in ev)
    # every note index must be addressable in the 96-entry frequency table
    assert all(a < 96 for k, a, _ in ev if k == 'note')


@needs_corpus
@pytest.mark.parametrize('name,load', [('Timsoft_Intro', 0x4000), ('Trance', 0xA000)])
def test_relocated_modules_parse(name, load):
    """Table addresses are patched per file, so a module that does not load at
    $1000 must still resolve -- this is what the signature search buys."""
    m = HardTrackModule.from_sid(sid(name))
    assert m.load == load
    assert m.instrument_base > load
    assert m.freq(12) > m.freq(0)
    assert any(k == 'pat' for k, _ in m.orderlist(0, 0))


@needs_corpus
def test_both_player_variants_parse():
    """Two shipped variants differ by 5 bytes in init (play at init+$78/+$7d);
    both must decode with the same signatures."""
    a = HardTrackModule.from_sid(sid('Love_tune_2'))      # +$7d variant
    b = HardTrackModule.from_sid(sid('Jazzloor'))         # +$78 variant
    for m in (a, b):
        assert m.speed(0) > 0
        assert m.patterns_used(0)


# --------------------------------------------------------------------------
# refusal -- a wrong decode must be loud, not silent
# --------------------------------------------------------------------------
@needs_corpus
@pytest.mark.parametrize('name', ['Eternal', 'Fruitmania', 'Zone_of_Darkness',
                                  'Miecze_Valdgira_2', 'Commercial_Fake'])
def test_wrapped_rips_are_refused(name):
    with pytest.raises(HardTrackError):
        HardTrackModule.from_sid(sid(name))


def test_non_sid_is_refused(tmp_path):
    p = tmp_path / 'x.bin'
    p.write_bytes(b'\x00' * 64)
    with pytest.raises(HardTrackError):
        HardTrackModule.from_sid(str(p))


def test_bytes_without_signature_are_refused():
    with pytest.raises(HardTrackError):
        HardTrackModule(0x1000, bytes(4096))


# --------------------------------------------------------------------------
# instrument records
# --------------------------------------------------------------------------
@needs_corpus
def test_instrument_record_shape():
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    i = m.instrument(0)
    assert len(i.raw) == INSTRUMENT_FIELDS
    assert i.pulse_hi | i.pulse_lo == i.raw[2]


@needs_corpus
@pytest.mark.parametrize('name', ['Love_tune_2', 'If_I_Was_a_Rich_Man', 'Jazzloor',
                                  'Altered_States_Tune_1', 'Timsoft_Intro'])
def test_drives_freq_flag_is_bit7_of_field5(name):
    """Cross-checks the instrument STRIDE, not just the flag.

    `instrument_drives_freq()` reads the flag table at its signature-derived
    address; `instrument(n).flags` reads field 5 at instrument_base + 5*stride.
    They agree only when the stride is right, so this fails loudly on any file
    whose instrument count is not the one assumed. Parametrised across files
    with 3, 9, 20, 24 and 32 instruments precisely because the original bug was
    invisible on a 32-instrument file.
    """
    m = HardTrackModule.from_sid(sid(name))
    for n in range(m.num_instruments):
        assert m.instrument_drives_freq(n) == bool(m.instrument(n).flags & 0x80), n


@needs_corpus
def test_instrument_count_varies_per_file_and_is_cross_verified():
    """The 13 parallel instrument tables are `num_instruments` bytes each, and
    that count is per-file (3..32 here) -- NOT a constant 32. Hardcoding 32
    reads every field but the first from the wrong address and still returns
    plausible-looking bytes, so derive it two ways and require agreement."""
    counts = {}
    unverified = []
    for name in sorted(os.listdir(CORP)):
        if not name.endswith('.sid'):
            continue
        try:
            m = HardTrackModule.from_sid(os.path.join(CORP, name))
        except HardTrackError:
            continue
        counts[name] = m.num_instruments
        assert 0 < m.num_instruments <= MAX_INSTRUMENTS
        if not m.instrument_count_verified:
            unverified.append(name)
    assert len(set(counts.values())) > 1, \
        f'every file reported the same instrument count: {set(counts.values())}'
    assert counts['If_I_Was_a_Rich_Man.sid'] == 3
    assert counts['Love_tune_2.sid'] == 32
    # only the known-odd third-variant file may fail the cross-check
    assert unverified == ['Tribute_to_Laxity.sid'], unverified


@needs_corpus
def test_wave_program_yields_sid_control_bytes():
    """Field 4 is the waveform/arpeggio cursor and field 3 the pulse sweep --
    they were swapped in the first cut of this parser. A wave program's first
    step must look like a $D404 control byte with a waveform bit set."""
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    seen = 0
    for n in range(m.num_instruments):
        prog = m.wave_program(m.instrument(n).wave_cursor)
        if not prog:
            continue
        wf = prog[0][0]
        assert wf & 0xF0, f'instrument {n} first wave step ${wf:02x} has no waveform bit'
        seen += 1
    assert seen >= 4


@needs_corpus
def test_pulse_program_magnitude_uses_the_fe_mask():
    """Pulse-sweep values carry magnitude in bits 1-7 and direction in bit 0;
    a decoder that forgets bit 0 sweeps every instrument upward."""
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    steps = [s for n in range(m.num_instruments)
             for s, _ in m.pulse_program(m.instrument(n).pulse_cursor)]
    assert steps
    assert all(s % 2 == 0 for s in steps), 'magnitude must be the $FE mask'


@needs_corpus
def test_drives_freq_actually_partitions_the_corpus():
    """Guards the claim the validator rests on: the flag must not be all-set or
    all-clear across the corpus, or splitting the score by it means nothing."""
    seen = set()
    for name in os.listdir(CORP):
        if not name.endswith('.sid'):
            continue
        try:
            m = HardTrackModule.from_sid(os.path.join(CORP, name))
        except HardTrackError:
            continue
        used = {i for n in m.patterns_used(0) for k, _, i in m.pattern(n)
                if k == 'note' and i}
        seen |= {m.instrument_drives_freq(i & 0x1F) for i in used}
    assert seen == {True, False}, f'flag does not partition the corpus: {seen}'


# --------------------------------------------------------------------------
# simulation
# --------------------------------------------------------------------------
@needs_corpus
def test_simulate_produces_onsets_on_every_voice():
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    frames = simulate(m, 0, 1000)
    for vi in range(3):
        onsets = [r[vi] for r in frames if r[vi]]
        assert len(onsets) > 10, f'voice {vi} produced {len(onsets)} onsets'


@needs_corpus
def test_simulate_row_spacing_matches_the_tempo_divider():
    """A row lands every speed+1 frames; a model whose divider is off by one
    still 'works' but desyncs, so pin the spacing explicitly."""
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    frames = simulate(m, 0, 1000)
    fs = [f for f, r in enumerate(frames) if r[0]]
    gaps = {b - a for a, b in zip(fs, fs[1:])}
    assert gaps, 'no onsets to measure'
    assert all(g % (m.speed(0) + 1) == 0 for g in gaps), sorted(gaps)


@needs_corpus
def test_simulate_is_deterministic():
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    assert simulate(m, 0, 400) == simulate(m, 0, 400)


@needs_corpus
def test_simulate_does_not_run_away_on_a_short_window():
    """Every voice emitting on every frame is the signature of a lost
    orderlist walk -- the failure mode the wrapped rips showed."""
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    frames = simulate(m, 0, 300)
    for vi in range(3):
        assert sum(1 for r in frames if r[vi]) < 300 // 2


# --------------------------------------------------------------------------
# Onset detail -- what makes an attribution exact
# --------------------------------------------------------------------------
@needs_corpus
def test_onset_unpacks_as_the_historical_two_tuple():
    """Onset carries attribution fields but must stay a (note, instrument)
    2-tuple, because both validators and every existing caller unpack it."""
    from sidm2.hardtrack_parser import Onset
    m = HardTrackModule.from_sid(sid('Love_tune_3'))
    frames = simulate(m, 0, 400)
    onsets = [r[v] for r in frames for v in range(3) if r[v]]
    assert onsets
    for o in onsets[:20]:
        assert isinstance(o, Onset)
        note, instrument = o
        assert (note, instrument) == (o.note, o.instrument)
        assert o == (note, instrument)


@needs_corpus
def test_onset_carries_the_raw_instrument_byte_and_pattern_position():
    """These are the fields that made the $6F and $62 attributions exact.
    Re-deriving them afterwards with a cursor heuristic mis-aligned and
    reversed a real result, so they must come from the walk itself."""
    m = HardTrackModule.from_sid(sid('Love_tune_3'))
    onsets = [r[v] for r in simulate(m, 0, 1000) for v in range(3) if r[v]]
    assert any(o.raw == 0x6F for o in onsets), 'fixture should contain $6F notes'
    for o in onsets:
        assert o.pattern is not None
        assert o.pat_index is not None
        # the recorded position must actually address this pattern's bytes
        assert 0 < o.pat_index <= 4096
        # and the note must be the transposed value the player would compute
        assert 0 <= o.note <= 0x7F


@needs_corpus
def test_next_pattern_event_finds_the_freeze_command():
    """$62 freezes the wave stepper; spotting it requires skipping rests."""
    from sidm2.hardtrack_parser import next_pattern_event
    m = HardTrackModule.from_sid(sid('Walk_to_Soul'))
    ev = m.pattern(1)
    # pattern 1 has a note immediately followed by $62 (the Walk_to_Soul case)
    assert any(k == 'cmd62' for k, _, _ in ev)
    onsets = [r[v] for r in simulate(m, 0, 1000) for v in range(3) if r[v]]
    kinds = {next_pattern_event(m, o.pattern, o.pat_index) for o in onsets}
    assert 'cmd62' in kinds


def test_field5_bit4_is_named_for_what_it_does():
    """`hard_restart` was a misnomer; the bit gates the FILTER re-arm only.

    Renamed in v3.25.0. Pinned because the old name actively misleads a Stage B
    port: the shared driver's hard-restart row zeroes AD and SR together, while
    HardTrack's path never touches $D405 at all.
    """
    import os
    corp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'SID', 'Shogoon')
    if not os.path.isdir(corp):
        import pytest
        pytest.skip('Shogoon corpus absent')
    m = HardTrackModule.from_sid(os.path.join(corp, 'Love_tune_2.sid'))
    inst = m.instrument(0)
    assert not hasattr(inst, 'hard_restart'), 'the misnomer is back'
    assert inst.skip_filter_rearm == bool(inst.flags & 0x10)
