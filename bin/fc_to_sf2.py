"""Future Composer SID -> editable Driver 11 SF2 (Stage A).

Parses a Future Composer tune (sidm2.fc_parser) and transpiles its score onto a
standard SF2 **Driver 11** module, reusing the Galway Driver-11 IR + emitter so
the result opens, plays (F1), and is editable in SID Factory II.

Usage:  py -3 bin/fc_to_sf2.py SID/Fun_Fun/Triangle_Intro.sid [out.sf2]
"""

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.sid_parser import SIDParser
from sidm2.fc_parser import parse_fc, detect_player, NUM_NOTES
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
    _nearest_pal, _norm_waveform, _pulse_program,
)
from sidm2.galway_driver11_emitter import emit_driver11_sf2


def load_sid(path):
    """Load a SID rip or a raw C64 PRG (native FC module). Returns (data, load)."""
    raw = open(path, 'rb').read()
    if raw[:4] in (b'PSID', b'RSID'):
        h = SIDParser(path).parse_header()
        d = raw[h.data_offset:]
        la = h.load_address
        if la == 0 and len(d) >= 2:            # PSID load=0 -> embedded load word
            la = d[0] | (d[1] << 8)
            d = d[2:]
        return d, la
    # raw PRG: 2-byte load word + data
    return raw[2:], raw[0] | (raw[1] << 8)


def calibrate_base(freq_lo, freq_hi, tol=12):
    """Modal (pal_index - fc_index) offset matching FC freqs to the PAL table."""
    offs = Counter()
    for i in range(NUM_NOTES):
        f = freq_lo[i] | (freq_hi[i] << 8)
        if f < 8:
            continue
        ni, dist = _nearest_pal(f)
        if dist < tol:
            offs[ni - i] += 1
    return offs.most_common(1)[0][0] if offs else 0


def _pwm_program(base_row, init=0x400, step=0x080, span=10, hold=2):
    """A triangle pulse-width-modulation program (Driver 11 pulse table).

    FC leads sweep the pulse width per frame (byte [6] sweep at $1b75); a static
    thin width is near-silent, so pulse-waveform instruments get a moving PWM.
    Rows: set init, then +step*span up, -step*span down, loop (excluding the
    one-shot set row so the sweep is continuous). `step`/`hold` shape the rate.
    """
    prog = [(0x80 | ((init >> 8) & 0x0F), init & 0xFF, hold)]
    for _ in range(span):
        prog.append((0x00, step & 0xFF, hold))            # + step
    neg = (-step) & 0xFFF
    for _ in range(span):
        prog.append(((neg >> 8) & 0x0F, neg & 0xFF, hold))  # - step
    prog.append((0x7F, 0x00, base_row + 1))               # loop after the set row
    return prog


def _drum_note(freq, base):
    """Map a drum SID frequency to a Driver 11 absolute semitone (0-95)."""
    idx, _ = _nearest_pal(freq)
    return max(0, min(idx + base + 1, 95))


