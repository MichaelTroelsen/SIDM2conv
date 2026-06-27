"""SF2 (Driver 11) -> Future Composer FCSong reader — closes the SF2->FC loop.

Reads a Driver-11 .sf2 (the kind `bin/fc_to_sf2.py` emits) back into per-voice
note/duration/instrument events and builds an `FCSong`, so an edited SF2 can be
serialized to a native FC module via `fc_writer.write_fc` and loaded into the real
C64 Future Composer editor.

Notes (pitch) and durations come from the SF2; the player code, freq/arp/drum
tables and the 8-byte instrument records are taken from a TEMPLATE FCSong (the
source FC module), since the Driver-11 instrument columns don't carry FC's arp/
drum bytes. This is the inverse of `fc_to_sf2.fc_to_song` + the Driver-11 emitter.
"""

from __future__ import annotations

from typing import List, Tuple

from collections import Counter

from .models import SF2DriverInfo
from . import sf2_parser
from .fc_parser import FCSong, FCNote, NUM_NOTES
from .galway_to_driver11 import _nearest_pal

REST_NOTE = 108         # generic FC rest index (>= NUM_NOTES); exact value is lossy


def calibrate_base(freq_lo, freq_hi, tol: int = 12) -> int:
    """Modal (pal_index - fc_index) offset matching FC freqs to the PAL table —
    must match bin/fc_to_sf2.calibrate_base so the note mapping inverts exactly."""
    offs = Counter()
    for i in range(NUM_NOTES):
        f = freq_lo[i] | (freq_hi[i] << 8)
        if f < 8:
            continue
        ni, dist = _nearest_pal(f)
        if dist < tol:
            offs[ni - i] += 1
    return offs.most_common(1)[0][0] if offs else 0


def _walk_sequence(sf2: bytes, off, addr: int, cur_instr: int
                   ) -> Tuple[List[Tuple[int, int, int, bool]], int]:
    """Unpack one packed sequence into (note, instr, rows, tie) events, threading
    the current instrument in/out (it persists across sequences in an orderlist,
    so the SF2 only re-emits it on change).
    Packed format (SF2II): $7f end, $c0-$ff cmd, $a0-$bf set-instr, $80-$9f dur
    (&$0f; $90 bit = tie), then the note ($00-$7f). $7e notes extend the prior
    note's duration (long notes split into multiple tokens)."""
    out: List[Tuple[int, int, int, bool]] = []
    i = addr
    guard = 0
    while guard < 4096:
        guard += 1
        b = sf2[off(i)]
        if b == 0x7F:
            break
        i += 1
        instr = cur_instr
        if 0xC0 <= b <= 0xFF:                 # command -> skip, read next
            b = sf2[off(i)]; i += 1
        if 0xA0 <= b <= 0xBF:                 # set instrument
            instr = b & 0x1F
            cur_instr = instr
            b = sf2[off(i)]; i += 1
        dur = 0
        tie = False
        if 0x80 <= b <= 0x9F:                 # duration (+ tie bit)
            dur = b & 0x0F
            tie = (b & 0x10) != 0
            b = sf2[off(i)]; i += 1
        note = b                              # $00 off, $01-$6f note, $7e sustain
        if note == 0x7E and out:              # extend previous note
            n0, i0, r0, t0 = out[-1]
            out[-1] = (n0, i0, r0 + dur + 1, t0)
        else:
            out.append((note, instr, dur + 1, tie))
    return out, cur_instr


def _track_events(sf2: bytes, off, di: SF2DriverInfo, v: int
                  ) -> List[Tuple[int, int, int, bool]]:
    """Walk track v's orderlist (one pass to $ff) -> its sequences -> events."""
    def u8(a):
        return sf2[off(a)]
    olp = u8(di.orderlist_ptrs_lo + v) | (u8(di.orderlist_ptrs_hi + v) << 8)
    seqs: List[int] = []
    a = olp
    for _ in range(256):
        b = u8(a); a += 1
        if b == 0xFF:
            break
        if b >= 0x80:                          # transpose marker (0 in our output)
            continue
        seqs.append(b)
    events: List[Tuple[int, int, int, bool]] = []
    cur_instr = 0
    for si in seqs:
        sp = u8(di.sequence_ptrs_lo + si) | (u8(di.sequence_ptrs_hi + si) << 8)
        ev, cur_instr = _walk_sequence(sf2, off, sp, cur_instr)
        events.extend(ev)
    return events


def sf2_to_fcsong(sf2_bytes: bytes, template: FCSong) -> FCSong:
    """Read a Driver-11 SF2 into an FCSong, using `template` for the player /
    tables / instrument records. Pitch base is inverted exactly as
    `fc_to_song` set it (calibrate_base(freq) - 1)."""
    sf2 = bytearray(sf2_bytes)
    di = SF2DriverInfo()
    la = sf2_parser.parse_sf2_blocks(sf2, di)
    if la is None:
        raise ValueError("not a parseable SF2")

    def off(addr: int) -> int:
        return addr - la + 2

    base = calibrate_base(template.freq_lo, template.freq_hi) - 1

    voices: List[List[FCNote]] = []
    for v in range(3):
        notes: List[FCNote] = []
        for note, instr, rows, tie in _track_events(sf2, off, di, v):
            dur = max(0, min(rows - 1, 0x3F))
            if note == 0x00 or note >= 0x70:           # note-off / out of range -> rest
                fc_note = REST_NOTE
            else:
                fc_note = (note - base - 1) & 0xFF
            notes.append(FCNote(note=fc_note, dur=dur, instr=instr, tie=tie))
        voices.append(notes)

    return FCSong(load=template.load, base=template.base, speed=template.speed,
                  freq_lo=template.freq_lo, freq_hi=template.freq_hi,
                  instruments=template.instruments, voices=voices,
                  voice_blocks=[], block_ptrs={},
                  _mem=template._mem, _drum_tbls=template._drum_tbls)
