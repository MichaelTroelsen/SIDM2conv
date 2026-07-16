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
                 $6F-$7F pattern-loop count ($10DE, replay pattern n+1x),
                 $80-$FD note-transpose ($10D8, value-$82), $FE stop,
                 $FF SEGMENT-ADVANCE (segidx += seg_step / else loop).
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

STATUS (honest, 2026-07-13, blockers-1&2 fixed pass):
  * Engine map above is complete and emulation-grounded (register writes read
    off the $1904 apply routine; the full orderlist/pattern row parser is
    transcribed instruction-for-instruction from $1288-$1494 -- see _parse_row).
  * BLOCKER 1 FIXED -- top-level multi-segment orderlist. decode_voice now
    threads the $195C segment table: segidx starts subtune*8+seed, orderlist $FF
    advances it by seg_step while < seg_cap (re-selecting the segment pointer),
    else loops. Pattern-loop counts ($6F-$7F -> $10DE) replay a pattern (n+1)x.
    Result: Ding_van_Charles 17%->100% onset+pitch, After_the_War 34%->100%.
  * BLOCKER 2 FIXED -- sub-variant-robust locate. flow_offsets() flow-disasms
    from init/play; the ord/pat table scans are ANCHORED to reachable code
    (`AA BD`/`0A A8 B9`) and pin the reloc from the following ADC. Two reloc
    modes handled: Variant A "Ding-class" (`ADC reloc`) and Variant B
    "Smooth-class" (absolute pointers, reloc 0). Located 5/19 -> 10/19.
  * plausible() rejects the decodes DeenenLocate.ok() still can't see: a decode
    where one (note,frames) pair dominates a voice = reading filler (the
    Variant-B files whose reloc/groove we cannot yet pin -- Eye_to_Eye reads all
    note $06, Zamzara all $00, Constant_Runner over-loops). The builder refuses
    to emit an SF2 for an implausible decode.
  * STILL OPEN (each a separate sub-variant RE): (a) the elaborate Variant-A
    engines (B_A_T/Astro/Lord_of_the_Rings/Mr_Heli) add vibrato/porta/filter and
    a segment layout whose seed the data contradicts (pitch is byte-correct;
    onset threading is partial). (b) the Variant-B "Smooth-class" groove clock
    ($49, ~1-of-3 frames) + the reloc for the absolute-pointer files is not yet
    modelled, so those over/under-generate. See bin/deenen_validate.py.