def build_instruments(fc, base):
    """FC 8-byte sound records -> Driver 11 instrument rows + wave/pulse tables.

    Three timbre classes are reproduced as Driver 11 wave programs (col1 $00-$7f
    = relative semitone added to the note, $80-$df = absolute semitone for drums):
    - Drum  (mctrl [7] & $10): a 14-frame (waveform, absolute-pitch) sequence
      from the drum tables (FC $1c7b engine), then a gate-off settle row.
    - Arp   (mctrl [7] & $04, byte [5] != 0): cycle [0, [5]>>4, [5]&$0f] one row
      per frame (FC $1d25 phase counter) -> a chord.
    - Plain: a single waveform held.
    """
    fc_instruments = fc.instruments
    instr_rows, wave_table, pulse_table = [], [], []
    for ins in fc_instruments[:32]:
        wf = _norm_waveform(ins.waveform)
        wave_row = len(wave_table)
        if ins.mctrl & 0x10:                          # drum
            # FC plays the note's OWN pitch on the trigger frame, then the drum
            # table from frame 1 (the engine indexes $1e56/$1e46 by frame-1 at
            # $1cad). Verified vs trace: real osc3 = B-3 (the note) then $2000…
            # So lead with one root frame before the absolute drum pitches.
            wave_table.append((_norm_waveform(ins.waveform), 0x00))
            for dwf, dfreq in fc.drum_sequence(ins.vibrato):
                wave_table.append((dwf, 0x80 | _drum_note(dfreq, base)))
            settle = len(wave_table)
            wave_table.append((0x10, 0x00))           # gate-off hold (decay)
            wave_table.append((0x7F, settle))
        elif (ins.mctrl & 0x04) and ins.vibrato:      # arpeggio enabled
            hi, lo = ins.vibrato >> 4, ins.vibrato & 0x0F
            # FC phase counter $2161 runs 2->1->0 after the note triggers at the
            # root, so the played offsets are root, +lo, +hi (verified vs trace:
            # real cycles root,+8,+5 for [5]=$58, not root,+5,+8).
            wave_table.append((wf, 0x00))             # root (trigger frame)
            wave_table.append((wf, lo & 0x7F))        # + low-nibble semitones
            wave_table.append((wf, hi & 0x7F))        # + high-nibble semitones
            wave_table.append((0x7F, wave_row))       # loop the 3-step arp
        else:
            wave_table.append((wf, 0x00))
            wave_table.append((0x7F, wave_row))
        pulse_row = len(pulse_table)
        if ins.waveform & 0x40:                  # pulse waveform -> PWM sweep
            pulse_table.extend(_pwm_program(pulse_row))
        else:
            pulse_table.extend(_pulse_program(0x800, pulse_row))
        # D15 uses a static pulse byte (hi of 12-bit width) -> 50% for pulse voices
        pw = 0x08 if (ins.waveform & 0x40) else 0x00
        instr_rows.append(D11Instrument(
            ad=ins.ad, sr=ins.sr, flags=0x80,
            filter_idx=0x00, pulse_idx=pulse_row, wave_idx=wave_row,
            pulse_width=pw))
    if not instr_rows:
        wave_table = [(0x41, 0x00), (0x7F, 0x00)]
        pulse_table = list(_pulse_program(0x800, 0))
        instr_rows = [D11Instrument(0x09, 0x00, 0x80, 0, 0, 0)]
    return instr_rows, wave_table, pulse_table


def _block_rows(block_notes, base, cur_instr):
    """Convert one FC block's notes to Driver 11 rows, threading instrument state
    across blocks (returns updated cur_instr). Same note/rest/tie logic as
    build_track, but per-block so the block stays its own short sequence."""
    out = []
    for n in block_notes:
        nrows = max(1, n.dur + 1)
        if n.is_rest:
            out.extend(D11Row(note=SF2_GATE_OFF) for _ in range(nrows))
            continue
        note = max(SF2_NOTE_MIN, min(n.note + base + 1, SF2_NOTE_MAX))
        inst = None
        if n.instr != cur_instr:
            inst = n.instr
            cur_instr = n.instr
        out.append(D11Row(note=note, instrument=inst, tie=n.tie))
        out.extend(D11Row(note=SF2_GATE_ON) for _ in range(nrows - 1))
    return out, cur_instr


def build_structured(fc, base):
    """Preserve FC's block/orderlist structure: emit one (deduplicated) Driver 11
    sequence per FC block instance, and a per-voice orderlist that replays them.

    FC voices stagger their entries with a short rest block repeated many times
    (e.g. the lead is silent for 6x block-0). Flattening that into one giant
    sequence breaks SF2II's driver; replaying a short rest sequence via the
    orderlist (exactly like FC) keeps every sequence small and plays correctly.
    """
    from sidm2.galway_driver11_emitter import segment_track
    seq_index = {}
    sequences = []
    orderlists = [[], [], []]

    def add(rows, v):
        for pk in segment_track(rows):
            idx = seq_index.get(pk)
            if idx is None:
                idx = len(sequences)
                seq_index[pk] = idx
                sequences.append(pk)
            orderlists[v].append(idx)

    for v in range(3):
        cur_instr = None
        pending = []                                 # deferred rest-only blocks
        for block_notes in fc.voice_blocks[v]:
            rows, cur_instr = _block_rows(block_notes, base, cur_instr)
            if all(b.is_rest for b in block_notes):  # never emit an all-rest
                pending += rows                      # sequence: SF2II's driver
                continue                             # stalls the orderlist on one
            add(pending + rows, v)
            pending = []
        if pending:
            add(pending, v)
    return sequences, orderlists


