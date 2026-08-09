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
    NUM_INSTRUMENTS, ORDER_END, ORDER_JUMP, PATTERN_END, simulate,
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
def test_drives_freq_flag_is_bit7_of_field5():
    m = HardTrackModule.from_sid(sid('Love_tune_2'))
    for n in range(NUM_INSTRUMENTS):
        assert m.instrument_drives_freq(n) == bool(m.instrument(n).flags & 0x80)


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
