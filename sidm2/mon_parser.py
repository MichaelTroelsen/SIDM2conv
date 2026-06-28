"""Maniacs of Noise (Jeroen Tel) player parser — Hawkeye and the Tel_Jeroen corpus.

Decodes the two-level MoN format (RE'd from Hawkeye.sid; see the `hawkeye-mon-player-re`
memory):
  - per-voice ORDERLISTS: bytes are pattern numbers (<$40) + per-voice param bytes
    ($80-$FF -> transpose/instrument base, $40-$7F -> other params) + $FE (pattern end)
    / $FF (orderlist loop).
  - PATTERNS (ptr from the $8409 table, pattern#*2): a byte stream where $00-$6F = NOTE,
    $70-$7F = instrument program, $80-$BF = DURATION (for the following note), $C0-$DF =
    slide, $E0-$FF = commands.
  - per-subtune orderlist-pointer sets are at `$7B00 | $83FC[subtune]` (6 bytes = 3 voice
    lo + 3 voice hi); per-subtune speed at `$83F5[subtune]`.

This is the note/structure layer (Stage A). Effect/instrument semantics (slide, vibrato,
filter, the $8580/$8589 programs) are decoded separately for timbre/Stage-B.

Table addresses are located relocation-safe via player-code signatures so the parser
works across the corpus (tunes load at different addresses), falling back to the Hawkeye
absolutes.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from sidm2.sid_parser import SIDParser


def load_sid(path):
    """Load a PSID/RSID. Returns (data, load_address). Handles PSID load=0 (the real
    load word is the first 2 data bytes — the MoN rips ship this way)."""
    raw = open(path, "rb").read()
    h = SIDParser(path).parse_header()
    d = raw[h.data_offset:]
    la = h.load_address
    if la == 0 and len(d) >= 2:
        la = d[0] | (d[1] << 8)
        d = d[2:]
    return d, la, h


# ---------------------------------------------------------------------------
# Relocation-safe table location via player-code signatures
# ---------------------------------------------------------------------------
def _find(d, *sig):
    """Find the first offset where the byte pattern matches (None = wildcard)."""
    for i in range(len(d) - len(sig)):
        if all(s is None or d[i + k] == s for k, s in enumerate(sig)):
            return i
    return None


@dataclass
class MONEvent:
    note: int = 0          # MoN note value (after transpose); -1 = none
    dur: int = 1           # duration in ticks
    instr: int = 0         # current instrument program
    is_rest: bool = False
    slide: int = 0


class MON:
    """Decoded MoN song for one subtune."""

    def __init__(self, d, la, subtune=0):
        self.d, self.la = d, la
        self._locate()
        self.subtune = subtune
        self.speed = self._u8(self.tbl_speed + subtune)
        self.voices = [self._voice(v) for v in range(3)]

    # -- memory access (absolute SID addresses) --
    def _u8(self, a):
        o = a - self.la
        return self.d[o] if 0 <= o < len(self.d) else 0xFF

    def _u16(self, a):
        return self._u8(a) | (self._u8(a + 1) << 8)

    # -- table location (relocation-safe via player-code signatures) --
    def _locate(self):
        d = self.d
        # orderlist-ptr-set table-index $83FC: `LDA $83fc,X (BD FC 83); STA $7b6b
        #   (8D 6B 7B); LDY #5 (A0 05)`. Then `LDA $7b2c,Y (B9 2C 7B); STA $8403,Y
        #   (99 03 84)` -> the orderlist-ptr SETS live at page = $7b2c's hi byte.
        off = _find(d, 0xBD, None, None, 0x8D, None, None, 0xA0, 0x05,
                    0xB9, None, None, 0x99)
        if off is not None:
            self.tbl_olptr = d[off + 1] | (d[off + 2] << 8)         # $83FC
            self.olset_hi = d[off + 10]                             # $7B (the LDA $7b2c,Y hi)
        else:
            self.tbl_olptr, self.olset_hi = 0x83FC, 0x7B
        # speed table $83F5: `LDA $83f5,X (BD F5 83); STA $7afe (8D FE 7A)` — the STA
        #   destination ($7afe) is the speed-reload byte read each frame; match the
        #   LDA-abs,X just before LDY #$17 won't generalize, so anchor on $83FC-7.
        self.tbl_speed = self.tbl_olptr - 7                         # $83F5 = $83FC-7
        # pattern-pointer table $8409: `ASL A (0A); TAY (A8); LDA $8409,Y (B9 09 84)`.
        po = _find(d, 0x0A, 0xA8, 0xB9, None, None, 0x85, 0xFD)
        self.tbl_pat = (d[po + 3] | (d[po + 4] << 8)) if po is not None else 0x8409
        # freq table $8337: `TAY (A8); LDA $8337,Y (B9 37 83); STA $9133,X (9D ..)`.
        fo = _find(d, 0xA8, 0xB9, None, None, 0x9D)
        self.tbl_freq = (d[fo + 2] | (d[fo + 3] << 8)) if fo is not None else 0x8337

    # -- orderlist pointers for this subtune --
    def _orderlist_ptr(self, voice):
        lo = self._u8(self.tbl_olptr + self.subtune)        # $83FC[sub] = low byte
        setaddr = (self.olset_hi << 8) | lo                 # $7B(low) = the 6-byte set
        return self._u8(setaddr + voice) | (self._u8(setaddr + 3 + voice) << 8)

    # -- decode one voice (orderlist -> patterns -> events) --
    def _voice(self, voice):
        ol = self._orderlist_ptr(voice)
        events, transpose, instr = [], 0, 0
        i, guard = 0, 0
        while guard < 512:
            guard += 1
            b = self._u8(ol + i); i += 1
            if b == 0xFF:                       # orderlist loop/end
                break
            if b == 0xFE:                       # pattern-end marker (skip)
                continue
            if b >= 0x80:                       # $80-$FF: transpose / instrument base
                transpose = b & 0x1F
                continue
            if b >= 0x40:                       # $40-$7F: other per-voice param (skip)
                continue
            # b < $40 = pattern number
            instr = self._pattern(b, transpose, instr, events)
        return events

    def _pattern(self, pat, transpose, instr, events):
        ptr = self._u16(self.tbl_pat + pat * 2)
        cur_dur = 1
        j, guard = 0, 0
        while guard < 1024:
            guard += 1
            b = self._u8(ptr + j); j += 1
            hi = b & 0xF0
            if hi == 0xF0:                      # command (filter/gate) — may consume a byte
                if b & 0x01:
                    j += 1                       # filter writes a following byte
                continue
            if hi == 0xE0:                      # command (TBD) — consume nothing for now
                continue
            if 0xC0 <= b <= 0xDF:               # slide (sets state; not a note)
                continue
            if 0x70 <= b <= 0x7F:               # set instrument program
                instr = b & 0x0F
                continue
            if 0x80 <= b <= 0xBF:               # DURATION for the following note
                cur_dur = (b & 0x3F)
                continue
            if b == 0xFF:                        # safety: pattern terminator
                break
            # b <= $6F = NOTE
            note = (b + transpose) & 0x7F
            events.append(MONEvent(note=note, dur=max(1, cur_dur), instr=instr))
            cur_dur = 1
        return instr

    def note_freq(self, note):
        return self._u16(self.tbl_freq + note * 2)