def build_track(rows, base):
    """Flatten FCNote rows -> Driver 11 sequence rows (note + sustain/rest rows).

    An FC note of duration ``dur`` plays for ``dur+1`` player ticks (the counter
    runs dur..0..-1), so it maps to ``dur+1`` Driver 11 rows. One row == one
    player tick; the master-speed frames/tick is carried by the song tempo.
    """
    out = []
    cur_instr = None
    for n in rows:
        nrows = max(1, n.dur + 1)
        if n.is_rest:
            out.extend(D11Row(note=SF2_GATE_OFF) for _ in range(nrows))
            continue
        note = max(SF2_NOTE_MIN, min(n.note + base + 1, SF2_NOTE_MAX))
        inst = None
        if n.instr != cur_instr:
            inst = n.instr
            cur_instr = n.instr
        out.append(D11Row(note=note, instrument=inst, tie=n.tie))
        out.extend(D11Row(note=SF2_GATE_ON) for _ in range(nrows - 1))
    return out


def fc_to_song(fc):
    # -1: the PAL-table calibration lands a semitone high vs Driver 11's own
    # freq table (confirmed by a clean from-INIT siddump: FC note 24 must emit
    # SF2 note B-1 / $0430, not C-2). So nudge the modal base down one.
    base = calibrate_base(fc.freq_lo, fc.freq_hi) - 1
    # One Driver 11 row == one FC player tick; each tick is (speed+1) video
    # frames (the master-speed divider reloads from $211d). SF2II's Driver 11
    # tempo value V holds each row V+1 frames (measured: V=2 -> 3 frames/row), so
    # to get (speed+1) frames/row we set tempo == speed.
    tempo = max(1, fc.speed)
    instr_rows, wave_table, pulse_table = build_instruments(fc, base)
    tracks = [build_track(v, base) for v in fc.voices]
    return GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=pulse_table,
        tracks=tracks, tempo=tempo, pitch_base=base, subtune=0)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        'out', os.path.splitext(os.path.basename(path))[0] + '.sf2')
    d, la = load_sid(path)
    if not detect_player(d, la):
        print(f"ERROR: {os.path.basename(path)} is not the supported Future "
              f"Composer $1800 player variant (load=${la:04X}); skipping.")
        return 2
    use_d15 = '--d15' in sys.argv
    fc = parse_fc(d, la)
    song = fc_to_song(fc)
    print(f"load=${la:04X} instruments={len(fc.instruments)} "
          f"base={song.pitch_base} tempo={song.tempo} driver={'15' if use_d15 else '11'}")
    if use_d15:
        # Driver 15 path: handles long silent intros (all-rest sequences), so emit
        # FC's real block structure via the orderlist. D15 instrument columns +
        # static pulse handled by instr_layout='d15'. See docs/players/FUTURECOMPOSER.md.
        sequences, orderlists = build_structured(fc, song.pitch_base)
        tpl = 'G5/examples/Driver 15 Test - Mood.sf2'
        sf2 = emit_driver11_sf2(song, template_path=tpl, sequences=sequences,
                                orderlists=orderlists, instr_layout='d15')
    else:
        # Driver 11 (default): flat emit. arps/bass/drums play; a voice with a long
        # silent intro plays wrong (use --d15 for those). See the doc.
        sf2 = emit_driver11_sf2(song)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'wb').write(sf2)
    print(f"emitted {len(sf2)} bytes -> {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
