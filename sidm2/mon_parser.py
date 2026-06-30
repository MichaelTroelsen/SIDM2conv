"""Maniacs of Noise (Jeroen Tel) player parser — Hawkeye and the Tel_Jeroen corpus.

Decodes the two-level MoN format (RE'd from Hawkeye.sid; see the `hawkeye-mon-player-re`
memory):
  - per-voice ORDERLISTS: bytes are pattern numbers (<$40) + per-voice param bytes
    ($80-$FF -> transpose/instrument base, $40-$7F -> other params) + $FE (pattern end)
    / $FF (orderlist loop).
  - PATTERNS (ptr from the $8409 table, pattern#*2): a byte stream where $00-$6F = NOTE,
    $70-$7F = instrument program, $80-$BF = DURATION, $C0-$DF = slide, $Ex = command,
    $Fx-odd = filter, $Fx-even = legato note. $FE in an orderlist = SONG END (halt).
  - per-subtune orderlist-pointer sets are at `$7B00 | $83FC[subtune]` (6 bytes = 3 voice
    lo + 3 voice hi); per-subtune speed at `$83F5[subtune]`.

TIMING (calibrated frame-exact vs siddump, all 3 voices): the sequencer advances one
"tick" every speed+1 frames (the $9116 tempo gate). DURATION is STICKY ($90CE, set by
$80-$BF bytes, a 2nd byte adds) and a note lasts (byte & $3F) ticks = that * (speed+1)
frames. MONEvent.dur is in TICKS; multiply by MON.frames_per_tick for frames.

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
    dur: int = 1           # duration in TICKS (frames = dur * (speed+1))
    instr: int = 0         # instrument index ($90DA, set by $Cx) -> $860C AD/SR/WF/PW record
    wprog: int = 0         # wave-program index ($7x -> $8580/$8589); Stage-B modulation
    retrig: bool = True    # False = legato ($F0-even prefix): freq change, no gate restart


class MON:
    """Decoded MoN song for one subtune."""

    def __init__(self, d, la, subtune=0):
        self.d, self.la = d, la
        self._locate()
        self.subtune = subtune
        self.speed = self._u8(self.tbl_speed + subtune)
        self.voices = [self._voice(v) for v in range(3)]

    @property
    def frames_per_tick(self):
        """The tempo gate (DEC $9116; reload $7AFE on <0; CMP $7AFE) fires the
        sequencer once every speed+1 frames."""
        return self.speed + 1

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
        # The subtune setup self-modifies a 6-byte 'set' source pointer (3 orderlist-ptr
        # lo + 3 hi) then copies it to the live OL pointers (`LDY #5; LDA setSrc,Y; STA
        # setDst,Y`). setSrc's LOW byte comes from a per-subtune index table (loTab); its
        # HIGH byte is either a 2nd table (hiTab — Cybernoid) or FIXED (Hawkeye). Resolve
        # both by finding which `LDA tab,X; STA m` self-modify writes the B9 operand bytes.
        cp = _find(d, 0xA0, 0x05, 0xB9, None, None, 0x99)
        if cp is not None:
            ss_lo = self.la + cp + 3            # C64 addr of the B9 set-source lo operand
            self.olset_hi = d[cp + 4]           # default (fixed) high byte
            lo_sm = _find(d, 0xBD, None, None, 0x8D, ss_lo & 0xFF, (ss_lo >> 8) & 0xFF)
            self.tbl_olptr = (d[lo_sm + 1] | (d[lo_sm + 2] << 8)) if lo_sm is not None else 0x83FC
            hi_sm = _find(d, 0xBD, None, None, 0x8D, (ss_lo + 1) & 0xFF, ((ss_lo + 1) >> 8) & 0xFF)
            self.tbl_olptr_hi = (d[hi_sm + 1] | (d[hi_sm + 2] << 8)) if hi_sm is not None else None
        else:
            self.tbl_olptr, self.tbl_olptr_hi, self.olset_hi = 0x83FC, None, 0x7B
        # speed table: `LDA speedTab,X; STA speedReload`. The tables (speed + olptr lo/hi
        # + others) sit in one small per-subtune block; the speed table is the lowest of
        # the setup's `LDA tab,X` reads. Anchor on the min of (loTab, hiTab) minus the
        # observed gap, but locate it directly when possible (below) for robustness.
        self.tbl_speed = self._find_speed_tbl(d)
        # pattern-pointer table: `ASL A (0A); TAY (A8); LDA tab,Y (B9 ..); STA zp (85 ..)`.
        # The STA zp byte is engine-relocation-specific (Hawkeye $FD, Cybernoid $BD), so
        # don't pin it; take the FIRST such read (the orderlist->pattern one).
        po = _find(d, 0x0A, 0xA8, 0xB9, None, None, 0x85, None)
        self.tbl_pat = (d[po + 3] | (d[po + 4] << 8)) if po is not None else 0x8409
        # freq table is SPLIT into two arrays indexed by note byte (NOT interleaved):
        #   LO read `TAY (A8); LDA loTab,Y (B9 ..); STA scratch,X (9D ..)`,
        #   HI read `LDA hiTab,Y (B9 ..); STA scratch+3,X (9D ..)`. The scratch dest is
        #   relocation-specific ($9133/$9136 Hawkeye, $BF4C/$BF4F Cybernoid), so locate
        #   the LO table as the MOST-COMMON A8-B9-9D read target, then the HI table as the
        #   B9-9D read whose dest is loDest+3 (the high byte stored next to the low).
        lo_reads = [(d[i + 2] | (d[i + 3] << 8), d[i + 5] | (d[i + 6] << 8))
                    for i in range(len(d) - 6)
                    if d[i] == 0xA8 and d[i + 1] == 0xB9 and d[i + 4] == 0x9D]
        if lo_reads:
            from collections import Counter
            tab = Counter(t for t, _ in lo_reads).most_common(1)[0][0]
            self.tbl_freq = tab
            lo_dest = next(de for t, de in lo_reads if t == tab)
        else:
            self.tbl_freq, lo_dest = 0x8337, 0x9133
        self.tbl_freq_hi = self.tbl_freq + (0x8396 - 0x8337)        # default stride
        for i in range(len(d) - 5):
            if (d[i] == 0xB9 and d[i + 3] == 0x9D
                    and (d[i + 4] | (d[i + 5] << 8)) == lo_dest + 3):
                self.tbl_freq_hi = d[i + 1] | (d[i + 2] << 8)
                break
        # instrument-record table $860C: the note handler reads AD via
        #   `LDA $860e,X (BD 0E 86); STA $d405,Y (99 05 D4)`. $860E is record+2 (AD),
        #   so the 8-byte-record base = operand - 2.
        io = _find(d, 0xBD, None, None, 0x99, 0x05, 0xD4)
        self.tbl_instr = ((d[io + 1] | (d[io + 2] << 8)) - 2) if io is not None else 0x860C

    def _find_speed_tbl(self, d):
        """Locate the per-subtune speed table. The play routine's tempo gate reloads a
        counter from a 'speed-reload' byte (`DEC counter ... LDA reload ... STA counter`);
        the subtune setup fills that byte from the speed table (`LDA speedTab,X; STA
        reload`). Find the gate, then the table that feeds its reload. Falls back to the
        Hawkeye offset (loTab-7)."""
        for i in range(len(d) - 3):
            if d[i] != 0xCE:                                # DEC counter (abs)
                continue
            clo, chi = d[i + 1], d[i + 2]
            for j in range(i + 3, min(i + 48, len(d) - 2)):
                if d[j] == 0x8D and d[j + 1] == clo and d[j + 2] == chi:   # STA same counter
                    for k in range(i + 3, j):               # LDA reload in between
                        if d[k] == 0xAD:
                            rl = d[k + 1] | (d[k + 2] << 8)
                            sm = _find(d, 0xBD, None, None, 0x8D, rl & 0xFF, (rl >> 8) & 0xFF)
                            if sm is not None:
                                return d[sm + 1] | (d[sm + 2] << 8)
                    break
        return self.tbl_olptr - 7

    # -- orderlist pointers for this subtune --
    def _orderlist_ptr(self, voice):
        lo = self._u8(self.tbl_olptr + self.subtune)        # per-subtune set-source lo
        hi = (self._u8(self.tbl_olptr_hi + self.subtune)    # ...hi from a 2nd table, or
              if self.tbl_olptr_hi else self.olset_hi)      # the fixed high byte (Hawkeye)
        setaddr = (hi << 8) | lo                            # the 6-byte OL-pointer set
        return self._u8(setaddr + voice) | (self._u8(setaddr + 3 + voice) << 8)

    # -- decode one voice (orderlist -> patterns -> events) --
    def _voice(self, voice):
        """Flat event list for the whole voice (all patterns concatenated)."""
        return [ev for _pat, blk in self._voice_blocks(voice) for ev in blk]

    def _voice_blocks(self, voice):
        """Walk the orderlist -> [(pattern_number, [MONEvent, ...]), ...], one block
        per orderlist pattern entry. The per-voice state PERSISTS across blocks
        (mirrors the player's per-voice RAM): transpose ($90F9), instrument base
        ($9139), current instrument ($90DA), wave-program, and the sticky stored
        duration $90CE — so identical pattern numbers under different transposes
        decode to different events (the caller dedups by the resulting rows)."""
        ol = self._orderlist_ptr(voice)
        st = {'transpose': 0, 'instr_base': 0, 'instr': 0, 'stored': 0, 'wprog': 0}
        blocks = []
        i, guard, repeat = 0, 0, 1
        while guard < 1024:
            guard += 1
            b = self._u8(ol + i); i += 1
            if b == 0xFE:                       # $FE = SONG END (halts player globally)
                break
            if b == 0xFF:                       # $FF = orderlist loop point (one pass here)
                break
            if b >= 0x80:                       # $80-$FF: transpose ($90F9 = b & $1F)
                st['transpose'] = b & 0x1F
                continue
            if b >= 0x60:                       # $60-$7F: instrument base ($9139 = b & $0F)
                st['instr_base'] = b & 0x0F
                continue
            if b >= 0x40:                       # $40-$5F: REPEAT counter for the next pattern
                repeat = (b & 0x3F) + 1         #   ($9118 = b&$3F -> pattern replays N+1 times)
                continue
            # b < $40 = pattern number (played `repeat` times, then repeat resets to 1)
            for _ in range(repeat):
                blk = []
                self._pattern(b, st, blk)
                blocks.append((b, blk))
            repeat = 1
        return blocks

    def _emit(self, events, raw, st, retrig):
        note = (raw + st['transpose']) & 0x7F
        events.append(MONEvent(note=note, dur=st['stored'] + 1, instr=st['instr'],
                               wprog=st['wprog'], retrig=retrig))

    def _pattern(self, pat, st, events):
        """Faithful emulation of the player's pattern-byte dispatch chain
        ($7C64..$7D22). One note is emitted per sequencer read; prefixes
        (filter $Fx-odd, command $Ex, slide $Cx, instrument $7x, duration
        $8x-$Bx) consume following bytes and modify state. $FF = pattern end."""
        ptr = self._u16(self.tbl_pat + pat * 2)
        j = [0]

        def rd():
            b = self._u8(ptr + j[0]); j[0] += 1
            return b

        guard, have, b = 0, False, 0
        while guard < 4096:
            guard += 1
            if not have:
                b = rd()
            have = False
            if b == 0xFF:                       # pattern terminator
                break
            # $7C64: high nibble $F0?
            if (b & 0xF0) == 0xF0:
                if b & 0x01:                    # $Fx odd -> filter: 1 value byte, redispatch next
                    v = rd()
                    if v == 0xFF:
                        break
                    b = rd()
                    if b == 0xFF:
                        break
                    # fall through to $7C89 with the new b
                else:                           # $F0 even -> legato note (no retrigger)
                    nb = rd()
                    if nb == 0xFF:
                        break
                    self._emit(events, nb, st, retrig=False)
                    continue
            # $7C89: $Ex command (reads 3 bytes; redispatches the middle one).
            # Subtune 3 has none; handled minimally to stay in sync.
            if (b & 0xF0) == 0xE0:
                rd()                             # $912E param (idx+1)
                redis = rd()                     # redispatched token (idx+2)
                rd()                             # $912B param (idx+3)
                if redis == 0xFF:
                    break
                b, have = redis, True
                continue
            # $Cx ($C0-$DF): INSTRUMENT select ($90DA = b&$1F + instr_base) -> $860C
            # record (AD/SR/waveform/PW). Prefix: read next, fall through linearly.
            if (b & 0xE0) == 0xC0:
                st['instr'] = (b & 0x1F) + st['instr_base']
                b = rd()
                if b == 0xFF:
                    break
            # $7x: wave-PROGRAM select ($8580/$8589 modulation). Prefix: read next.
            if (b & 0xF0) == 0x70:
                st['wprog'] = b & 0x0F
                b = rd()
                if b == 0xFF:
                    break
            # $8x-$Bx DURATION (sticky $90CE): stored=(b&$3F)-1, optional 2nd adds.
            # Player then re-dispatches the following byte from $7C64.
            if (b & 0xC0) == 0x80:
                stored = (b & 0x3F) - 1
                b = rd()
                if b == 0xFF:
                    break
                if (b & 0xC0) == 0x80:           # 2nd duration byte adds
                    stored = (stored + (b & 0x3F)) & 0xFF
                    b = rd()
                    if b == 0xFF:
                        break
                st['stored'] = stored & 0xFF
                have = True
                continue
            # $7D22: NOTE
            self._emit(events, b, st, retrig=True)

    def note_freq(self, note):
        """SID freq for a note byte, from MoN's SPLIT freq table (lo $8337[note],
        hi $8396[note])."""
        return self._u8(self.tbl_freq + note) | (self._u8(self.tbl_freq_hi + note) << 8)

    def instrument(self, idx):
        """8-byte instrument record at $860C + idx*8 (selected by the $Cx byte ->
        $90DA). Byte-verified vs siddump WF/ADSR/Pulse. Returns a dict:
          ad, sr       : the $D405/$D406 envelope bytes (record[2], record[3])
          waveform     : the SID control byte (record[1], e.g. $41 saw+gate)
          pw           : 12-bit pulse width = (record[0] & $0F) << 8 ($D403=lo nib, $D402=0)
          wave_prog    : pointer to the record's own wave/arp program (record[5]/[6])
          flags        : record[7]
          raw          : the 8 bytes"""
        r = [self._u8(self.tbl_instr + (idx & 0x1F) * 8 + k) for k in range(8)]
        return {
            'ad': r[2], 'sr': r[3], 'waveform': r[1],
            'pw': (r[0] & 0x0F) << 8,
            'wave_prog': r[5] | (r[6] << 8),
            'flags': r[7], 'raw': r,
        }