"""
import struct

DISPATCH_SIG = bytes.fromhex('c960b0034c')      # CMP #$60 / BCS +3 / JMP

# opcode -> instruction size (bytes). Undocumented opcodes omitted (treated as
# code end during flow-disasm). Enough to walk the reachable play/init code.
_OP_SIZE = {
    0x00: 1, 0x01: 2, 0x05: 2, 0x06: 2, 0x08: 1, 0x09: 2, 0x0A: 1, 0x0D: 3,
    0x0E: 3, 0x10: 2, 0x11: 2, 0x15: 2, 0x16: 2, 0x18: 1, 0x19: 3, 0x1D: 3,
    0x1E: 3, 0x20: 3, 0x21: 2, 0x24: 2, 0x25: 2, 0x26: 2, 0x28: 1, 0x29: 2,
    0x2A: 1, 0x2C: 3, 0x2D: 3, 0x2E: 3, 0x30: 2, 0x31: 2, 0x35: 2, 0x36: 2,
    0x38: 1, 0x39: 3, 0x3D: 3, 0x3E: 3, 0x40: 1, 0x41: 2, 0x45: 2, 0x46: 2,
    0x48: 1, 0x49: 2, 0x4A: 1, 0x4C: 3, 0x4D: 3, 0x4E: 3, 0x50: 2, 0x51: 2,
    0x55: 2, 0x56: 2, 0x58: 1, 0x59: 3, 0x5D: 3, 0x5E: 3, 0x60: 1, 0x61: 2,
    0x65: 2, 0x66: 2, 0x68: 1, 0x69: 2, 0x6A: 1, 0x6C: 3, 0x6D: 3, 0x6E: 3,
    0x70: 2, 0x71: 2, 0x75: 2, 0x76: 2, 0x78: 1, 0x79: 3, 0x7D: 3, 0x7E: 3,
    0x81: 2, 0x84: 2, 0x85: 2, 0x86: 2, 0x88: 1, 0x8A: 1, 0x8C: 3, 0x8D: 3,
    0x8E: 3, 0x90: 2, 0x91: 2, 0x94: 2, 0x95: 2, 0x96: 2, 0x98: 1, 0x99: 3,
    0x9A: 1, 0x9D: 3, 0xA0: 2, 0xA1: 2, 0xA2: 2, 0xA4: 2, 0xA5: 2, 0xA6: 2,
    0xA8: 1, 0xA9: 2, 0xAA: 1, 0xAC: 3, 0xAD: 3, 0xAE: 3, 0xB0: 2, 0xB1: 2,
    0xB4: 2, 0xB5: 2, 0xB6: 2, 0xB8: 1, 0xB9: 3, 0xBA: 1, 0xBC: 3, 0xBD: 3,
    0xBE: 3, 0xC0: 2, 0xC1: 2, 0xC4: 2, 0xC5: 2, 0xC6: 2, 0xC8: 1, 0xC9: 2,
    0xCA: 1, 0xCC: 3, 0xCD: 3, 0xCE: 3, 0xD0: 2, 0xD1: 2, 0xD5: 2, 0xD6: 2,
    0xD8: 1, 0xD9: 3, 0xDD: 3, 0xDE: 3, 0xE0: 2, 0xE1: 2, 0xE4: 2, 0xE5: 2,
    0xE6: 2, 0xE8: 1, 0xE9: 2, 0xEA: 1, 0xEC: 3, 0xED: 3, 0xEE: 3, 0xF0: 2,
    0xF1: 2, 0xF5: 2, 0xF6: 2, 0xF8: 1, 0xF9: 3, 0xFD: 3, 0xFE: 3,
}
_BRANCH = {0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0, 0xF0}


def flow_offsets(d, la, entries):
    """Flow-follow 6502 from entry addresses; return the set of image OFFSETS
    that begin a decoded instruction. Follows branches/JMP-abs/JSR, stops at
    RTS/RTI/BRK/JMP-indirect and undocumented opcodes. Used to anchor table
    scans to code actually reached from init/play (kills data false-positives)."""
    n = len(d)
    seen = set()
    work = [e - la for e in entries]
    while work:
        off = work.pop()
        while 0 <= off < n and off not in seen:
            op = d[off]
            sz = _OP_SIZE.get(op)
            if sz is None:
                break
            seen.add(off)
            if op in _BRANCH:
                rel = d[off + 1] if off + 1 < n else 0
                tgt = off + 2 + (rel - 256 if rel >= 128 else rel)
                if tgt not in seen:
                    work.append(tgt)
                off += sz
            elif op == 0x4C:                     # JMP abs
                off = (d[off + 1] | (d[off + 2] << 8)) - la if off + 2 < n else n
            elif op == 0x20:                     # JSR
                tgt = (d[off + 1] | (d[off + 2] << 8)) - la if off + 2 < n else n
                if 0 <= tgt < n and tgt not in seen:
                    work.append(tgt)
                off += sz
            elif op in (0x60, 0x40, 0x00, 0x6C):  # RTS/RTI/BRK/JMP(ind)
                break
            else:
                off += sz
    return seen


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


class DeenenGrammar:
    """The orderlist grammar, READ FROM THE FILE'S OWN CODE.

    The Deenen replay is not one grammar. Every rip carries its class
    boundaries as immediates in its orderlist-fetch routine, and they differ:
    the pattern threshold is $5F on Ding_van_Charles, $40 on Constant_Runner,
    $6F on After_the_War, $50 on Soldier_of_Light; `$FF` means SEGMENT-ADVANCE
    on the Ding class but RESTART-TO-INDEX-0 on the Constant_Runner class; and
    the note-transpose base is $82 on Ding but $84 on After_the_War
    (`SBC #$80 / CLC / ADC #$FC`).

    Hardcoding Ding's constants (as this parser originally did) decodes any file
    that happens not to exercise the differences and silently mangles the rest —
    Constant_Runner read $43/$4E as pattern indices whose pointers land outside
    the file, and ran away to 500 notes on a voice that really has 44.

    So: disassemble the fetch site and read the immediates. Anything we cannot
    recognise falls back to the Ding constants, which is exactly the previous
    behaviour — this can add fidelity but not take it away.

    Shape (Constant_Runner $13F3, the reference for the reader):
        LDA ord,Y ; CMP #$FE / BEQ stop
                  ; CMP #$FF / BNE + <handler>   handler A9 00 = restart
                  ;                              handler BD .. C9 cap .. 69 step = seg
                  ; CMP #thr / BCC pattern
                  ; CMP #$80 / BCC mid ; SBC #$80 [CLC ADC #imm]  -> note transpose
        mid:      ; CMP #b   / BCC low ; SBC #b                   -> A-transpose
        low:      ; SEC / SBC #b                                  -> loop count

    STATUS -- read but NOT yet consumed by the decoder (2026-07-16)
    --------------------------------------------------------------
    Only `fetch`, `pat_thr` and `ff_mode` are reported here, because only those
    are verified against the real disassembly (Ding $12A6, Constant_Runner
    $13F3, After_the_War $0E94, Soldier_of_Light $0CDC).

    The class chain (A-transpose / loop-count boundaries and their SBC bases) is
    deliberately NOT parsed. A first attempt scanned for `CMP #imm / BCC` + `SBC
    #imm` and produced garbage on the very file it should reproduce exactly —
    Ding came back `loop=$70-$5E` (inverted) because Ding branches with BCS where
    Constant_Runner uses BCC, and the SBC scan caught unrelated instructions. It
    would have altered all four currently-100% files. Parsing it needs a real
    flow-walk of the CMP/BCC/BCS chain, not a byte scan.

    `decode_voice` therefore still uses its hardcoded Ding constants. This class
    is the evidence + the entry point for that work; wiring it up is the next
    step, and it must be validated file-by-file before it replaces anything.
    """

    def __init__(self, d, la):
        self.fetch = None            # the LDA ord,Y site
        self.pat_thr = None          # byte < this is a PATTERN index
        self.ff_mode = None          # 'seg' (advance) | 'restart' (index 0)
        self.read_ok = False
        self._read(d, la)

    def _read(self, d, la):
        # The orderlist fetch: LDA abs,Y immediately followed by CMP #$FE.
        i = None
        for k in range(len(d) - 24):
            if d[k] == 0xB9 and d[k + 3] == 0xC9 and d[k + 4] == 0xFE:
                i = k
                break
        if i is None:
            return
        self.fetch = la + i
        # The $FF test within a few bytes of the $FE test.
        j = None
        for k in range(i + 5, min(i + 14, len(d) - 8)):
            if d[k] == 0xC9 and d[k + 1] == 0xFF:
                j = k
                break
        if j is None:
            return
        # $FF handler: A9 00 -> restart to index 0; LDA abs,X -> segment advance.
        h = j + 4
        if d[h] == 0xA9 and d[h + 1] == 0x00:
            self.ff_mode = 'restart'
        elif d[h] == 0xBD:
            self.ff_mode = 'seg'
        # The class chain: first CMP #imm / BCC after the handler is the
        # pattern threshold. Scan a bounded window so we cannot run into data.
        k = j + 2
        end = min(j + 0x40, len(d) - 3)
        while k < end and not (d[k] == 0xC9 and d[k + 2] == 0x90):
            k += 1
        if k >= end:
            return
        self.pat_thr = d[k + 1]
        self.read_ok = True

    def __repr__(self):
        f = f'${self.fetch:04X}' if self.fetch is not None else 'None'
        t = f'${self.pat_thr:02X}' if self.pat_thr is not None else 'None'
        return (f'<DeenenGrammar fetch={f} pattern<{t} $FF={self.ff_mode} '
                f'read_ok={self.read_ok}>')


class DeenenLocate:
    """Relocation-safe table addresses located by code byte-patterns."""

    def __init__(self, d, la, entries=None):
        self.d, self.la = d, la
        self.dispatch = None
        i = d.find(DISPATCH_SIG)
        if i >= 0:
            self.dispatch = la + i
        # Reachable instruction-start offsets (anchor for the table scans). Seed
        # from init/play (+ dispatch) so scans see real code, not data.
        ents = list(entries or [])
        if self.dispatch is not None:
            ents.append(self.dispatch)
        self.reach = flow_offsets(d, la, ents) if ents else set()
        self.freq_lo = self.freq_hi = None
        self.instr = None
        self.ord_ptr = self.pat_ptr = self.reloc = None
        self.reloc_val = None
        self.subtune_tbl = None
        self.seg_cap = self.seg_step = None      # $FF segment-advance immediates
        self.seg_seed = 0                        # init `ADC #imm` after song*8
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
        # (B)/(C) segment-ptr table (ord) and pattern-ptr table, anchored to
        #   REACHABLE code (kills data false-positives + handles both reloc modes):
        #     ord read : `TAX / LDA seg,X`        (AA BD ll hh)   -- $128D/$0A8A
        #     pat read : `ASL / TAY / LDA pat,Y`  (0A A8 B9 ll hh)-- $12FD/$0AD4
        #   Variant A ("Ding-class") follows each with `[CLC] ADC reloc` ($6D);
        #   Variant B ("Smooth-class") uses absolute pointers -> no ADC, reloc 0.
        reach = self.reach
        n = len(d)

        def _adc_after(off):
            """If the LDA at `off` is followed by [CLC] ADC abs, return that abs
            (the reloc address); else None."""
            j = off + 3
            if j < n and d[j] == 0x18:            # CLC
                j += 1
            if j + 2 < n and d[j] == 0x6D:        # ADC abs
                return self._w(j + 1)
            return None

        def _anchored(pred):
            """Yield reachable offsets satisfying pred(off); if flow-disasm found
            nothing usable, fall back to a global scan."""
            if reach:
                hits = [o for o in reach if pred(o)]
                if hits:
                    return sorted(hits)
            return [o for o in range(n - 4) if pred(o)]

        def _ord_site(o):
            return (d[o] == 0xAA and d[o + 1] == 0xBD
                    and lo_lim <= self._w(o + 2) < hi_lim)

        def _pat_site(o):
            return (d[o] == 0x0A and d[o + 1] == 0xA8 and d[o + 2] == 0xB9
                    and lo_lim <= self._w(o + 3) < hi_lim)

        # pattern table first (its ADC pins the reloc)
        reloc = None
        for o in _anchored(_pat_site):
            self.pat_ptr = self._w(o + 3)
            r = _adc_after(o + 1)                 # LDA is at o+1 (after ASL/TAY)
            if r is not None:
                reloc = r
            break
        # segment/orderlist table; prefer a site that carries the ADC reloc
        ord_hits = _anchored(_ord_site)
        best = None
        for o in ord_hits:
            r = _adc_after(o + 1)                 # LDA is at o+1 (after TAX)
            if r is not None:
                best = (o, r)
                break
            if best is None:
                best = (o, None)
        if best is not None:
            self.ord_ptr = self._w(best[0] + 2)
            if reloc is None:
                reloc = best[1]
        self.reloc = reloc
        # (D) subtune-param table + segment-seed: init `0A 0A 0A 69 imm` computes
        #     song*8 + imm -> the initial segment index (seeds $106C AND indexes
        #     the groove table via `AA BD ll hh`). imm varies per file (Ding $00,
        #     B_A_T $04): read it so decode threads the right first segment.
        i = -1
        for c in _find_all(d, b'\x0a\x0a\x0a\x69'):
            i = c
            self.seg_seed = d[c + 4]
            break
        if i >= 0:
            for j in range(i, min(i + 32, len(d) - 3)):
                if d[j] == 0xAA and d[j + 1] == 0xBD:
                    self.subtune_tbl = self._w(j + 2)
                    break
        # (E) segment-advance handler (the top-level multi-segment $FF). Reads the
        #     cap/step immediates so the decoder can thread the $195C segment table:
        #       CMP #$FF / BNE / LDA seg,X / CMP #cap / BCS / CLC / ADC #step / STA seg,X
        #       C9 FF   D0 rr  BD ll hh   C9 cap  B0 rr  18    69 step   9D ll hh
        for i in _find_all(d, b'\xc9\xff\xd0'):
            if (i + 15 < len(d) and d[i + 4] == 0xBD and d[i + 7] == 0xC9
                    and d[i + 11] == 0x18 and d[i + 12] == 0x69
                    and d[i + 14] == 0x9D):
                self.seg_cap = d[i + 8]
                self.seg_step = d[i + 13]
                break

        if self.reloc is not None:
            off = self.reloc - self.la
            if 0 <= off + 1 < len(d):
                self.reloc_val = self._w(off)
        elif self.ord_ptr is not None and self.pat_ptr is not None:
            self.reloc_val = 0                   # Variant B: absolute pointers

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
    def __init__(self, d, la, subtune=0, h=None):
        self.d, self.la = d, la
        self.subtune = subtune
        self.init_addr = (h or {}).get('init')
        self.play_addr = (h or {}).get('play')
        self._rate_cache = None
        # Seed the flow-disasm with init/play (+ their header JMP targets) so the
        # locate anchors table scans to reachable code.
        entries = []
        if h:
            for a in (h.get('init'), h.get('play')):
                if a:
                    entries.append(a)
                    o = a - la
                    if 0 <= o + 2 < len(d) and d[o] == 0x4C:
                        entries.append(d[o + 1] | (d[o + 2] << 8))
        self.loc = DeenenLocate(d, la, entries)
        # The orderlist grammar, read from THIS file's code (see DeenenGrammar).
        # pat_thr == $40 marks the Jeroen Tel MoN class — the same byte grammar
        # sidm2/mon_parser.py:397-404 already implements for Hawkeye/Cybernoid.
        self.gram = DeenenGrammar(d, la)
        self._fix_selfmod_ord_ptr()

    def _fix_selfmod_ord_ptr(self):
        """Some rips (Zamzara) fetch the per-voice orderlist through a SHARED
        subroutine whose `LDA tbl,y` operand is SELF-MODIFIED per voice from a
        real pointer table, rather than a plain `TAX/LDA abs,X` DeenenLocate's
        generic scan can find directly. That generic scan can false-positive
        on unrelated code with the same byte shape (on Zamzara it landed on an
        SFX-init dispatch table instead of the real per-voice orderlist).

        Detected by finding the two `STA abs` stores that target the fetch
        instruction's OWN operand bytes (`gram.fetch+1`, `gram.fetch+2`) --
        each immediately preceded by `LDA tbl,X` (`BD ll hh`), whose operand
        is the real per-voice pointer table. Verified emulation-side on
        Zamzara: table `$C4AC`, voice*2-indexed (the SAME convention
        `_ord_ptr_for` already uses for segidx=0), three distinct in-image
        pointers ($CE22/$CEBA/$CF3C) -- confirmed a false-positive `$C4B2`
        replaced with the correct `$C4AC`, matching what the fetch site
        actually reads once self-modified."""
        if not (self.gram.read_ok and self.gram.fetch is not None):
            return
        d = self.d
        lo_target, hi_target = self.gram.fetch + 1, self.gram.fetch + 2
        lo_site = d.find(bytes([0x8D, lo_target & 0xFF, (lo_target >> 8) & 0xFF]))
        hi_site = d.find(bytes([0x8D, hi_target & 0xFF, (hi_target >> 8) & 0xFF]))
        if lo_site < 3 or hi_site < 3:
            return
        if d[lo_site - 3] != 0xBD or d[hi_site - 3] != 0xBD:
            return                                       # not LDA abs,X-preceded
        tbl = d[lo_site - 2] | (d[lo_site - 1] << 8)
        tbl_hi = d[hi_site - 2] | (d[hi_site - 1] << 8)
        if tbl_hi != tbl + 1:                              # lo/hi tables must be adjacent
            return
        self.loc.ord_ptr = tbl

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

    def _ord_ptr_for(self, v, segidx):
        """Orderlist pointer for voice v at segment index segidx: the word at
        $195C[voice*2 + segidx] + reloc (the top-level $195C indirection)."""
        idx = (v * 2 + segidx) & 0xFF
        lo = self._u8(self.loc.ord_ptr + idx)
        hi = self._u8(self.loc.ord_ptr + idx + 1)
        return ((lo | (hi << 8)) + (self.loc.reloc_val or 0)) & 0xFFFF

    def _pat_ptr(self, pat):
        lo = self._u8(self.loc.pat_ptr + pat * 2)
        hi = self._u8(self.loc.pat_ptr + pat * 2 + 1)
        return ((lo | (hi << 8)) + (self.loc.reloc_val or 0)) & 0xFFFF

    def _in_image(self, addr):
        return 0 <= addr - self.la < len(self.d)

    def _seg_head_ok(self, ord_ptr):
        """True if this orderlist points in-image and reaches an in-image pattern
        within a few bytes (used to validate a candidate segment index)."""
        if not self._in_image(ord_ptr):
            return False
        oi = 0
        for _ in range(64):
            ob = self._u8(ord_ptr + oi)
            if ob in (0xFE, 0xFF):
                return False
            if ob < 0x5F:
                return self._in_image(self._pat_ptr(ob))
            oi += 1
        return False

    def _segidx0(self):
        """Initial segment index. Init computes subtune*8 + seg_seed, but a few
        sub-variants (B_A_T) lay the song-0 record so that the raw seed walks a
        voice off-image; pick the first candidate whose three voice orderlists all
        validate. Memoized."""
        if getattr(self, '_seg0_cache', None) is not None:
            return self._seg0_cache
        base = (self.subtune * 8) & 0xFF
        seed = self.loc.seg_seed
        # segidx0 is the per-voice SEGMENT BASE cell ($0CAC-class), which the init
        # zeroes -> 0 for subtune 0. The `0A0A0A 69 imm` immediate we read into
        # seg_seed is the SUBTUNE-table index (song*8+imm), NOT the segment base
        # (emulator-confirmed on B_A_T: seed=4 there, but the real segment base is
        # 0). So try 0/base BEFORE the seed-derived candidates.
        cands = list(dict.fromkeys([base, 0, (base + seed) & 0xFF, seed & 0xFF]))
        chosen = cands[0]
        for s0 in cands:
            if all(self._seg_head_ok(self._ord_ptr_for(v, s0)) for v in range(3)):
                chosen = s0
                break
        self._seg0_cache = chosen
        return chosen

    def _parse_row(self, pat, pi, st):
        """Decode ONE pattern row starting at byte index pi, mirroring the 6502
        row parser ($131D-$1494). Mutates the state dict st (note_transpose,
        a_transpose, cur_instr, cur_dur). Returns (next_pi, event_or_None):
          event None + next_pi==pi  -> pattern end ($FF)
          event kind 'note'/'rest'  -> onset / rest of `frames` advance-ticks."""
        u8 = self._u8
        y = pi
        b = u8(pat + y)                                  # $1320
        if b < 0x60:                                     # $1324 -> $1406 bare note
            return y + 1, self._emit_note(b, st)
        if b == 0xFF:                                    # pattern end
            return pi, None
        if b == 0xFE:                                    # $1347 set speed
            y += 1                                       # speed param ($1957)
            y += 1
            b = u8(pat + y)                              # note candidate ($07)
        if b == 0xFD:                                    # $1356 slide -> note
            y += 1                                       # $10BF param
            y += 1
            b = u8(pat + y)                              # note ($07)
            y += 1                                       # slide target ($10BC)
            return y + 1, self._emit_note(b, st)
        # $1372 -> $1379: FC / FB gate commands
        if b == 0xFC:                                    # $1379
            y += 1                                       # $1009 param
            y += 1
            b = u8(pat + y)
        if b == 0xFB:                                    # $1388
            y += 1
            b = u8(pat + y)
        if b >= 0xE0:                                    # $1398 REST (holds b-$E1+1)
            return y + 1, dict(kind='rest', frames=((b - 0xE1) & 0xFF) + 1)
        if b >= 0xC0:                                    # $13BB instrument $C0-$DF
            st['cur_instr'] = (b - 0xC0 + st['a_transpose']) & 0xFF
            y += 1
            b = u8(pat + y)                              # $13C9
            if b == 0xFD:                                # $13CB -> slide ($135A)
                y += 1
                y += 1
                b = u8(pat + y)
                y += 1
                return y + 1, self._emit_note(b, st)
        if b >= 0x80:                                    # $13D6 default duration
            st['cur_dur'] = (b - 0x81) & 0xFF
            while True:                                  # accumulate $80-$FF chain
                y += 1
                b = u8(pat + y)                          # $13DE
                if b == 0xFD:                            # $13E0 -> slide
                    y += 1
                    y += 1
                    b = u8(pat + y)
                    y += 1
                    return y + 1, self._emit_note(b, st)
                if b < 0x80:                             # $13E7 done accumulating
                    break
                st['cur_dur'] = (st['cur_dur'] + (b - 0x80)) & 0xFF
        if b >= 0x60:                                    # $13FA arp param $60-$7F
            y += 1
            b = u8(pat + y)                              # $1402
        return y + 1, self._emit_note(b, st)             # $1406 note

    def _parse_row_zamzara(self, pat, pi, st):
        """Decode ONE pattern row for the Zamzara-class row grammar
        ($BE88-$BF9F on Zamzara.sid, dispatch $BE8A), routed via
        `_is_zamzara_row_class()`. Verified byte-for-byte against a live py65
        trace 2026-07-16 (captured row `FE F4 C3 A0 A0 76 1A` = filter-write,
        instrument, duration x2, arp, note -- decodes to exactly 7 bytes,
        matching the emulator's own $e9,X advance count for that row).

        Differs from Ding's `_parse_row`: the arp threshold is $70 (not $60);
        $FE writes the SID filter register ($D417) directly instead of staging
        a zero-page shadow (not modelled -- Driver 11 has no per-row filter
        write path yet); duration accumulation is RE-ENTRANT (an overflow byte
        re-enters the top-level dispatch, not a simple linear loop) but nets
        the same shape as long as $FD can appear mid-accumulate; the $FD slide
        consumes exactly 2 bytes (a first param, structurally skipped, and a
        second byte that is BOTH the slide target and -- unmodified -- the
        note that follows), one fewer than Ding's 3-byte slide encoding."""
        u8 = self._u8
        y = pi
        b = u8(pat + y)
        if b == 0xFF:                                     # pattern end
            return pi, None
        if b < 0x60:                                       # bare note
            return y + 1, self._emit_note(b, st)
        if b == 0xFD:                                       # slide -> note
            y += 1                                          # param (structurally skipped)
            y += 1                                          # 2nd byte: slide target AND the note
            b = u8(pat + y)
            return y + 1, self._emit_note(b, st)
        if b == 0xFE:                                       # filter write -> $D417 (not modelled)
            y += 1                                          # filter value (skipped)
            y += 1
            b = u8(pat + y)
        elif b == 0xFC:                                      # gate/unknown param
            y += 1
            y += 1
            b = u8(pat + y)
        if b >= 0xE0:                                        # rest
            return y + 1, dict(kind='rest', frames=((b - 0xE1) & 0xFF) + 1)
        if b >= 0xC0:                                        # instrument
            st['cur_instr'] = (b - 0xC0) & 0xFF
            y += 1
            b = u8(pat + y)
        if b >= 0x80:                                        # duration, re-entrant accumulate
            st['cur_dur'] = (b - 0x81) & 0xFF
            while True:
                y += 1
                b = u8(pat + y)
                if b == 0xFD:                                # slide can interrupt accumulation
                    y += 1
                    b = u8(pat + y)
                    return y + 1, self._emit_note(b, st)
                if b < 0x80:
                    break
                st['cur_dur'] = (st['cur_dur'] + (b - 0x80)) & 0xFF
        if b >= 0x70:                                        # arp param (Ding's threshold is $60)
            y += 1
            b = u8(pat + y)
        return y + 1, self._emit_note(b, st)

    def _is_zamzara_row_class(self):
        """True if this rip uses the Zamzara-class row grammar, not Ding's.
        Detected by a direct `STA $D417` (8D 17 D4) within the row dispatch's
        own code window -- Zamzara's $FE handler pokes the SID filter register
        straight from the row parser, which no Ding-class file does (checked
        against the whole SID/deenen corpus 2026-07-16: False on every
        currently-decoding file, True only on Zamzara + Smooth_Criminal)."""
        if self.loc.dispatch is None:
            return False
        off = self.loc.dispatch - self.la
        window = self.d[off:off + 0x120]
        return bytes([0x8D, 0x17, 0xD4]) in window

    def _emit_note(self, b, st):
        note = (b + st['note_transpose']) & 0xFF
        return dict(kind='note', frames=(st['cur_dur'] + 1) & 0xFF,
                    note=note, instr=st['cur_instr'], freq=self._freq(note))

    def decode_voice(self, v, max_rows=8000, stop_on_loop=False):
        """Walk voice v's two-level song (segment table -> orderlist -> patterns
        -> rows), threading the top-level multi-segment $195C indirection. Returns
        a list of events dict(kind='note'|'rest', frames, note=?, instr=?, freq=?).

        Segment threading mirrors init + the $FF handler ($1288/$12B0): segidx
        starts at subtune*8; the orderlist $FF advances segidx by `seg_step` while
        segidx < `seg_cap` (re-selecting $195C[voice*2+segidx]); once segidx>=cap
        (or no handler was located) $FF loops the current segment. Orderlist $6F-$7F
        loop counts replay the following pattern (count+1) times ($10DE)."""
        st = dict(note_transpose=0, a_transpose=0, cur_instr=0, cur_dur=0)
        events = []
        # Route by the grammar this file's own code declares. pat_thr == $40 is
        # the Jeroen Tel MoN class; anything else keeps the Ding-class path that
        # the 4 current clean wins were measured on.
        tel = (self.gram.read_ok and self.gram.pat_thr == 0x40
               and self.gram.ff_mode == 'restart')
        row_parser = (self._parse_row_zamzara if self._is_zamzara_row_class()
                      else self._parse_row)
        segidx = self._segidx0()
        ord_ptr = self._ord_ptr_for(v, segidx)
        oi = 0
        pending_loop = 0
        guard = 0
        seg_loops = 0
        visited = {segidx}                               # for stop_on_loop
        while len(events) < max_rows and guard < 40000:
            guard += 1
            ob = self._u8(ord_ptr + oi)
            if ob == 0xFE:                               # $12A9 stop song
                break
            if ob == 0xFF:
                if tel:
                    # Tel class ($13FA): $FF is RESTART TO INDEX 0, not a segment
                    # advance — LDA #$00 / STA $d7,X. Without this the Ding path
                    # ran away (Constant_Runner v2: 500 notes for a real 44).
                    if stop_on_loop:
                        break                            # one pass -> song end
                    seg_loops += 1
                    if seg_loops > 6000:
                        break
                    oi = 0
                    pending_loop = 0
                    continue
                # $12B0 segment advance (Ding class)
                if (self.loc.seg_cap is not None and self.loc.seg_step is not None
                        and segidx < self.loc.seg_cap):
                    segidx = (segidx + self.loc.seg_step) & 0xFF
                else:
                    if stop_on_loop:
                        break                            # segment loops -> song end
                    seg_loops += 1
                    if seg_loops > 6000:
                        break                            # looping tail -> stop
                if stop_on_loop and segidx in visited:
                    break                                # one song pass -> stop
                visited.add(segidx)
                ord_ptr = self._ord_ptr_for(v, segidx)
                oi = 0
                pending_loop = 0
                continue
            if tel:
                # Jeroen Tel MoN classes, verified two ways: Constant_Runner's
                # $13F3 routine (SEC/SBC #$40 -> $e0,X with DEC $e0,X at $145B =
                # the repeat counter; SBC #$60 -> $dd,X; SBC #$80 -> $da,X), and
                # sidm2/mon_parser.py:397-404, which already ships this grammar.
                if ob >= 0x80:                           # transpose
                    nt = (ob - 0x80) & 0xFF
                    st['note_transpose'] = nt - 0x100 if nt >= 0x80 else nt
                    oi += 1
                    continue
                if ob >= 0x60:                           # instrument / A-transpose
                    st['a_transpose'] = ob - 0x60
                    oi += 1
                    continue
                if ob >= 0x40:                           # pattern-REPEAT count
                    pending_loop = (ob & 0x3F) & 0xFF
                    oi += 1
                    continue
                # else: pattern index (< $40)
            else:
                if 0x5F <= ob <= 0x6E:                   # $12D7 A-transpose
                    st['a_transpose'] = ob - 0x5F
                    oi += 1
                    continue
                if 0x6F <= ob <= 0x7F:                   # $12F2 pattern-loop count
                    pending_loop = (ob - 0x70) & 0xFF
                    oi += 1
                    continue
                if 0x80 <= ob <= 0xFD:                   # $12E5 note-transpose
                    nt = (ob - 0x82) & 0xFF
                    st['note_transpose'] = nt - 0x100 if nt >= 0x80 else nt
                    oi += 1
                    continue
                # else: pattern index (< $5F)
            pat = self._pat_ptr(ob)
            plays = (pending_loop & 0xFF) + 1
            pending_loop = 0
            for _ in range(plays):
                pi = 0
                pguard = 0
                while pguard < 8192 and len(events) < max_rows:
                    pguard += 1
                    npi, ev = row_parser(pat, pi, st)
                    if ev is None:
                        break                            # pattern end ($FF)
                    events.append(ev)
                    pi = npi
                if len(events) >= max_rows:
                    break
            oi += 1
        return events

    def p106b(self):
        """The groove/tempo divisor ($106B), read from the subtune table (byte 0
        of the subtune*8 record). Defaults to 1 when the table isn't located."""
        if self.loc.subtune_tbl is None:
            return 1
        idx = self.subtune * 8 + self.loc.seg_seed
        return self._u8(self.loc.subtune_tbl + idx) or 1

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

    def _emulate_onsets(self, frames=1500):
        """Run the real player (py65) init + `frames` play calls; return per-voice
        [(onset_frame, freq)] gate-rise onsets. Lazy py65 import -> [] if absent.
        This is the ground-truth used ONLY to measure the per-file groove rate;
        the note/pitch content itself comes from the static decoder."""
        if self.init_addr is None or self.play_addr is None:
            return None
        try:
            from py65.devices.mpu6502 import MPU
        except Exception:
            return None
        d, la = self.d, self.la

        class Mem:
            def __init__(s):
                s.m = bytearray(0x10000)
            def __len__(s):
                return len(s.m)
            def __getitem__(s, a):
                return s.m[a]
            def __setitem__(s, a, v):
                if isinstance(a, slice):
                    s.m[a] = v
                else:
                    s.m[a] = v & 0xFF

        mem = Mem()
        mem.m[la:la + len(d)] = d
        mem.m[1] = 0x37
        mpu = MPU(memory=mem)

        def call(addr):
            mpu.a = 0
            mpu.pc = addr
            mpu.sp = 0xFF
            # cap well above any single init/play frame; IRQ players (play=$0000)
            # or ones that never RTS to top SP hit the cap instead of hanging.
            for _ in range(60000):
                if mem.m[mpu.pc] == 0x60 and mpu.sp >= 0xFF:
                    break
                mpu.step()

        # IRQ-driven replays (play at $0000 / not a callable subroutine) can't be
        # frame-stepped this way -> skip (caller falls back to advance_schedule).
        if not (self.la <= self.play_addr < self.la + len(d)):
            return None
        call(self.init_addr)
        onsets = [[], [], []]
        prev = [0, 0, 0]
        for fr in range(frames):
            call(self.play_addr)
            for v in range(3):
                g = mem.m[0xD404 + v * 7] & 1
                if g and not prev[v]:
                    f = mem.m[0xD400 + v * 7] | (mem.m[0xD401 + v * 7] << 8)
                    onsets[v].append((fr, f))
                prev[v] = g
        return onsets

    # Candidate groove rates (real frames per decoder TICK). The Deenen tempo is
    # always one of a few small rationals (measured: 2, 2.5, 3; higher for the
    # multispeed/relocated variants).
    _RATE_CANDS = (1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0)

    def groove_rate(self, frames=1000, window=900):
        """Real frames per decoder note-duration TICK. The groove rate is the one
        global scalar that maps the decoder's tick clock onto the real (emulated)
        frame clock; measured by picking, over a small candidate set, the R whose
        uniform schedule (frame = R*tick) best aligns the decoder's onset stream to
        the real gate-rise stream under a monotonic 1-1 match (a single scalar can
        only align hundreds of onsets at the true tempo, so this is a measurement,
        not an overfit). Emulation-based (py65); 0.0 if unmeasurable -> caller falls
        back to advance_schedule. Cached."""
        if self._rate_cache is not None:
            return self._rate_cache
        self._rate_cache = 0.0
        onsets = self._emulate_onsets(frames)
        if not onsets:
            return 0.0
        from sidm2.fidelity_common import freq_to_semi
        real = [sorted((f, freq_to_semi(fr) % 12) for f, fr in onsets[v] if f < window)
                for v in range(3)]
        if sum(len(r) for r in real) < 12:
            return 0.0
        decoded = [[(t, freq_to_semi(e['freq']) % 12)
                    for t, e in self._voice_ticks(v)] for v in range(3)]

        def align(myl, rl, so, tol=4):
            i = j = hits = 0
            while i < len(myl) and j < len(rl):
                pf, ps = myl[i]
                rf, rs = rl[j]
                if abs(pf - rf) <= tol:
                    if (ps + so) % 12 == rs:
                        hits += 1
                    i += 1
                    j += 1
                elif pf < rf - tol:
                    i += 1
                else:
                    j += 1
            return hits

        best = (-1, 0.0)
        for R in self._RATE_CANDS:
            myl = [sorted((round(R * t), pc) for t, pc in decoded[v]
                          if R * t < window) for v in range(3)]
            for so in range(-3, 4):
                tot = sum(align(myl[v], real[v], so) for v in range(3))
                if tot > best[0]:
                    best = (tot, R)
        self._rate_cache = best[1]
        return self._rate_cache

    def _voice_ticks(self, v, max_rows=4000):
        """decode_voice(v) as [(cumulative_tick_before_note, event)] for notes."""
        out = []
        t = 0
        for e in self.decode_voice(v, max_rows=max_rows):
            if e['kind'] == 'note':
                out.append((t, e))
            t += e['frames']
        return out

    def groove_schedule(self, nframes=4000):
        """Uniform advance schedule tick->frame using the emulation-measured
        groove_rate(); falls back to advance_schedule() when the rate can't be
        measured (no py65 / degenerate)."""
        r = self.groove_rate()
        if r and r > 0:
            return [round(r * t) for t in range(nframes)]
        return self.advance_schedule(nframes)

    def plausible(self):
        """Reject the mis-located / wrong-reloc decodes that DeenenLocate.ok()
        can't see: a decode where one (note,frames) pair dominates a voice is
        reading filler (Variant-B absolute-pointer files whose reloc we can't pin
        -- Eye_to_Eye reads all note $06, Zamzara all note $00). Cheap: a short
        one-pass sample per voice. Returns False on any degenerate voice."""
        from collections import Counter
        # Tel-class ($40) files: their ORDERLIST grammar is decoded now and the
        # structure comes out exact (Constant_Runner's note counts match the real
        # player on all three voices: 113/101/44). But their PATTERN-ROW grammar
        # is still the Deenen one and is demonstrably wrong -- pitch 35.6%. A
        # structurally-perfect decode with wrong pitches is precisely the lossy
        # output this project does not ship silently, and plausible() is
        # structural so it cannot see it. Refuse until the rows are ported
        # (sidm2/mon_parser.py already has that grammar too -- see DEENEN.md).
        if (self.gram.read_ok and self.gram.pat_thr == 0x40
                and self.gram.ff_mode == 'restart'):
            return False
        degenerate = False
        any_notes = False
        counts = []
        for v in range(3):
            notes = [e for e in self.decode_voice(v, max_rows=500)
                     if e['kind'] == 'note']
            counts.append(len(notes))
            if len(notes) < 8:
                continue
            any_notes = True
            top = Counter((e['note'], e['frames']) for e in notes).most_common(1)
            if top and top[0][1] / len(notes) > 0.85:
                degenerate = True
        # A dead voice (0 notes) beside a busy one is a broken decode -- the ord
        # table / reloc is wrong for that voice (Mr_Heli v0=0 while v1/v2 play).
        # No genuine 3-voice Deenen tune leaves a whole voice empty.
        if any(c == 0 for c in counts) and any(c > 20 for c in counts):
            return False
        return any_notes and not degenerate

    def voice_onsets(self, v, sched=None):
        """-> [(onset_frame, note_index)] for retriggered notes, mapped through
        the groove clock (advance-tick -> real frame)."""
        if sched is None:
            sched = self.groove_schedule()
        tick = 0
        out = []
        for e in self.decode_voice(v):
            if e['kind'] == 'note' and tick < len(sched):
                out.append((sched[tick], e['note']))
            tick += e['frames']
        return out
