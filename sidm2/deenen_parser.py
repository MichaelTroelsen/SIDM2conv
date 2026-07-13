"""Charles Deenen / Maniacs-of-Noise game-replay decoder (Stage A locate + event
decoder).

This is the replay used by ~19 Deenen game rips in SID/deenen/ (and a large
MoN/Deenen group in SID/Tel_Jeroen/). It is NOT the Jeroen-Tel Hawkeye engine
that sidm2/mon_parser.py handles -- different dispatcher, different tables. The
player identifies via the note-dispatch signature `C9 60 B0 03 4C` (CMP #$60 /
BCS +3 / JMP note-handler).

ENGINE MAP (reverse-engineered from Ding_van_Charles, load $1000, dispatch
$1324; every branch target below read straight out of the code, register writes
confirmed against the $1904 SID-apply routine):

  Two-level song structure, per voice v (0..2):
    orderlist  : pointer read from  ORD_PTR[v*2 (+ subtune*8)]  + RELOC
                 bytes: <$5F pattern#, $5F-$6E set A-transpose ($10DB),
                 $6F-$7F pattern-loop count, $80-$FD note-transpose ($10D8,
                 value-$82), $FE stop, $FF loop orderlist.
    pattern    : pointer read from  PAT_PTR[pattern# * 2]  + RELOC
                 a row = optional prefix bytes then a note byte (<$60):
                   $C0-$DF  instrument = byte-$C0 + A-transpose
                   $80-$BF  default note duration = byte-$81 (accumulates)
                   $60-$7F  arp/vib param
                   <$60     NOTE, pitch = byte + note-transpose; onset here;
                            note holds `default duration`(+1) frames.
                   $E0-$FF  REST, holds byte-$E1 frames (no onset)
                   $FD/$FC/$FB/$FE/$FF  slide / enable / gate / speed / end
  Note -> SID:
    pitch index = note + $10D8  ->  FREQ_LO[i] / FREQ_HI[i]  (95-entry split)
    instrument record @ INSTR + instr*8:
       [0] PW packed (lo nibble->PW hi, hi nibble->PW lo)
       [1] waveform/control ($D404)   [2] AD ($D405)   [3] SR ($D406)
       [4] flags (bit3 = filter/vib)  [7] flags
  Timing: the play routine runs once per frame; each voice's note-duration
  counter ($10EA,X) is decremented every frame; a note lasts (duration+1)
  frames.  Verified by onset-matching siddump (see bin/deenen_validate.py).

The locate is RELOCATION-SAFE: table addresses come from byte-pattern searches
over the code (operands are read from the actual instructions), never fixed
offsets -- the corpus relocates the player to many different load addresses.

STATUS (honest, 2026-07-13): this is a Stage-A DRAFT.
  * Engine map above is complete and emulation-grounded (register writes read
    off the $1904 apply routine; the groove clock derived from $125C-$1280 and
    confirmed by exact onset-matching Ding_van_Charles's sparse voice 2).
  * The locate + decoder are VERIFIED on the "Ding-class" variant only. The
    global B9/BD operand scans still FALSE-POSITIVE on other sub-variants
    (e.g. After_the_War/Astro/B_A_T mislocate ord_ptr -> runaway note counts;
    Constant_Runner-class uses a different ZP layout with no reloc-ADC). So
    DeenenLocate.ok() currently OVER-reports; treat a decode with implausible
    note counts (>~10x siddump) as a mis-locate.
  * OPEN before this is a real corpus win: (1) the TOP-LEVEL multi-segment
    orderlist -- $FF advances $106C which re-selects the $195C segment pointer;
    this file's decoder treats $FF as a same-segment separator, so dense voices
    truncate/mis-thread after the first segment. (2) sub-variant-robust locate
    (anchor the operand scans to the code reached by a flow-disasm FROM the
    dispatch, don't scan the whole image). See bin/deenen_validate.py.
"""
import struct

