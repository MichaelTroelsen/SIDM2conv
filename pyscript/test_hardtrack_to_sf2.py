"""Tests for the HardTrack Composer Stage A builder (bin/hardtrack_to_sf2.py)."""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sidm2.galway_driver11_emitter import unpack_sequence  # noqa: E402
from sidm2.galway_to_driver11 import SF2_GATE_OFF, SF2_GATE_ON  # noqa: E402
from sidm2.hardtrack_parser import HardTrackError, HardTrackModule  # noqa: E402

CORP = os.path.join(ROOT, 'SID', 'Shogoon')
needs_corpus = pytest.mark.skipif(not os.path.isdir(CORP), reason='Shogoon corpus absent')

_spec = importlib.util.spec_from_file_location(
    'hardtrack_to_sf2', os.path.join(ROOT, 'bin', 'hardtrack_to_sf2.py'))
h2s = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h2s)


def build(name, subtune=0):
    m = HardTrackModule.from_sid(os.path.join(CORP, name + '.sid'))
    warn = h2s.StageAWarning()
    song, sequences, orderlists = h2s.build_song(m, subtune, warn)
    return m, song, sequences, orderlists, warn


# --------------------------------------------------------------------------
# note mapping and timing
# --------------------------------------------------------------------------
@needs_corpus
def test_tempo_equals_the_hardtrack_speed():
    """A HardTrack row lands every speed+1 frames and a Driver 11 row plays
    tempo+1, so tempo must equal speed. Off by one here desyncs the whole song
    while still producing a playable file."""
    m, song, _, _, _ = build('Love_tune_2')
    assert song.tempo == m.speed(0)


@needs_corpus
def test_note_byte_is_the_semitone_index_not_index_plus_one():
    """Regression: emitting index+1 put every note exactly one semitone sharp
    ($0F82 where the original plays $0E93)."""
    m, _, sequences, orderlists, _ = build('Love_tune_2')
    rows = unpack_sequence(sequences[orderlists[0][0]])
    first_note = next(r for r in rows if r not in (SF2_GATE_ON, SF2_GATE_OFF))
    ht_first = next(a for k, a, _ in m.pattern(0) if k == 'note')
    assert first_note == ht_first


# --------------------------------------------------------------------------
# gating
# --------------------------------------------------------------------------
@needs_corpus
def test_rest_before_the_first_note_is_a_note_off_not_a_sustain():
    """A '+++' row gates a voice that has no pitch yet, and Driver 11 plays
    frequency $0000 -- silence for the rest of that row. A pattern opening with
    $67 must therefore emit '---'."""
    m, _, sequences, orderlists, _ = build('Love_tune_2')
    rows = unpack_sequence(sequences[orderlists[1][0]])
    assert m.pattern(1)[0][0] == 'rest', 'fixture no longer opens with a rest'
    lead = []
    for r in rows:
        if r in (SF2_GATE_ON, SF2_GATE_OFF):
            lead.append(r)
        else:
            break
    assert lead and all(r == SF2_GATE_OFF for r in lead), lead


@needs_corpus
def test_rest_after_a_note_sustains():
    m, _, sequences, orderlists, _ = build('Love_tune_2')
    rows = unpack_sequence(sequences[orderlists[0][0]])
    assert rows[0] not in (SF2_GATE_ON, SF2_GATE_OFF)
    assert rows[1] == SF2_GATE_ON, rows[:4]


# --------------------------------------------------------------------------
# wave table transliteration
# --------------------------------------------------------------------------
@needs_corpus
def test_wave_table_preserves_absolute_note_bit():
    """Both formats use $80+ in the wave table's second column to mean an
    ABSOLUTE note. Masking it to $7F silently turns every absolute-pitch step
    into a relative one, which is what the first cut did."""
    m, song, _, _, _ = build('Love_tune_2')
    length = m.arp_table - m.wave_table
    absolute_src = [i for i in range(length)
                    if m.byte(m.wave_table + i) not in (0xFF, 0xFE)
                    and m.byte(m.arp_table + i) & 0x80]
    if not absolute_src:
        pytest.skip('fixture has no absolute-note wave steps')
    for i in absolute_src:
        assert song.wave_table[i][1] == m.byte(m.arp_table + i)


@needs_corpus
def test_wave_table_emits_no_raw_ff_or_fe_waveform():
    """$FF (jump) and $FE (stop) are control values, not $D404 waveforms;
    emitting them literally made Driver 11 write nonsense to the SID."""
    for name in ('Love_tune_2', 'Jazzloor', 'Teekkno'):
        _, song, _, _, _ = build(name)
        assert all(c0 not in (0xFE, 0xFF) for c0, _ in song.wave_table), name


@needs_corpus
def test_wave_table_fits_the_driver11_cap():
    for name in sorted(os.listdir(CORP)):
        if not name.endswith('.sid'):
            continue
        try:
            _, song, _, _, _ = build(name[:-4])
        except HardTrackError:
            continue
        assert len(song.wave_table) <= h2s.WAVE_ROW_CAP, name


# --------------------------------------------------------------------------
# structure
# --------------------------------------------------------------------------
@needs_corpus
def test_every_orderlist_entry_indexes_a_real_sequence():
    """An out-of-range index is silently dropped by the emitter, which loses
    music without failing."""
    for name in ('Love_tune_2', 'Zakplus', 'Hopscotch', 'Timsoft_Intro'):
        _, _, sequences, orderlists, _ = build(name)
        for v, ol in enumerate(orderlists):
            assert ol, f'{name} voice {v} has an empty orderlist'
            assert all(0 <= s < len(sequences) for s in ol), (name, v)


