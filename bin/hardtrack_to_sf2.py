"""HardTrack Composer SID -> editable Driver 11 SF2 (Stage A, cut 1).

Maps the decoded module (`sidm2/hardtrack_parser.py`) onto Driver 11 through the
shared IR (`GalwayDriver11Song` + `galway_driver11_emitter`).

WHAT TRANSFERS EXACTLY
  - notes and their timing. A HardTrack row lands every `speed+1` frames and a
    Driver 11 row plays `tempo+1` frames, so `tempo = speed` and one HardTrack
    row is one Driver 11 row. Both note grids are C-0-based 96-semitone tables
    and HardTrack's is PAL to within 19 cents (only at note 95), so the SF2 note
    byte is the semitone index itself. (MEASURED: `index + 1`, which the shared
    IR's comment suggests, puts every note exactly one semitone sharp.)
  - the waveform/arpeggio program. HardTrack's is a pair of parallel tables
    walked by one cursor with an `$FF <index>` jump; Driver 11's wave table is a
    2-column table with a `$7F <row>` jump and column 1 as a relative semitone.
    That is the same structure, so the whole table is transliterated 1:1 and the
    instrument keeps its own cursor as `wave_idx` -- jumps stay valid without
    remapping. The longest table in the Shogoon corpus is 253 rows against the
    256-row cap.
  - per-instrument AD/SR and the initial pulse width.

WHAT DOES NOT (cut-1 approximations -- all logged, none silent)
  - the PULSE SWEEP. HardTrack sweeps the width every frame (signed step,
    direction in bit 0); Driver 11's pulse table is set-and-hold. Each
    instrument gets its starting width held, so pulse-swept leads will sound
    static. Stage B material.
  - the SLIDE / PORTAMENTO commands ($63/$64) become plain sustain rows.
  - the GLOBAL FILTER SWEEP is not ported.
  - ORDERLIST TRANSPOSE is materialised, not expressed. Driver 11 orderlists do
    have an `$A0+transpose` command, but the shared emitter writes transpose 0
    unconditionally, and changing it would touch a code path eight other players
    depend on. So a pattern used at two transposes becomes two sequences with
    the notes pre-transposed. Correct output, more sequences than necessary.
  - the LOOP POINT. HardTrack's `$FD n` loops to orderlist index n; a Driver 11
    orderlist can only loop to its start, so a song with an intro replays the
    intro on every repeat.
  - CROSS-PATTERN GATE STATE. One HardTrack pattern becomes one Driver 11
    sequence, so whether a voice is still sounding when the pattern starts is
    decided per sequence, not per voice. A pattern that opens with `$67` (rest)
    is emitted with note-offs, but the player would have sustained a note
    carried in from the previous pattern. This is the leading suspect for the
    voice-localised Stage A losses (Zakplus voice 2, Hopscotch voice 1) -- a
    hypothesis consistent with the evidence (losses are per-voice and flat over
    time, not drifting), not yet a confirmed diagnosis.

Usage:
    py -3 bin/hardtrack_to_sf2.py SID/Shogoon/Love_tune_2.sid [out.sf2]
    py -3 bin/hardtrack_to_sf2.py SID/Shogoon/Griffin_Score.sid --subtune 2
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.galway_driver11_emitter import emit_driver11_sf2, segment_track
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_GATE_OFF, SF2_GATE_ON, SF2_NOTE_MAX, SF2_NOTE_MIN,
)
from sidm2.hardtrack_parser import (
    CMD_GATE_OFF, HardTrackError, HardTrackModule, INSTR_HOLD, INSTR_LEGATO,
)

MAX_INSTRUMENT_SLOTS = 31     # slot 31 is the silent/rest instrument
WAVE_ROW_CAP = 256
SEQUENCE_CAP = 120            # 128 slots minus margin (PLAYBOOK sec.3)


class StageAWarning(list):
    """Collected approximations, printed at the end -- never swallowed."""

    def note(self, msg):
        self.append(msg)


# ---------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------
def build_wave_table(module, warn):
    """Transliterate HardTrack's whole waveform/arpeggio table into D11 rows.

    Returns [(col0, col1)] where col0 is the $D404 waveform or $7F for a jump,
    and col1 is the arpeggio semitone offset or the jump target row. Row indices
    are preserved, so an instrument's own cursor is a valid `wave_idx` and every
    internal jump stays correct without remapping.
    """
    if module.wave_table is None or module.arp_table is None:
        warn.note('wave/arp program tables not located - instruments get a '
                  'plain gated waveform, no arpeggio')
        return [(0x41, 0x00), (0x7F, 0x00)]
    length = module.arp_table - module.wave_table
    if not 0 < length <= WAVE_ROW_CAP:
        warn.note(f'wave table is {length} rows (cap {WAVE_ROW_CAP}) - truncated')
        length = max(0, min(length, WAVE_ROW_CAP))
    rows = []
    for i in range(length):
        wf = module.byte(module.wave_table + i)
        val = module.byte(module.arp_table + i)
        if wf == 0xFF:
            # HardTrack jump (target in the arp column) -> Driver 11 jump.
            rows.append((0x7F, val if val < length else 0x00))
        elif wf == 0xFE:
            # HardTrack "stop stepping": the player sets a flag that skips the
            # wave stepper from then on, holding the last waveform written.
            # Driver 11 has no stop, so jump back one row -- replaying the last
            # real waveform row is audibly the same hold.
            rows.append((0x7F, i - 1 if i else 0))
            if i == 0:
                warn.note('a wave program stops at row 0; emitted as a '
                          'self-jump, which may spin in the editor')
        else:
            # Column 1 is passed through VERBATIM. Both formats use the same
            # rule -- $00-$7F is a relative semitone added to the note, $80+ is
            # an absolute note -- so masking it here would silently turn every
            # absolute-pitch step into a relative one.
            rows.append((wf, val))
    return rows or [(0x41, 0x00), (0x7F, 0x00)]


def settled_cursor(module, cursor, limit=64):
    """Where an instrument's wave program ENDS UP, not where it starts.

    A $6F legato note changes pitch without restarting the instrument's
    programs, so what matters is the step the program has settled on:

      * program terminated by `$FF <target>` -> the jump target (the loop body);
      * terminated by `$FE` (stop stepping)  -> the last real step, which the
        player then holds.

    Returns `cursor` unchanged when no terminator is found, so a malformed or
    over-long program degrades to today's behaviour rather than to garbage.
    """
    if module.wave_table is None:
        return cursor
    for i in range(limit):
        wf = module.byte(module.wave_table + cursor + i)
        if wf == 0xFF:
            return module.byte(module.arp_table + cursor + i)
        if wf == 0xFE:
            return cursor + i - 1 if i else cursor
    return cursor


def legato_instruments(module, subtune):
    """{hardtrack index} of instruments in effect at a $6F legato note.

    Walks each voice's orderlist in play order, carrying the current instrument
    across pattern boundaries the way the sequencer does -- a $6F note inherits
    whatever instrument was last selected, which may have been set in an earlier
    pattern.
    """
    need = set()
    for voice in range(3):
        current = None
        for kind, value in module.orderlist(voice, subtune):
            if kind in ('end', 'jump', 'hold'):
                break
            if kind == 'transpose':
                continue
            for k, _, b in module.pattern(value):
                if k == 'end':
                    break
                if k != 'note':
                    continue
                if b == INSTR_LEGATO:
                    if current is not None:
                        need.add(current)
                elif b != INSTR_HOLD:
                    current = b & 0x1F
    return need


def build_instruments(module, used, wave_rows, warn, legato_needed=()):
    """-> (instrument rows, pulse table, {ht index: slot}, {ht index: legato slot})."""
    instr_rows, pulse_table, slot_of, legato_of = [], [], {}, {}
    for ht_index in sorted(used):
        if len(instr_rows) >= MAX_INSTRUMENT_SLOTS:
            warn.note(f'more than {MAX_INSTRUMENT_SLOTS} instruments used; '
                      f'instrument {ht_index} and later reuse slot 0')
            slot_of[ht_index] = 0
            continue
        ins = module.instrument(ht_index)
        # set-and-hold the instrument's starting width, then jump to self.
        prow = len(pulse_table)
        pulse_table.append((0x80 | ins.pulse_hi, ins.pulse_lo, 0x01))
        pulse_table.append((0x7F, 0x00, prow))
        wave_idx = ins.wave_cursor if ins.wave_cursor < len(wave_rows) else 0
        slot_of[ht_index] = len(instr_rows)
        instr_rows.append(D11Instrument(
            ad=ins.ad, sr=ins.sr, flags=0x80, filter_idx=0x00,
            pulse_idx=prow, wave_idx=wave_idx,
            pulse_width=ins.pulse_hi))
        if module.pulse_program(ins.pulse_cursor):
            warn.note(f'instrument {ht_index}: pulse sweep not ported (Stage B)')

    # $6F legato variants: same instrument, but the wave program starts at the
    # step it would have SETTLED on rather than at its attack. Driver 11 always
    # restarts a wave program on note-on and cannot express a tie at all (its
    # $90-$9F tie durations desync the runtime driver), so this is the only way
    # to get "new pitch, no re-attack" through the real driver.
    for ht_index in sorted(legato_needed):
        if ht_index not in slot_of:
            continue
        base = module.instrument(ht_index)
        settled = settled_cursor(module, base.wave_cursor)
        if settled == base.wave_cursor or settled >= len(wave_rows):
            continue                      # nothing gained, or out of range
        if len(instr_rows) >= MAX_INSTRUMENT_SLOTS:
            warn.note(f'no instrument slot left for the $6F legato variant of '
                      f'instrument {ht_index}; its legato notes re-attack')
            continue
        src = instr_rows[slot_of[ht_index]]
        legato_of[ht_index] = len(instr_rows)
        instr_rows.append(D11Instrument(
            ad=src.ad, sr=src.sr, flags=src.flags, filter_idx=src.filter_idx,
            pulse_idx=src.pulse_idx, wave_idx=settled,
            pulse_width=src.pulse_width))

    if not instr_rows:
        instr_rows.append(D11Instrument(ad=0x00, sr=0xF0, flags=0x80,
                                        filter_idx=0, pulse_idx=0, wave_idx=0))
        pulse_table = [(0x88, 0x00, 0x01), (0x7F, 0x00, 0x00)]
    return instr_rows, pulse_table, slot_of, legato_of


# ---------------------------------------------------------------------------
# sequences
# ---------------------------------------------------------------------------
def pattern_rows(module, pattern, transpose, slot_of, state, warn, legato_of=None):
    """One HardTrack pattern at one transpose -> Driver 11 rows."""
    rows = []
    for kind, a, b in module.pattern(pattern):
        if kind == 'end':
            break
        if kind == 'note':
            # MEASURED, not derived: the Driver 11 note byte is the C-0-based
            # semitone index itself. Emitting index+1 put every note exactly one
            # semitone sharp ($0F82 where the original plays $0E93).
            note = (a + transpose) & 0x7F
            if not SF2_NOTE_MIN <= note <= SF2_NOTE_MAX:
                warn.note(f'pattern {pattern}: note {a}+{transpose} out of the '
                          f'Driver 11 range - emitted as a rest')
                rows.append(D11Row(note=SF2_GATE_OFF))
                state['sounding'] = False
                continue
            # $00 keeps the instrument AND restarts its programs; $6F keeps it
            # and does NOT restart. So they select different Driver 11 slots.
            if b not in (INSTR_HOLD, INSTR_LEGATO):
                state['ht_instr'] = b & 0x1F
            want = None
            if state['ht_instr'] is not None:
                if b == INSTR_LEGATO and legato_of:
                    want = legato_of.get(state['ht_instr'])
                if want is None:
                    want = slot_of.get(state['ht_instr'], 0)
            instr = None
            if want is not None and want != state['slot']:
                instr = want
                state['slot'] = want
            rows.append(D11Row(note=note, instrument=instr))
            state['sounding'] = True
        elif kind == 'rest':
            # $67 n holds the voice for exactly n rows. The gate is untouched,
            # so a note already sounding keeps sounding -> '+++'. But BEFORE the
            # pattern's first note nothing is sounding, and emitting '+++' there
            # gates a voice that has no pitch yet: Driver 11 dutifully plays
            # frequency $0000, i.e. silence that never recovers on that row.
            hold = SF2_GATE_ON if state['sounding'] else SF2_GATE_OFF
            rows.extend(D11Row(note=hold) for _ in range(max(0, a)))
        elif kind == f'cmd{CMD_GATE_OFF:02x}':
            state['sounding'] = False
            rows.append(D11Row(note=SF2_GATE_OFF))
        else:
            # tie / reset / slide / portamento: hold. The slide engine is Stage B.
            rows.append(D11Row(note=SF2_GATE_ON if state['sounding']
                               else SF2_GATE_OFF))
    return rows


def build_song(module, subtune, warn):
    used_instruments = set()
    for n in module.patterns_used(subtune):
        for kind, _, b in module.pattern(n):
            if kind == 'note' and b not in (0x00, 0x6F):
                used_instruments.add(b & 0x1F)

    wave_rows = build_wave_table(module, warn)
    needed = legato_instruments(module, subtune)
    instr_rows, pulse_table, slot_of, legato_of = build_instruments(
        module, used_instruments, wave_rows, warn, needed)
    if needed and not legato_of:
        warn.note('$6F legato notes present but no legato variant was usable; '
                  'they will re-attack')

    sequences, orderlists = [], []
    seq_of = {}                                   # (pattern, transpose) -> index
    for voice in range(3):
        transpose = 0
        indices = []
        for kind, value in module.orderlist(voice, subtune):
            if kind == 'transpose':
                transpose = value
                continue
            if kind in ('end', 'jump', 'hold'):
                break
            key = (value, transpose)
            if key not in seq_of:
                state = {'slot': None, 'ht_instr': None, 'sounding': False}
                rows = pattern_rows(module, value, transpose, slot_of, state,
                                    warn, legato_of)
                packed = segment_track(rows)
                if len(packed) > 1:
                    warn.note(f'pattern {value} split into {len(packed)} '
                              f'sequences (packing limit)')
                seq_of[key] = (len(sequences), len(packed))
                sequences.extend(packed)
            base, count = seq_of[key]
            # a pattern too big for one sequence becomes several, played in
            # order -- they must all be referenced, and AFTER the first, not
            # before it
            indices.extend(range(base, base + count))
        orderlists.append(indices)

    if len(sequences) > SEQUENCE_CAP:
        warn.note(f'{len(sequences)} sequences exceed the {SEQUENCE_CAP} cap - '
                  f'the emitter will drop the overflow')

    song = GalwayDriver11Song(
        instruments=instr_rows,
        wave_table=wave_rows,
        pulse_table=pulse_table,
        filter_table=[],
        tracks=[[], [], []],
        tempo=module.speed(subtune),
        subtune=subtune,
    )
    return song, sequences, orderlists


def convert(path, out_path=None, subtune=0, quiet=False):
    module = HardTrackModule.from_sid(path)
    warn = StageAWarning()
    if not module.instrument_count_verified:
        warn.note('instrument count could NOT be cross-verified for this file; '
                  'instrument fields may be read at the wrong stride')
    song, sequences, orderlists = build_song(module, subtune, warn)
    data = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)

    if out_path is None:
        stem = os.path.splitext(os.path.basename(path))[0]
        suffix = f'_sub{subtune}' if subtune else ''
        out_path = os.path.join('out', 'hardtrack', f'{stem}{suffix}.sf2')
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'wb') as fh:
        fh.write(data)

    if not quiet:
        print(f'{os.path.basename(path)} -> {out_path}')
        print(f'  tempo={song.tempo} (row every {song.tempo + 1} frames)  '
              f'instruments={len(song.instruments)}  '
              f'wave rows={len(song.wave_table)}  sequences={len(sequences)}')
        print(f'  orderlist lengths: {[len(o) for o in orderlists]}')
        seen = set()
        for w in warn:
            if w not in seen:
                seen.add(w)
                print(f'  NOTE: {w}')
    return out_path, warn


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('sid')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--subtune', type=int, default=0)
    ap.add_argument('-q', '--quiet', action='store_true')
    a = ap.parse_args(argv)
    try:
        convert(a.sid, a.out, a.subtune, a.quiet)
    except HardTrackError as e:
        print(f'REFUSED: {e}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