DISPATCH_SIG = bytes.fromhex('c960b0034c')      # CMP #$60 / BCS +3 / JMP


def load_sid(path):
    """PSID -> (image_bytes, load_addr, header_dict). image indexed [addr-load]."""
    raw = open(path, 'rb').read()
    doff = struct.unpack('>H', raw[6:8])[0]
    load = struct.unpack('>H', raw[8:10])[0]
    h = dict(
        init=struct.unpack('>H', raw[0x0a:0x0c])[0],
        play=struct.unpack('>H', raw[0x0c:0x0e])[0],
        songs=struct.unpack('>H', raw[0x0e:0x10])[0],
        start=struct.unpack('>H', raw[0x10:0x12])[0],
    )
    body = raw[doff:]
    if load == 0:
        load = struct.unpack('<H', body[:2])[0]
        body = body[2:]
    return body, load, h


def _find_all(hay, needle, start=0):
    out = []
    i = hay.find(needle, start)
    while i >= 0:
        out.append(i)
        i = hay.find(needle, i + 1)
    return out


class DeenenLocate:
    """Relocation-safe table addresses located by code byte-patterns."""

    def __init__(self, d, la):
        self.d, self.la = d, la
        self.dispatch = None
        i = d.find(DISPATCH_SIG)
        if i >= 0:
            self.dispatch = la + i
        self.freq_lo = self.freq_hi = None
        self.instr = None
        self.ord_ptr = self.pat_ptr = self.reloc = None
        self.reloc_val = None
        self.subtune_tbl = None
        self._locate()

    def _w(self, off):
        return self.d[off] | (self.d[off + 1] << 8)

    def _locate(self):
        d = self.d
        lo_lim, hi_lim = self.la, self.la + len(d)
        # (A) freq + instrument reads. The note handler reads freq via two
        #     `LDA abs,Y` (opcode $B9) whose operands differ by exactly $5F (the
        #     95-entry lo/hi split), and the instrument record via a cluster of
        #     `LDA abs,Y` with consecutive operands. Variants put either abs,X or
        #     zp,X state stores between them, so we scan the B9 operands directly
        #     rather than matching the surrounding bytes.
        b9 = []
        for i in _find_all(d, b'\xb9'):
            if i + 2 < len(d):
                op = self._w(i + 1)
                if lo_lim <= op < hi_lim:
                    b9.append((self.la + i, op))
        opset = {op for _, op in b9}
        # freq: adjacent B9 sites (<=8 bytes apart) whose operands differ by $5F
        best = None
        for pc, op in b9:
            if (op + 0x5F) in opset:
                for pc2, op2 in b9:
                    if op2 == op + 0x5F and abs(pc2 - pc) <= 8:
                        d2 = abs(pc2 - pc)
                        if best is None or d2 < best[0]:
                            best = (d2, op)
        if best:
            self.freq_lo, self.freq_hi = best[1], best[1] + 0x5F
        # instrument: the tightest window of >=3 distinct B9 operands spanning
        # <=7 (one 8-byte record); base = min operand of that window.
        ops = sorted(opset)
        bestw = None
        for a in ops:
            grp = [o for o in ops if a <= o <= a + 7]
            if len(grp) >= 3:
                span = grp[-1] - grp[0]
                if bestw is None or len(grp) > bestw[0] or (
                        len(grp) == bestw[0] and span < bestw[1]):
                    bestw = (len(grp), span, grp[0])
        if bestw and (self.freq_lo is None or bestw[2] != self.freq_lo):
            self.instr = bestw[2]
        # (B) orderlist-ptr table + reloc: `LDA ord,X` ($BD) then within 4 bytes
        #     `ADC reloc` ($6D). (The CLC / STA-selfmod between them varies by
        #     sub-variant; some sub-variants relocate differently and are skipped.)
        for i in _find_all(d, b'\xbd'):
            if i + 3 > len(d):
                continue
            for k in (3, 4):
                if i + k + 2 < len(d) and d[i + k] == 0x6D:
                    self.ord_ptr = self._w(i + 1)
                    self.reloc = self._w(i + k + 1)
                    break
            if self.ord_ptr is not None:
                break
        # (C) pattern-ptr table: `ASL / TAY / LDA pat,Y` then `ADC reloc`
        for i in _find_all(d, b'\x0a\xa8\xb9'):
            for k in (5, 6):
                if i + k + 2 < len(d) and d[i + k] == 0x6D:
                    self.pat_ptr = self._w(i + 3)
                    break
            if self.pat_ptr is not None:
                break
        # (D) subtune-param table: init `0A 0A 0A 69 00` (song*8) then `AA BD ll hh`
        i = d.find(b'\x0a\x0a\x0a\x69\x00')
        if i >= 0:
            for j in range(i, min(i + 32, len(d) - 3)):
                if d[j] == 0xAA and d[j + 1] == 0xBD:
                    self.subtune_tbl = self._w(j + 2)
                    break
        if self.reloc is not None:
            off = self.reloc - self.la
            if 0 <= off + 1 < len(d):
                self.reloc_val = self._w(off)

    def ok(self):
        return None not in (self.dispatch, self.freq_lo, self.instr,
                            self.ord_ptr, self.pat_ptr, self.reloc_val)

    def summary(self):
        def h(x):
            return f'{x:#06x}' if x is not None else 'None'
        return (f'disp={h(self.dispatch)} freq={h(self.freq_lo)}/{h(self.freq_hi)} '
                f'instr={h(self.instr)} ord={h(self.ord_ptr)} pat={h(self.pat_ptr)} '
                f'reloc={h(self.reloc)}={h(self.reloc_val)}')


