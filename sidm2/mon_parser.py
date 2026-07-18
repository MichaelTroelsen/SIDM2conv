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
    rest: bool = False     # Supremacy top-level $E0-$FE: silence ($F0=$FF) for `dur` ticks
    slide: tuple = None    # Supremacy $FD (after an instr/dur prefix): (speed, target_note)
    tie: bool = False      # Supremacy $FB after the PREVIOUS event: this note skips the
                           # instrument/gate restart ($12C5 branch), and the previous
                           # note's gate-off is suppressed ($1155 check on $100A,X)


class MON:
    """Decoded MoN song for one subtune."""

    def __init__(self, d, la, subtune=0):
        self.d, self.la = d, la
        self.note_base = 0
        self.tempo_toggle = False
        self._locate()
        self.subtune = subtune
        if getattr(self, "ol_mode", None) == "supremacy":
            # per-subtune tables are stride-8 (subtune*8). The speed byte's $80 bit is a
            # SWING-TEMPO flag (see tick_to_frame); note base is a SIGNED byte added to notes.
            raw = self._u8(self.tbl_speed + subtune * 8)
            self.speed = raw & 0x7F
            self.tempo_toggle = bool(raw & 0x80)
            b = self._u8(self.tbl_base + subtune * 8)
            self.note_base = b - 256 if b >= 0x80 else b
        else:
            # B1-indirect (see _locate_b1): speed is one shared reload byte, not a
            # per-subtune table -> read it directly, ignore the subtune offset.
            off = 0 if getattr(self, "_speed_fixed", False) else subtune
            self.speed = self._u8(self.tbl_speed + off)
        self.song_loop_ticks = 0
        self._ol_loop_ticks = {}
        self.voices = [self._voice(v) for v in range(3)]
        if self._ol_loop_ticks:
            # Supremacy $00 orderlist marker = GLOBAL song loop: the first voice
            # to reach one restarts ALL orderlists. Cut every voice's one-pass
            # decode at the earliest mark (else the parser overruns into the
            # overlapping shared-tail orderlist bytes — sub1's tails alias V0+4).
            self.song_loop_ticks = min(self._ol_loop_ticks.values())
            self.voices = [self._voice(v) for v in range(3)]

    @property
    def frames_per_tick(self):
        """The tempo gate (DEC $9116; reload $7AFE on <0; CMP $7AFE) fires the
        sequencer once every speed+1 frames. For swing tunes (tempo_toggle) this
        is only the LONG period — use tick_to_frame for exact frame positions."""
        return self.speed + 1

    def tick_to_frame(self, ticks):
        """Cumulative sequencer ticks -> exact frame offset from the first tick.

        Constant tempo: one tick every speed+1 frames. Swing tempo (Supremacy
        speed byte bit7, RE'd from the $1128-$114D gate: the reload toggles $E2
        via EOR #$FF and picks speed-1 on the negative phase): tick periods
        ALTERNATE speed, speed+1, speed, ... — e.g. Supremacy sub2 speed=2
        alternates 2,3 frames (avg 2.5), which the old constant speed+1 model
        got 20% wrong (the whats-next.md ~9-frame note-length drift).
        """
        if not self.tempo_toggle:
            return ticks * (self.speed + 1)
        pair = 2 * self.speed + 1                 # one short + one long period
        return pair * (ticks // 2) + self.speed * (ticks % 2)

    def frame_to_tick(self, frame):
        """Smallest tick T with tick_to_frame(T) >= frame (ceil — the first
        sequencer tick at or after a frame position; used for window/lead math)."""
        if frame <= 0:
            return 0
        if not self.tempo_toggle:
            return (frame + self.speed) // (self.speed + 1)
        pair = 2 * self.speed + 1
        k, r = divmod(frame, pair)
        if r == 0:
            return 2 * k
        return 2 * k + (1 if r <= self.speed else 2)

    @property
    def onset_delay(self):
        """Constant frames between a sequencer tick and its SID output (the engine
        writes registers in the OUTPUT phase after the sequencer). Supremacy's play
        runs output BEFORE the sequencer -> +2; the Hawkeye/Cybernoid engine
        validated at 0 (mon_validate offset 0, native builds byte-exact)."""
        return 2 if getattr(self, "ol_mode", None) == "supremacy" else 0

    # -- memory access (absolute SID addresses) --
    def _u8(self, a):
        o = a - self.la
        return self.d[o] if 0 <= o < len(self.d) else 0xFF

    def _u16(self, a):
        return self._u8(a) | (self._u8(a + 1) << 8)

    # -- table location (relocation-safe via player-code signatures) --
    def _locate(self):
        d = self.d
        if self._locate_supremacy(d):           # distinct flat variant -> its own path
            return
        # orderlist-ptr-set table-index $83FC: `LDA $83fc,X (BD FC 83); STA $7b6b
        #   (8D 6B 7B); LDY #5 (A0 05)`. Then `LDA $7b2c,Y (B9 2C 7B); STA $8403,Y
        #   (99 03 84)` -> the orderlist-ptr SETS live at page = $7b2c's hi byte.
        # The subtune setup self-modifies a 6-byte 'set' source pointer (3 orderlist-ptr
        # lo + 3 hi) then copies it to the live OL pointers (`LDY #5; LDA setSrc,Y; STA
        # setDst,Y`). setSrc's LOW byte comes from a per-subtune index table (loTab); its
        # HIGH byte is either a 2nd table (hiTab — Cybernoid) or FIXED (Hawkeye). Resolve
        # both by finding which `LDA tab,X; STA m` self-modify writes the B9 operand bytes.
        self.ol_mode, self.tbl_olptr_hi = "selfmod", None
        cp = _find(d, 0xA0, 0x05, 0xB9, None, None, 0x99)
        cp_bd = _find(d, 0xA0, 0x05, 0xBD, None, None, 0x99)
        if cp is not None:
            ss_lo = self.la + cp + 3            # C64 addr of the B9 set-source lo operand
            self.olset_hi = d[cp + 4]           # default (fixed) high byte
            lo_sm = _find(d, 0xBD, None, None, 0x8D, ss_lo & 0xFF, (ss_lo >> 8) & 0xFF)
            self.tbl_olptr = (d[lo_sm + 1] | (d[lo_sm + 2] << 8)) if lo_sm is not None else 0x83FC
            hi_sm = _find(d, 0xBD, None, None, 0x8D, (ss_lo + 1) & 0xFF, ((ss_lo + 1) >> 8) & 0xFF)
            self.tbl_olptr_hi = (d[hi_sm + 1] | (d[hi_sm + 2] << 8)) if hi_sm is not None else None
        elif cp_bd is not None:
            # STRIDE-INDEX variant (Cybernoid_II): `...; (ASL A)^n; TAX; LDY #5;
            # LDA olBase,X; STA setDst,Y` — X = subtune*stride+5, so the 6-byte OL set for
            # a subtune is olBase + subtune*stride (stride = 2^(#ASL before the copy)).
            self.ol_mode = "stride"
            self.ol_base = d[cp_bd + 3] | (d[cp_bd + 4] << 8)
            n_asl = sum(1 for k in range(max(0, cp_bd - 12), cp_bd) if d[k] == 0x0A)
            self.ol_stride = 1 << n_asl if n_asl else 1
            self.tbl_olptr, self.olset_hi = self.ol_base, 0x00
        elif self._locate_b1(d):                # B1-indirect variant (Tel mainstream)
            self.olset_hi = None                # olset from tbl_olptr_hi, not a fixed byte
        else:
            self.tbl_olptr, self.olset_hi = 0x83FC, 0x7B
        # speed table: `LDA speedTab,X; STA speedReload`. The tables (speed + olptr lo/hi
        # + others) sit in one small per-subtune block; the speed table is the lowest of
        # the setup's `LDA tab,X` reads. Anchor on the min of (loTab, hiTab) minus the
        # observed gap, but locate it directly when possible (below) for robustness.
        self.tbl_speed = self._find_speed_tbl(d)
        if getattr(self, "_b1_speed_addr", None) is not None:
            self.tbl_speed = self._b1_speed_addr    # B1: single reload byte (LDA abs)
        # pattern-pointer table: `ASL A (0A); TAY (A8); LDA tab,Y (B9 ..); STA zp (85 ..)`.
        # The STA zp byte is engine-relocation-specific (Hawkeye $FD, Cybernoid $BD), so
        # don't pin it; take the FIRST such read (the orderlist->pattern one).
        po = _find(d, 0x0A, 0xA8, 0xB9, None, None, 0x85, None)
        self.tbl_pat = (d[po + 3] | (d[po + 4] << 8)) if po is not None else 0x8409
        if getattr(self, "_tel", False):
            self._locate_b1_row_variant(d, po)
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
        if getattr(self, "_b1_freq", None) is not None:   # B1: split tables read `85`/`8D`
            self.tbl_freq, self.tbl_freq_hi = self._b1_freq
        # instrument-record table $860C: the note handler reads AD via
        #   `LDA $860e,X (BD 0E 86); STA $d405,Y (99 05 D4)`. $860E is record+2 (AD),
        #   so the 8-byte-record base = operand - 2.
        io = _find(d, 0xBD, None, None, 0x99, 0x05, 0xD4)
        self.tbl_instr = ((d[io + 1] | (d[io + 2] << 8)) - 2) if io is not None else 0x860C
        if getattr(self, "_tel", False):
            self._locate_tel_instr_fields(d, io)

    def _locate_b1(self, d):
        """MoN 'B1-indirect' variant (mainstream Jeroen Tel: Alloyrun, Beginning,
        Scout, Zynon_Zak, ...). The subtune setup copies the 6-byte OL-pointer set
        via an INDIRECT source `LDY #5; LDA ($zp),Y; STA live,Y` (opcode B1), with
        $zp/$zp+1 fed from per-subtune tables just before the copy
        (`LDA loTab,X; STA $zp` / `LDA hiTab,X; STA $zp+1`). This reuses the selfmod
        `_orderlist_ptr` formula (tbl_olptr=loTab, tbl_olptr_hi=hiTab): the copy is
        a verbatim 6-byte move, so reading the SOURCE set == reading the live copy.

        MISS-ONLY: `_locate` calls this only after the B9/BD copy loops miss, and it
        REQUIRES both feeders + the freq split to resolve in-image, so a stray
        `A0 05 B1 .. 99` byte run in another variant's DATA (Hawkeye has one) is
        rejected and falls through to the $83FC default. Returns True on success.

        freq is a SPLIT lo/hi table (~$60 apart) read as `TAY; LDA loTab,Y; <store>;
        LDA hiTab,Y`; the store is `85` (zp) or `8D` (abs), so the Hawkeye
        A8-B9-9D freq signature misses -> overridden via self._b1_freq. speed is a
        single reload byte loaded DIRECTLY (LDA abs) by the tempo gate
        (`DEC cnt; BPL; LDA reload; STA cnt`), not a per-subtune table -> stashed in
        self._b1_speed_addr and read subtune-independently (see __init__)."""
        inimg = lambda a: self.la <= a < self.la + len(d)
        cp = zp = None
        for i in range(len(d) - 7):
            if d[i] == 0xA0 and d[i+1] == 0x05 and d[i+2] == 0xB1 and d[i+4] == 0x99:
                cp, zp = i, d[i+3]
                break
        if cp is None:
            return False
        # feeders `BD loTab,X; STA $zp` / `BD hiTab,X; STA $zp+1` just before the copy
        tbl_lo = tbl_hi = None
        for i in range(cp - 1, max(0, cp - 24), -1):
            if d[i] == 0xBD and d[i+3] == 0x85:
                if d[i+4] == zp and tbl_lo is None:
                    tbl_lo = d[i+1] | (d[i+2] << 8)
                elif d[i+4] == ((zp + 1) & 0xFF) and tbl_hi is None:
                    tbl_hi = d[i+1] | (d[i+2] << 8)
        if tbl_lo is None or tbl_hi is None or not (inimg(tbl_lo) and inimg(tbl_hi)):
            return False
        # freq split: `TAY; LDA loTab,Y; <store 2-3b>; LDA hiTab,Y`, tables ~$60 apart
        freq = None
        for i in range(len(d) - 9):
            if d[i] == 0xA8 and d[i+1] == 0xB9:
                lo = d[i+2] | (d[i+3] << 8)
                for j in (i + 5, i + 6, i + 7):
                    if j + 2 < len(d) and d[j] == 0xB9:
                        hi = d[j+1] | (d[j+2] << 8)
                        if inimg(lo) and inimg(hi) and 0x30 <= hi - lo <= 0x90:
                            freq = (lo, hi)
                            break
                if freq:
                    break
        if freq is None:
            return False
        # speed: tempo gate `DEC cnt; BPL; LDA reload(abs); STA cnt`
        for i in range(len(d) - 2):
            if d[i] != 0xCE:
                continue
            cnt = d[i+1] | (d[i+2] << 8)
            if not inimg(cnt):
                continue
            for j in range(i + 3, min(i + 14, len(d) - 5)):
                if (d[j] == 0xAD and d[j+3] == 0x8D
                        and (d[j+4] | (d[j+5] << 8)) == cnt):
                    self._b1_speed_addr = d[j+1] | (d[j+2] << 8)
                    break
            if getattr(self, "_b1_speed_addr", None) is not None:
                break
        if getattr(self, "_b1_speed_addr", None) is None:
            return False                         # no locatable speed -> don't claim it
        self.tbl_olptr, self.tbl_olptr_hi = tbl_lo, tbl_hi
        self._b1_freq = freq
        self._speed_fixed = True
        self._tel = True                         # use the tel orderlist+row grammar
        return True

    def _locate_b1_row_variant(self, d, po):
        """B1 'tel' generation: some compiles extend the base orderlist/row grammar
        (05-09-87-style) with per-file dispatch quirks. Detected structurally (never
        assumed) so files without these bytes are provably untouched:

        REPEAT op (orderlist $40-$7F, disassembled from Alloyrun $E127-$E137 and
        confirmed byte-identical in Scout's dispatch -- Scout is one of the 6 EXACT
        wins, so this code path is proven safe/inert when a song's orderlist never
        emits a $40-$7F byte): `AND #$40; BEQ ..; AND #$3F; STA,X reload` sets a
        per-voice repeat counter = byte&$3F; the pattern selected by the NEXT
        orderlist byte then replays (repeat+1) times before the orderlist advances
        (disassembled at $E210-$E22B: DEC the counter each pattern-end, BPL -> redo).

        PATTERN-INDEX off-by-one (Alloyrun only, $E13A: SEC;SBC#$01 before the
        ASL/TAY table index): this compile's orderlist pattern numbers are 1-based.

        CLASSIC ROW grammar (Alloyrun/Starball only, disassembled at Alloyrun
        $E182-$E19A): instead of the simple ctrl-byte-encodes-length grammar, the
        row byte stream is dispatched through the SAME $8x-duration/$Cx-instrument/
        $Ex-command chain already implemented (and Hawkeye/Cybernoid-validated) in
        `_pattern` -- reuse it rather than re-deriving it.

        ROW-CTRL off-by-one (Bantam only, disassembled $80E3-$80F9): unlike Scout's
        identically-shaped simple grammar (raw ctrl AND #$7F for length, raw ctrl's
        bit7 tested for the instrument-command branch), Bantam's compile does
        `SEC;SBC#$01` on the ctrl byte BEFORE both the length mask and the bit7
        test -- so its instrument-command threshold is raw-ctrl>=$81, one higher
        than every other compile in the bucket.

        ROW LENGTH MASK (read directly from each file's own `AND #imm` operand,
        not assumed): 05-09-87 masks `$1F` (5-bit length); Zynon_Zak's otherwise
        byte-identical dispatch ($C098: `AND #$3F`, disassembled) masks `$3F`
        (6-bit) -- a strictly WIDER mask is safe to read even for files that don't
        need it (any length under the old mask decodes identically; the old $1F
        default was silently wrapping any real length >=32 into a bogus value),
        so this is read for every non-classic file rather than gated to one."""
        self._tel_repeat = False
        self._tel_pat_off1 = False
        self._tel_classic_row = False
        self._tel_row_ctrl_off1 = False
        self._tel_row_len_mask = 0x1F
        if po is None:
            return
        pre = d[max(0, po - 40):po]
        i40 = pre.find(bytes([0x29, 0x40]))
        if i40 != -1 and i40 + 2 < len(pre) and pre[i40 + 2] == 0xF0:
            i3f = pre.find(bytes([0x29, 0x3F]), i40)
            if i3f != -1 and i3f + 2 < len(pre) and pre[i3f + 2] == 0x9D:
                self._tel_repeat = True
        self._tel_pat_off1 = po >= 3 and d[po - 3:po] == bytes([0x38, 0xE9, 0x01])
        row = bytes(d[po:po + 220])
        if (row.find(bytes([0x29, 0xE0, 0xC9, 0xC0])) != -1
                or row.find(bytes([0x29, 0xC0, 0xC9, 0x80])) != -1):
            self._tel_classic_row = True
        elif po >= 6:
            # locate the row-ctrl fetch: the FIRST `B1 zp` (same zp the tbl_pat
            # lookup stored to, d[po+6]) after po, then check the ~20 bytes after
            # it for a SEC;SBC#$01 preceding the first AND #imm (the length mask).
            zp = d[po + 6]
            cf = None
            for i in range(po, min(po + 80, len(d) - 1)):
                if d[i] == 0xB1 and d[i + 1] == zp:
                    cf = i
                    break
            if cf is not None:
                win = d[cf:cf + 24]
                ai = next((i for i in range(len(win) - 1) if win[i] == 0x29), None)
                if ai is not None and ai + 1 < len(win):
                    self._tel_row_len_mask = win[ai + 1]
                    if bytes(win[:ai]).find(bytes([0x38, 0xE9, 0x01])) != -1:
                        self._tel_row_ctrl_off1 = True

    def _locate_tel_instr_fields(self, d, ad_io):
        """B1-tel instrument table shape check (disassembled from Tel_1, whose
        onsets were badly wrong despite an otherwise byte-for-byte 05-09-87-style
        grammar): the shared `tbl_instr` locate assumes ROW-MAJOR 8-byte records
        (Hawkeye/Cybernoid), but Tel_1's actual layout is COLUMN-major -- separate
        parallel arrays for pulse-lo/hi ($D402/$D403), waveform ($D404), AD
        ($D405), SR ($D406), each indexed DIRECTLY by instrument number (no *8),
        e.g. `LDA $1520,X; STA $D404,Y` / `LDA $1525,X; STA $D405,Y` five bytes
        apart. `_silent_instr`'s row-major guess silently reads the WRONG bytes
        for such files -- Tel_1's instrument 0 (the padding/rest slot used
        throughout its orderlists) tested non-silent, so the parser emitted
        phantom onsets the pattern never intended. Locate the real waveform/AD/SR
        array bases by searching NEAR the already-confirmed AD site (`ad_io`,
        same anchor `tbl_instr` uses) rather than a blind file-first `_find` (a
        stray unrelated `BD..99 0N D4` elsewhere in the file is not rare enough to
        risk -- caught two false positives this way, Orion_Intro/Chrome_Met1,
        where the "near" window still snagged an unrelated D404 write; REQUIRE
        `ad-wf == sr-ad` too, the evenly-spaced-column signature every genuine
        match showed, before trusting it). Only wires in when all three are found
        AND evenly spaced; `_silent_instr` falls back to the row-major guess
        otherwise (Hawkeye/Cybernoid never hit this path -- `_tel` is B1-only)."""
        self._tel_instr_fields = None
        if ad_io is None:
            return
        def near(reg):
            lo, hi = max(0, ad_io - 80), min(len(d) - 3, ad_io + 80)
            for i in range(lo, hi):
                if d[i] != 0xBD:
                    continue
                for gap in range(3, 7):
                    j = i + gap
                    if j + 3 <= len(d) and d[j] == 0x99 and d[j + 1] == reg and d[j + 2] == 0xD4:
                        return d[i + 1] | (d[i + 2] << 8)
            return None
        ad = d[ad_io + 1] | (d[ad_io + 2] << 8)
        wf, sr = near(0x04), near(0x06)
        if wf is None or sr is None or ad - wf != sr - ad or ad <= wf:
            return
        fields = [wf, ad, sr]
        stride = ad - wf
        pl, ph = near(0x02), near(0x03)
        if ph is not None and wf - ph == stride:
            fields.append(ph)
            if pl is not None and ph - pl == stride:
                fields.append(pl)
        self._tel_instr_fields = fields

    def _locate_supremacy(self, d):
        """Detect + locate the SUPREMACY variant (a flat MoN player, play=$1003, no
        relocation). It has a distinctive per-(subtune,voice) orderlist pointer table
        (indexed subtune*8 + voice*2) and a note = pattern_byte + transpose + subtune_base
        formula. Relocation-safe signatures (see memory/myth-supremacy-mon-re.md):
          orderlist: `TXA;ASL;ADC selfmodIdx;TAY;LDA olptr,Y;STA $E0`
                     = 8A 0A 6D ?? ?? A8 B9 <olptr> 85 E0
          freq:      `TAY;LDA freqLo,Y;STA zp,X;LDA freqHi,Y;STA zp,X`
                     = A8 B9 <lo> 95 ?? B9 <hi> 95
          base:      `STA idx;TAY;LDA baseTab,Y;STA ...` = 8D ?? ?? A8 B9 <base> 8D
          pattern:   `LDA patLo,Y;STA $E0;LDA patHi,Y;STA $E1` where patHi != patLo+1
                     = B9 <lo> 85 E0 B9 <hi> 85 E1 (split tables)."""
        ol = _find(d, 0x8A, 0x0A, 0x6D, None, None, 0xA8, 0xB9, None, None, 0x85, 0xE0)
        if ol is None:
            return False
        self.ol_mode = "supremacy"
        self.tbl_olptr = d[ol + 7] | (d[ol + 8] << 8)          # $16DC
        fr = _find(d, 0xA8, 0xB9, None, None, 0x95, None, 0xB9, None, None, 0x95)
        self.tbl_freq = (d[fr + 2] | (d[fr + 3] << 8)) if fr is not None else 0x1644
        self.tbl_freq_hi = (d[fr + 7] | (d[fr + 8] << 8)) if fr is not None else 0x168A
        bs = _find(d, 0x8D, None, None, 0xA8, 0xB9, None, None, 0x8D)
        self.tbl_base = (d[bs + 5] | (d[bs + 6] << 8)) if bs is not None else 0x16E3
        self.tbl_speed = self.tbl_base - 1                     # $16E2 (speed table, stride 8)
        # pattern-ptr SPLIT tables: the B9..$E0 / B9..$E1 pair whose two operands are NOT
        # consecutive (the orderlist pair is lo/lo+1; the pattern pair is separate tables).
        self.tbl_pat_lo, self.tbl_pat_hi = 0x16F3, 0x171C
        for i in range(len(d) - 9):
            if (d[i] == 0xB9 and d[i + 3] == 0x85 and d[i + 4] == 0xE0
                    and d[i + 5] == 0xB9 and d[i + 8] == 0x85 and d[i + 9] == 0xE1):
                lo = d[i + 1] | (d[i + 2] << 8)
                hi = d[i + 6] | (d[i + 7] << 8)
                if hi != lo + 1:                               # split -> pattern table
                    self.tbl_pat_lo, self.tbl_pat_hi = lo, hi
                    break
        # instrument table: the note handler reads the control byte via
        #   `LDA instrTab,Y (B9 ..); STA $104F,X (9D 4F 10)` (Y = instr*7). 7-byte records:
        #   [0]=ctrl/$D404, [1]=AD/$D405, [2]=SR/$D406, [3]=pw (&$0F -> $D403 hi).
        it = _find(d, 0xB9, None, None, 0x9D, 0x4F, 0x10)
        self.tbl_instr = (d[it + 1] | (d[it + 2] << 8)) if it is not None else 0x1869
        self.instr_stride = 7
        # arp / wave-program table (Stage-B pitch): the $60-$7F pattern byte -> $1064
        # index; the engine does `LDA $1064,X; TAY; LDA idxtab,Y; CLC; ADC #baseoff;
        # STA $E0; LDA #basehi` -> program = arp_base + idxtab[wprog]. Each program is
        # [duration][signed semitone steps...][$ff loop | $fe end]; the step value is
        # ADDed to the note ($106D + $F0 -> freq lookup) so it is a pitch-independent arp.
        ap = _find(d, 0xBD, 0x64, 0x10, 0xA8, 0xB9, None, None, 0x18, 0x69,
                   None, 0x85, 0xE0, 0xA9)
        if ap is not None:
            self.tbl_arp_idx = d[ap + 5] | (d[ap + 6] << 8)
            self.tbl_arp_base = (d[ap + 13] << 8) | d[ap + 9]
        else:
            self.tbl_arp_idx, self.tbl_arp_base = 0x1746, 0x17C0
        return True

    def arp_program(self, wprog):
        """Supremacy arp/wave-program (Stage-B): the compact LOOPING SEMITONE table the
        $60-$7F pattern byte selects. Returns {'dur','steps','loop'} where `steps` are the
        signed semitone offsets added to the note each step (pitch-independent -> ~16
        programs total, byte-exact from ROM, vs the trace's per-pitch Hz-offset explosion).
        See memory/myth-supremacy-mon-re.md (arp engine $15CB, table $1746/$17C0)."""
        if getattr(self, "ol_mode", None) != "supremacy":
            return None
        idx = self._u8(self.tbl_arp_idx + (wprog & 0x1F))
        addr = self.tbl_arp_base + idx
        dur = self._u8(addr)
        steps, i = [], addr + 1
        while len(steps) <= 32:
            b = self._u8(i)
            if b in (0xFF, 0xFE):
                return {"dur": dur, "steps": steps, "loop": b == 0xFF}
            steps.append(b - 256 if b >= 128 else b)
            i += 1
        return {"dur": dur, "steps": steps, "loop": False}

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
                    # the reload VALUE is the nearest `LDA abs` before this STA — between
                    # the DEC and STA (Hawkeye) OR just ahead of the DEC (Cybernoid_II
                    # loads it pre-DEC). Then the setup `LDA speedTab,X; STA reload` gives
                    # the table.
                    for k in range(j - 1, max(0, j - 18), -1):
                        if d[k] == 0xAD:
                            rl = d[k + 1] | (d[k + 2] << 8)
                            sm = _find(d, 0xBD, None, None, 0x8D, rl & 0xFF, (rl >> 8) & 0xFF)
                            if sm is not None:
                                return d[sm + 1] | (d[sm + 2] << 8)
                            break
                    break
        return self.tbl_olptr - 7

    # -- orderlist pointers for this subtune --
    def _orderlist_ptr(self, voice):
        if self.ol_mode == "supremacy":                     # per-(subtune,voice) ptr table
            return self._u16(self.tbl_olptr + self.subtune * 8 + voice * 2)
        if self.ol_mode == "stride":                        # Cybernoid_II: olBase+sub*stride
            setaddr = self.ol_base + self.subtune * self.ol_stride
        else:
            lo = self._u8(self.tbl_olptr + self.subtune)    # per-subtune set-source lo
            hi = (self._u8(self.tbl_olptr_hi + self.subtune)  # ...hi from a 2nd table, or
                  if self.tbl_olptr_hi else self.olset_hi)  # the fixed high byte (Hawkeye)
            setaddr = (hi << 8) | lo                        # the 6-byte OL-pointer set
        return self._u8(setaddr + voice) | (self._u8(setaddr + 3 + voice) << 8)

    # -- decode one voice (orderlist -> patterns -> events) --
    def _voice(self, voice):
        """Flat event list for the whole voice (all patterns concatenated)."""
        return [ev for _pat, blk in self._voice_blocks(voice) for ev in blk]

    def _voice_blocks_tel(self, voice):
        """B1 'tel' generation (see _locate_b1) orderlist + row grammar, RE'd from
        the player's own dispatch (orderlist advance $105F; pattern read $1093).
        DISTINCT from the Hawkeye/Cyb grammar:
          ORDERLIST: byte bit7 set -> transpose = byte & $1F (per voice, `AND #$1F;
            STA $1735,X`); byte < $80 -> pattern index (ASL -> tbl_pat); $FF/$FE end.
            Some compiles ALSO have bit6 set ($40-$7F, no bit7) -> REPEAT: the NEXT
            pattern plays (byte&$3F)+1 times before the orderlist advances (see
            `_locate_b1_row_variant`; gated so files without the dispatch code are
            untouched). One compile (Alloyrun) 1-base-indexes patterns (-1 before
            the table lookup); also gated.
          PATTERN ROW (default/"simple"): ctrl -> length = (ctrl & $1F) + 1 ticks.
            ctrl bit6 set -> GATE-OFF/rest (`BVS`; DEC gate-mask; NO note, NO
            command byte; 1 byte). Else ctrl bit7 set -> one INSTRUMENT command
            byte precedes the note (`BPL` skips it); then a NOTE byte = raw +
            transpose -> the split freq tables. $FF -> pattern end. Notes are
            RAW+transpose (no note_base). Some compiles (Alloyrun/Starball) use the
            richer $8x-duration/$Cx-instrument/$Ex-command chain instead -- already
            implemented (and Hawkeye/Cybernoid-validated) as `_pattern`; reused
            verbatim when `_locate_b1_row_variant` detects that dispatch code. One
            compile (Bantam) applies `SEC;SBC#$01` to ctrl before the length mask
            AND the bit7 test (shifting the instrument-command threshold); also
            gated (`_tel_row_ctrl_off1`)."""
        ol = self._orderlist_ptr(voice)
        transpose, instr, repeat = 0, 0, 1
        st = {'transpose': 0, 'instr_base': 0, 'instr': 0, 'stored': 0, 'wprog': 0}
        classic = getattr(self, "_tel_classic_row", False)
        row_off1 = getattr(self, "_tel_row_ctrl_off1", False)
        row_mask = getattr(self, "_tel_row_len_mask", 0x1F)
        blocks = []
        i = guard = 0
        while guard < 2048:
            guard += 1
            b = self._u8(ol + i); i += 1
            if b in (0xFF, 0xFE):               # orderlist end (one pass)
                break
            if b & 0x80:                        # transpose command ($1735,X = b & $1F)
                transpose = st['transpose'] = b & 0x1F
                continue
            if getattr(self, "_tel_repeat", False) and (b & 0x40):  # $40-$7F: repeat
                repeat = (b & 0x3F) + 1                             # the NEXT pattern
                continue
            idx = ((b - 1) & 0xFF) if getattr(self, "_tel_pat_off1", False) else b
            for _ in range(repeat):
                blk = []
                if classic:
                    self._pattern(idx, st, blk)
                else:
                    pp = self._u16(self.tbl_pat + idx * 2)
                    j = pg = 0
                    while pg < 1024:
                        pg += 1
                        ctrl = self._u8(pp + j); j += 1
                        if ctrl == 0xFF:                # pattern terminator (checked pre-adjust)
                            break
                        if row_off1:                     # Bantam: length/bit7 test the ctrl-1'd
                            ctrl = (ctrl - 1) & 0xFF      # value, not the raw byte (see
                                                          # _locate_b1_row_variant)
                        length = (ctrl & row_mask) + 1  # mask read from this file's own
                                                          # code (_locate_b1_row_variant)
                        if ctrl & 0x40:                 # bit6: gate-off / rest (no note byte)
                            blk.append(MONEvent(note=-1, dur=length, instr=instr,
                                                retrig=False, rest=True))
                            continue
                        if ctrl & 0x80:                 # bit7: instrument command byte precedes note
                            instr = self._u8(pp + j); j += 1
                        note = self._u8(pp + j); j += 1
                        if note == 0xFF:
                            break
                        retrig = not self._silent_instr(instr)  # instr 0 = rest slot
                        blk.append(MONEvent(note=(note + transpose) & 0x7F, dur=length,
                                            instr=instr, retrig=retrig))
                if blk:
                    blocks.append((b, blk))
            repeat = 1
        return blocks

    def _voice_blocks(self, voice):
        """Walk the orderlist -> [(pattern_number, [MONEvent, ...]), ...], one block
        per orderlist pattern entry. The per-voice state PERSISTS across blocks
        (mirrors the player's per-voice RAM): transpose ($90F9), instrument base
        ($9139), current instrument ($90DA), wave-program, and the sticky stored
        duration $90CE — so identical pattern numbers under different transposes
        decode to different events (the caller dedups by the resulting rows)."""
        if getattr(self, "_tel", False):        # B1 'tel' generation -> its own grammar
            return self._voice_blocks_tel(voice)
        ol = self._orderlist_ptr(voice)
        st = {'transpose': 0, 'instr_base': 0, 'instr': 0, 'stored': 0, 'wprog': 0}
        blocks = []
        if self.ol_mode == "supremacy":
            i, guard, repeat = 0, 0, 1
            while guard < 1024:
                guard += 1
                b = self._u8(ol + i); i += 1
                if b == 0xFE:                       # $FE = GLOBAL song HALT ($11DD ->
                    self._ol_loop_ticks[voice] = sum(   # $117B zeroes freqs + gates
                        ev.dur for _p, bl in blocks     # play off) — the FIRST voice
                        for ev in bl)                   # to reach it stops the song,
                    break                               # so cut all voices there too
                if b == 0xFF:                       # loop marker (one pass)
                    break
                if b == 0x00:                       # $11CD: an orderlist step starting
                    self._ol_loop_ticks[voice] = sum(   # with $00 = GLOBAL SONG LOOP —
                        ev.dur for _p, bl in blocks     # ALL voices' positions reset
                        for ev in bl)                   # ($11CF-$11D6 STY $E9/$EA/$EB).
                    break                           # The parser stops; __init__ cuts
                                                    # every voice at the EARLIEST mark.
                if b == 0xFA:                       # 2-byte command (skip 1 arg)
                    i += 1
                    continue
                if b == 0xFD:                       # 4-byte command (skip 3 args)
                    i += 3
                    continue
                if b >= 0x80:                       # transpose ($1007 = b & $7F)
                    st['transpose'] = b & 0x7F
                    continue
                if b >= 0x70:                       # $70-$7F: modifier ($100D) — no note effect
                    continue
                if b >= 0x40:                       # $40-$6F: repeat next pattern N+1 times
                    repeat = (b & 0x1F) + 1
                    continue
                for _ in range(repeat):             # b < $40 = pattern index
                    blk = []
                    self._pattern(b, st, blk)
                    blocks.append((b, blk))
                repeat = 1
            return self._clip_to_song_loop(blocks)
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

    def _clip_to_song_loop(self, blocks):
        """Truncate a voice's decoded blocks at the GLOBAL song-loop tick (the
        earliest $00 orderlist marker across all voices — set by __init__'s
        second decode pass; 0 = no loop found = no clipping)."""
        lim = getattr(self, 'song_loop_ticks', 0)
        if not lim:
            return blocks
        from dataclasses import replace
        out, tk = [], 0
        for pat, blk in blocks:
            nb = []
            for ev in blk:
                if tk >= lim:
                    break
                if tk + ev.dur > lim:
                    ev = replace(ev, dur=lim - tk)
                nb.append(ev)
                tk += ev.dur
            if nb:
                out.append((pat, nb))
            if tk >= lim:
                break
        return out

    def _emit(self, events, raw, st, retrig):
        note = (raw + st['transpose'] + self.note_base) & 0x7F
        tie = st.pop('pending_tie', False)      # $FB after the previous event ($12C5:
        # Instrument 0 in MoN is the REST/silent slot: its 8-byte record is all
        # zero (verified across Hawkeye/Cybernoid/Cybernoid_II/Double_Dragon), so
        # a zero SID voice (waveform 0, no envelope) makes no sound on real
        # hardware -- siddump shows NO fresh onset for it. An event on such an
        # instrument is a REST, not a retriggered note; marking it non-retrig
        # keeps it out of the onset comparison (it stays an event so durations/
        # timing are preserved, and the SF2 renders it via the same silent
        # instrument). This is what let Double_Dragon's 8x-instr0 intro read as
        # notes; the real V0 is silent until frame 340.
        if retrig and not tie and self._silent_instr(st['instr']):
            retrig = False
        events.append(MONEvent(note=note, dur=st['stored'] + 1, instr=st['instr'],
                               wprog=st['wprog'], retrig=retrig and not tie, tie=tie))
        st['dur_acc'] = 0                       # finalize resets the $F3 accumulator

    def _silent_instr(self, i):
        """True if instrument i's record is entirely zero (the MoN rest slot -- a
        voice it drives produces no sound). Cached. Hawkeye/Cybernoid-style tables
        are row-major (8-byte records, `tbl_instr + i*8`); several B1-tel compiles
        (disassembled from Tel_1) are COLUMN-major instead -- 3-5 separate
        same-length parallel arrays (waveform/AD/SR/pulse), each indexed directly
        by instrument number (`field_base + i`, no *8). `_locate_tel_instr_fields`
        locates the real field bases when this shape is detected; use them when
        available instead of assuming row-major."""
        c = self.__dict__.setdefault('_silent_cache', {})
        if i not in c:
            fields = getattr(self, "_tel_instr_fields", None)
            if fields:
                c[i] = all(self._u8(base + i) == 0 for base in fields)
            else:
                base = self.tbl_instr + (i & 0xFF) * 8
                c[i] = all(self._u8(base + k) == 0 for k in range(8))
        return c[i]

    def _pattern(self, pat, st, events):
        """Faithful emulation of the player's pattern-byte dispatch chain
        ($7C64..$7D22). One note is emitted per sequencer read; prefixes
        (filter $Fx-odd, command $Ex, slide $Cx, instrument $7x, duration
        $8x-$Bx) consume following bytes and modify state. $FF = pattern end."""
        if self.ol_mode == "supremacy":
            self._pattern_supremacy(pat, st, events)
            return
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

    def _pattern_supremacy(self, pat, st, events):
        """Supremacy PATTERN dispatch (pattern ptr from the SPLIT $16F3/$171C tables).
        NOTE: this is the PATTERN processor, distinct from the ORDERLIST processor
        ($1212, where $FD is a 4-byte command). From the $1246-$12C1 disasm, each
        EVENT is a linear prefix chain [instr]?[dur]*[wave]?[note]? — and each prefix
        handler PEEKS the next byte: if it is not a valid continuation the event
        FINALIZES at $12C1 without a new note byte, i.e. it RETRIGGERS the previous
        note ($F0,X unchanged) with the sticky duration. That retrigger is how a
        phrase plays a note 3x from only 2 note bytes (e.g. sub2 V2 `... 84 30 CE
        DF ...`: the lone `CE` sets instr $0E and retriggers note $30).
        Byte map: $FF = end; $F0-$FE = command + 1 arg (2 bytes); $C0-$DF =
        instrument prefix; $80-$BF = duration (sticky); $60-$7F = wave-program/arp
        selector; <$60 = NOTE (b + transpose + base)."""
        ptr = self._u8(self.tbl_pat_lo + pat) | (self._u8(self.tbl_pat_hi + pat) << 8)
        j, guard = 0, 0

        def retrig_last():
            if st.get('last_note_raw') is not None:
                self._emit(events, st['last_note_raw'], st, retrig=True)

        def fin():
            # ROM event EPILOGUE ($1335 — run on the note/retrig/slide finalize
            # path only; the REST handler enters at $1343 PAST this): peek the
            # next pattern byte; $FB = a 1-byte TIE flag (INC $100A,X), consumed
            # here. Effect: the NEXT note skips the instrument/gate restart
            # ($12C5) and THIS note's gate-off is suppressed ($1155). The old
            # top-level decode read it as a 27-tick REST — 27 phantom ticks per
            # $FB desynced sub0 V2 from 138.6s (freq fell to 44-85%).
            nonlocal j
            if self._u8(ptr + j) == 0xFB:
                j += 1
                st['pending_tie'] = True

        while guard < 4096:
            guard += 1
            b = self._u8(ptr + j); j += 1
            if b == 0xFF:
                break
            if b == 0xFA:                           # top-level $FA ($1212): 2-byte command
                j += 1                              #   (arg -> $10DB) — the event reader
                continue                            #   enters at $1212, so this is legal
            if b == 0xFD:                           # top-level $FD ($121F): the 4-byte
                self._slide(events, ptr, j, st)     #   SLIDE (tracer: sub1 v1 fr240,
                j += 3                              #   Y 23->27)
                fin()
                continue
            if b >= 0xE0:                           # remaining $E0+: REST ($124A — $F6 =
                dr = b & 0x1F                       #   b&$1F, $F0 = $FF, ctrl/AD/SR zeroed).
                if dr:                              #   Silence for b&$1F ticks (tracer:
                    st['stored'] = dr - 1           #   sub1 v2 fr800, $F0 = 16 ticks);
                    st['dur_acc'] = 0               #   also updates the sticky duration.
                    events.append(MONEvent(
                        note=0, dur=dr, instr=st['instr'],
                        wprog=st['wprog'], retrig=False, rest=True))
                continue
            if b >= 0xC0:                           # instrument select ($1263)
                st['instr'] = (b & 0x1F) + st['instr_base']
                peek = self._u8(ptr + j)
                # $127D-$1283: next byte $FD = the 4-byte SLIDE; other >= $C0 =
                # finalize -> the event ends WITHOUT a note byte = retrigger the
                # previous note. $FF INCLUDED (event-tracer ground truth: it
                # finalizes here, unconsumed — only a TOP-LEVEL $FF ends the pattern).
                if peek == 0xFD:
                    self._slide(events, ptr, j + 1, st)
                    j += 4
                    fin()
                elif peek >= 0xC0:
                    retrig_last()
                    fin()
                continue
            if b >= 0x80:                           # duration ($1289: ADC $F3 — ADDITIVE
                st['dur_acc'] = st.get('dur_acc', 0) + (b & 0x3F)
                # within one event: `A0 A0` = 64 ticks, event-tracer verified on
                # sub0 pattern $03; STA $F6 = the accumulated total becomes sticky)
                st['stored'] = max(st['dur_acc'], 1) - 1
                peek = self._u8(ptr + j)
                if peek == 0xFA:                    # $FA = 2 bytes (arg -> $10DB), then
                    j += 2                          #   the chain continues ($1212->$121F)
                    peek = self._u8(ptr + j)
                # $1295-$12A2: $FD = the 4-byte SLIDE; other >= $C0 = finalize ->
                # retrigger with the new duration. `A4 FF` (dur 36 + $FF) is the
                # pattern-$1C hold the fr1510 event trace shows as a real 36-tick
                # gated retrigger.
                if peek == 0xFD:
                    self._slide(events, ptr, j + 1, st)
                    j += 4
                    fin()
                elif peek >= 0xC0:
                    retrig_last()
                    fin()
                continue
            if b >= 0x60:                           # $60-$7F: wave-program / arp
                st['wprog'] = b & 0x1F              #   ($12AC: $1064 = b&$1F). NOTE is
                peek = self._u8(ptr + j)            #   strictly <$60.
                # $12B4: next byte >= $60 = finalize -> retrigger.
                if peek >= 0x60:
                    retrig_last()
                    fin()
                continue
            st['last_note_raw'] = b                 # note (b < $60)
            self._emit(events, b, st, retrig=True)
            fin()

    def _slide(self, events, ptr, j, st):
        """The $FD 4-byte SLIDE ($121F, reached as the byte AFTER an instrument or
        duration prefix): speed -> $102F, note -> $F0 (+transpose+base), target ->
        $1032 (+transpose+base), then FINALIZES at $12C1 — i.e. it IS a gated note
        trigger that glides note -> target at `speed` (event-tracer verified:
        sub1 v1 fr80 = note $33 -> target $35, speed 6, 5 bytes consumed)."""
        speed = self._u8(ptr + j)
        nb = self._u8(ptr + j + 1)
        tb = self._u8(ptr + j + 2)
        st['last_note_raw'] = nb
        self._emit(events, nb, st, retrig=True)
        events[-1].slide = (speed,
                            (tb + st['transpose'] + self.note_base) & 0x7F)

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
        if getattr(self, "ol_mode", None) == "supremacy":
            # 7-byte records at $1869: [0]=ctrl/waveform, [1]=AD, [2]=SR, [3]=pw (low nibble)
            r = [self._u8(self.tbl_instr + (idx & 0x1F) * 7 + k) for k in range(7)]
            return {
                'ad': r[1], 'sr': r[2], 'waveform': r[0],
                'pw': (r[3] & 0x0F) << 8,
                'wave_prog': 0, 'flags': 0, 'raw': r,
            }
        r = [self._u8(self.tbl_instr + (idx & 0x1F) * 8 + k) for k in range(8)]
        return {
            'ad': r[2], 'sr': r[3], 'waveform': r[1],
            'pw': (r[0] & 0x0F) << 8,
            'wave_prog': r[5] | (r[6] << 8),
            'flags': r[7], 'raw': r,
        }
