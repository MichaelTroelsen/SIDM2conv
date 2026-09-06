"""ROMUZAK V6.x SID -> editable Driver 11 SF2 (Stage A), like bin/fc_to_sf2.py.

ROMUZAK (Oliver Blasnik, 1989) is an expanded Future Composer: 3 TRACKS (orderlists)
reference SECTORS (patterns) of NOTE/DUR/SND commands, with 8-byte SOUND records.
Format fully RE'd (player disasm + decrunched editor + the V6.x manual); see the
`romuzak-player-re` memory. We decode it and transpile onto a real Driver 11 SF2,
reusing the FC IR + emitter + silent-intro anchors + trace-driven pulse/filter.

Usage:  py -3 bin/romuzak_to_sf2.py SID/Fun_Fun/Delirious_9_tune_1.sid [out.sf2]

With no second argument the artifact goes to `out/romuzak/<stem>.sf2`, NOT the
`out/` root. It used to land in the root, where a caller that had declared only
`out/romuzak` wrote outside its own scope without noticing -- `out/` already
holds hundreds of loose .sf2 files, so nothing looked wrong.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.sid_parser import SIDParser
from sidm2.galway_to_driver11 import (
    D11Instrument, D11Row, GalwayDriver11Song,
    SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
    _norm_waveform, _pulse_program, _nearest_pal,
)


def _drum_semitone(value):
    """A drum table entry's value is the frequency HIGH byte (the player keeps the
    note's freq LOW byte and overwrites the high byte per frame); map it to the
    nearest absolute SF2 semitone via the PAL freq table. (RE'd from the $30EB note
    engine + verified vs the original osc3 drum trace: B4=2 [$40,$08,$06,$04] ->
    B-5,C-3,G-2,C#2.) The old code treated the value as a semitone directly (wrong)."""
    semi, _ = _nearest_pal((value << 8) | 0x80)
    return max(0, min(95, semi))
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
        """Decode one sector -> [(note,rows,instr,is_rest)] (CONT extends prev).

        Durations come from the player's shared per-voice tick counter ($2C3E):
        a DUR byte ($60-$7F) sets the reload value `b & $1F` ($2C3B); the counter
        is reloaded on every NOTE/CONT, decrements one per tick, and the event ends
        only when it goes NEGATIVE -> the event lasts `reload + 1` ticks (= rows).
        A PSE byte ($80-$9F) loads the counter DIRECTLY with its own `b & $1F`
        (falling back to the current DUR when that is 0), so a pause is NOT the last
        DUR — sector 00 = `8F FF` is a 15(+1)-row rest, the silent-intro unit.
        (RE'd from the $2FE9/$302B/$3079 handler; see docs/players/ROMUZAK.md.)"""
        out = []
        i = 0
        dur_reload, cur_snd = 0, 0
        while i < 256:
            b = self._u8(addr + i); i += 1
            if b == 0xFF:
                break
            if b < 0x60:                          # NOTE (chromatic)
                out.append([(b + ntr) & 0xFF, dur_reload + 1,
                            (cur_snd + str_) & 0x1F, False])
            elif b < 0x80:                        # DUR -> reload value (b & $1F)
                dur_reload = b & 0x1F
            elif b < 0xA0:                         # PSE: counter = (b&$1F) or DUR
                pr = (b & 0x1F) or dur_reload
                out.append([0, pr + 1, cur_snd, True])
            elif b < 0xC0:                        # SND
                cur_snd = b & 0x1F
            elif b < 0xE0:                        # SND base (rare)
                cur_snd = b & 0x1F
            elif b == 0xE0:                       # GLD/APM glide: 1 param byte, 0 rows
                i += 1
            elif b == 0xF0:                       # CONT -> extend prev by DUR+1 ticks
                if out:
                    out[-1][1] += dur_reload + 1
                else:
                    out.append([0, dur_reload + 1, cur_snd, True])
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
    duration tick fires every (reload + 1) video frames. One decoded row = one tick
    (durations are emitted in ticks, see _sector); the Driver-11 plays `tempo + 1`
    video frames per row (verified note-for-note vs the original onset timing), so to
    match a (reload + 1)-frame tick we set tempo = reload. This is PER-TUNE: Delirious
    reload $03 -> tempo 3, Road $02 -> tempo 2. Located by signature (relocation-safe);
    falls back to 3 if not found."""
    for i in range(len(d) - 9):
        if (d[i] == 0xCE and d[i + 3] == 0x10 and d[i + 5] == 0xA9
                and d[i + 7] == 0x8D and d[i + 1] == d[i + 8] and d[i + 2] == d[i + 9]):
            return d[i + 6]
    return 3


def build_instruments(rmz):
    """ROMUZAK 8-byte sound -> Driver 11 instrument + wave/pulse tables.

    B7 effect byte (like FC mctrl): bit1=ARP (semitones in the next sound row),
    bit4=SEEK (pulse-width ramps from 0 by B0/tick), bit6=waveform->pulse after 2
    DUR.

    THE REMAINING BITS, MEASURED 2026-09-05 over the WHOLE ROMUZAK corpus rather
    than argued about. SID/Fun_Fun holds 20 .sid files but only TWO decode to a
    sound bank -- Delirious_9_tune_1 and Road_of_Excess_end -- and they share it
    byte for byte (sound table $36F6, drum table $2D60, identical contents). So
    n = 64 non-$FF sounds across 2 files, and every count below is out of that.
    The distinct B7 values in the entire corpus are {$00, $09, $10, $40, $42}.

      bit5 FILTER -- UNEXERCISED. Set on 0 of 64 sounds. There is nothing in
        this corpus to decode it against, and modelling it blind would produce
        exactly the 0==0 confident-100% shape fidelity_common.exercised() exists
        to catch. Leave it undecoded until a file that sets it turns up; if one
        does, this count is the thing to re-run first.

      bit0 DRUM -- EXERCISED, and heavily. Set on 4 sounds (indices 2 and 4 in
        both files, B7=$09 each). Voice 2 selects a drum sound 363 times in
        Delirious_9 and 560 in Road_of_Excess; voice 1 24 and 14; voice 0 never.
        So this is the percussion voice of both songs, not a corner case.
        WHAT IS KNOWN ABOUT THE TABLE: $2D60 holds EIGHT little-endian pointers
        ($2D7D $2D94 $2DA5 $2DB0 $2D70 $2DBB $2DD2 $2DEF) and the data begins
        immediately after them at $2D70, in 4-byte rows -- the first two read
        `81 C0 11 04` and `81 C0 11 02`, differing only in the last byte.
        CORROBORATED BY A TRACE, not just by the bytes: siddump of
        Delirious_9_tune_1 (-t30, 1500 frames) shows voice 2 carrying waveform
        $81/$80 on 295 frames and $11/$10 on 130 -- and $81 and $11 are exactly
        the two waveforms that first row names. NOT DECODED: what $C0 and the
        trailing byte mean. The obvious reading (waveform, param) x2 with the
        last byte a duration is a HYPOTHESIS and is deliberately not implemented
        -- it needs a py65/zig64 trace of the player's own drum path, and this
        repo does not ship a model on a plausible-sounding byte reading.

      bit3 -- UNDOCUMENTED, and it is a THIRD open bit rather than part of the
        two above. It is set on exactly the sounds that set bit0 ($09 = bit0 |
        bit3) and on no others, so this corpus cannot separate them: any
        behaviour attributed to bit0 here could belong to bit3. Whoever decodes
        the drum path must decode both or say which one the evidence isolates.
    """
    instr_rows, wave_table, pulse_table = [], [], []
    for idx, s in enumerate(rmz.sounds):
        b0, b1, b2, b3, b4, b5, b6, b7 = s
        wf = _norm_waveform(b1)
        wave_row = len(wave_table)
        if b7 & 0x01:                               # DRUM: per-frame (waveform,pitch)
            wave_table.append((wf, 0x00))           # frame 0 = note pitch (the onset)
            for dwf, dval in (rmz.drum_sequence(b4) or [(wf, 0)]):
                wave_table.append((dwf, 0x80 | _drum_semitone(dval)))
            settle = len(wave_table)
            wave_table.append((0x10, 0x00))         # gate-off settle
            wave_table.append((0x7F, settle))
        elif b7 & 0x02:                             # ARPEGGIO: offsets in next sound row
            arp = rmz.sounds[idx + 1] if idx + 1 < len(rmz.sounds) else (0,) * 8
            # Stored [d0,d1,d2,d3] with d3 = root 0; the engine plays it ROTATED
            # RIGHT (root-first) -> [d3,d0,d1,d2] = [0,12,7,3]. Verified vs trace:
            # data 0C 07 03 00 on note C-5 -> C-5,C-6,G-5,D#5 (offsets 0,12,7,3).
            for sem in (arp[3] & 0x7F, arp[0] & 0x7F, arp[1] & 0x7F, arp[2] & 0x7F):
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


def default_out(path):
    """Where an artifact goes when the caller names no destination.

    `out/romuzak/`, not the `out/` ROOT. The root default was invisible in the
    normal case -- the file appeared, the build reported success -- and only
    showed up as a scope violation: a task declaring `rw:out/romuzak` invoked
    this the documented way and wrote `out/<stem>.sf2` instead, a path it had
    not declared. Returning the corpus directory makes the documented
    invocation and the declared scope the same thing.
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    return os.path.join('out', 'romuzak', stem + '.sf2')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else default_out(path)
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