# ---------------------------------------------------------------------------
# Decoder
# ---------------------------------------------------------------------------

class DeenenModule:
    def __init__(self, d, la, subtune=0):
        self.d, self.la = d, la
        self.subtune = subtune
        self.loc = DeenenLocate(d, la)

    def _u8(self, addr):
        o = addr - self.la
        return self.d[o] if 0 <= o < len(self.d) else 0

    def _ptr(self, tbl, idx):
        """Read a relocated 16-bit pointer from table[idx] + reloc_val."""
        lo = self._u8(tbl + idx)
        hi = self._u8(tbl + idx + 1)
        return ((lo | (hi << 8)) + self.loc.reloc_val) & 0xFFFF

    def instrument(self, i):
        base = self.loc.instr + (i & 0xFF) * 8
        rec = [self._u8(base + k) for k in range(8)]
        pw = ((rec[0] & 0x0F) << 8) | ((rec[0] & 0xF0) >> 4)  # packed nibbles
        return dict(pw=pw, wf=rec[1], ad=rec[2], sr=rec[3],
                    flags=rec[4], raw=rec)

    def _freq(self, note):
        lo = self._u8(self.loc.freq_lo + note)
        hi = self._u8(self.loc.freq_hi + note)
        return lo | (hi << 8)

    def decode_voice(self, v, max_rows=20000):
        """Walk voice v's orderlist -> patterns -> rows. Returns a list of row
        events: dict(kind='note'|'rest', frames, note=?, instr=?, freq=?).
        One pass of the orderlist (stops at $FE/$FF loop or row cap)."""
        loc = self.loc
        base = self.subtune * 8
        ord_ptr = self._ptr(loc.ord_ptr, base + v * 2)
        events = []
        note_transpose = 0
        a_transpose = 0
        cur_instr = 0
        cur_dur = 1
        oi = 0                                   # orderlist index
        guard_ol = 0
        while guard_ol < 512 and len(events) < max_rows:
            guard_ol += 1
            ob = self._u8(ord_ptr + oi)
            if ob == 0xFE:
                break                            # $FE = stop -> end of song
            if ob == 0xFF:
                oi += 1                          # $FF = pattern separator/loop
                continue
            if 0x5F <= ob <= 0x6E:
                a_transpose = ob - 0x5F
                oi += 1
                continue
            if 0x6F <= ob <= 0x7F:
                oi += 1                          # pattern-loop count (Stage B)
                continue
            if 0x80 <= ob <= 0xFD:
                note_transpose = (ob - 0x82) & 0xFF
                if note_transpose >= 0x80:
                    note_transpose -= 0x100
                oi += 1
                continue
            # else: pattern index
            pat = self._ptr(loc.pat_ptr, ob * 2)
            pi = 0
            guard_p = 0
            while guard_p < 4096 and len(events) < max_rows:
                guard_p += 1
                b = self._u8(pat + pi)
                if b == 0xFF:
                    break                        # end of pattern
                # multi-byte commands
                if b == 0xFE:                    # set global speed (skip 1 param)
                    pi += 2
                    continue
                if b == 0xFD:                    # slide note: params then note
                    pi += 3
                    b = self._u8(pat + pi)
                if b == 0xFC:                    # enable +param
                    pi += 2
                    b = self._u8(pat + pi)
                if b == 0xFB:                    # gate clear +param
                    pi += 2
                    b = self._u8(pat + pi)
                if 0xE0 <= b <= 0xFA:            # REST, holds (b-$E1) frames
                    events.append(dict(kind='rest', frames=(b - 0xE1) & 0xFF))
                    pi += 1
                    continue
                if 0xC0 <= b <= 0xDF:            # instrument
                    cur_instr = (b - 0xC0 + a_transpose) & 0xFF
                    pi += 1
                    b = self._u8(pat + pi)
                if 0x80 <= b <= 0xBF:            # default duration (accumulate)
                    cur_dur = (b - 0x81) & 0xFF
                    pi += 1
                    b = self._u8(pat + pi)
                    while 0x80 <= b <= 0xBF:
                        cur_dur = (cur_dur + (b - 0x80)) & 0xFF
                        pi += 1
                        b = self._u8(pat + pi)
                if 0x60 <= b <= 0x7F:            # arp/vib param
                    pi += 1
                    b = self._u8(pat + pi)
                if b >= 0x60:                    # not a note after all -> bail row
                    pi += 1
                    continue
                # NOTE
                note = (b + note_transpose) & 0xFF
                events.append(dict(kind='note', frames=(cur_dur + 1) & 0xFF,
                                   note=note, instr=cur_instr,
                                   freq=self._freq(note)))
                pi += 1
            oi += 1
        return events

    def p106b(self):
        """The groove/tempo divisor ($106B), read from the subtune table (byte 0
        of the subtune*8 record). Defaults to 1 when the table isn't located."""
        if self.loc.subtune_tbl is None:
            return 1
        return self._u8(self.loc.subtune_tbl + self.subtune * 8) or 1

    def advance_schedule(self, nframes=4000):
        """The global note-advance frame schedule: the player DECs each voice's
        note-duration counter only on frames where $106F==$106B, gated by the
        $10CB reload-4 clock (derived from the play routine $125C-$1280). Returns
        a list mapping advance-tick index -> frame number."""
        p = self.p106b()
        cb = 0
        f6 = 0
        sched = []
        for fr in range(nframes):
            cb -= 1
            if cb < 0:
                cb = 4
                adv = (p == f6)
            else:
                f6 -= 1
                if f6 < 0:
                    f6 = p
                adv = (p == f6)
            if adv:
                sched.append(fr)
        return sched

    def voice_onsets(self, v, sched=None):
        """-> [(onset_frame, note_index)] for retriggered notes, mapped through
        the groove clock (advance-tick -> real frame)."""
        if sched is None:
            sched = self.advance_schedule()
        tick = 0
        out = []
        for e in self.decode_voice(v):
            if e['kind'] == 'note' and tick < len(sched):
                out.append((sched[tick], e['note']))
            tick += e['frames']
        return out
