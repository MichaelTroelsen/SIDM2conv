"""Jeroen Kimmel SID -> editable Driver 11 SF2 (Stage A, cut 1).

Maps the decoded Kimmel event streams (sidm2/kimmel_parser.py) onto Driver 11:
one Kimmel note-tick = one Driver-11 row, pitch = the tune's own split freq
table resolved to the PAL semitone grid, AD/SR/waveform/pulse-width taken from
the located 8-byte instrument records (unlike SDI cut-1, Kimmel's instruments
ARE located, so no default-timbre fallback is needed).

Cut-1 approximations (all logged, none silent):
  - the per-frame effects engine ($12CC: arpeggio, freq slide, pulse-width
    sweep, octave/waveform toggles, drum blips) is NOT ported — Stage A emits
    the base note/instrument only (Stage B material),
  - every note re-gates (the runtime Driver 11 has no ties — the Sound Monitor
    lesson); Kimmel's note stream has no explicit tie/rest byte anyway.

All of Radax's six subtunes decode via ``--subtune N`` (the parser is now
relocation/multi-subtune aware); single-subtune tunes ignore it.

Usage:  py -3 bin/kimmel_to_sf2.py SID/Red_kommel_jeroen/Think_Twice_V.sid [out.sf2]
        py -3 bin/kimmel_to_sf2.py SID/Red_kommel_jeroen/Radax.sid --subtune 3
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.kimmel_parser import KimmelModule
from sidm2.fidelity_common import freq_to_semi
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
)
from sidm2.galway_driver11_emitter import emit_driver11_sf2, segment_track

MAX_INSTRUMENTS = 31


def _minimal_period(block):
    """Shortest period p|12 of a 12-entry arp block (usually 3 for a triad)."""
    for p in (1, 2, 3, 4, 6, 12):
        if all(block[i] == block[i % p] for i in range(12)):
            return p
    return 12


def _wave_program(wave, arp_block, fx, base_row):
    """Driver-11 wave rows (waveform, YY) reproducing the $12CC per-frame engine.

      - fx high-nibble set  -> a 1-frame $81 noise ATTACK (the drum/percussion
        blip the engine forces via its $1047 counter on every note onset),
      - non-zero arp block   -> one wave row per arp step (YY = 0x00-0x7F relative
        semitone added to the note), looped — restores the chord ARPEGGIO,
      - else                 -> hold the base waveform.
    """
    rows = []
    drum = (fx & 0xF0) != 0
    if drum:
        # the $130C engine forces 1 frame of noise at freq|=$8000 (a bright
        # high-pitched click / octave-snap) on every note onset. Reproduce with
        # a noise row at a high ABSOLUTE semitone ($80-$DF = absolute note).
        rows.append((0x81, 0x80 | 0x50))   # noise attack, high snap, 1 frame
        body0 = base_row + 1
    else:
        body0 = base_row
    # only treat as a real chord arp if every step is a sane semitone add
    # (< 2 octaves). Blocks with large values are `arp_off` pointing at non-arp
    # data (e.g. some Rhaa instruments) — emit a plain hold rather than garbage
    # absolute-note ($80-$DF) wave rows.
    is_arp = any(arp_block) and max(arp_block) < 0x18
    if is_arp:
        p = _minimal_period(arp_block)
        for i in range(p):
            rows.append((wave, arp_block[i] & 0x7F))   # +semitone arp step
        rows.append((0x7F, body0))
    else:
        rows.append((wave, 0x00))          # hold the note pitch
        rows.append((0x7F, body0))
    return rows


def _table_caps(wave_table, pulse_table):
    """Guard the Driver-11 table sizes (256 rows each)."""
    assert len(wave_table) <= 256, f"wave table overflow: {len(wave_table)}"
    assert len(pulse_table) <= 256, f"pulse table overflow: {len(pulse_table)}"


def _slide_speed16(ins):
    """The $138E engine slides the note freq by ``PWhi & $F0`` per frame whenever
    that nibble is non-zero (the `$1003` gate); `fx` bit4 picks direction
    (set = up, clear = down). Returns a signed 16-bit per-frame speed (0 = none)
    — the SF2 Driver-11 T0 command's XXYY 16-bit speed maps 1:1 to it."""
    rate = ins["pwhi"] & 0xF0
    if rate == 0:
        return 0
    return rate if (ins["fx"] & 0x10) else ((-rate) & 0xFFFF)


