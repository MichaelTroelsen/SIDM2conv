"""ROMUZAK V6.x SID -> editable Driver 11 SF2 (Stage A), like bin/fc_to_sf2.py.

ROMUZAK (Oliver Blasnik, 1989) is an expanded Future Composer: 3 TRACKS (orderlists)
reference SECTORS (patterns) of NOTE/DUR/SND commands, with 8-byte SOUND records.
Format fully RE'd (player disasm + decrunched editor + the V6.x manual); see the
`romuzak-player-re` memory. We decode it and transpile onto a real Driver 11 SF2,
reusing the FC IR + emitter + silent-intro anchors + trace-driven pulse/filter.

Usage:  py -3 bin/romuzak_to_sf2.py SID/Fun_Fun/Delirious_9_tune_1.sid [out.sf2]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.sid_parser import SIDParser
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
    _norm_waveform, _pulse_program,
)
from sidm2.galway_driver11_emitter import emit_driver11_sf2

def _find_tables(d):
    """Locate the 3 data tables by their player-code signatures (relocation-safe):
      TRACK ptrs:  `B9 lo hi 85 F8`  (LDA track,Y ; STA $F8)  — 1st occurrence
      SECTOR ptrs: `B9 lo hi 85 F8`  (LDA sector,Y; STA $F8)  — 2nd occurrence
      SOUND tbl:   `BD lo hi 85 F8`  (LDA sound,X ; STA $F8)
    (Delirious -> $3640/$3676/$36F6; works on the relocated Road rip too.)"""
    ptr_ys = []
    for i in range(len(d) - 4):
        if d[i] == 0xB9 and d[i + 3] == 0x85 and d[i + 4] == 0xF8:
            ptr_ys.append(d[i + 1] | (d[i + 2] << 8))
    track = ptr_ys[0] if ptr_ys else 0
    sector = ptr_ys[1] if len(ptr_ys) > 1 else 0
    drum = ptr_ys[2] if len(ptr_ys) > 2 else 0   # `LDA $2D60,Y` drum/arp ptr table
    # the 8-byte sound table sits right after the 64-entry ($80-byte) sector ptr table
    sound = (sector + 0x80) & 0xFFFF
    return track, sector, sound, drum


def load_sid(path):
    raw = open(path, 'rb').read()
    h = SIDParser(path).parse_header()
    d = raw[h.data_offset:]
    la = h.load_address
    if la == 0 and len(d) >= 2:
        la = d[0] | (d[1] << 8)
        d = d[2:]
    return d, la


class RMZ:
    """Decoded ROMUZAK song: per-voice flat note events + 8-byte sounds."""
    def __init__(self, d, la):
        self.d, self.la = d, la
        self.track_ptrs, self.sect_ptrs, self.sound_tbl, self.drum_tbl = _find_tables(d)
        self.voices = [self._track(v) for v in range(3)]   # [(note,dur,instr,rest)]
        self.sounds = [tuple(self._u8(self.sound_tbl + s * 8 + k) for k in range(8))
                       for s in range(32)]

    def _u8(self, a):
        o = a - self.la
        return self.d[o] if 0 <= o < len(self.d) else 0xFF

    def _u16(self, a):
        return self._u8(a) | (self._u8(a + 1) << 8)

    def _sector(self, addr, ntr, str_):
        """Decode one sector -> [(note,dur,instr,is_rest)] (CONT extends prev)."""
        out = []
        i = 0
        cur_dur, cur_snd = 1, 0
        while i < 256:
            b = self._u8(addr + i); i += 1
            if b == 0xFF:
                break
            if b < 0x60:                          # NOTE (chromatic)
                out.append([(b + ntr) & 0xFF, cur_dur, (cur_snd + str_) & 0x1F, False])
            elif b < 0x80:                        # DUR
                cur_dur = (b & 0x1F) or 1
            elif b < 0xA0:                        # PSE / pause
                out.append([0, cur_dur, cur_snd, True])
            elif b < 0xC0:                        # SND
                cur_snd = b & 0x1F
            elif b < 0xE0:                        # SND base (rare)
                cur_snd = b & 0x1F
            elif b == 0xE0:                       # +1 param (GLD/APM) — skip param
                i += 1
            elif b == 0xF0:                       # CONT -> extend previous note
                if out:
                    out[-1][1] += cur_dur
                else:
                    out.append([0, cur_dur, cur_snd, True])
        return out

    def _orderlist(self, v):
        """Walk a track orderlist -> [(sector, note_transpose, sound_transpose)]
        (repeats expanded; transposes tracked). The real song structure."""
        addr = self._u16(self.track_ptrs + v * 2)
        ol = []
        i, ntr, str_, guard = 0, 0, 0, 0
        while guard < 1024:
            guard += 1
            b = self._u8(addr + i); i += 1
            if b < 0x40:                          # play sector
                ol.append((b, ntr, str_))
            elif b < 0x80:                        # repeat next sector (b-$40+1)x
                rep = b - 0x40 + 1
                sec = self._u8(addr + i); i += 1
                ol += [(sec, ntr, str_)] * rep
            elif b < 0xC0:                        # note transpose
                ntr = b - 0x80
            elif b < 0xFC:                        # sound transpose
                str_ = b - 0xC0
            else:                                 # fc goto / fd / fe / ff -> end
                break
        return ol

    def drum_sequence(self, b4):
        """Drum B4 -> [(waveform, value), ...] from $2D60[B4] until $FF."""
        ptr = self._u16(self.drum_tbl + b4 * 2)
        seq = []
        i = 0
        while i < 64:
            wf = self._u8(ptr + i); i += 1
            if wf == 0xFF:
                break
            seq.append((wf, self._u8(ptr + i))); i += 1
        return seq

    def _track(self, v):
        """Flat note events for the (legacy) flat build."""
        seq = []
        for sector, ntr, str_ in self._orderlist(v):
            seq += self._sector(self._u16(self.sect_ptrs + sector * 2), ntr, str_)
        return seq


def calibrate_base(rmz):
    """ROMUZAK note values ARE SF2 chromatic semitones ($00 = C-0), so the base is a
    FIXED 0 — verified note-for-note against the original siddump on both corpus tunes
    (the bass voice aligns at a modal semitone offset of exactly 0 for Delirious AND
    Road; see bin/romuzak_validate.py). The earlier per-tune median-centering was wrong
    — it left Delirious at 0 by luck but shifted Road +2 semitones."""
    return 0


def find_tempo(d):
    """Derive the SF2II tempo from the player's tick-divider reload constant.

    The play routine runs `DEC divider ; BPL skip ; LDA #reload ; STA divider`, so the
    note-duration tick fires every (reload + 1) video frames. SF2II advances one row per
    `tempo` frames; Delirious's 4-frame tick (reload $03) is faithful at SF2II tempo 5,
    so tempo = reload + 2. This is PER-TUNE: Delirious reload $03 -> 5, Road $02 -> 4.
    Located by signature (relocation-safe); falls back to 5 if not found."""
    for i in range(len(d) - 9):
        if (d[i] == 0xCE and d[i + 3] == 0x10 and d[i + 5] == 0xA9
                and d[i + 7] == 0x8D and d[i + 1] == d[i + 8] and d[i + 2] == d[i + 9]):
            return d[i + 6] + 2
    return 5


def build_instruments(rmz):
    """ROMUZAK 8-byte sound -> Driver 11 instrument + wave/pulse tables.
    B7 effect byte (like FC mctrl): bit1=ARP (semitones in the next sound row),
    bit4=SEEK (pulse-width ramps from 0 by B0/tick), bit6=waveform->pulse after 2
    DUR. (bit0 DRUM + bit5 FILTER: TODO — need the drum table / trace-driven filter.)"""
    instr_rows, wave_table, pulse_table = [], [], []
    for idx, s in enumerate(rmz.sounds):
        b0, b1, b2, b3, b4, b5, b6, b7 = s
        wf = _norm_waveform(b1)
        wave_row = len(wave_table)
        if b7 & 0x01:                               # DRUM: per-frame (waveform,pitch)
            for dwf, dval in (rmz.drum_sequence(b4) or [(wf, 0)]):
                wave_table.append((dwf, 0x80 | (dval & 0x7F)))
            settle = len(wave_table)
            wave_table.append((0x10, 0x00))         # gate-off settle
            wave_table.append((0x7F, settle))
        elif b7 & 0x02:                             # ARPEGGIO: 4 semitones in row idx+1
            arp = rmz.sounds[idx + 1] if idx + 1 < len(rmz.sounds) else (0,) * 8
            for sem in (arp[0] & 0x7F, arp[1] & 0x7F, arp[2] & 0x7F, arp[3] & 0x7F):
                wave_table.append((wf, sem))
            wave_table.append((0x7F, wave_row))
        elif b7 & 0x40:                             # waveform -> $41 pulse after 2 DUR
            wave_table.append((wf, 0x00))
            wave_table.append((wf, 0x00))
            prow = len(wave_table)
            wave_table.append((0x41, 0x00))
            wave_table.append((0x7F, prow))
        else:                                       # plain held waveform
            wave_table.append((wf, 0x00))
            wave_table.append((0x7F, wave_row))
        pulse_row = len(pulse_table)
        pw = ((b0 & 0x0F) << 8) | ((b0 >> 4) << 4)  # B0: digit1=lo*16, digit2=hi
        if b7 & 0x10:                               # SEEK: PW from 0, +B0 each tick
            pulse_table.append((0x80, 0x00, 0x01))  # set 0
            pulse_table.append((0x00, b0, 0x01))    # add B0
            pulse_table.append((0x7F, 0x00, pulse_row + 1))  # loop the add (ramp)
        else:
            pulse_table.extend(_pulse_program(pw or 0x800, pulse_row))
        instr_rows.append(D11Instrument(
            ad=b2, sr=b3, flags=0x80, filter_idx=0x00,
            pulse_idx=pulse_row, wave_idx=wave_row,
            pulse_width=(b0 >> 4) & 0x0F))
    return instr_rows, wave_table, pulse_table


_MAX_REST_RUN = 64


def build_track(events, base, silent_idx):
    """Flat note events -> Driver 11 rows (note + sustain/rest), with silent anchors
    for long rests (the silent intro), exactly like fc_to_sf2.build_track."""
    out = []
    cur_instr = None
    rest_run = 0
    for note, dur, instr, is_rest in events:
        nrows = max(1, dur)
        if is_rest:
            for _ in range(nrows):
                if rest_run >= _MAX_REST_RUN:
                    out.append(D11Row(note=1, instrument=silent_idx))
                    cur_instr = silent_idx
                    rest_run = 0
                else:
                    out.append(D11Row(note=SF2_GATE_OFF))
                    rest_run += 1
            continue
        rest_run = 0
        n = max(SF2_NOTE_MIN, min(note + base, SF2_NOTE_MAX))
        inst = None
        if instr != cur_instr:
            inst = instr
            cur_instr = instr
        out.append(D11Row(note=n, instrument=inst))
        out.extend(D11Row(note=SF2_GATE_ON) for _ in range(nrows - 1))
    return out


def _sector_rows(events, base, silent_idx):
    """One sector's note events -> Driver 11 rows. cur_instr=None per sector so each
    sequence sets its own instrument (dedup-safe); silent anchors for all-rest sectors
    (the PSE-00 silent intro) — exactly like fc_to_sf2._block_rows."""
    out = []
    cur = None
    rest_run = 0
    for note, dur, instr, is_rest in events:
        nrows = max(1, dur)
        if is_rest:
            for _ in range(nrows):
                if rest_run >= _MAX_REST_RUN:
                    out.append(D11Row(note=1, instrument=silent_idx)); cur = silent_idx; rest_run = 0
                else:
                    out.append(D11Row(note=SF2_GATE_OFF)); rest_run += 1
            continue
        rest_run = 0
        n = max(SF2_NOTE_MIN, min(note + base, SF2_NOTE_MAX))
        inst = None
        if instr != cur:
            inst = instr; cur = instr
        out.append(D11Row(note=n, instrument=inst))
        out.extend(D11Row(note=SF2_GATE_ON) for _ in range(nrows - 1))
    if silent_idx is not None and out and all(r.note == SF2_GATE_OFF for r in out):
        out[-1] = D11Row(note=1, instrument=silent_idx)
    return out


def build_structured(rmz, base, silent_idx):
    """Emit one (deduplicated) Driver 11 sequence per SECTOR instance + a per-voice
    orderlist that replays them — so the SF2 editor shows the song's real patterns."""
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
        for sector, ntr, str_ in rmz._orderlist(v):
            ev = rmz._sector(rmz._u16(rmz.sect_ptrs + sector * 2), ntr, str_)
            add(_sector_rows(ev, base, silent_idx), v)
    return sequences, orderlists