@needs_corpus
def test_instrument_slots_stay_within_the_driver11_cap():
    for name in ('Hopscotch', 'Zakplus', 'Something_to_Eat'):
        _, song, _, _, _ = build(name)
        assert len(song.instruments) <= h2s.MAX_INSTRUMENT_SLOTS, name


@needs_corpus
def test_approximations_are_reported_not_swallowed():
    """Every lossy step must announce itself; a silent approximation is how a
    Stage A build gets mistaken for a faithful one."""
    _, _, _, _, warn = build('Love_tune_2')
    assert any('pulse sweep' in w for w in warn)


@needs_corpus
def test_emits_a_loadable_sf2(tmp_path):
    out = tmp_path / 'x.sf2'
    path, _ = h2s.convert(os.path.join(CORP, 'Love_tune_2.sid'),
                          str(out), 0, quiet=True)
    data = open(path, 'rb').read()
    assert len(data) > 0x1000
    from sidm2 import sf2_parser
    from sidm2.models import SF2DriverInfo
    di = SF2DriverInfo()
    sf2_parser.parse_sf2_blocks(bytearray(data), di)
    assert di.orderlist_start


@needs_corpus
def test_wrapped_rips_are_refused_by_the_builder(tmp_path):
    with pytest.raises(HardTrackError):
        h2s.convert(os.path.join(CORP, 'Eternal.sid'),
                    str(tmp_path / 'x.sf2'), 0, quiet=True)


# --------------------------------------------------------------------------
# falsification guard
# --------------------------------------------------------------------------
@needs_corpus
def test_pattern_gate_ambiguity_does_not_predict_stage_a_loss():
    """Pins a FALSIFIED hypothesis so it is not re-adopted.

    It was proposed that Stage A loses notes because one pattern becomes one
    sequence, so "is this voice sounding at pattern start" is fixed per sequence
    while the player decides it per voice -- making patterns entered both ways
    lossy. Two facts kill it, and this test keeps them visible:

      * Zakplus, whose voice 2 is the worst loss, has NO such ambiguous pattern;
      * Love_tune_2 HAS them and converts at 100.0% on every voice.

    The real cause is a systematic +1 frame lag; see docs/players/HARDTRACK.md.
    """
    import collections
    from sidm2.hardtrack_parser import (
        CMD_GATE_OFF, CMD_PORTA, CMD_REST, CMD_RESET, CMD_SLIDE, CMD_TIE,
        ORDER_END, ORDER_HOLD, ORDER_JUMP, PATTERN_END,
    )

    def ambiguous_keys(m):
        seen = collections.defaultdict(set)
        V = [dict(op=m.order_pointer(v, 0), oi=0, pp=None, pi=0, tr=0, cmd=0,
                  dur=1, active=1, halted=False, sounding=False, pat=None)
             for v in range(3)]
        speed, ctr = m.speed(0), 2
        for _ in range(1000):
            ctr -= 1
            if ctr < 0:
                ctr = speed
            for vi, v in enumerate(V):
                if v['halted']:
                    continue
                if ctr == 0:
                    if not v['active']:
                        continue
                    v['dur'] = 1
                    c = v['cmd']
                    if c in (CMD_SLIDE, CMD_PORTA):
                        v['pi'] += 1
                        continue
                    if c == CMD_REST:
                        v['active'] = 0
                        v['dur'] = m.byte(v['pp'] + v['pi'])
                        v['pi'] += 1
                        continue
                    if c == CMD_GATE_OFF:
                        v['sounding'] = False
                    trig = c not in (CMD_TIE, CMD_GATE_OFF, CMD_RESET)
                    v['pi'] += 1
                    if trig:
                        v['sounding'] = True
                elif ctr == 1:
                    v['dur'] -= 1
                    if v['dur'] == 0:
                        v['active'] = 1
                        a = (PATTERN_END if v['pp'] is None
                             else m.byte(v['pp'] + v['pi']))
                        v['pi'] += 1
                        if a != PATTERN_END:
                            v['cmd'] = a
                            continue
                        v['pi'] = 0
                        for _ in range(512):
                            b = m.byte(v['op'] + v['oi'])
                            v['oi'] += 1
                            if b == ORDER_END:
                                v['oi'] = 0
                                continue
                            if b == ORDER_HOLD:
                                v['halted'] = True
                                break
                            if b == ORDER_JUMP:
                                v['oi'] = m.byte(v['op'] + v['oi'])
                                continue
                            if b >= 0x80:
                                v['tr'] = b & 0x7F
                                b = m.byte(v['op'] + v['oi'])
                                v['oi'] += 1
                            v['pp'] = m.pattern_pointer(b)
                            v['cmd'] = m.byte(v['pp'])
                            v['pi'] = 1
                            seen[(vi, b, v['tr'])].add(v['sounding'])
                            break
        return {k for k, st in seen.items() if len(st) > 1}

    worst = HardTrackModule.from_sid(os.path.join(CORP, 'Zakplus.sid'))
    perfect = HardTrackModule.from_sid(os.path.join(CORP, 'Love_tune_2.sid'))
    assert not ambiguous_keys(worst),         'Zakplus gained ambiguous patterns; re-check the falsification'
    assert ambiguous_keys(perfect),         'Love_tune_2 lost its ambiguous patterns; re-check the falsification'