def _pulse_ramp(pwhi, pulse_speed, base_row):
    """Driver-11 pulse rows reproducing the engine's PWM sweep: SET width to
    ``pwhi<<8`` (the per-note reset), then ADD ``pulse_speed`` every frame,
    looping — a 12-bit ramp that wraps exactly like the runtime accumulator.
    The set row is re-entered on every note onset (default flags), matching the
    engine resetting $1034/35 to PWhi<<8 at note-on."""
    width = (pwhi << 8) & 0xFFF
    set_row = (0x80 | ((width >> 8) & 0x0F), width & 0xFF, 0x01)
    if pulse_speed == 0:                    # static width, hold
        return [set_row, (0x7F, 0x00, base_row)]
    add_row = (0x00 | ((pulse_speed >> 8) & 0x0F), pulse_speed & 0xFF, 0x01)
    return [set_row, add_row, (0x7F, 0x00, base_row + 1)]  # loop the ADD


def build_instruments(m, used):
    """One Driver-11 slot per distinct (voice, Kimmel-index) instrument actually
    used — instruments are resolved from each voice's OWN bank (Radax/TT-III/Rhaa
    give voice 1 a separate bank). Emits real per-instrument ADSR + waveform +
    arpeggio wave program + PWM pulse ramp + drum noise attack (the $12CC engine).
    Identical descriptors share a slot; ``slot_of`` is keyed by (voice, index)."""
    instr_rows, wave_table, pulse_table = [], [], []
    slot_of, desc_to_slot = {}, {}
    for (voice, idx), _n in used.most_common():
        ins = m.instrument(idx, voice)
        wave = ins["wave"] or 0x41
        arp = m.arp_block(ins["arp"])
        # descriptor key: identical timbre+effects reuse one slot
        desc = (wave, ins["ad"], ins["sr"], ins["pwhi"], ins["pulse_speed"],
                ins["fx"], tuple(arp))
        slot = desc_to_slot.get(desc)
        if slot is None:
            if len(instr_rows) >= MAX_INSTRUMENTS:
                slot_of[(voice, idx)] = 0
                continue
            wrow = len(wave_table)
            wave_table.extend(_wave_program(wave, arp, ins["fx"], wrow))
            prow = len(pulse_table)
            pulse_table.extend(_pulse_ramp(ins["pwhi"], ins["pulse_speed"], prow))
            slot = len(instr_rows)
            instr_rows.append(D11Instrument(
                ad=ins["ad"], sr=ins["sr"] if ins["sr"] else 0xF9,
                flags=0x80, filter_idx=0x00,
                pulse_idx=prow, wave_idx=wrow,
                pulse_width=((ins["pwhi"] & 0x0F)) or 0x08))
            desc_to_slot[desc] = slot
        slot_of[(voice, idx)] = slot
    return instr_rows, wave_table, pulse_table, slot_of


def _append_silent_instrument(instr_rows, wave_table):
    wrow = len(wave_table)
    wave_table.append((0x00, 0x00))
    wave_table.append((0x7F, wrow))
    idx = len(instr_rows)
    instr_rows.append(D11Instrument(ad=0, sr=0, flags=0x80, filter_idx=0,
                                    pulse_idx=0, wave_idx=wrow, pulse_width=0))
    return idx


_MAX_REST_RUN = 64


def build_rows(m, ev, slot_of, silent_idx, slide_cmd):
    """Event streams (tick-domain) -> per-voice Driver-11 rows.

    ``slide_cmd`` maps a signed-16-bit slide speed -> command index (0 speed =
    the T0 0000 stop command). The freq-slide/portamento ($138E engine) is
    emitted as a T0 slide sequence command, issued on a note only when the
    active slide speed CHANGES (start / rate-change / stop-on-transition)."""
    all_rows = []
    for v in range(3):
        rows, cur, cur_slide, tick = [], None, 0, 0
        for e in ev[v]:
            etick = e.frame // max(1, m.fpt)
            while tick < etick:                       # decode gaps -> rests
                rows.append(D11Row(note=SF2_GATE_OFF))
                tick += 1
            dur = max(1, e.dur_ticks)
            semi = freq_to_semi(m.note_freq(e.note))
            n = max(SF2_NOTE_MIN, min(semi, SF2_NOTE_MAX))
            slot = slot_of.get((v, e.instr), 0)
            inst = slot if slot != cur else None
            cur = slot if inst is not None else cur
            speed = _slide_speed16(m.instrument(e.instr, v))
            cmd = None
            if speed != cur_slide:                    # start / change / stop
                cmd = slide_cmd.get(speed)
                cur_slide = speed
            rows.append(D11Row(note=n, instrument=inst, command=cmd))
            rows.extend(D11Row(note=SF2_GATE_ON) for _ in range(dur - 1))
            tick += dur
        if rows and all(r.note == SF2_GATE_OFF for r in rows):
            rows[-1] = D11Row(note=1, instrument=silent_idx)
        all_rows.append(rows)
    return all_rows