def _append_silent_instrument(instr_rows, wave_table, pulse_table):
    wrow = len(wave_table)
    wave_table.append((0x00, 0x00))
    wave_table.append((0x7F, wrow))
    idx = len(instr_rows)
    instr_rows.append(D11Instrument(ad=0, sr=0, flags=0x80, filter_idx=0,
                                    pulse_idx=0, wave_idx=wrow, pulse_width=0))
    return idx


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        'out', os.path.splitext(os.path.basename(path))[0] + '.sf2')
    d, la = load_sid(path)
    rmz = RMZ(d, la)
    base = calibrate_base(rmz)
    instr_rows, wave_table, pulse_table = build_instruments(rmz)
    silent_idx = _append_silent_instrument(instr_rows, wave_table, pulse_table)
    # Structured: one sequence per SECTOR + a real orderlist (the song's patterns),
    # like fc_to_sf2. base = fixed 0 (ROMUZAK note == SF2 semitone); tempo derived
    # per-tune from the player's tick-divider reload (find_tempo).
    sequences, orderlists = build_structured(rmz, base, silent_idx)
    tempo = find_tempo(d)
    song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=pulse_table,
        tracks=[], tempo=tempo, pitch_base=base, subtune=0)
    print(f"load=${la:04X} base={base} tempo={tempo} sectors/voice={[len(rmz._orderlist(v)) for v in range(3)]} "
          f"sequences={len(sequences)} sounds={sum(1 for s in rmz.sounds if s != (0xFF,)*8)}")
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    open(out, 'wb').write(sf2)
    print(f"emitted {len(sf2)} bytes -> {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