def _build_slide_commands(m, ev):
    """Collect every distinct slide speed the tune uses -> a command-index map
    and the SF2 command-table rows (type=Cmd_Slide $00, p1=hi, p2=lo). Index 0
    is reserved for the T0 0000 stop command."""
    speeds = {0}
    for v in range(3):
        for e in ev[v]:
            speeds.add(_slide_speed16(m.instrument(e.instr, v)))
    slide_cmd, cmd_table = {0: 0}, [(0x00, 0x00, 0x00)]     # index 0 = stop
    for sp in sorted(s for s in speeds if s):
        if len(cmd_table) >= 64:
            break
        slide_cmd[sp] = len(cmd_table)
        cmd_table.append((0x00, (sp >> 8) & 0xFF, sp & 0xFF))
    return slide_cmd, cmd_table


def _patch_command_table(sf2, cmd_table):
    """Write the command table into an already-emitted SF2 (the shared Driver-11
    emitter doesn't emit commands). Column-major (type, p1, p2) x 64 rows —
    format per docs/reference/SF2_FORMAT_SPEC.md. Read-only use of sf2_parser."""
    from sidm2.models import SF2DriverInfo
    from sidm2 import sf2_parser
    out = bytearray(sf2)
    di = SF2DriverInfo()
    la = sf2_parser.parse_sf2_blocks(out, di)
    if la is None or 'Commands' not in di.table_addresses:
        return bytes(out)
    ent = di.table_addresses['Commands']
    addr, rows, cols = ent['addr'], ent['rows'], ent.get('columns', 3)

    def w(a, val):
        o = a - la + 2
        if 0 <= o < len(out):
            out[o] = val & 0xFF
    for r, row in enumerate(cmd_table[:rows]):
        for c in range(min(cols, len(row))):
            w(addr + c * rows + r, row[c])
    return bytes(out)


def convert(path, out, subtune=0):
    m = KimmelModule(path, subtune=subtune)
    ev = m.events()
    used = Counter((v, e.instr) for v in range(3) for e in ev[v])
    instr_rows, wave_table, pulse_table, slot_of = build_instruments(m, used)
    silent_idx = _append_silent_instrument(instr_rows, wave_table)
    _table_caps(wave_table, pulse_table)
    slide_cmd, cmd_table = _build_slide_commands(m, ev)
    all_rows = build_rows(m, ev, slot_of, silent_idx, slide_cmd)

    sequences, orderlists = [], [[], [], []]
    seq_index = {}
    for v in range(3):
        for pk in segment_track(all_rows[v]):
            idx = seq_index.get(pk)
            if idx is None:
                idx = len(sequences)
                seq_index[pk] = idx
                sequences.append(pk)
            orderlists[v].append(idx)
    tempo = max(0, m.fpt - 1)
    song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table,
        pulse_table=pulse_table, tracks=[], tempo=tempo, pitch_base=0,
        subtune=0)
    print(f"load=${m.la:04X} fpt={m.fpt} instr_base=${m.instr_base:04X} "
          f"instruments={len(instr_rows)} sequences={len(sequences)} "
          f"events={[len(e) for e in ev]}")
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    sf2 = _patch_command_table(sf2, cmd_table)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'wb').write(sf2)
    print(f"emitted {len(sf2)} bytes -> {out}  (slide cmds={len(cmd_table)})")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    subtune = 0
    if "--subtune" in sys.argv:
        i = sys.argv.index("--subtune")
        subtune = int(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    path = sys.argv[1]
    base = os.path.splitext(os.path.basename(path))[0]
    if subtune:
        base += f"_sub{subtune}"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        'out', 'kimmel_sf2', base + '.sf2')
    return convert(path, out, subtune=subtune)


if __name__ == '__main__':
    sys.exit(main())
